import logging
import time
import json
import pickle
from datetime import datetime
from io import BytesIO
from pytz import timezone
from sqlalchemy.sql import text

from constants import YANG_TERM
from learning.regression import linear_regression
from location_utils import map_raw_to_states
from redisclient import r as cache
from models import Tweet, Price, Database
from nlp.wordcloud_gen import generate_wordcloud
from queries import (
    query_last_n, query_tweet_count, get_eastern_date_today,
    query_count_nhr_at_xmin, query_count_14d_at_1d, query_retweet_count,
    query_count_group_by_location, query_all_tweets
)
from settings import PORT, DB_USER, DB_PASSWORD, RDS_POSTGRES_ENDPOINT, DB_NAME
from sqlalchemy.orm import sessionmaker, scoped_session


class DataJob:
    db = Database(env='prod')
    Session = scoped_session(sessionmaker(bind=db.engine))
    Session.subtransactions = True


class ScheduledJob(DataJob):

    # pylint: disable=logging-fstring-interpolation
    @classmethod
    def get_top_retweets(cls):
        """Top retweeted tweet ids, refresh every 30min based on the query granularity"""
        colname = "retweeted_status_id_str"
        # Return top 10 retweeted tweet ids
        query = query_retweet_count(colname, top_n=20)
        top_retweet_ids = []

        if not cache.get(query):
            logging.info(f"Cache MISS: {query}")
            top_retweet_ids_raw = cls.Session.query(colname).from_statement(text(query)).all()
            top_retweet_ids = [tup[0] for tup in top_retweet_ids_raw]
            cls.Session.commit()
            cache.set(query, json.dumps(top_retweet_ids))
        else:
            logging.info(f"Cache HIT: {query}")
            top_retweet_ids = json.loads(cache.get(query))

        return top_retweet_ids


    """Charts"""

    @classmethod
    def tweets_chart_request(cls, chart_type, track_term=YANG_TERM):
        count_colname = 'count'
        interval_colname = 'interval'
        query = None
        if chart_type == '14d_at_1d':
            query = query_count_14d_at_1d(
                track_term, count_colname=count_colname, interval_colname=interval_colname)
            # logging.info(f"[14d_at_1d SQL]: {query}")
        elif chart_type == '72hr_at_1hr':
            query = query_count_nhr_at_xmin(
                n_hours=72, x_mins=60, track_term=track_term,
                count_colname=count_colname, interval_colname=interval_colname)
            # logging.info(f"[72hr_at_1hr SQL]: {query}\n\n")
        elif chart_type == '72h_for_loc':
            interval_colname = 'location'
            query = query_count_group_by_location(
                track_term, colname=interval_colname)
            # logging.info(f"[72h_for_loc SQL]: {query}\n\n")
        else:
            raise Exception(f"chart_type is not supported: {chart_type} ")

        # Query db, postprocess, cache.set(query, postprocessed)
        resp_dict = {}
        try:
            if not cache.get(query):
                logging.info(f"Cache MISS: {query}")
                counts_raw = cls.Session.query(
                    interval_colname, count_colname).from_statement(text(query)).all()
                cls.Session.commit()
                resp_dict = _postprocess_chart_data(counts_raw, chart_type)
                cache.set(query, json.dumps(resp_dict))
            else:
                logging.info(f"Cache HIT: {query}")
                resp_dict = json.loads(cache.get(query))
            # Deploy the following line to staging if there's a date discrepancy at remote
            # logging.info(f"[{chart_type} Query RESULT]: {counts_raw}\n\n")

            return resp_dict
        except Exception as e:
            logging.error(
                f"An unexpected exception occurred during {chart_type} chart request: {e}\n")
        finally:
            if len(cache.keys()) >= 400:
                cache.flushall()
            cls.Session.close()

    """Sentiment"""

    @classmethod
    def get_wordcloud(cls):
        """
        Get the word cloud for tweets in the last 6 hours
        """
        # Query tweets in the last 6 hours, refresh at 1 hour
        # Cache the generated image
        query = query_all_tweets()

        if not cache.get(query):
            logging.info(f"Cache MISS: {query}")
            tweets = cls.Session.query('tweet_text').from_statement(text(query)).all()
            cls.Session.commit()
            logging.info(f"Wordcloud query completed.")
            wc = generate_wordcloud(tweets)
            logging.info(f"Wordcloud generation completed.")
            img = BytesIO()
            wc.to_image().save(img, 'PNG')
            imgp = pickle.dumps(img)
            cache.set(query, imgp)
        else:
            logging.info(f"Cache HIT: {query}")
            img = pickle.loads(cache.get(query))

        return img


class StreamJob(DataJob):
    @classmethod
    def count_stream(cls, track_term):
        while True:
            try:
                query = query_tweet_count(
                    track_term=track_term, created_date=get_eastern_date_today())
                # Note: if this returns empty result, log the query on server to check
                # if time in the query is wrong. Server time and local time are different
                # so it can create unexpected bugs
                count = cls.Session.query(
                    'tweet_count').from_statement(text(query)).first()
                if count:
                    yield f"data:{str(count[0])}\n\n"
                else:
                    logging.error(
                        f"Tweet count stream returned empty result unexpectedly.")
                cls.Session.commit()
                time.sleep(5)
            except Exception as e:
                logging.error(
                    f"An unexpected exception occurred during streaming: {e}\n")
            finally:
                cls.Session.close()

    @classmethod
    def latest_tweet_stream(cls, n):
        while True:
            try:
                query = query_last_n(Tweet.__tablename__, n, track_term=YANG_TERM)

                latest_tweet_objects = cls.Session.query(Tweet).from_statement(
                    text(query))
                if latest_tweet_objects:
                    latest_tweets_objs_list = latest_tweet_objects.all()
                    latest_tweets_list = [
                        obj.tweet_text for obj in latest_tweets_objs_list]
                    yield f"data:{json.dumps(latest_tweets_list)}\n\n"
                else:
                    logging.error(
                        f"Lastest tweets stream returned empty result unexpectedly.")
                cls.Session.commit()
                time.sleep(5)
            except Exception as e:
                logging.error(
                    f"An exception occurred during query to RDS Postgres: {e}\n")
            finally:
                cls.Session.close()


"""Helpers"""


def _convert_counts_interval_data(counts_raw_list):
    timestamps = []
    counts_data = []
    for interval, count in counts_raw_list:
        if isinstance(interval, str):
            interval_dt = datetime.strptime(interval, '%Y-%m-%d')
            interval_dt_tzlocal = timezone('US/Eastern').localize(interval_dt)
            timestamps.append(interval_dt_tzlocal.timestamp())
            counts_data.append(count)
        elif isinstance(interval, datetime):
            # Note that datetime must be localized!! datetime by itself has no timezone!
            interval_dt_tzlocal = timezone('US/Eastern').localize(interval)
            timestamps.append(interval_dt_tzlocal.timestamp())
            counts_data.append(count)
        else:
            raise Exception(f"Invalid interval object provided.")
    return timestamps, counts_data


def _get_counts_by_states(counts_raw):
    state_hist, state_map = map_raw_to_states(counts_raw)
    state, count = zip(*state_hist)
    return state, count


def _postprocess_chart_data(counts_raw, chart_type):
    resp_dict = {}
    if chart_type == '72h_for_loc':
        # Note that less than 10% users have location, and in the 10%, the majority are either
        # outside of US or use inaccurate info such as 'earth' or 'usa'.
        states, counts = _get_counts_by_states(counts_raw)
        resp_dict = {
            'xticks': states,
            'counts': counts
        }
    elif chart_type == '14d_at_1d' or chart_type == '72hr_at_1hr':
        timestamps, counts_data = _convert_counts_interval_data(counts_raw)
        # trend_y_list: list of predicted value, trend: 0 for insignif, 1 for positive, -1 for negative
        trend_y_list, trend = linear_regression(X=timestamps, y=counts_data)
        resp_dict = {
            'timestamps': timestamps,
            'counts': counts_data,
            'trendline': trend_y_list,
            'trend': trend
        }
    return resp_dict
