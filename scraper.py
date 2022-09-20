# Web Scraping
import requests
from bs4 import BeautifulSoup

# Sentiment Analysis
import nltk
nltk.download()
from nltk.sentiment import SentimentIntensityAnalyzer

# Pattern Matching
import re

def sentiment_analysis(text):
    sia = SentimentIntensityAnalyzer()
    sentiment = sia.polarity_scores(text)
    negative, neutral, positive = sentiment['neg'], sentiment['neu'], sentiment['pos']

    if negative > positive and negative > neutral:
        return("🙁")
    elif positive > negative:
        return("🙂")
    else:
        return("😐")

def html_debug(soup):
    f = open("index.html", "w")
    f.write(soup.prettify())
    f.close()

def get_title(soup):
    title = soup.find("meta", {"name": "DC.title"})
    title_content = title["content"]
    return title_content

def get_description(soup):
    description = soup.find("meta", {"name": "DC.description"})
    description_content = description["content"]
    return description_content

def main():
    url = input("Enter URL: ")
    shortened_url = re.search(r"(^.*)?\?", url).group(0)
    mobile_url = shortened_url.replace("www", "m")

    response = requests.get(shortened_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    print("\nHow we feel about this posting: {}".format(sentiment_analysis(get_description(soup))))

if __name__ == "__main__":
    main()