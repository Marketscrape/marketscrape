# Web Scraping
from distutils.command.clean import clean
import requests
from bs4 import BeautifulSoup

# Math
import statistics

# Currency Conversion
from currency_converter import CurrencyConverter

# Sentiment Analysis
#nltk.download()
import nltk.corpus
#nltk.download('stopwords')
from nltk.corpus import stopwords
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import RegexpTokenizer
from nltk.stem import WordNetLemmatizer
from difflib import SequenceMatcher

# Pattern Matching
import re

def sentiment_analysis(text):
    sia = SentimentIntensityAnalyzer()
    sentiment = sia.polarity_scores(text)

    feeling = sentiment[max(sentiment, key=sentiment.get)]
    rating = (feeling * 100) / 20

    if sentiment["compound"] <= -0.05:
        rating -= rating * sentiment["neg"]

    return truncate_rating(rating)

def clean_text(text):
    tokenizer = RegexpTokenizer('\w+|\$[\d\.]+|http\S+')
    tokenized = tokenizer.tokenize(text)
    tokenized = [word.lower() for word in tokenized]

    stop_words = stopwords.words('english')
    filtered = [word for word in tokenized if word not in stop_words and word.isalpha()]

    lemmatizer = WordNetLemmatizer()
    lemmatized = [lemmatizer.lemmatize(word) for word in filtered]
    
    return " ".join(lemmatized)

def price_difference_rating(initial, final):
    value = 100 - (initial / (final + initial)) * 100
    rating = (value + 50) / 20

    return truncate_rating(rating)

def truncate_rating(rating):
    if rating >= 5.0:
        rating = 5.0
    
    return rating

def stars(rating):
    pure_rating = int(rating)
    decimal = rating - pure_rating
    score = "🌕" * pure_rating

    if decimal > 0.75:
        score += "🌕"
    elif decimal > 0.25:
        score += "🌗"

    if len(score) < 5:
        score += "🌑" * (5 - len(score))
    
    return score

def get_listing_title(soup):
    title = soup.find("meta", {"name": "DC.title"})
    title_content = title["content"]

    return title_content

def get_listing_description(soup):
    description = soup.find("meta", {"name": "DC.description"})
    description_content = description["content"]

    return clean_text(description_content)

def get_listing_price(soup):
    spans = soup.find_all("span")
    price = [str(span.text) for span in spans if "$" in span.text][0]

    return price

def create_soup(url, headers):
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    return soup

def convert_currency(price, base_currency, target_currency):
    c = CurrencyConverter()
    price = c.convert(price, base_currency, target_currency)

    return price

def clean_listing_title(title):
    title = re.sub(r"#", "%2", title)
    title = re.sub(r"&", "%26", title)

    return title

def get_product_price(soup):
    prices = soup.find_all("span", {"class": "HRLxBb"})

    values = []
    for price in prices:
        values.append(price.text)

    normalized = [re.sub("\$", "", price) for price in values]
    normalized = [re.search(r"[0-9,.]*", price).group(0) for price in normalized]
    normalized = [float(price.replace(",", "")) for price in normalized]

    return normalized

def get_product_description(soup):
    description = soup.find_all("div", {"class": "rgHvZc"})

    return description

def clean_title_description(title):
    cleaned = re.sub(r"[^A-Za-z0-9\s]+", " ", title)
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned

def listing_product_similarity(soup, title, similarity_threshold):
    normalized = get_product_price(soup)
    description = get_product_description(soup)

    price_description = {}

    for key, value in zip(description, normalized):
        google_shopping_title = clean_title_description(key.text.lower())
        listing_title = clean_title_description(title.lower())

        if SequenceMatcher(None, google_shopping_title, listing_title).ratio() >= similarity_threshold:
            price_description[key.text] = value
    
    prices = []
    for key, value in price_description.items():
        prices.append(value)
    
    return prices   

def find_viable_product(title, ramp_down):
    title = clean_listing_title(title)
    headers = { 
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582"
    }
    url = "https://www.google.com/search?q=" + title + "&sa=X&biw=1920&bih=927&tbm=shop&sxsrf=ALiCzsbtwkWiDOQEcm_9X1UBlEG1iaqXtg%3A1663739640147&ei=-KYqY6CsCLez0PEP0Ias2AI&ved=0ahUKEwigiP-RmaX6AhW3GTQIHVADCysQ4dUDCAU&uact=5&oq=REPLACE&gs_lcp=Cgtwcm9kdWN0cy1jYxADMgUIABCABDIFCAAQgAQyBQgAEIAEMgsIABCABBCxAxCDATIECAAQAzIFCAAQgAQyBQgAEIAEMgUIABCABDIFCAAQgAQyBQgAEIAEOgsIABAeEA8QsAMQGDoNCAAQHhAPELADEAUQGDoGCAAQChADSgQIQRgBUM4MWO4TYJoVaAFwAHgAgAFDiAGNA5IBATeYAQCgAQHIAQPAAQE&sclient=products-cc"

    soup = create_soup(url, headers)
    similarity_threshold = 0.5

    try:
        prices = listing_product_similarity(soup, title, similarity_threshold)
        assert len(prices) > 0
    except AssertionError:
        print("Error: no viable products found, now searching for more general products...")
        while len(prices) == 0:
            ramp_down += 0.05
            prices = listing_product_similarity(soup, title, similarity_threshold - ramp_down)
    
    median = statistics.median_grouped(prices)
    
    return min(prices), max(prices), median

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
        print("Error: URL is not from Facebook Marketplace.")
        exit(1)

    shortened_url = re.search(r".*[0-9]", url).group(0)
    mobile_url = shortened_url.replace("www", "m")

    sentiment_rating = sentiment_analysis(get_listing_description(create_soup(url, headers=None)))
    title = get_listing_title(create_soup(url, headers=None))

    initial_price = int(re.sub("[\$,]", "", get_listing_price(create_soup(mobile_url, headers=None))))
    lower_bound, upper_bound, median = find_viable_product(title, ramp_down=0.0)

    price_rating = price_difference_rating(initial_price, median)
    average_rating = statistics.mean([sentiment_rating, price_rating])

    print("\nProduct: {} \nPrice: ${:,.2f}\n".format(title, initial_price))
    print("Price range of similar products: ${:,.2f} - ${:,.2f}".format(lower_bound, upper_bound))
    print("Price median: ${:,.2f}\n".format(median))
    print("Description rating: {}".format(stars(sentiment_rating)))
    print("Price rating: {}".format(stars(price_rating)))
    print("Overall rating: {}".format(stars(average_rating)))

if __name__ == "__main__":
    main()