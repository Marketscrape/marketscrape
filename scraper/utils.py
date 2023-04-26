from bs4 import BeautifulSoup
from .exceptions import *
import numpy as np
import requests
import re
import plotly.express as px
import pandas as pd

def remove_illegal_characters(title: str) -> str:
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

def clean_text(title: str) -> str:
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

def reject_outliers(data: list[float], m: float) -> list[int]:
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
        A list of indices where the outliers occured.
    """

    try:
        if len(data) <= 0:
            raise InvalidDataFormat("No data was provided")

        distribution = np.abs(data - np.median(data))
    except InvalidDataFormat:
        return []

    m_deviation = np.median(distribution)
    standard = distribution / (m_deviation if m_deviation else 1.)

    indices = np.where(standard >= m)[0]

    return indices.tolist()

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
        price_difference = initial - final
        rating = 5.0 - (price_difference / initial) * 5.0
    
    return max(0.0, min(rating, 5.0))

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

def create_chart(shortened_item_names: list[str], similar_prices: list[float], similar_descriptions: list[str], similar_urls: list[str]) -> object:
    """
    Creates a scatter chart using Plotly Express to visualize a list of items with their prices, descriptions, and URLs.

    Args:
        shortened_item_names (list[str]): A list of shortened names of the items.
        similar_prices (list[float]): A list of prices of the items.
        similar_descriptions (list[str]): A list of descriptions of the items.
        similar_urls (list[str]): A list of URLs of the items.

    Returns:
        A Plotly JSON object containing the scatter chart.
    """

    # Create a DataFrame from the data
    data = {'Product': shortened_item_names, 'Price': similar_prices, 'Description': similar_descriptions, 'URL': similar_urls}
    df = pd.DataFrame(data)

    # Determine color range bounds and size reference for the chart
    cmin = min(similar_prices)
    cmax = max(similar_prices)
    desired_diameter = 150
    sizeref = cmax / desired_diameter

    # Create a scatter chart using Plotly Express
    fig = px.scatter(df, x='Product', text='Description', y='Price', size='Price', color='Price', color_continuous_scale='RdYlGn_r', range_color=[cmin, cmax])
    fig.update_traces(mode='markers', marker=dict(symbol='circle', sizemode='diameter', sizeref=sizeref))
    fig.update_layout(template='plotly_white')

    return fig.to_json() 