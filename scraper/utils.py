from nltk.corpus import stopwords
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import RegexpTokenizer
from nltk.stem import WordNetLemmatizer
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
import numpy as np
import requests
import re

def clean_text(text: str) -> str:
    """
    Cleans a string of text by removing punctuation and extra whitespace.

    Args:
        text: The string of text to clean.

    Returns:
        The cleaned string of text.
    """
    tokenizer = RegexpTokenizer('\w+|\$[\d\.]+|http\S+')
    tokenized = tokenizer.tokenize(text)
    tokenized = [word.lower() for word in tokenized]

    stop_words = stopwords.words('english')
    filtered = [word for word in tokenized if word not in stop_words and word.isalpha()]

    lemmatizer = WordNetLemmatizer()
    lemmatized = [lemmatizer.lemmatize(word) for word in filtered]
    
    return " ".join(lemmatized)

def clean_listing_title(title: str) -> str:
    """
    Clean a listing title by removing punctuation and converting to lowercase.

    Args:
        title: The listing title to clean.

    Returns:
        The cleaned listing title.
    """
    title = re.sub(r"#", "%2", title)
    title = re.sub(r"&", "%26", title)

    return title

def clean_title_description(title: str) -> str:
    """
    Remove non-ASCII characters from title and description fields.

    Args:
        title (str): Title of the item.

    Returns:
        str: Cleaned title.
    """
    cleaned = re.sub(r"[^A-Za-z0-9\s]+", " ", title)
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned

def get_product_description(soup: BeautifulSoup) -> str:
    """
    Returns the product description in the soup.

    Args:
        soup: a BeautifulSoup object containing a product page

    Returns:
        The product description
    """
    description = soup.find_all("div", {"class": "rgHvZc"})

    return description

def get_product_url(soup: BeautifulSoup) -> str:
    """
    Returns the product URL in the soup.

    Args:
        soup: a BeautifulSoup object containing a product page

    Returns:
        The product URL
    """
    urls = soup.find_all("div", {"class": "rgHvZc"})

    values = []
    for url in urls:
        link = url.find('a', href=True)
        result = link['href'].replace('/url?url=', '')
        values.append(result)

    return values

def get_product_price(soup: BeautifulSoup) -> np.ndarray:
    """
    Extracts the price of each product from the HTML.

    Args:
        soup: The HTML to extract the price from.
        
    Returns:
        The price of each product. The price is represented as a
        NumPy array.
    """
    prices = soup.find_all("span", {"class": "HRLxBb"})

    values = []
    for price in prices:
        values.append(price.text)

    normalized = [re.sub("\$", "", price) for price in values]
    normalized = [re.search(r"[0-9,.]*", price).group(0) for price in normalized]
    normalized = [float(price.replace(",", "")) for price in normalized]
    
    outlierless = reject_outliers(np.array(normalized))

    return outlierless

def sentiment_analysis(text: str) -> float:
    """
    Returns the sentiment score of the text, with higher values indicating a more positive sentiment.

    Args:
        text (str): The text to analyze.
    Returns:
        float: The sentiment score, with higher values indicating a more positive sentiment.
    """
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

def create_soup(url: str, headers: dict) -> BeautifulSoup:
    """
    Create a BeautifulSoup object from a URL.

    Args:
        url (str): URL of the page to scrape
        headers (dict): Dictionary of headers to use in the request
    Returns:
        BeautifulSoup: BeautifulSoup object of the URL's HTML content
    """
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    return soup

def reject_outliers(data: list[float], m: float = 1.5) -> list[float]:
    """
    This function rejects outliers from the input list of data. The outliers are rejected using the
    Tukey method, which defines the outliers as the data that are more than m times the interquartile
    range outside the first and third quartiles. The default value of m is 1.5, but can be changed
    by the user.

    Args:
        data: A list of float values.
        m: A float value defining the number of interquartile ranges outside which the data are
            considered outliers. The default value is 1.5.

    Returns:
        A list of float values, with the outliers removed.
    """
    distribution = np.abs(data - np.median(data))
    m_deviation = np.median(distribution)
    standard = distribution / (m_deviation if m_deviation else 1.)

    return data[standard < m].tolist()

def price_difference_rating(initial: float, final: float) -> float:
    """
    The rating is based on the difference between the initial and final
    price. The rating is 0 if the final price is greater than the initial
    price, and 1 if the initial price is greater than the final price.
    Otherwise, the rating is the ratio of the initial price to the final
    price.

    Args:
        initial: The initial price.
        final: The final price.

    Returns:
        The rating.
    """
    if initial <= final:
        rating = 5.0
    else:
        difference = min(initial, final) / max(initial, final)
        rating = (difference / 20) * 100

    return rating

def find_viable_product(title: str, ramp_down: float) -> tuple[float, float, float]:
    """
    Finds viable products based on the title of the Marketplace listing,
    and utilizes the ramp down of the previous product in the sequence, to 
    find the descriptions, prices, and urls of the prices of the product.

    Args:
        title: The title of the product.
        ramp_down: The ramp down of the previous product in the
            sequence.

    Returns:
        The descriptions, prices and urls the viable products.
    """
    cleaned_title = clean_listing_title(title)
    headers = { 
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582"
    }

    url = f"https://www.google.com/search?q={cleaned_title}&sa=X&biw=1920&bih=927&tbm=shop&sxsrf=ALiCzsbtwkWiDOQEcm_9X1UBlEG1iaqXtg%3A1663739640147&ei=-KYqY6CsCLez0PEP0Ias2AI&ved=0ahUKEwigiP-RmaX6AhW3GTQIHVADCysQ4dUDCAU&uact=5&oq=REPLACE&gs_lcp=Cgtwcm9kdWN0cy1jYxADMgUIABCABDIFCAAQgAQyBQgAEIAEMgsIABCABBCxAxCDATIECAAQAzIFCAAQgAQyBQgAEIAEMgUIABCABDIFCAAQgAQyBQgAEIAEOgsIABAeEA8QsAMQGDoNCAAQHhAPELADEAUQGDoGCAAQChADSgQIQRgBUM4MWO4TYJoVaAFwAHgAgAFDiAGNA5IBATeYAQCgAQHIAQPAAQE&sclient=products-cc"
    soup = create_soup(url, headers)
    similarity_threshold = 0.25

    try:
        filtered_prices_descriptions = listing_product_similarity(soup, cleaned_title, similarity_threshold)
        assert len(filtered_prices_descriptions) > 0
    except AssertionError:
        while len(filtered_prices_descriptions) == 0:
            ramp_down += 0.05
            filtered_prices_descriptions = listing_product_similarity(soup, cleaned_title, similarity_threshold - ramp_down)

    descriptions = list(filtered_prices_descriptions.keys())

    prices = list(filtered_prices_descriptions.values())
    prices = [f"{price['price']:,.2f}" for price in prices]

    urls = [price['url'] for price in filtered_prices_descriptions.values()]
    
    return descriptions, prices, urls

def listing_product_similarity(soup: BeautifulSoup, title: str, similarity_threshold: float) -> dict:
    """
    Returns a dictionary of all products listed on the page that are similar to the given title.

    Args:
        soup (BeautifulSoup): The parsed HTML of the page.
        title (str): The title of the product to compare against.
        similarity_threshold (float): The minimum similarity ratio to consider a product similar.

    Returns:
        dict: A dictionary mapping the product ID to the product title.
    """
    normalized = get_product_price(soup)
    description = get_product_description(soup)
    url = get_product_url(soup)

    price_description = {}
    for key, value, product_url in zip(description, normalized, url):
        google_shopping_title = clean_title_description(key.text.lower())
        listing_title = clean_title_description(title.lower())
        price_description[key.text] = {'price': value, 'similarity': SequenceMatcher(None, google_shopping_title, listing_title).ratio(), 'url': product_url}

    filtered_prices_descriptions = {}
    for key, value in price_description.items():
        if value['similarity'] >= similarity_threshold:
            filtered_prices_descriptions[key] = {'price': value['price'], 'url': value['url']}

    return filtered_prices_descriptions


def percentage_difference(list_price: float, best_price: float) -> dict:
    """
    Returns a dictionary of both the percentage difference between the listing price and the best
    found price via Google Shopping, and whether or not the difference is categorized as being an
    increase or decrease.

    Args:
        list_price (float): The listing price.
        best_price (float): The best found price.
    
    Returns:
        dict: A dictionary mapping the percentage difference amount to the difference type.
    """
    difference = {
        "amount": -1,
        "type": "NaN"
    }

    if list_price > best_price:
        percentage = (np.abs(list_price - best_price) / list_price) * 100
        difference["amount"] = f"{percentage:.2f}"
        difference["type"] = "decrease"
    else:
        percentage = (np.abs(best_price - list_price) / best_price) * 100
        difference["amount"] = f"{percentage:.2f}"
        difference["type"] = "increase"

    return difference