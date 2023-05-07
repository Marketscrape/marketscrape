from bs4 import BeautifulSoup
from .exceptions import *
import numpy as np
import requests
import re
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import mean_squared_error
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
    found price via Ebay, and whether or not the difference is categorized as being an
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

def create_chart(similar_prices: list[float], similar_shipping: list[float], similar_descriptions: list[str], similar_conditions: list[str], listing_currency: str, listing_title: str, best_title: str) -> object:
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
    
    sorted_indices = np.argsort(similar_shipping)
    sorted_similar_prices = np.array([similar_prices[i] for i in sorted_indices]).reshape(-1, 1)
    sorted_similar_shipping = np.array([similar_shipping[i] for i in sorted_indices])
    sorted_similar_descriptions = np.array([similar_descriptions[i] for i in sorted_indices])
    sorted_similar_conditions = np.array([similar_conditions[i] for i in sorted_indices])
  
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=sorted_similar_prices[:, 0], 
            y=sorted_similar_shipping, 
            mode='markers',
            marker=dict(
                color=sorted_similar_prices[:, 0] + sorted_similar_shipping,
                colorscale='RdYlGn_r',
                colorbar=dict(title="Total Price"),
                size=8
            ),
            hovertemplate="%{text}",
            text=[
                f"Product: {desc.title()}<br>Price: ${price:,.2f}<br>Shipping: ${ship:,.2f}<br>Condition: {cond}" 
                for desc, price, ship, cond in zip(sorted_similar_descriptions, sorted_similar_prices[:, 0], sorted_similar_shipping, sorted_similar_conditions)
            ],
            showlegend=False,
            name="Products"
        )
    )
    
    fig.update_layout(
        template='plotly_white', 
        hovermode='closest', 
        xaxis_title=f"Product Price $({listing_currency})", 
        yaxis_title=f"Shipping Cost $({listing_currency})",
        legend_title="Categories", 
        title={
            'text': f"Products Similar to: {listing_title}", 
            'xanchor': 'center',
            'yanchor': 'top',
            'y': 0.9, 
            'x': 0.5
        }
    )
    
    # Add best match annotation
    best_price = similar_prices[similar_descriptions.index(best_title)]
    best_shipping = similar_shipping[similar_descriptions.index(best_title)]
    fig.add_trace(
        go.Scatter(
            x=[best_price],
            y=[best_shipping],
            mode='markers',
            marker=dict(
                color='#fc0',
                symbol='star',
                size=12
            ),
            showlegend=False,
            hoverinfo='skip'
        )
    )

    # Perform polynomial regression to obtain polynomial coefficients
    poly_features = PolynomialFeatures(degree=4, include_bias=True)
    X_poly = poly_features.fit_transform(sorted_similar_prices)
    poly_model = LinearRegression()
    poly_model.fit(X_poly, sorted_similar_shipping)

    X_range = np.linspace(sorted_similar_prices.min(), sorted_similar_prices.max(), 100)
    X_range_poly = poly_features.fit_transform(X_range.reshape(-1, 1))
    Y_range = poly_model.predict(X_range_poly)

    # Calculate confidence interval
    y_pred = poly_model.predict(X_poly)
    mse = mean_squared_error(sorted_similar_shipping, y_pred)
    # 95% confidence interval
    ci = 1.96 * np.sqrt(mse)

    upper_bound = Y_range + ci
    lower_bound = Y_range - ci

    fig.add_trace(
        go.Scatter(
            x=X_range, 
            y=Y_range, 
            mode='lines', 
            hovertemplate="%{text}",
            text=[f"Predicted Price: ${price:.2f}<br>Predicted Shipping: ${ship:.2f}" for price, ship in zip(X_range, Y_range)],
            showlegend=False,
            name="Trend Line",
            line_color='rgb(128, 128, 128)',
            line=dict(
                dash='longdash',
            )
        )
    )

    fig.add_trace(
        go.Scatter(
            x=np.concatenate([X_range, X_range[::-1]]),
            y=np.concatenate([upper_bound, lower_bound[::-1]]),
            fill='toself',
            fillcolor='rgba(128, 128, 128, 0.15)',
            line_color='rgba(255, 255, 255, 0)',
            hoverinfo="skip",
            showlegend=False
        )
    )

        
    return fig.to_json()

def create_bargraph(countries: list[str]) -> object:
    """
    Creates a word cloud visualization based on a list of countries.

    Args:
        countries (list[str]): A list of countries to be used to generate the word cloud.

    Returns:
        A JSON string containing the Plotly Express figure of the word cloud.
    """

    # Count the occurrences of each country
    country_counts = Counter(countries)
    
    # Get the names and counts of the countries
    country_names = list(country_counts.keys())
    country_values = list(country_counts.values())
    
    # Create a bar graph with the country names on the x-axis and counts on the y-axis
    fig = go.Figure(
        go.Bar(
            x=country_names,
            y=country_values,
            hoverinfo='text',
            hovertext=[f"Country: {country}<br>Citations: {count}" for country, count in zip(country_names, country_values)],
            marker=dict(
                color=country_values,
                colorscale='RdYlGn_r',
                showscale=True,
                colorbar=dict(
                    title='Citations'
                )
            )
        )
    )
    
    fig.update_layout(
        xaxis_title="Country of Origin",
        yaxis_title="Citations",
        title={
            'text': "Frequently Cited Countries",
            'xanchor': 'center',
            'yanchor': 'top',
            'y': 0.9,
            'x': 0.5},
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig.to_json()