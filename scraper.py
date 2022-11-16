# Database
import database

# Web Scraping
import requests
from bs4 import BeautifulSoup

# Math
import statistics
import numpy as np

# Currency Conversion
from currency_converter import CurrencyConverter

# Sentiment Analysis
#nltk.download()
#nltk.download('stopwords')
from nltk.corpus import stopwords
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import RegexpTokenizer
from nltk.stem import WordNetLemmatizer
from difflib import SequenceMatcher

# Pattern Matching
import re

def sentiment_analysis(text):
    # Create a SentimentIntensityAnalyzer object
    sia = SentimentIntensityAnalyzer()
    sentiment = sia.polarity_scores(text)
    # Get the sentiment scores
    neg, neu, pos, compound = sentiment["neg"], sentiment["neu"], sentiment["pos"], sentiment["compound"]

    # Assign a rating based on the compound score
    if compound > 0.0:
        rating = 5 * max(pos, compound)
    elif compound < 0.0:
        rating = 5 * min(neg, compound)
    else:
        rating = 5 * neu
        
    return abs(rating)

def clean_text(text):
    # Remove punctuation
    tokenizer = RegexpTokenizer('\w+|\$[\d\.]+|http\S+')
    tokenized = tokenizer.tokenize(text)
    # Lowercase all words
    tokenized = [word.lower() for word in tokenized]

    # Remove stopwords
    stop_words = stopwords.words('english')
    # Filter out any tokens not containing letters
    filtered = [word for word in tokenized if word not in stop_words and word.isalpha()]

    # Lemmatize all words
    lemmatizer = WordNetLemmatizer()
    lemmatized = [lemmatizer.lemmatize(word) for word in filtered]
    
    return " ".join(lemmatized)

def price_difference_rating(initial, final):
    # If the listing price is less than or equal to the median price found online, set the rating to 5
    if initial <= final:
        rating = 5.0
    else:
        # If the listing price is greater than the median price found online, calculate the difference
        difference = min(initial, final) / max(initial, final)
        rating = (difference / 20) * 100

    return rating

def get_listing_title(soup):
    # Get the title of the listing
    title = soup.find("meta", {"name": "DC.title"})
    title_content = title["content"]

    return title_content

def get_listing_description(soup):
    # Get the description of the listing
    description = soup.find("meta", {"name": "DC.description"})
    description_content = description["content"]

    return clean_text(description_content)

def get_listing_price(soup):
    # Get the price of the listing
    spans = soup.find_all("span")
    # Find the span that contains the price of the listing and extract the price
    price = [str(span.text) for span in spans if "$" in span.text][0]

    return price

def create_soup(url, headers):
    # Create a request object 
    response = requests.get(url, headers=headers)
    # Create a BeautifulSoup object
    soup = BeautifulSoup(response.text, 'html.parser')

    return soup

def convert_currency(price, base_currency, target_currency):
    # Convert the price to the target currency
    c = CurrencyConverter()
    price = c.convert(price, base_currency, target_currency)

    return price

def clean_listing_title(title):
    # Certain symbols are not allowed in the search query for Google Shopping, so they must be removed
    title = re.sub(r"#", "%2", title)
    title = re.sub(r"&", "%26", title)

    return title

def get_product_price(soup):
    # Get the price of the product
    prices = soup.find_all("span", {"class": "HRLxBb"})

    # Extract the price from the span
    values = []
    for price in prices:
        values.append(price.text)

    # Remove the dollar sign from the price
    normalized = [re.sub("\$", "", price) for price in values]
    # Convert the price to a float
    normalized = [re.search(r"[0-9,.]*", price).group(0) for price in normalized]
    # Remove the commas from the price
    normalized = [float(price.replace(",", "")) for price in normalized]
    
    # Remove statistical outliers as to not skew the median price
    outlierless = reject_outliers(np.array(normalized))

    return outlierless

def get_product_description(soup):
    # Get the description of the product
    description = soup.find_all("div", {"class": "rgHvZc"})

    return description

def clean_title_description(title):
    # Remove punctuation
    cleaned = re.sub(r"[^A-Za-z0-9\s]+", " ", title)
    # Remove extra spaces
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned

def listing_product_similarity(soup, title, similarity_threshold):
    # Get the median price of the product
    normalized = get_product_price(soup)
    # Get the product description
    description = get_product_description(soup)

    price_description = {}
    # Iterate through the product descriptions
    for key, value in zip(description, normalized):
        google_shopping_title = clean_title_description(key.text.lower())
        listing_title = clean_title_description(title.lower())
        # Get the similarity between the listing title and the product description on Google Shopping
        price_description[key.text] = [value, SequenceMatcher(None, google_shopping_title, listing_title).ratio()]

    prices = []
    # Iterate through the product descriptions and their similarity scores
    for key, value in price_description.items():
        # If the similarity score is greater than the similarity threshold, add the price to the list of prices
        if value[1] >= similarity_threshold:
            prices.append(value[0])
    
    return prices   

def find_viable_product(title, ramp_down):
    title = clean_listing_title(title)
    headers = { 
        "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582"
    }
    url = "https://www.google.com/search?q=" + title + "&sa=X&biw=1920&bih=927&tbm=shop&sxsrf=ALiCzsbtwkWiDOQEcm_9X1UBlEG1iaqXtg%3A1663739640147&ei=-KYqY6CsCLez0PEP0Ias2AI&ved=0ahUKEwigiP-RmaX6AhW3GTQIHVADCysQ4dUDCAU&uact=5&oq=REPLACE&gs_lcp=Cgtwcm9kdWN0cy1jYxADMgUIABCABDIFCAAQgAQyBQgAEIAEMgsIABCABBCxAxCDATIECAAQAzIFCAAQgAQyBQgAEIAEMgUIABCABDIFCAAQgAQyBQgAEIAEOgsIABAeEA8QsAMQGDoNCAAQHhAPELADEAUQGDoGCAAQChADSgQIQRgBUM4MWO4TYJoVaAFwAHgAgAFDiAGNA5IBATeYAQCgAQHIAQPAAQE&sclient=products-cc"

    soup = create_soup(url, headers)
    # Set the similarity threshold to a initial value, and decrease it when no products are found
    similarity_threshold = 0.45

    try:
        prices = listing_product_similarity(soup, title, similarity_threshold)
        # The length of the list of prices should be greater than 0 if there are viable products
        assert len(prices) > 0
    except AssertionError:
        print("Error: no viable products found, now searching for more general products...")
        while len(prices) == 0:
            # If no viable products are found, the search is further generalized by 5%, until a reasonable number of products are found
            ramp_down += 0.05
            prices = listing_product_similarity(soup, title, similarity_threshold - ramp_down)
    
    # Get the median price of the viable products
    median = statistics.median_grouped(prices)
    
    return min(prices), max(prices), median

def valid_url(url):
    if re.search(r"^https://www.facebook.com/", url):
        return True
    else:
        return False

# The larger the value of m is, the less outliers are removed
# Source: https://stackoverflow.com/questions/62802061/python-find-outliers-inside-a-list
def reject_outliers(data, m=1.5):
    distribution = np.abs(data - np.median(data))
    m_deviation = np.median(distribution)
    standard = distribution / (m_deviation if m_deviation else 1.)
    return data[standard < m].tolist()

def print_results(title, initial_price, sentiment_rating, price_rating, average_rating, median, lower_bound, upper_bound):
    print("\n● Listing:")
    print("  ○ Product: {}".format(title))
    print("  ○ Price: ${:,.2f}".format(initial_price))
    print("● Similar products:")
    print("  ○ Range: ${:,.2f} - ${:,.2f}".format(lower_bound, upper_bound))
    print("  ○ Median: ${:,.2f}".format(median))
    print("● Ratings:")
    print("  ○ Description: {:,.2f}/5.00".format(sentiment_rating))
    print("  ○ Price: {:,.2f}/5.00".format(price_rating))
    print("  ○ Overall: {:,.2f}/5.00".format(average_rating))

def main():
    # Initialize the database
    database.initialize()

    # Get the URL of the Facebook Marketplace listing
    url = input("Enter URL: ")

    # Check if the URL is valid
    if valid_url(url):
        pass
    else:
        print("Error: URL is not from Facebook Marketplace.")
        exit(1)

    # Shorten the URL listing to the title of the listing
    shortened_url = re.search(r".*[0-9]", url).group(0)
    # Use the shortened URL and convert it to mobile, to get the price of the listing
    mobile_url = shortened_url.replace("www", "m")

    records = database.retrieve(url)
    if records:
        title = records[1]
        initial_price = records[2]
        sentiment_rating = records[3]
        price_rating = records[4]
        average_rating = records[5]
        median = records[6]
        lower_bound = records[7]
        upper_bound = records[8]
    elif not records:
        # Get the sentiment rating of the listing
        sentiment_rating = sentiment_analysis(get_listing_description(create_soup(url, headers=None)))

        # Get the title of the listing
        title = get_listing_title(create_soup(url, headers=None))

        # Get the minimum, maximum, and median prices of the viable products found on Google Shopping
        initial_price = int(re.sub("[\$,]", "", get_listing_price(create_soup(mobile_url, headers=None))))
        lower_bound, upper_bound, median = find_viable_product(title, ramp_down=0.0)

        # Calculate the price difference between the listing and the median price of the viable products, and generate ratings
        price_rating = price_difference_rating(initial_price, median)
        average_rating = statistics.mean([sentiment_rating, price_rating])

        # Add the listing to the database
        database.insert(url, title, initial_price, sentiment_rating, price_rating, average_rating, median, lower_bound, upper_bound)

    print_results(title, initial_price, sentiment_rating, price_rating, average_rating, median, lower_bound, upper_bound)

if __name__ == "__main__":
    main()