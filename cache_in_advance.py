import logging
import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from application import _tweets_chart_request, top_retweets


def cache_in_advance():
    while True:
        _tweets_chart_request(chart_type='14d_at_1d')
        _tweets_chart_request(chart_type='72hr_at_1hr')
        _tweets_chart_request(chart_type='72h_for_loc')
        top_retweets()
        logging.info(f"Advance caching executed at {datetime.now()}")
        time.sleep(10 * 60)

def start_advance_caching():
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(cache_in_advance, 'interval', minutes=10)
    sched.start()
