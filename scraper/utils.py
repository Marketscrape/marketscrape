from bs4 import BeautifulSoup
from .exceptions import *
import numpy as np
import requests
import re
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from wordcloud import WordCloud
from collections import Counter

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

def create_chart(categorized: dict, similar_prices: list[float], similar_descriptions: list[str]) -> object:
    """
    Creates a line chart visualization based on the categorized items, their prices, and their descriptions.

    Args:
        categorized (dict): A dictionary where the keys are the names of the clusters and the values are lists of the items in that cluster.
        similar_prices (list[float]): A list of prices of the items.
        similar_descriptions (list[str]): A list of descriptions of the items.

    Returns:
        A JSON string containing the Plotly figure of the line chart.
    """

    items, prices, descriptions = [], [], []
    unit = 1

    for categories, titles in categorized.items():
        items.append(categories)

        sub_prices, sub_descriptions = [], []
        for title in titles:
            idx = similar_descriptions.index(title)
            sub_prices.append(similar_prices[idx])

            sub_descriptions.append(title)
        prices.append(sub_prices)
        descriptions.append(sub_descriptions)

    fig = go.Figure()

    for i, _ in enumerate(items):
        x = [j*unit for j in range(len(prices[i]))]
        hovertext = [f"Product: {desc.title()}<br>Price: ${price:.2f}" for price, desc in zip(prices[i], descriptions[i])]
        fig.add_trace(go.Scatter(x=x, y=prices[i], mode='markers+lines', hovertemplate="%{text}", text=hovertext, name=f"Category {i+1}"))
        
    fig.update_layout(template='plotly_white', hovermode='x')
    
    return fig.to_json()

def create_wordcloud(urls: list[str]) -> tuple[object, dict]:
    """
    Creates a word cloud visualization based on a list of website URLs.

    Args:
        urls (list[str]): A list of website URLs to be used to generate the word cloud.

    Returns:
        A tuple of the following:
        - A JSON string containing the Plotly Express figure of the word cloud.
        - A dictionary where the keys are the website names and the values are the frequency count of each website in the URLs list.
    """

    websites = []
    for url in urls:
        match = re.search(r'^https?://(?:www\.)?([^/]+)', url)
        if match:
            website = match.group(1)
            websites.append(website)

    website_counts = Counter(websites)
    wordcloud = WordCloud(
        background_color='white',
        width=2000,
        height=1000, 
        scale=4, 
        prefer_horizontal=0.9,
        colormap='seismic_r').generate_from_frequencies(website_counts)

    fig = px.imshow(wordcloud)

    return fig.to_json(), dict(website_counts)

def categorize_titles(items: list[str]) -> dict:
    """
    Categorizes a list of text items using KMeans clustering and TF-IDF vectorization.

    Args:
    items (list[str]): A list of text items to be categorized.

    Returns:
    A dictionary where the keys are the names of the clusters and the values are lists of the items in that cluster.
    """

    vectorizer = TfidfVectorizer()
    X = vectorizer.fit_transform(items)

    num_clusters = len(items) // 5
    kmeans = KMeans(n_clusters=num_clusters, n_init=10)
    kmeans.fit(X)

    cluster_names = []
    for i in range(num_clusters):
        cluster_items = [items[j] for j in range(len(items)) if kmeans.labels_[j] == i]
        representative_item = f"{i+1}"
        cluster_names.append(representative_item)

    clusters = {}
    for i in range(num_clusters):
        cluster_items = [items[j] for j in range(len(items)) if kmeans.labels_[j] == i]
        cluster_name = cluster_names[i]
        clusters[cluster_name] = cluster_items

    return clusters