# Web Scraping
import requests
from bs4 import BeautifulSoup

# Math
import statistics

# Currency Conversion
from currency_converter import CurrencyConverter

# Sentiment Analysis
import nltk
#nltk.download()
import nltk.corpus
#nltk.download('stopwords')
from nltk.corpus import stopwords
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import RegexpTokenizer
from nltk.stem import WordNetLemmatizer

# Pattern Matching
import re

def sentiment_analysis(text):
    sia = SentimentIntensityAnalyzer()
    sentiment = sia.polarity_scores(text)
    
    if sentiment["compound"] >= 0.05:
        return "🙂"
    elif sentiment["compound"] <= -0.05:
        return "🙁"
    else:
        return "😐"

def max_sentiment(sentiment):
    try:
        del sentiment["compound"]
    except KeyError:
        pass
    value = sentiment[max(sentiment, key=sentiment.get)]

    return value

def min_sentiment(sentiment):
    try:
        del sentiment["compound"]
    except KeyError:
        pass
    value = sentiment[min(sentiment, key=sentiment.get)]

    return value

def clean_text(text):
    tokenizer = RegexpTokenizer('\w+|\$[\d\.]+|http\S+')
    tokenized = tokenizer.tokenize(text)
    tokenized = [word.lower() for word in tokenized]

    stop_words = stopwords.words('english')
    filtered = [word for word in tokenized if word not in stop_words and word.isalpha()]

    lemmatizer = WordNetLemmatizer()
    lemmatized = [lemmatizer.lemmatize(word) for word in filtered]
    
    return " ".join(lemmatized)

def get_title(soup):
    title = soup.find("meta", {"name": "DC.title"})
    title_content = title["content"]

    return title_content

def get_description(soup):
    description = soup.find("meta", {"name": "DC.description"})
    description_content = description["content"]

    return clean_text(description_content)

def get_price(soup):
    spans = soup.find_all("span")
    price = [str(span.text) for span in spans if "$" in span.text][0]

    return price

def percentage_difference(intial, final):
    value = (final - intial) / intial

    if value < 0.0:
        return "👎"
    elif value >= 0.0:
        return "👍"

def create_soup(url, headers):
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    return soup

def convert_currency(price, base_currency, target_currency):
    c = CurrencyConverter()
    price = c.convert(price, base_currency, target_currency)

    return price

def find_product_prices(title):
    headers = { 
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582"
    }
    url = "https://www.google.com/search?q=" + title + "&sa=X&biw=1920&bih=927&tbm=shop&sxsrf=ALiCzsbtwkWiDOQEcm_9X1UBlEG1iaqXtg%3A1663739640147&ei=-KYqY6CsCLez0PEP0Ias2AI&ved=0ahUKEwigiP-RmaX6AhW3GTQIHVADCysQ4dUDCAU&uact=5&oq=REPLACE&gs_lcp=Cgtwcm9kdWN0cy1jYxADMgUIABCABDIFCAAQgAQyBQgAEIAEMgsIABCABBCxAxCDATIECAAQAzIFCAAQgAQyBQgAEIAEMgUIABCABDIFCAAQgAQyBQgAEIAEOgsIABAeEA8QsAMQGDoNCAAQHhAPELADEAUQGDoGCAAQChADSgQIQRgBUM4MWO4TYJoVaAFwAHgAgAFDiAGNA5IBATeYAQCgAQHIAQPAAQE&sclient=products-cc"
    
    soup = create_soup(url, headers)
    prices = soup.find_all("span", {"class": "HRLxBb"})

    values = []
    for price in prices:
        values.append(price.text)

    normalized = [re.sub("\$", "", price) for price in values]
    normalized = [re.search(r"[0-9,.]*", price).group(0) for price in normalized]
    normalized = [float(price.replace(",", "")) for price in normalized]
    normalized = sorted(normalized)

    median = statistics.median_grouped(normalized)
    deviation = statistics.stdev(normalized)

    return median, deviation

def valid_url(url):
    if re.search(r"^https://www.facebook.com/", url):
        return True
    else:
        return False

def main():
    url = input("Enter URL: ")

    if valid_url(url):
        pass
    else:
        print("Invalid URL")
        exit(1)

    shortened_url = re.search(r".*[0-9]", url).group(0)
    mobile_url = shortened_url.replace("www", "m")

    sentiment = sentiment_analysis(get_description(create_soup(url, headers=None)))
    title = get_title(create_soup(url, headers=None))

    initial_price = int(re.sub("[\$,]", "", get_price(create_soup(mobile_url, headers=None))))
    median, deviation = find_product_prices(title)

    print("\nProduct: {}".format(title))
    print("How we feel about the description: {}".format(sentiment))
    print("How we feel about the price: {}".format(percentage_difference(initial_price, median)))
    print("Price range of similar products we found: ${:,.2f} - ${:,.2f}".format(abs(median - deviation), abs(median + deviation)))

if __name__ == "__main__":
    main()