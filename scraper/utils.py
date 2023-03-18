from nltk.corpus import stopwords
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import RegexpTokenizer
from nltk.stem import WordNetLemmatizer
import requests
import re
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
import numpy as np
import statistics

def clean_text(text):
    tokenizer = RegexpTokenizer('\w+|\$[\d\.]+|http\S+')
    tokenized = tokenizer.tokenize(text)
    tokenized = [word.lower() for word in tokenized]

    stop_words = stopwords.words('english')
    filtered = [word for word in tokenized if word not in stop_words and word.isalpha()]

    lemmatizer = WordNetLemmatizer()
    lemmatized = [lemmatizer.lemmatize(word) for word in filtered]
    
    return " ".join(lemmatized)

def sentiment_analysis(text):
    sia = SentimentIntensityAnalyzer()
    sentiment = sia.polarity_scores(text)
    neg, neu, pos, compound = sentiment["neg"], sentiment["neu"], sentiment["pos"], sentiment["compound"]

    if compound > 0.0:
        rating = 5 * max(pos, compound)
    elif compound < 0.0:
        rating = 5 * min(neg, compound)
    else:
        rating = 5 * neu

    return abs(rating)

def create_soup(url, headers):
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    return soup

def clean_listing_title(title):
    title = re.sub(r"#", "%2", title)
    title = re.sub(r"&", "%26", title)

    return title

def reject_outliers(data, m=1.5):
    distribution = np.abs(data - np.median(data))
    m_deviation = np.median(distribution)
    standard = distribution / (m_deviation if m_deviation else 1.)

    return data[standard < m].tolist()

def price_difference_rating(initial, final):
    if initial <= final:
        rating = 5.0
    else:
        difference = min(initial, final) / max(initial, final)
        rating = (difference / 20) * 100

    return rating

def find_viable_product(title, ramp_down):
    title = clean_listing_title(title)
    headers = { 
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582"
    }
    url = f"https://www.google.com/search?q={title}&sa=X&biw=1920&bih=927&tbm=shop&sxsrf=ALiCzsbtwkWiDOQEcm_9X1UBlEG1iaqXtg%3A1663739640147&ei=-KYqY6CsCLez0PEP0Ias2AI&ved=0ahUKEwigiP-RmaX6AhW3GTQIHVADCysQ4dUDCAU&uact=5&oq=REPLACE&gs_lcp=Cgtwcm9kdWN0cy1jYxADMgUIABCABDIFCAAQgAQyBQgAEIAEMgsIABCABBCxAxCDATIECAAQAzIFCAAQgAQyBQgAEIAEMgUIABCABDIFCAAQgAQyBQgAEIAEOgsIABAeEA8QsAMQGDoNCAAQHhAPELADEAUQGDoGCAAQChADSgQIQRgBUM4MWO4TYJoVaAFwAHgAgAFDiAGNA5IBATeYAQCgAQHIAQPAAQE&sclient=products-cc"
    soup = create_soup(url, headers)
    similarity_threshold = 0.25

    try:
        filtered_prices_descriptions = listing_product_similarity(soup, title, similarity_threshold)
        prices = list(filtered_prices_descriptions.values())
        assert len(prices) > 0
    except AssertionError:
        while len(prices) == 0:
            ramp_down += 0.05
            filtered_prices_descriptions = listing_product_similarity(soup, title, similarity_threshold - ramp_down)
            prices = list(filtered_prices_descriptions.values())

    median = statistics.median_grouped(prices)
    
    return min(prices), max(prices), median

def clean_title_description(title):
    cleaned = re.sub(r"[^A-Za-z0-9\s]+", " ", title)
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned

def get_product_description(soup):
    description = soup.find_all("div", {"class": "rgHvZc"})

    return description

def get_product_price(soup):
    prices = soup.find_all("span", {"class": "HRLxBb"})

    values = []
    for price in prices:
        values.append(price.text)

    normalized = [re.sub("\$", "", price) for price in values]
    normalized = [re.search(r"[0-9,.]*", price).group(0) for price in normalized]
    normalized = [float(price.replace(",", "")) for price in normalized]
    
    outlierless = reject_outliers(np.array(normalized))

    return outlierless

def listing_product_similarity(soup, title, similarity_threshold):
    normalized = get_product_price(soup)
    description = get_product_description(soup)

    price_description = {}
    for key, value in zip(description, normalized):
        google_shopping_title = clean_title_description(key.text.lower())
        listing_title = clean_title_description(title.lower())
        price_description[key.text] = [value, SequenceMatcher(None, google_shopping_title, listing_title).ratio()]

    filtered_prices_descriptions = {}
    for key, value in price_description.items():
        if value[1] >= similarity_threshold:
            filtered_prices_descriptions[key] = value[0]

    return filtered_prices_descriptions