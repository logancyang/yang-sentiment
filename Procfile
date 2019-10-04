# --max-requests 1200: avoid memory leaks by limiting the number of requests a worker processes
# https://devcenter.heroku.com/articles/python-gunicorn
# also use `heroku config:set WEB_CONCURRENCY=3` in CLI and don't use `-w 3` here
web: gunicorn --worker-class=gevent -t 99999 application:app --max-requests 1200 -b 0.0.0.0:$PORT