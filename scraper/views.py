from django.shortcuts import render
from django.views import View
from .forms import MarketForm
from .utils import *
from .scraper_class import FacebookScraper
import re
import plotly.express as px
import pandas as pd

class Index(View):
    def get(self, request):
        form = MarketForm()
        context = {'form': form}
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

            is_listing_missing = scraper_instance.is_listing_missing()
            if is_listing_missing:
                return render(request, 'scraper/missing.html')

            listing_image = scraper_instance.get_listing_image()
            listing_days, listing_hours = scraper_instance.get_listing_date()
            listing_description = scraper_instance.get_listing_description()
            title = scraper_instance.get_listing_title()
            list_price = scraper_instance.get_listing_price()

            sentiment_rating = sentiment_analysis(listing_description)

            list_price = re.sub("[\$,]", "", list_price)
            initial_price = int(re.sub("[\$,]", "", list_price))

            similar_descriptions, similar_prices, similar_urls = find_viable_product(title, ramp_down=0.0)
            similar_prices = [float(price.replace(',', '')) for price in similar_prices]
            shortened_item_names = [description[:10] + '...' if len(description) > 10 else description for description in similar_descriptions]

            # Create a DataFrame from the data
            data = {'Product': shortened_item_names, 'Price': similar_prices, 'Description': similar_descriptions, 'URL': similar_urls}
            df = pd.DataFrame(data)

            cmin = min(similar_prices)
            cmax = max(similar_prices)

            idx = similar_prices.index(cmin)
            best_similar_price = f"{similar_prices[idx]:,.2f}"
            best_similar_description = similar_descriptions[idx]
            best_similar_category = shortened_item_names[idx]
            best_similar_url = similar_urls[idx]

            # Ratio 
            desired_diameter = 150
            sizeref = cmax / desired_diameter

            fig = px.scatter(df, x='Product', text='Description', y='Price', size='Price', color='Price', color_continuous_scale='RdYlGn_r', range_color=[cmin, cmax])
            fig.update_traces(mode='markers', marker=dict(symbol='circle', sizemode='diameter', sizeref=sizeref))

            chart = fig.to_json()           

            # Percetage difference between the listing price and the best found price
            list_best_context = percentage_difference(float(list_price), float(best_similar_price))

            # Needs to be redone
            price_rating = price_difference_rating(initial_price, cmin)

            categories = list(set(shortened_item_names))

            context = {
                'shortened_url': shortened_url,
                'mobile_url': mobile_url,
                'market_id': market_id,
                'sentiment_rating': round(sentiment_rating, 1),
                'title': title,
                'list_price': f"{float(list_price):,.2f}",
                'initial_price': initial_price,
                'chart': chart,
                'price_rating': round(price_rating, 1),
                'days': listing_days,
                'hours': listing_hours,
                'image': listing_image[0],
                'categories': categories,
                'best_similar_price': best_similar_price,
                'best_similar_description': best_similar_description,
                'best_similar_category': best_similar_category,
                'best_similar_url': best_similar_url,
                'list_best_context': list_best_context,
                'id': market_id
            }

            return render(request, 'scraper/result.html', context)
