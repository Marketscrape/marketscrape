from django.shortcuts import render
from django.views import View
from .forms import MarketForm
from .utils import *
from .scraper_class import FacebookScraper
import re
import statistics
from .models import Item

class Index(View):
    def get(self, request):
        form = MarketForm()
        latest_items = Item.objects.all().order_by('-id')[:10]
        context = {'form': form, 'latest_items': latest_items}
        return render(request, 'scraper/index.html', context)

    def post(self, request):
        form = MarketForm(request.POST)
        if form.is_valid():
            url = form.cleaned_data['url']
            shortened_url = re.search(r".*[0-9]", url).group(0)
            mobile_url = shortened_url.replace("www", "m")
            market_id = re.search(r"\/item\/([0-9]*)", url).group(1)
            mobile_soup = create_soup(mobile_url, headers=None)
            base_soup = create_soup(url, headers=None)
            scraper_instance = FacebookScraper(mobile_soup, base_soup)

            listing_image = scraper_instance.get_listing_image()
            listing_days, listing_hours = scraper_instance.get_listing_date()
            listing_description = scraper_instance.get_listing_description()
            title = scraper_instance.get_listing_title()
            list_price = scraper_instance.get_listing_price()

            sentiment_rating = sentiment_analysis(listing_description)

            list_price = re.sub("[\$,]", "", list_price)
            initial_price = int(re.sub("[\$,]", "", list_price))

            lower_bound, upper_bound, median = find_viable_product(title, ramp_down=0.0)
            price_rating = price_difference_rating(initial_price, median)
            average_rating = statistics.mean([sentiment_rating, price_rating])

            # Create a new Item object
            average_rating = round(average_rating, 1)
            item = Item.objects.create(image=listing_image[0], title=title, rating=average_rating, url=shortened_url)

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
                'average_rating': average_rating,
                'days': listing_days,
                'hours': listing_hours,
                'image': listing_image[0],
                'id': market_id
            }

            return render(request, 'scraper/result.html', context)

        else:
            latest_items = Item.objects.all().order_by('-id')[:10]
            context = {'form': form, 'latest_items': latest_items}
            return render(request, 'scraper/index.html', context)
