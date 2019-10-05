# Data Streaming for Tweet Sentiment Dashboard

This is a streaming job that streams live tweets with specific track terms to an AWS RDS Postgres database.
There are Flask apps consuming this data in the database.

## Development
- Create a virtualenv folder `virtualenv -p python3.6 venv`
- Activate `source venv/bin/activate`
- Install the requirements `pip install -r requirements.txt`

Note that the env variables are in `.env` and should be kept out of git securely.

## Run the Stream

```
nohup python stream_to_db.py &
```


