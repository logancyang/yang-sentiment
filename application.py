import logging
import time
import json
from datetime import datetime
from flask import Flask, render_template, Response, stream_with_context
from flask_sqlalchemy import SQLAlchemy
from pytz import timezone
from sqlalchemy.sql import text
from sqlitedict import SqliteDict

from constants import YANG_TERM
from learning.regression import linear_regression
from models import Tweet, Price
from queries import (
    query_last_n, query_tweet_count, get_eastern_date_today,
    query_count_6hr_at_5min, query_count_14d_at_1d
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
def btccount():
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
    top_retweet_ids = ["1164295013423091712", "1164886394407444480"]
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
    return _tweets_chart_request(chart_type='6hr_at_5min')


# pylint: disable=no-member
@app.route('/tweets_daily_chart')
def tweets_daily_chart():
    """
    Get the counts of tweets for the last 14 days at 1 day granularity
    A total 14 data points including today
    """
    return _tweets_chart_request(chart_type='14d_at_1d')


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
    elif chart_type == '6hr_at_5min':
        query = query_count_6hr_at_5min(
            track_term, count_colname=count_colname, interval_colname=interval_colname)
        # logging.info(f"[6hr_at_5min SQL]: {query}\n\n")
    else:
        raise Exception(f"chart_type is not supported: {chart_type} ")

    try:
        with SqliteDict('./cache.sqlite') as cache:
            if query not in cache:
                logging.info(f"Cache MISS: {query}\n\n")
                counts_raw = db.session.query(
                    interval_colname, count_colname).from_statement(text(query)).all()
                db.session.commit()
                cache[query] = counts_raw
                cache.commit()
            else:
                logging.info(f"Cache HIT: {query}\n\n")
                counts_raw = cache[query]
        # Deploy the following line to staging if there's a date discrepancy at remote
        # logging.info(f"[Query RESULT]: {counts_raw}\n\n")
        timestamps, counts_data = _convert_counts_interval_data(counts_raw)
        # trend_y_list: list of predicted value, trend: bool whether positive
        trend_y_list, trend = linear_regression(X=timestamps, y=counts_data)
        resp_dict = {
            'timestamps': timestamps,
            'counts': counts_data,
            'trendline': trend_y_list,
            'trend': trend
        }
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
            if len(cache) >= 40:
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


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=PORT, threaded=True)
