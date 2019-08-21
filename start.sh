#!/bin/sh

gunicorn --worker-class=gevent -w 4 -t 20000 application:app -b 0.0.0.0:$PORT
