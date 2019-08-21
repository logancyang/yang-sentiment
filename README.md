# Live Bitcoin and Cardano Tweet Sentiment Dashboard

This is a Flask app visualizing statistics and sentiment for tweets about the cryptocurrencies
bitcoin and cardano.

There is a streaming job that streams live tweets about bitcoin and cardano to an AWS RDS Postgres database.
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

Heroku app url: https://crypto-sentiment-board.herokuapp.com/


## Production: Deploy to AWS Beanstalk

Refer to EB CLI instruction about how to setup and initialize an EB project properly.

This time I'm using GoDaddy domain name and setting name servers in AWS Route 53. It was not easy to make it work. Next time, directly register/buy domain names in AWS Route 53!

After proper setup, to make update to the app, simply commit the code and run

```
eb deploy
```

The change will be live on http://cryptosentiment.co after a couple of minutes.
