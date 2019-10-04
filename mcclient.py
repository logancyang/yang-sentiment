import bmemcached
import os


SERVERS = os.environ.get('MEMCACHIER_SERVERS', '').split(',')
USER = os.environ.get('MEMCACHIER_USERNAME', '')
PASSWORD = os.environ.get('MEMCACHIER_PASSWORD', '')


mc = bmemcached.Client(servers=SERVERS, username=USER, password=PASSWORD)

mc.enable_retry_delay(True)  # Enabled by default. Sets retry delay to 5s.
