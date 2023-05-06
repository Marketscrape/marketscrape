from bs4 import BeautifulSoup
from .exceptions import *
import numpy as np
import requests
import re
import plotly.express as px
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
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

def price_difference_rating(initial: float, final: float, days: int) -> float:
    """
    The rating is based on the difference between the initial and final
    price. The rating is 0 if the final price is greater than the initial
    price, and 1 if the initial price is greater than the final price.
    Otherwise, the rating is the ratio of the initial price to the final
    price.

    Args:
        initial: The initial price.
        final: The final price.
        days: The number of days a listing has been active.

    Returns:
        The rating.
    """
    
    # Decay constant (a value greater than 0)
    decay_constant = 0.01

    # Adjust this value to control the rate of increase of the penalty
    linear_factor = 0.0125

    # Threshold number of days after which the penalty is applied
    threshold_days = 7

    if days >= threshold_days:
        days_past_threshold = days - threshold_days
        penalty_amount = initial*np.exp(-decay_constant*days_past_threshold) + linear_factor*days_past_threshold*initial
        initial += penalty_amount

    if initial <= final:
        rating = 5.0
    else:
        price_difference = initial - final
        rating = 5.0 - (price_difference/initial)*5.0
    
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

def create_chart(categorized: dict, similar_prices: list[float], similar_shipping: list[float], similar_descriptions: list[str], listing_currency: str, listing_title: str) -> object:
    """
    Creates a line chart visualization based on the categorized items, their prices, and their descriptions.

    Args:
        categorized (dict): A dictionary where the keys are the names of the clusters and the values are lists of the items in that cluster.
        similar_prices (list[float]): A list of prices of the items.
        similar_shipping (list[float]): A list of shipping costs of the items.
        similar_descriptions (list[str]): A list of descriptions of the items.

    Returns:
        A JSON string containing the Plotly figure of the line chart.
    """

    items, prices, shipping, descriptions = [], [], [], []
    unit = 1

    for categories, titles in categorized.items():
        items.append(categories)

        sub_prices, sub_shipping, sub_descriptions = [], [], []
        for title in titles:
            idx = similar_descriptions.index(title)

            sub_prices.append(similar_prices[idx])
            sub_shipping.append(similar_shipping[idx])
            sub_descriptions.append(title)
        prices.append(sub_prices)
        shipping.append(sub_shipping)
        descriptions.append(sub_descriptions)
    
    sort_indices = [sorted(range(len(sublist)), key=lambda x: sublist[x]) for sublist in prices]
    sorted_prices = [[sublist[i] for i in indices] for sublist, indices in zip(prices, sort_indices)]

    sorted_shipping = [[sublist[i] for i in indices] for sublist, indices in zip(shipping, sort_indices)]
    formatted_shipping = [[f"${ship}" if ship != "0.00" else "Free" for ship in row] for row in sorted_shipping]

    sorted_descriptions = [[sublist[i] for i in indices] for sublist, indices in zip(descriptions, sort_indices)]

    fig = go.Figure()

    for i, _ in enumerate(items):
        x = [j*unit + 1 for j in range(len(sorted_prices[i]))]
        hovertext = [f"Product: {desc.title()}<br>Price: ${price:.2f}<br>Shipping: {ship}" for price, ship, desc in zip(sorted_prices[i], formatted_shipping[i], sorted_descriptions[i])]
        fig.add_trace(go.Scatter(
            x=x, y=sorted_prices[i], 
            mode='markers', 
            hovertemplate="%{text}", 
            text=hovertext, 
            name=f"Category {i + 1}"))

    # Compute the polynomial regression on all data points
    x = np.concatenate([np.arange(len(prices))*unit + 1 for prices in sorted_prices])
    y = np.concatenate(sorted_prices)

    poly_features = PolynomialFeatures(degree=4, include_bias=True)
    x_poly = poly_features.fit_transform(x.reshape(-1, 1))

    reg = LinearRegression().fit(x_poly, y)
    x_reg = np.linspace(np.min(x), np.max(x), num=100)
    x_reg_poly = poly_features.fit_transform(x_reg.reshape(-1, 1))
    y_reg = reg.predict(x_reg_poly)

    # Add the trend line to the plot
    fig.add_trace(
        go.Scatter(x=x_reg, 
            y=y_reg, 
            mode='lines', 
            name='Trend Line'))

    # Add annotations to all x values
    for x_val in x:
        y_val = reg.predict(poly_features.transform([[x_val]]))[0]
        fig.add_annotation(x=x_val, y=y_val, text=f"Prediction: ${y_val:.2f}", showarrow=True)
            
    fig.update_layout(
        template='plotly_white', 
        hovermode='closest', 
        xaxis_title="Product Number", 
        yaxis_title=f"Price $({listing_currency})", 
        legend_title="Categories", 
        title={
            'text': f"Products Similar to: {listing_title}", 
            'xanchor': 'center',
            'yanchor': 'top',
            'y': 0.9, 
            'x': 0.5})
    
    return fig.to_json()

def create_wordcloud(urls: list[str]) -> object:
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
        scale=4, 
        prefer_horizontal=0.9,
        colormap='rainbow').generate_from_frequencies(website_counts)

    fig = px.imshow(wordcloud)
    fig.update_layout(
        xaxis_title="Website URL",
        yaxis_title="Citations",
        title={
            'text': "Frequently Cited Websites",
            'xanchor': 'center',
            'yanchor': 'top',
            'y': 0.9,
            'x': 0.5})

    return fig.to_json()

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

    wcss = []
    for i in range(1, len(items)//2):
        kmeans = KMeans(n_clusters=i, n_init=10)
        kmeans.fit(X)
        wcss.append(kmeans.inertia_)

    # Select the optimal number of clusters based on the elbow point
    optimal_num_clusters = int(min(wcss))
    kmeans = KMeans(n_clusters=optimal_num_clusters, n_init=10)
    kmeans.fit(X)

    clusters = {}
    for i in range(optimal_num_clusters):
        cluster_items = [items[j] for j in range(len(items)) if kmeans.labels_[j] == i]
        representative_item = f"{i + 1}"
        clusters[representative_item] = cluster_items

    return clusters