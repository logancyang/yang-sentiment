# Live Tweet Sentiment Dashboard For Andrew Yang

This is a Flask app visualizing statistics and sentiment for tweets about Andrew Yang, the 2020 presidential candidate.

There is a streaming job that streams live tweets about Andrew Yang, Yang Gang and the Freedom Dividend to an AWS RDS Postgres database.

This Flask app consumes data in that database.

## Development
- Create a virtualenv folder `virtualenv -p python3.6 venv`
- Activate `source venv/bin/activate`
- Install the requirements `pip install -r requirements.txt`
- Run Flask app

```python
FLASK_ENV=development python application.py
```

Note that the env variables are in `.env` and should be kept out of git securely.


## Staging: Heroku Free Tier

Sometimes there are issues which only can be found on the server side, such as timezone problems. Staging is a great
place to test it. With the `Procfile` and automatic deployment from Github setup, we can deploy to Heroku by simply
`git push -u origin master`.

Heroku app url: https://andrewyangtrend.herokuapp.com/


## Production: Deploy to AWS Beanstalk

Refer to EB CLI instruction about how to setup and initialize an EB project properly.

I'm using AWS Route 53 domain name and setting name servers in AWS Route 53 as well. GoDaddy is not the best experience, go with AWS Route 53 for domain names.

After proper setup, to make update to the app, simply commit the code and run

```
eb deploy
```

The change will be live on http://www.andrewyangtrend.com after a couple of minutes.


## References

- Twitter API Tweet Object
    - https://developer.twitter.com/en/docs/tweets/data-dictionary/overview/tweet-object
- AWS Elastic Beanstalk CLI
    - https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli3.html
- AWS RDS Database Monitoring and Performance Check
    - https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Monitoring.html
- Alembic Database Autogenerate Migration
    - https://alembic.sqlalchemy.org/en/latest/autogenerate.html
- Statsmodels Linear Regression Coefficients and P-values
    - https://stackoverflow.com/questions/47388258/how-to-extract-the-regression-coefficient-from-statsmodels-api
    - https://stackoverflow.com/questions/41075098/how-to-get-the-p-value-in-a-variable-from-olsresults-in-python
- Wordcloud
    - http://amueller.github.io/word_cloud/auto_examples/simple.html#sphx-glr-auto-examples-simple-py
- Add HTTPS to your website
- Add Google Analytics to your website
- AWS Kinesis Firehose
- AWS Elasticsearch
