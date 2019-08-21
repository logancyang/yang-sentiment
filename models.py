import os
from sqlalchemy import Column, Integer, String, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


Base = declarative_base()


class Tweet(Base):
    __tablename__ = 'crypto_tweets'

    id = Column(Integer, primary_key=True)
    # Time properties
    created_at = Column(String)  # created_at: 'Mon Jul 08 12:43:19 +0000 2019'
    inserted_at = Column(BigInteger)

    # Tweet properties
    tweet_id = Column(String)  # id_str: "1148411390236844032"
    tweet_text = Column(String)  # text: "tweet content"
    tweet_lang = Column(String)  # lang: 'en'
    in_reply_to_status_id_str = Column(String)
    in_reply_to_user_id_str = Column(String)
    retweeted_status_id_str = Column(String)
    quoted_status_id_str = Column(String)

    # Search properties
    track_term = Column(String)  # either bitcoin or cardano

    # User properties
    user_name = Column(String)  # user.name: "user john"
    user_screen_name = Column(String)  # user.screen_name
    user_location = Column(String)  # user.location: "New York"
    user_followers = Column(Integer)  # user.followers_count: 234

    # Place properties
    place = Column(String)
    coordinates = Column(String)

    # __init__() is taken care of by Base
    def __repr__(self):
        return (f"<Tweet("
                f"created_at={self.created_at}, "
                f"tweet_id={self.tweet_id}, "
                f"tweet_text={self.tweet_text}, "
                f"tweet_lang={self.tweet_lang}, "
                f"track_term={self.track_term}, "
                f"user_name={self.user_name}, "
                f"user_screen_name={self.user_screen_name}, "
                f"user_location={self.user_location}, "
                f"user_followers={self.user_followers}, "
                f"in_reply_to_status_id_str={self.in_reply_to_status_id_str}, "
                f"in_reply_to_user_id_str={self.in_reply_to_user_id_str}, "
                f"retweeted_status_id_str={self.retweeted_status_id_str}, "
                f"quoted_status_id_str={self.quoted_status_id_str}, "
                f"place={self.place}, "
                f"coordinates={self.coordinates}, "
                f"inserted_at={self.inserted_at}"
                ")>")


class TweetDailyCount(Base):
    __tablename__ = 'tweet_daily_count'

    id = Column(Integer, primary_key=True)
    created_date = Column(String)  # '20190712' us eastern time
    track_term = Column(String)
    tweet_count = Column(Integer)

    # __init__() is taken care of by Base
    def __repr__(self):
        return (f"<TweetDailyCount("
                f"created_date={self.created_date}, "
                f"track_term={self.track_term}, "
                f"tweet_count={self.tweet_count}"
                ")>")


class Price(Base):
    __tablename__ = 'crypto_prices'

    id = Column(Integer, primary_key=True)
    # Example api response {'BTC': {'USD': 10418.83}, 'ADA': {'USD': 0.05811}}
    inserted_at = Column(String)  # current timestamp in millisecond
    coin_type = Column(String)  # BTC or ADA
    price_usd = Column(String)  # price in usd

    def __repr__(self):
        return (f"<Price("
                f"inserted_at={self.inserted_at}, "
                f"coin_type={self.coin_type}, "
                f"price_usd={self.price_usd}"
                ")>")


class Database:
    def __init__(self, env='dev'):
        """DB setup"""
        # Initialize the database :: Connection & Metadata retrieval
        self.db_url = self._set_db_url_by_env(env)
        self.engine = create_engine(self.db_url, echo=False)

    def create_db_session(self):
        # Create all tables that do not already exist
        Base.metadata.create_all(self.engine, Base.metadata.tables.values(), checkfirst=True)
        # SqlAlchemy :: Session setup
        Session = sessionmaker(bind=self.engine)
        # SqlAlchemy :: Starts a session
        return Session()

    def _set_db_url_by_env(self, env='dev'):
        db_url = None
        dev_url = 'sqlite:///' + os.path.join(
            os.path.abspath(os.path.dirname(__file__)), 'db.sqlite')
        # format: (user):(password)@(db_identifier).amazonaws.com:5432/(db_name)
        prod_path = ("postgresql+psycopg2://dukelolo_crypto:h3v5H8R9@crypto-sentiment-db"
                     ".cjnd7boyg5li.us-east-1.rds.amazonaws.com:5432/crypto_sentiment_db")
        if env == 'dev':
            print(f"Environment: dev. Using dev db_url: {dev_url}")
            db_url = dev_url
        elif env == 'prod':
            print(f"Environment: prod. Using prod db_url: {prod_path}")
            db_url = prod_path
        else:
            print(f"Environment invalid. Please make sure to set it as dev or prod.")
        return db_url
