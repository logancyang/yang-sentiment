from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from datajobs import ScheduledJob


sched = BlockingScheduler()

@sched.scheduled_job('interval', minutes=1)
def cache_in_advance():
    print(f"Scheduled job: executing...")
    ScheduledJob.tweets_chart_request(chart_type='14d_at_1d')
    ScheduledJob.tweets_chart_request(chart_type='72hr_at_1hr')
    ScheduledJob.tweets_chart_request(chart_type='72h_for_loc')
    ScheduledJob.get_top_retweets()
    ScheduledJob.get_wordcloud()
    print(f"Scheduled Job: advance caching executed at {datetime.now()}")


print(f"Scheduled job: started...")
sched.start()
