from bs4 import BeautifulSoup
from difflib import SequenceMatcher
import numpy as np
import requests
import string
import re

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

def compare_titles(string1: str, string2: str) -> float:
    """
    Compares two titles using the SequenceMatcher class from the difflib
    module. The similarity is returned as a float between 0 and 1.

    Args:
        string1: The first title.
        string2: The second title.

    Returns:
        The similarity between the two titles.
    """

    string1 = string1.lower().strip()
    string2 = string2.lower().strip()

    string1 = ' '.join(string1.split())
    string2 = ' '.join(string2.split())

    translator = str.maketrans('', '', string.punctuation)
    string1_clean = string1.translate(translator)
    string2_clean = string2.translate(translator)

    # Compute the similarity score using SequenceMatcher
    similarity = SequenceMatcher(None, string1_clean, string2_clean).ratio()

    return similarity

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
        price_diff = initial - final
        rating = 5.0 - (price_diff / initial) * 5.0
    
    return max(0.0, min(rating, 5.0))

def lowest_price_highest_similarity(filtered_prices_descriptions: dict) -> tuple[float, str, float]:
    """
    Finds the lowest price and the highest similarity of the filtered
    prices and descriptions.

    Args:
        filtered_prices_descriptions: The filtered prices and descriptions.

    Returns:
        The lowest price, the highest similarity, and the description
        associated with the highest similarity.
    """
    
    # Initialize variables to hold the item with the highest similarity and lowest price
    max_similarity_item = None
    min_price_item = None

    # Iterate over each item in the dictionary
    for item_name, item_details in filtered_prices_descriptions.items():
        # If this is the first item we've seen, initialize max_similarity_item and min_price_item to this item
        if max_similarity_item is None and min_price_item is None:
            max_similarity_item = item_details
            min_price_item = item_details
        else:
            # Compare the similarity and price of the current item to the current max_similarity_item and min_price_item
            if item_details['similarity'] > max_similarity_item['similarity']:
                max_similarity_item = item_details
            if item_details['price'] < min_price_item['price']:
                min_price_item = item_details

    # Check if the highest similarity item is the same as the lowest price item
    if max_similarity_item == min_price_item:
        return (item_name, max_similarity_item)
    else:
        # Find the item with the highest similarity
        max_similarity_item = max(filtered_prices_descriptions.values(), key=lambda x: x['similarity'])

        # Find all items that have the highest similarity
        max_similar_items = [(item_name, item_details) for item_name, item_details in filtered_prices_descriptions.items() if item_details['similarity'] == max_similarity_item['similarity']]

        # Find the item with the highest price among the items with the highest similarity
        max_similar_item = max(max_similar_items, key=lambda x: x[1]['price'])

        return max_similar_item
    
def construct_candidates(descriptions, prices, urls, similarities):
    """
    Constructs a list of candidates from the descriptions, prices, and
    urls.

    Args:
        descriptions: The descriptions of the products.
        prices: The prices of the products.
        urls: The urls of the products.

    Returns:
        The list of candidates.
    """

    candidates = {}
    # Construct a nested dictionary of candidates where the key is the description and the value is a dictionary containing the price, url, and similarity
    for i in range(len(descriptions)):
        candidates[descriptions[i]] = {
            "price": prices[i],
            "url": urls[i],
            "similarity": similarities[i]
        }

    return candidates


def find_viable_product(title: str, ramp_down: float) -> tuple[list, list, list]:
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

    descriptions = []
    prices = []
    urls = []
    similarities = []

    for page_number in range(3):
        start = page_number * 60
        url = f"https://www.google.com/search?q={cleaned_title}&tbs=vw:d&tbm=shop&sxsrf=APwXEdeCneQw6hWKHlHMJptjJHcIzqvmvw:1682209446957&ei=pnpEZILiOcmD0PEPifacgAw&start={start}&sa=N&ved=0ahUKEwiCzZfE3r7-AhXJATQIHQk7B8AQ8tMDCLEY&biw=1920&bih=927&dpr=1"
        soup = create_soup(url, headers)
        similarity_threshold = 0.25

        try:
            filtered_prices_descriptions = listing_product_similarity(soup, cleaned_title, similarity_threshold)
            assert len(filtered_prices_descriptions) > 0
        except AssertionError:
            while len(filtered_prices_descriptions) == 0:
                ramp_down += 0.05
                filtered_prices_descriptions = listing_product_similarity(soup, cleaned_title, similarity_threshold - ramp_down)

        descriptions += list(filtered_prices_descriptions.keys())

        prices += [f"{product['price']:,.2f}" for product in filtered_prices_descriptions.values()]

        urls += [product['url'] for product in filtered_prices_descriptions.values()]

        similarities += [product['similarity'] for product in filtered_prices_descriptions.values()]

    candidates = construct_candidates(descriptions, prices, urls, similarities)
    best_result = lowest_price_highest_similarity(candidates)

    return descriptions, prices, urls, best_result


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
        price_description[key.text] = {'price': value, 'similarity': compare_titles(google_shopping_title, listing_title), 'url': product_url}

    filtered_prices_descriptions = {}
    for key, value in price_description.items():
        if value['similarity'] >= similarity_threshold:
            filtered_prices_descriptions[key] = {'price': value['price'], 'url': value['url'], 'similarity': value['similarity']}

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