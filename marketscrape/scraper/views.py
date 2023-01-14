from django.shortcuts import render
from django.views import View
from .forms import MarketForm

import re
from nltk.corpus import stopwords
from nltk.sentiment import SentimentIntensityAnalyzer
from nltk.tokenize import RegexpTokenizer
from nltk.stem import WordNetLemmatizer
import requests
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

import statistics
import numpy as np


class Index(View):
    def get(self, request):
        form = MarketForm()
        return render(request, 'scraper/index.html', {'form': form})

    def post(self, request):
        form = MarketForm(request.POST)

        if form.is_valid():
            input_url = form.cleaned_data['input_url']

        # Shorten the URL listing to the title of the listing
        shortened_url = re.search(r".*[0-9]", input_url).group(0)
        # Use the shortened URL and convert it to mobile, to get the price of the listing
        mobile_url = shortened_url.replace("www", "m")
        # Find the ID of the product
        market_id = (re.search(r"\/item\/([0-9]*)", input_url)).group(1)
        
        # Get the sentiment rating of the listing
        sentiment_rating = self.sentiment_analysis(self.get_listing_description(self.create_soup(input_url, headers=None)))

        # Get the title of the listing
        title = self.get_listing_title(self.create_soup(input_url, headers=None))
        
         # Get the minimum, maximum, and median prices of the viable products found on Google Shopping
        list_price = self.get_listing_price(self.create_soup(mobile_url, headers=None))
        initial_price = int(re.sub("[\$,]", "", list_price))

        lower_bound, upper_bound, median = self.find_viable_product(title, ramp_down=0.0)


        context = {
            'shortened_url': shortened_url,
            'mobile_url': mobile_url,
            'market_id': market_id,
            'sentiment_rating': sentiment_rating,
            'title': title,
            'list_price': list_price,
            'initial_price': initial_price,
            'lower_bound': lower_bound,
            'upper_bound': upper_bound,
            'median': median,
        }
        return render(request, 'scraper/result.html', context)

    def find_viable_product(self, title, ramp_down):
        title = self.clean_listing_title(title)
        headers = { 
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582"
        }
        url = "https://www.google.com/search?q=" + title + "&sa=X&biw=1920&bih=927&tbm=shop&sxsrf=ALiCzsbtwkWiDOQEcm_9X1UBlEG1iaqXtg%3A1663739640147&ei=-KYqY6CsCLez0PEP0Ias2AI&ved=0ahUKEwigiP-RmaX6AhW3GTQIHVADCysQ4dUDCAU&uact=5&oq=REPLACE&gs_lcp=Cgtwcm9kdWN0cy1jYxADMgUIABCABDIFCAAQgAQyBQgAEIAEMgsIABCABBCxAxCDATIECAAQAzIFCAAQgAQyBQgAEIAEMgUIABCABDIFCAAQgAQyBQgAEIAEOgsIABAeEA8QsAMQGDoNCAAQHhAPELADEAUQGDoGCAAQChADSgQIQRgBUM4MWO4TYJoVaAFwAHgAgAFDiAGNA5IBATeYAQCgAQHIAQPAAQE&sclient=products-cc"

        soup = self.create_soup(url, headers)
        # Set the similarity threshold to a initial value, and decrease it when no products are found
        similarity_threshold = 0.45

        try:
            prices = self.listing_product_similarity(soup, title, similarity_threshold)
            # The length of the list of prices should be greater than 0 if there are viable products
            assert len(prices) > 0
        except AssertionError:
            print("Error: no viable products found, now searching for more general products...")
            while len(prices) == 0:
                # If no viable products are found, the search is further generalized by 5%, until a reasonable number of products are found
                ramp_down += 0.05
                prices = self.listing_product_similarity(soup, title, similarity_threshold - ramp_down)
        
        # Get the median price of the viable products
        median = statistics.median_grouped(prices)
        
        return min(prices), max(prices), median

    def clean_title_description(self, title):
        # Remove punctuation
        cleaned = re.sub(r"[^A-Za-z0-9\s]+", " ", title)
        # Remove extra spaces
        cleaned = re.sub(r"\s+", " ", cleaned)

        return cleaned

    def listing_product_similarity(self, soup, title, similarity_threshold):
        # Get the median price of the product
        normalized = self.get_product_price(soup)
        # Get the product description
        description = self.get_product_description(soup)

        price_description = {}
        # Iterate through the product descriptions
        for key, value in zip(description, normalized):
            google_shopping_title = self.clean_title_description(key.text.lower())
            listing_title = self.clean_title_description(title.lower())
            # Get the similarity between the listing title and the product description on Google Shopping
            price_description[key.text] = [value, SequenceMatcher(None, google_shopping_title, listing_title).ratio()]

        prices = []
        # Iterate through the product descriptions and their similarity scores
        for key, value in price_description.items():
            # If the similarity score is greater than the similarity threshold, add the price to the list of prices
            if value[1] >= similarity_threshold:
                prices.append(value[0])
        
        return prices

    def get_product_description(self, soup):
        # Get the description of the product
        description = soup.find_all("div", {"class": "rgHvZc"})
        return description

    def reject_outliers(self, data, m=1.5):
        distribution = np.abs(data - np.median(data))
        m_deviation = np.median(distribution)
        standard = distribution / (m_deviation if m_deviation else 1.)
        return data[standard < m].tolist()


    def get_product_price(self, soup):
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
        outlierless = self.reject_outliers(np.array(normalized))

        return outlierless

    def clean_listing_title(self, title):
        # Certain symbols are not allowed in the search query for Google Shopping, so they must be removed
        title = re.sub(r"#", "%2", title)
        title = re.sub(r"&", "%26", title)
        return title

    def get_listing_price(self, soup):
        # Get the price of the listing
        spans = soup.find_all("span")

        # Check if the listing is free
        free = [span.text for span in spans if "free" in span.text.lower()]
        if (free):
            return free

        # Find the span that contains the price of the listing and extract the price
        price = [str(span.text) for span in spans if "$" in span.text][0]
        return price

    def get_listing_title(self, soup):
        # Get the title of the listing
        title = soup.find("meta", {"name": "DC.title"})
        title_content = title["content"]
        return title_content

    def create_soup(self, url, headers):
        # Create a request object 
        response = requests.get(url, headers=headers)
        # Create a BeautifulSoup object
        soup = BeautifulSoup(response.text, 'html.parser')
        return soup

    def clean_text(self, text):
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

    def get_listing_description(self, soup):
        # Get the description of the listing
        description = soup.find("meta", {"name": "DC.description"})
        description_content = description["content"]
        return self.clean_text(description_content)

    def sentiment_analysis(self, text):
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


    