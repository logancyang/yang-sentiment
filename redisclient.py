import redis
import os
from settings import REDIS_URL


r = redis.from_url(REDIS_URL)
