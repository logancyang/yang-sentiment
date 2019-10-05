import logging
import time
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from query_funcs import tweets_chart_request, get_top_retweets, get_wordcloud


sched = BlockingScheduler()

@sched.scheduled_job('interval', minutes=10)
def cache_in_advance():
    tweets_chart_request(chart_type='14d_at_1d')
    tweets_chart_request(chart_type='72hr_at_1hr')
    tweets_chart_request(chart_type='72h_for_loc')
    get_top_retweets()
    get_wordcloud()
    logging.info(f"Scheduled Job: advance caching executed at {datetime.now()}")


sched.start()
