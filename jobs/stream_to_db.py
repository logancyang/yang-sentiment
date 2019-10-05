import json
import time
from http.client import IncompleteRead
from multiprocessing import Process
from urllib3.exceptions import ProtocolError
from sqlalchemy import BigInteger
from sqlalchemy.sql.expression import cast
from TwitterAPI import TwitterAPI

from cryptocompare_client import CryptocompareClient
from models import Tweet, Price, Database, TweetDailyCount
from queries import get_eastern_date_from_epoch, convert_date_to_tsinterval
from settings import (
    API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET
)


BTC_TERM = 'bitcoin'
ADA_TERM = 'cardano'
YANG_TERM = 'andrewyang'
NO_TERM = 'noterm'


class TweetStream:
    def __init__(self, database):
        # Create this database instance first with correct env
        # Create all tables if not exist
        self.session = database.create_db_session()
        """Streaming"""
        self.track_terms = [ADA_TERM, YANG_TERM]
        self.stream_api = TwitterAPI(
            API_KEY, API_SECRET_KEY, ACCESS_TOKEN, ACCESS_TOKEN_SECRET
        )

    def get_track_term(self, tweet_text, track_terms):
        if not track_terms:
            return NO_TERM
        expanded_ada_terms = ['#ada', '$ada']
        expanded_btc_terms = ['#btc', '$btc']
        expanded_yang_terms = [
            '#yanggang', 'yang gang', 'andrew yang', 'freedom dividend',
            'universal basic income', 'yang2020'
        ]
        expanded_terms = track_terms + expanded_btc_terms + expanded_ada_terms + expanded_yang_terms
        for term in expanded_terms:
            if term in tweet_text.lower():
                if term in expanded_yang_terms or term == YANG_TERM:
                    return YANG_TERM
                if term in expanded_ada_terms or term == ADA_TERM:
                    return ADA_TERM
                if term in expanded_btc_terms or term == BTC_TERM:
                    return BTC_TERM
        return NO_TERM

    def get_tweet_stream(self):
        return self.stream_api.request(
            'statuses/filter', {'track': self.track_terms})

    def stream_tweet_to_db(self):
        """
        Stream live tweets from Twitter to SQLite, also update corresponding
        statistics, e.g. increment daily count for different coins in cache
        """
        while True:
            try:
                tweet_dicts = self.get_tweet_stream()
                for tweet_item in tweet_dicts:
                    current_ts = int(round(time.time() * 1000))
                    created_at = tweet_item.get('created_at')
                    tweet_id = tweet_item.get('id_str')
                    tweet_text = tweet_item.get('text')
                    tweet_lang = tweet_item.get('lang')  # lang: 'en'
                    track_term = self.get_track_term(
                        tweet_text, self.track_terms
                    )
                    # noterm: bitcoin: cardano ~ 500 : 100 : 1, skip noterms
                    # do not stream them to db
                    if track_term == NO_TERM:
                        continue
                    # user.name: "user john"
                    user_name = tweet_item.get('user', {}).get('name')
                    # user.screen_name
                    user_screen_name = tweet_item.get('user', {})\
                        .get('screen_name')
                    # user.location: "New York"
                    user_location = tweet_item.get('user', {})\
                        .get('location')
                    # user.followers_count: 234
                    user_followers = tweet_item.get('user', {})\
                        .get('followers_count')
                    inserted_at = current_ts

                    place_dict = tweet_item.get('place')
                    place = json.dumps(place_dict) if place_dict else None
                    # NOTE: geo is deprecated, use coordinates [long, lat]
                    coordinates_dict = tweet_item.get('coordinates')
                    coordinates = json.dumps(coordinates_dict) if coordinates_dict else None

                    # If tweet is a reply, this is the original tweet id replied to
                    in_reply_to_status_id_str = tweet_item.get('in_reply_to_status_id_str')
                    # If tweet is a reply, this is the original tweet author's user id
                    in_reply_to_user_id_str = tweet_item.get('in_reply_to_user_id_str')
                    # If tweet is a quote, this is the original tweet id
                    quoted_status_id_str = tweet_item.get('quoted_status_id_str')
                    # If tweet is a retweet, this is the original tweet id
                    retweeted_status_id_str = tweet_item.get('retweeted_status', {}).get('id_str')

                    # NOTE: This needs to be updated every time there is a db migration
                    tweet = Tweet(
                        created_at=created_at,
                        tweet_id=tweet_id,
                        tweet_text=tweet_text,
                        tweet_lang=tweet_lang,
                        track_term=track_term,
                        user_name=user_name,
                        user_screen_name=user_screen_name,
                        user_location=user_location,
                        user_followers=user_followers,
                        place=place,
                        coordinates=coordinates,
                        in_reply_to_status_id_str=in_reply_to_status_id_str,
                        in_reply_to_user_id_str=in_reply_to_user_id_str,
                        retweeted_status_id_str=retweeted_status_id_str,
                        quoted_status_id_str=quoted_status_id_str,
                        inserted_at=inserted_at
                    )

                    self.session.add(tweet)
                    self.session.commit()

                    # Increment the right (created_date, track_term): count in tweet_daily_count
                    self._increment_daily_count(inserted_at, track_term)

            except (IncompleteRead, ProtocolError, AttributeError) as e:
                # Oh well, reconnect and keep trucking
                print(f"An exception occurred during streaming: {e}\n")
                continue
            except Exception as e:
                print(
                    f"An unexpected exception occurred during streaming: {e}\n")
                continue
            except KeyboardInterrupt as e:
                print(f"Stopping the stream... closing the session...")
                self.session.close()
                print(f"Good bye!")
                break

    def _increment_daily_count(self, inserted_at, track_term):
        """
        Get date by inserted_at
        Check if row exists in TweetDailyCount by (date, track_term)
            If row exists, row.tweet_count += 1
            Else insert new row with count() query to tweet table
        Q: Is there ever going to be bad count data? How to deal with it?
        A: Since only this stream can modify the counts, should be fine
        """
        # Get us eastern date from inserted_at epoch
        created_date = get_eastern_date_from_epoch(inserted_at)
        count_row = self.session.query(TweetDailyCount).filter_by(
            created_date=created_date, track_term=track_term).first()
        if count_row:
            count_row.tweet_count += 1
            self.session.commit()
            if count_row.tweet_count % 10 == 0:
                print(f"Count for {track_term} on {created_date}, "
                      f"ts {int(time.time())}: {count_row.tweet_count}\n")
        else:
            start_ms, end_ms = convert_date_to_tsinterval(
                date_str=created_date)
            queried_count = self.session\
                .query(Tweet)\
                .filter(Tweet.track_term == track_term)\
                .filter(cast(Tweet.inserted_at, BigInteger) >= start_ms)\
                .filter(cast(Tweet.inserted_at, BigInteger) < end_ms).count()
            new_row = TweetDailyCount(
                created_date=created_date,
                track_term=track_term,
                tweet_count=queried_count
            )
            self.session.add(new_row)
            self.session.commit()


# This stream process needs to be triggered independently from the tweet stream
# Tweet stream gets tweet and insert to db on each tweet event
# Price call queries api very 1 minute
class CryptoPriceApi:
    def __init__(self, database):
        self.session = database.create_db_session()
        self.client = CryptocompareClient()

    # Example response: {'BTC': {'USD': 10418.83}, 'ADA': {'USD': 0.05811}}
    def get_current_prices(self):
        resp = self.client.get_prices()
        return {
            'BTC': resp.get('BTC', {}).get('USD'),
            'ADA': resp.get('ADA', {}).get('USD')
        }

    def stream_prices_to_db(self):
        while True:
            try:
                prices = self.get_current_prices()
                current_ts = int(round(time.time() * 1000))
                for coin, price in prices.items():
                    inserted_at = current_ts
                    coin_type = coin  # BTC or ADA
                    price_usd = price
                    price = Price(
                        inserted_at=inserted_at,
                        coin_type=coin_type,
                        price_usd=price_usd
                    )

                    self.session.add(price)
                    self.session.commit()
                    self.session.close()
                time.sleep(60)
            except (IncompleteRead, ProtocolError, AttributeError) as e:
                # Oh well, reconnect and keep trucking
                print(f"An exception occurred during crypto price call: {e}\n")
                continue
            except Exception as e:
                print(
                    f"An unexpected exception occurred during crypto price call: {e}\n")
                continue
            except KeyboardInterrupt as e:
                print(f"Stopping the stream... closing the session...")
                self.session.close()
                print(f"Good bye!")
                break


if __name__ == "__main__":
    # SQLAlchemy with multiprocessing:
    # Each subprocess needs its own engine!
    # Note: for local testing, env='dev'
    def worker(Stream, methodname, env='prod'):
        db = Database(env=env)
        stream = Stream(db)
        getattr(stream, methodname)()

    workers = [worker, worker]
    args = [(TweetStream, 'stream_tweet_to_db'),
            (CryptoPriceApi, 'stream_prices_to_db')]
    procs = [Process(target=w, args=a) for w, a in zip(workers, args)]
    for proc in procs:
        proc.start()
    for proc in procs:
        proc.join()
    print(f"Stream ended at {int(time.time())}.")


