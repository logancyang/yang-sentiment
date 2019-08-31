"""Query helpers"""
from datetime import datetime, timedelta, time
from pytz import timezone
from constants import YANG_TERM


def query_last_n(tablename, n=5, track_term=YANG_TERM):
    return (f"SELECT * FROM {tablename} WHERE track_term = '{track_term}' "
            f"ORDER BY id DESC LIMIT {str(n)};")


def query_tweet_count(track_term, created_date):
    return (f"SELECT tweet_count FROM tweet_daily_count WHERE track_term = '{track_term}' AND "
            f"created_date = '{created_date}';")


def query_retweet_count(colname='retweeted_status_id_str', track_term='andrewyang', top_n=10, n_hours=6):
    """Query top n retweeted tweet ids for the last n_hours, refresh every 30min"""
    dt_nhr_ago = datetime.now() - timedelta(hours=n_hours)
    thirtymin_in_seconds = 30 * 60
    epochms_nhr_ago = dt_nhr_ago.timestamp() // thirtymin_in_seconds * thirtymin_in_seconds * 1000
    return (f"SELECT COUNT(*), {colname} "
            f"FROM crypto_tweets "
            f"WHERE inserted_at::bigint >= {epochms_nhr_ago} "
            f"AND track_term = '{track_term}' "
            f"AND {colname} is not NULL "
            f"GROUP BY {colname} "
            f"ORDER BY COUNT(*) DESC LIMIT {top_n}")


def query_count_nhr_at_xmin(n_hours, x_mins, track_term, count_colname, interval_colname):
    dt_nhr_ago = datetime.now() - timedelta(hours=n_hours)
    xmin_in_seconds = 60 * x_mins
    epochms_nhr_ago = dt_nhr_ago.timestamp() // xmin_in_seconds * xmin_in_seconds * 1000
    return _query_count_period_at_granularity(
        track_term,
        period_start=epochms_nhr_ago,
        granularity=xmin_in_seconds,
        count_colname=count_colname,
        interval_colname=interval_colname
    )


def query_count_14d_at_1d(track_term, count_colname, interval_colname):
    n_days = 15
    dt_14d_ago = datetime.now() - timedelta(days=n_days)
    dt_14d_ago_local = timezone('US/Eastern').localize(dt_14d_ago)
    dt_14d_ago_localmidnight = dt_14d_ago_local.replace(hour=0, minute=0, second=0, microsecond=0)
    epochms_14d_ago = dt_14d_ago_localmidnight.timestamp() * 1000
    return (f"SELECT d.date AS {interval_colname}, count(ct.id) AS {count_colname} "
            f"FROM (SELECT to_char(date_trunc('day', (current_date - offs)), 'YYYY-MM-DD') AS date "
            f"FROM generate_series(0, {n_days}) AS offs) d LEFT OUTER JOIN "
            f"crypto_tweets ct "
            f"ON d.date = to_char(date_trunc('day', ct.created_at::timestamp "
            f"with time zone at time zone 'US/Eastern'), 'YYYY-MM-DD') "
            f"WHERE ct.inserted_at::bigint >= {epochms_14d_ago} AND ct.track_term = '{track_term}' "
            f"GROUP BY d.date;")


def query_count_group_by_location(track_term, colname='location', n_hours=72):
    """Query top n retweeted tweet ids for the last n_hours, refresh every 30min"""
    dt_nhr_ago = datetime.now() - timedelta(hours=n_hours)
    hour_in_seconds = 60 * 60
    epochms_nhr_ago = dt_nhr_ago.timestamp() // hour_in_seconds * hour_in_seconds * 1000
    return (f"SELECT COUNT(*), user_location AS {colname} "
            f"FROM crypto_tweets "
            f"WHERE inserted_at::bigint >= {epochms_nhr_ago} "
            f"AND track_term = '{track_term}' "
            f"AND user_location is not NULL "
            f"GROUP BY user_location "
            f"ORDER BY COUNT(*) DESC")


def _query_count_period_at_granularity(
        track_term, period_start, granularity, count_colname, interval_colname
):
    granularity_ms = granularity * 1000
    return (f"SELECT COUNT(*) {count_colname}, "
            f"to_timestamp(floor((inserted_at::bigint / {granularity_ms} )) * {granularity}) "
            f"AT TIME ZONE 'US/Eastern' as {interval_colname} "
            f"FROM crypto_tweets "
            f"WHERE inserted_at::bigint >= {period_start} AND track_term = '{track_term}' "
            f"GROUP BY {interval_colname}")


"""
Time utilities
"""


def convert_date_to_tsinterval(date_str, pytz_timezone='US/Eastern'):
    """date format example: 20190714"""
    tz = timezone(pytz_timezone)
    dt = datetime.strptime(date_str, "%Y%m%d")
    past_midnight_dt = tz.localize(datetime.combine(dt, time()))
    next_midnight_dt = past_midnight_dt + timedelta(days=1)
    return _get_epoch_ms(past_midnight_dt), _get_epoch_ms(next_midnight_dt)


def _get_epoch_ms(dt):
    return int(dt.timestamp() * 1000)


def get_eastern_date_today():
    """Get date today in US East timezone, e.g. 20190715"""
    # define eastern timezone
    eastern = timezone('US/Eastern')
    # localized datetime
    loc_dt = datetime.now(eastern)
    # BEWARE!! loc_dt.today() returns to UTC (or your local OS time)!!! DO NOT .today()
    return loc_dt.strftime("%Y%m%d")


def get_utc_date_today():
    """Get date today in UTC, e.g. 20190715"""
    return datetime.utcnow().strftime("%Y%m%d")


def get_eastern_date_from_epoch(epoch_ms):
    """Get the US Eastern date in "YYYYMMDD" format from unix epoch milliseconds

    Arguments:
        epoch_ms {int} -- unix epoch milliseconds

    Returns:
        str -- US Eastern date in "YYYYMMDD" format
    """
    eastern_dt = datetime.fromtimestamp(
        epoch_ms / 1000, tz=timezone('US/Eastern'))
    return eastern_dt.strftime("%Y%m%d")
