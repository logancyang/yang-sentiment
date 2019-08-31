import logging
import time
import json
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from flask import Flask, render_template, Response, stream_with_context
from flask_sqlalchemy import SQLAlchemy
from pytz import timezone
from sqlalchemy.sql import text
from sqlitedict import SqliteDict

from constants import YANG_TERM
from learning.regression import linear_regression
from location_utils import map_raw_to_states
from models import Tweet, Price
from queries import (
    query_last_n, query_tweet_count, get_eastern_date_today,
    query_count_nhr_at_xmin, query_count_14d_at_1d, query_retweet_count,
    query_count_group_by_location
)
from settings import PORT, DB_USER, DB_PASSWORD, RDS_POSTGRES_ENDPOINT, DB_NAME


# pylint: disable=logging-fstring-interpolation
# AWS Beanstalk needs it to be named 'application', and file 'application.py'
application = app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{RDS_POSTGRES_ENDPOINT}:5432/{DB_NAME}"
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# CONFIG = Config.from_file('config_prod.yml')
# CONFIG.init_app(app)
db = SQLAlchemy(app)


"""
View Functions
"""


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/yangcount')
def yangcount():
    return Response(
        stream_with_context(_count_stream(YANG_TERM)),
        mimetype='text/event-stream'
    )


@app.route('/latest_tweets')
def latest_tweets():
    return Response(
        stream_with_context(_latest_tweet_stream(n=5)),
        mimetype='text/event-stream'
    )


@app.route('/top_retweets')
def top_retweets():
    """Top retweeted tweet ids, refresh every 30min based on the query granularity"""
    colname = "retweeted_status_id_str"
    # Return top 10 retweeted tweet ids
    query = query_retweet_count(colname, top_n=10)
    top_retweet_ids = []

    with SqliteDict('./cache.sqlite') as cache:
        if query not in cache:
            logging.info(f"Cache MISS: {query}")
            top_retweet_ids_raw = db.session.query(colname).from_statement(text(query)).all()
            top_retweet_ids = [tup[0] for tup in top_retweet_ids_raw]
            db.session.commit()
            cache[query] = top_retweet_ids
            cache.commit()
        else:
            logging.info(f"Cache HIT: {query}")
            top_retweet_ids = cache[query]

    response = app.response_class(
            response=json.dumps(top_retweet_ids),
            status=200,
            mimetype='application/json'
        )
    return response


"""Charts"""


@app.route('/tweets_min_chart')
def tweets_min_chart():
    """
    Get the counts of tweets for the last 6hr at 5min granularity
    A total 72 data points - the last 5 min = 71 data points
    """
    return _tweets_chart_request(chart_type='72hr_at_1hr')


# pylint: disable=no-member
@app.route('/tweets_daily_chart')
def tweets_daily_chart():
    """
    Get the counts of tweets for the last 14 days at 1 day granularity
    A total 14 data points including today
    """
    return _tweets_chart_request(chart_type='14d_at_1d')


@app.route('/tweets_loc_chart')
def tweets_loc_chart():
    """
    Get the counts of tweets for the last 14 days at 1 day granularity
    A total 14 data points including today
    """
    return _tweets_chart_request(chart_type='14d_for_loc')


"""Helpers"""


def _count_stream(track_term):
    while True:
        try:
            query = query_tweet_count(
                track_term=track_term, created_date=get_eastern_date_today())
            # Note: if this returns empty result, log the query on server to check
            # if time in the query is wrong. Server time and local time are different
            # so it can create unexpected bugs
            count = db.session.query(
                'tweet_count').from_statement(text(query)).first()
            if count:
                yield f"data:{str(count[0])}\n\n"
            else:
                logging.error(
                    f"Tweet count stream returned empty result unexpectedly.")
            db.session.commit()
            time.sleep(5)
        except Exception as e:
            logging.error(
                f"An unexpected exception occurred during streaming: {e}\n")
        finally:
            db.session.close()


def _latest_tweet_stream(n):
    while True:
        try:
            query = query_last_n(Tweet.__tablename__, n, track_term=YANG_TERM)

            latest_tweet_objects = db.session.query(Tweet).from_statement(
                text(query))
            if latest_tweet_objects:
                latest_tweets_objs_list = latest_tweet_objects.all()
                latest_tweets_list = [
                    obj.tweet_text for obj in latest_tweets_objs_list]
                yield f"data:{json.dumps(latest_tweets_list)}\n\n"
            else:
                logging.error(
                    f"Lastest tweets stream returned empty result unexpectedly.")
            db.session.commit()
            time.sleep(5)
        except Exception as e:
            logging.error(
                f"An exception occurred during query to RDS Postgres: {e}\n")
        finally:
            db.session.close()


def _tweets_chart_request(chart_type, track_term=YANG_TERM):
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
    elif chart_type == '14d_for_loc':
        interval_colname = 'location'
        query = query_count_group_by_location(
            track_term, count_colname=count_colname, interval_colname=interval_colname)
        # logging.info(f"[14d_for_loc SQL]: {query}\n\n")
    else:
        raise Exception(f"chart_type is not supported: {chart_type} ")

    # Query db, postprocess, cache[query] = postprocessed
    resp_dict = {}
    try:
        with SqliteDict('./cache.sqlite') as cache:
            if query not in cache:
                logging.info(f"Cache MISS: {query}")
                counts_raw = db.session.query(
                    interval_colname, count_colname).from_statement(text(query)).all()
                db.session.commit()
                resp_dict = _postprocess_chart_data(counts_raw, chart_type)
                cache[query] = resp_dict
                cache.commit()
            else:
                logging.info(f"Cache HIT: {query}")
                resp_dict = cache[query]
        # Deploy the following line to staging if there's a date discrepancy at remote
        # logging.info(f"[{chart_type} Query RESULT]: {counts_raw}\n\n")

        response = app.response_class(
            response=json.dumps(resp_dict),
            status=200,
            mimetype='application/json'
        )
        return response
    except Exception as e:
        logging.error(
            f"An unexpected exception occurred during {chart_type} chart request: {e}\n")
    finally:
        with SqliteDict('./cache.sqlite') as cache:
            if len(cache) >= 400:
                cache.clear()
        db.session.close()


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
    if chart_type == '14d_for_loc':
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


def cache_in_advance():
    while True:
        _tweets_chart_request(chart_type='14d_at_1d')
        _tweets_chart_request(chart_type='72hr_at_1hr')
        _tweets_chart_request(chart_type='14d_for_loc')
        top_retweets()
        logging.info(f"Advance caching executed at {datetime.now()}")
        time.sleep(10 * 60)


# sched = BackgroundScheduler(daemon=True)
# sched.add_job(cache_in_advance, 'interval', minutes=10)
# sched.start()


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=PORT, threaded=True)
