import logging
import time
import json
from flask import Flask, render_template, Response, stream_with_context, send_file
from flask_sqlalchemy import SQLAlchemy

from constants import YANG_TERM
from query_funcs import (
    get_top_retweets, tweets_chart_request, query_all_tweets,
    count_stream, latest_tweet_stream, get_wordcloud
)
from settings import PORT, DB_USER, DB_PASSWORD, RDS_POSTGRES_ENDPOINT, DB_NAME


# pylint: disable=logging-fstring-interpolation
# AWS Beanstalk needs it to be named 'application', and file 'application.py'
application = app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{RDS_POSTGRES_ENDPOINT}:5432/{DB_NAME}"
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# CONFIG = Config.from_file('config_prod.yml')
# CONFIG.init_app(app)
# db = SQLAlchemy(app)


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
        stream_with_context(count_stream(YANG_TERM)),
        mimetype='text/event-stream'
    )


@app.route('/latest_tweets')
def latest_tweets():
    return Response(
        stream_with_context(latest_tweet_stream(n=5)),
        mimetype='text/event-stream'
    )


@app.route('/top_retweets')
def top_retweets():
    """Top retweeted tweet ids, refresh every 30min based on the query granularity"""
    top_retweet_ids = get_top_retweets()
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
    return tweets_chart_request(chart_type='72hr_at_1hr')


# pylint: disable=no-member
@app.route('/tweets_daily_chart')
def tweets_daily_chart():
    """
    Get the counts of tweets for the last 14 days at 1 day granularity
    A total 14 data points including today
    """
    return tweets_chart_request(chart_type='14d_at_1d')


@app.route('/tweets_loc_chart')
def tweets_loc_chart():
    """
    Get the counts of tweets for the last 14 days at 1 day granularity
    A total 14 data points including today
    """
    return tweets_chart_request(chart_type='72h_for_loc')


"""Sentiment"""


@app.route('/wordcloud')
def wordcloud():
    """
    Get the word cloud for tweets in the last 6 hours
    """
    # Query tweets in the last 6 hours, refresh at 1 hour
    # Cache the generated image
    img = get_wordcloud()

    if img:
        img.seek(0)
        logging.info(f"Word cloud image sent.")
        return send_file(img, mimetype='image/png')


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=PORT, threaded=True)
