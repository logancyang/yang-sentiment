import redis
import os


r = redis.from_url(os.environ.get("REDIS_URL"))
