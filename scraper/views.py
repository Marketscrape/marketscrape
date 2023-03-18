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
import datetime

class Index(View):
    def get(self, request):
        form = MarketForm()
        return render(request, 'scraper/index.html', {'form': form})

    def post(self, request):
        form = MarketForm(request.POST)

        if form.is_valid():
            url = form.cleaned_data['url']

        shortened_url = re.search(r".*[0-9]", url).group(0)
        mobile_url = shortened_url.replace("www", "m")
        market_id = (re.search(r"\/item\/([0-9]*)", url)).group(1)

        image = self.get_listing_image(self.create_soup(mobile_url, headers=None))

        days, hours = self.get_listing_date(self.create_soup(mobile_url, headers=None))
        
        sentiment_rating = self.sentiment_analysis(self.get_listing_description(self.create_soup(url, headers=None)))

        title = self.get_listing_title(self.create_soup(url, headers=None))
        
        list_price = self.get_listing_price(self.create_soup(mobile_url, headers=None))
        list_price = re.sub("[\$,]", "", list_price)
        initial_price = int(re.sub("[\$,]", "", list_price))

        lower_bound, upper_bound, median = self.find_viable_product(title, ramp_down=0.0)

        price_rating = self.price_difference_rating(initial_price, median)
        average_rating = statistics.mean([sentiment_rating, price_rating])

        context = {
            'shortened_url': shortened_url,
            'mobile_url': mobile_url,
            'market_id': market_id,
            'sentiment_rating': round(sentiment_rating, 1),
            'title': title,
            'list_price': "{0:,.2f}".format(float(list_price)),
            'initial_price': initial_price,
            'lower_bound': "{0:,.2f}".format(lower_bound),
            'upper_bound': "{0:,.2f}".format(upper_bound),
            'median': "{0:,.2f}".format(median),
            'price_rating': round(price_rating, 1),
            'average_rating': round(average_rating, 1),
            'days': days,
            'hours': hours,
            'image': image[0],
        }

        return render(request, 'scraper/result.html', context)

    def price_difference_rating(self, initial, final):
        if initial <= final:
            rating = 5.0
        else:
            difference = min(initial, final) / max(initial, final)
            rating = (difference / 20) * 100

        return rating

    def find_viable_product(self, title, ramp_down):
        title = self.clean_listing_title(title)
        headers = { 
            "User-Agent":
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582"
        }
        url = "https://www.google.com/search?q=" + title + "&sa=X&biw=1920&bih=927&tbm=shop&sxsrf=ALiCzsbtwkWiDOQEcm_9X1UBlEG1iaqXtg%3A1663739640147&ei=-KYqY6CsCLez0PEP0Ias2AI&ved=0ahUKEwigiP-RmaX6AhW3GTQIHVADCysQ4dUDCAU&uact=5&oq=REPLACE&gs_lcp=Cgtwcm9kdWN0cy1jYxADMgUIABCABDIFCAAQgAQyBQgAEIAEMgsIABCABBCxAxCDATIECAAQAzIFCAAQgAQyBQgAEIAEMgUIABCABDIFCAAQgAQyBQgAEIAEOgsIABAeEA8QsAMQGDoNCAAQHhAPELADEAUQGDoGCAAQChADSgQIQRgBUM4MWO4TYJoVaAFwAHgAgAFDiAGNA5IBATeYAQCgAQHIAQPAAQE&sclient=products-cc"

        soup = self.create_soup(url, headers)
        similarity_threshold = 0.25

        try:
            filtered_prices_descriptions = self.listing_product_similarity(soup, title, similarity_threshold)
            prices = list(filtered_prices_descriptions.values())
            assert len(prices) > 0
        except AssertionError:
            while len(prices) == 0:
                ramp_down += 0.05
                filtered_prices_descriptions = self.listing_product_similarity(soup, title, similarity_threshold - ramp_down)
                prices = list(filtered_prices_descriptions.values())

        median = statistics.median_grouped(prices)
        
        return min(prices), max(prices), median

    def clean_title_description(self, title):
        cleaned = re.sub(r"[^A-Za-z0-9\s]+", " ", title)
        cleaned = re.sub(r"\s+", " ", cleaned)

        return cleaned

    def listing_product_similarity(self, soup, title, similarity_threshold):
        normalized = self.get_product_price(soup)
        description = self.get_product_description(soup)

        price_description = {}
        for key, value in zip(description, normalized):
            google_shopping_title = self.clean_title_description(key.text.lower())
            listing_title = self.clean_title_description(title.lower())
            price_description[key.text] = [value, SequenceMatcher(None, google_shopping_title, listing_title).ratio()]

        filtered_prices_descriptions = {}
        for key, value in price_description.items():
            if value[1] >= similarity_threshold:
                filtered_prices_descriptions[key] = value[0]

        return filtered_prices_descriptions

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
        prices = soup.find_all("span", {"class": "HRLxBb"})

        values = []
        for price in prices:
            values.append(price.text)

        normalized = [re.sub("\$", "", price) for price in values]
        normalized = [re.search(r"[0-9,.]*", price).group(0) for price in normalized]
        normalized = [float(price.replace(",", "")) for price in normalized]
        
        outlierless = self.reject_outliers(np.array(normalized))

        return outlierless

    def clean_listing_title(self, title):
        title = re.sub(r"#", "%2", title)
        title = re.sub(r"&", "%26", title)

        return title

    def get_listing_price(self, soup):
        spans = soup.find_all("span")

        free = [span.text for span in spans if "free" in span.text.lower()]
        if (free):
            return free

        price = [str(span.text) for span in spans if "$" in span.text][0]

        return price
    
    def get_listing_image(self, soup):
        images = soup.find_all("img")
        image = [image["src"] for image in images if "https://scontent" in image["src"]]

        return image

    def get_listing_title(self, soup):
        title = soup.find("meta", {"name": "DC.title"})
        title_content = title["content"]
        return title_content
    
    def get_listing_date(self, soup):
        tag = soup.find('abbr')
        tag = tag.text.strip()

        try:
            month_str = re.search(r"[a-zA-Z]+", tag).group(0)
            month_num = datetime.datetime.strptime(month_str, '%B').month
        except ValueError:
            hour_str = re.search(r"[0-9]+", tag).group(0)
            return 0, hour_str

        try:
            year_str = re.search(r"[0-9]{4}", tag).group(0)
        except AttributeError:
            year_str = datetime.datetime.now().year

        date_str = re.search(r"[0-9]+", tag).group(0)
        time_str = re.search(r"[0-9]+:[0-9]+", tag).group(0)
        am_pm = re.search(r"[A-Z]{2}", tag).group(0)

        formated_time = f'{time_str}:00 {am_pm}'
        formated_date = f'{year_str}-{month_num}-{date_str}'

        dt_str = f'{formated_date} {formated_time}'
        dt = datetime.datetime.strptime(dt_str, '%Y-%m-%d %I:%M:%S %p')

        now = datetime.datetime.now()
        diff = now - dt

        days = diff.days
        hours = diff.seconds // 3600

        return days, hours


    def create_soup(self, url, headers):
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        return soup

    def clean_text(self, text):
        tokenizer = RegexpTokenizer('\w+|\$[\d\.]+|http\S+')
        tokenized = tokenizer.tokenize(text)
        tokenized = [word.lower() for word in tokenized]

        stop_words = stopwords.words('english')
        filtered = [word for word in tokenized if word not in stop_words and word.isalpha()]

        lemmatizer = WordNetLemmatizer()
        lemmatized = [lemmatizer.lemmatize(word) for word in filtered]
        
        return " ".join(lemmatized)

    def get_listing_description(self, soup):
        description = soup.find("meta", {"name": "DC.description"})
        description_content = description["content"]

        return self.clean_text(description_content)

    def sentiment_analysis(self, text):
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