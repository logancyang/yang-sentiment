#!/bin/sh

PORT=7800
DB_NAME=crypto_sentiment_db
DB_USER=dukelolo_crypto
DB_PASSWORD=h3v5H8R9
RDS_POSTGRES_ENDPOINT=crypto-sentiment-db.cjnd7boyg5li.us-east-1.rds.amazonaws.com

gunicorn --worker-class=gevent -w 4 -t 20000 wsgi:application -b 0.0.0.0:$PORT
