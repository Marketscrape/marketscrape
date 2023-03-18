from django.shortcuts import render
from django.views import View
from .forms import MarketForm

from .utils import create_soup, sentiment_analysis, find_viable_product, price_difference_rating

import re

import statistics
import datetime

class Index(View):
    def get(self, request):
        form = MarketForm()
        return render(request, 'scraper/index.html', {'form': form})

    def post(self, request):
        form = MarketForm(request.POST)

        if form.is_valid():
            url = form.cleaned_data['url']

        # Shorten the URL listing to the title of the listing
        shortened_url = re.search(r".*[0-9]", url).group(0)
        # Use the shortened URL and convert it to mobile, to get the price of the listing
        mobile_url = shortened_url.replace("www", "m")
        # Find the ID of the product
        market_id = (re.search(r"\/item\/([0-9]*)", url)).group(1)
        soup = create_soup(url, headers=None)

        instance = FacebookScraper(soup=soup)

        listing_image = instance.get_listing_image()
        listing_days, listing_hours = instance.get_listing_date()
        listing_description = instance.get_listing_description()
        
        sentiment_rating = sentiment_analysis(listing_description)

        title = instance.get_listing_title()
        
        list_price = instance.get_listing_price()
        list_price = re.sub("[\$,]", "", list_price)
        initial_price = int(re.sub("[\$,]", "", list_price))

        lower_bound, upper_bound, median = find_viable_product(title, ramp_down=0.0)

        price_rating = price_difference_rating(initial_price, median)
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
            'days': listing_days,
            'hours': listing_hours,
            'image': listing_image[0],
        }

        return render(request, 'scraper/result.html', context)

class FacebookScraper:
    def __init__(self, soup):
        self.soup = soup

    def get_listing_price(self):
        spans = self.soup.find_all("span")

        free = [span.text for span in spans if "free" in span.text.lower()]
        if (free):
            return free

        # Find the span that contains the price of the listing and extract the price
        price = [str(span.text) for span in spans if "$" in span.text][0]

        return price
    
    def get_listing_image(self):
        images = self.soup.find_all("img")
        image = [image["src"] for image in images if "https://scontent" in image["src"]]

        return image

    def get_listing_title(self):
        title = self.soup.find("meta", {"name": "DC.title"})
        title_content = title["content"]
        return title_content
    
    def get_listing_date(self):
        tag = self.soup.find('abbr')
        tag = tag.text.strip()

        month_str = re.search(r"[a-zA-Z]+", tag).group(0)
        month_num = datetime.datetime.strptime(month_str, '%B').month

        date_str = re.search(r"[0-9]+", tag).group(0)
        year_str = datetime.datetime.now().year

        time_str = re.search(r"[0-9]+:[0-9]+", tag).group(0)
        am_pm = re.search(r"[A-Z]{2}", tag).group(0)
        formated_time = f'{time_str}:00 {am_pm}'

        date_str = f'{year_str}-{month_num}-{date_str}'

        dt_str = f'{date_str} {formated_time}'
        dt = datetime.datetime.strptime(dt_str, '%Y-%m-%d %I:%M:%S %p')

        now = datetime.datetime.now()
        diff = now - dt

        days = diff.days
        hours = diff.seconds // 3600

        return days, hours

    def get_listing_description(self):
        description = self.soup.find("meta", {"name": "DC.description"})
        description_content = description["content"]

        return self.clean_text(description_content)