import logging
import time
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from application import _tweets_chart_request, top_retweets, wordcloud


sched = BlockingScheduler()

@sched.scheduled_job('interval', minutes=10)
def cache_in_advance():
    _tweets_chart_request(chart_type='14d_at_1d')
    _tweets_chart_request(chart_type='72hr_at_1hr')
    _tweets_chart_request(chart_type='72h_for_loc')
    top_retweets()
    wordcloud()
    logging.info(f"Scheduled Job: advance caching executed at {datetime.now()}")


sched.start()
