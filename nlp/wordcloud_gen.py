import random
from collections import Counter

import wordcloud
import preprocessor as p
import spacy


CUSTOM_STOPWORDS = [
    'good', 'looking', 'look', 'word', 'going', 'door', 'andrewyang', 'yang20',
    'actually', 'dude', 'yanggang', 'yang', 'need', 'lol', 'thank', 'thanks',
    'got', 'andrew', 'want', 'year', 'years', 'month', 'know', 'think',
    'thing', 'things', 'saying', 'guy', 'amp', 'yes', 'way', 'said', 'let',
    'talking', 'hey', 'yeah', 'gang', 'time', 'come', 'mean', 'fuck', 'says'
]


def _join_tweets(tweet_objs):
    tweets = [tweet_obj.tweet_text for tweet_obj in tweet_objs]
    return ' '.join(tweets)


# 1. tweet preprocess using package 2. Remove extra punctuations 3. tokenize 4. remove stopwords
def _clean_tweet_specs(text):
    p.set_options(p.OPT.URL, p.OPT.EMOJI, p.OPT.MENTION, p.OPT.HASHTAG)
    cleaned_tweets = p.clean(text)
    return cleaned_tweets


def _get_stopwords(custom_stopwords, stopwords=None):
    if not stopwords:
        nlp = spacy.load('en_core_web_sm')
        stopwords = spacy.lang.en.stop_words.STOP_WORDS | set(wordcloud.STOPWORDS)
    for custom in custom_stopwords:
        stopwords.add(custom)
    return stopwords


def _tokenize(text):
    nlp = spacy.load('en_core_web_sm')
    doc = nlp.tokenizer(text)
    token_strs = [str(token) for token in doc]
    return token_strs


def _remove_stopwords(tokens, stopwords):
    txt_no_stop = []
    for token in tokens:
        if token.lower() not in stopwords:
            txt_no_stop.append(token)
    random.shuffle(txt_no_stop)
    return ' '.join(txt_no_stop)


def generate_wordcloud(tweet_objs):
    text = _join_tweets(tweet_objs)
    stops = _get_stopwords(CUSTOM_STOPWORDS)
    cleaned = _clean_tweet_specs(text)
    tokens = _tokenize(cleaned)
    txt_no_stop = _remove_stopwords(tokens, stops)
    wc = wordcloud.WordCloud(
            background_color="white",
            max_words=900,
            width=900,
            height=450
        ).generate(txt_no_stop)
    return wc

