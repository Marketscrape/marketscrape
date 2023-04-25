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

            # Shorten the URL and create a mobile URL
            shortened_url = re.search(r".*[0-9]", url).group(0)
            mobile_url = shortened_url.replace("www", "m")

            # Create soup objects from the desktop and mobile versions of the page
            mobile_soup = create_soup(mobile_url, headers=None)
            base_soup = create_soup(url, headers=None)

            # Create a FacebookScraper instance
            scraper_instance = FacebookScraper(mobile_soup, base_soup)

            # Check if the listing is missing
            if scraper_instance.is_listing_missing():
                return render(request, 'scraper/missing.html')
            
            # Get the listing data
            image = scraper_instance.get_listing_image()
            days, hours = scraper_instance.get_listing_date()
            description = scraper_instance.get_listing_description()
            title = scraper_instance.get_listing_title()
            condition = scraper_instance.get_listing_condition()
            category = scraper_instance.get_listing_category()
            price = scraper_instance.get_listing_price()
            city = scraper_instance.get_listing_city()

            # Find viable products based on the title
            similar_descriptions, similar_prices, similar_urls, best_similar_product = find_viable_product(title, ramp_down=0.0)

            # Convert prices to float and shorten the descriptions if necessary
            similar_prices = [float(price.replace(',', '')) for price in similar_prices]
            shortened_item_names = [description[:8] + '...' if len(description) > 10 else description for description in similar_descriptions]

            # Based on the best similar product, get the price, description, category, and URL
            idx = similar_urls.index(best_similar_product[1]["url"])
            best_similar_price = f"{similar_prices[idx]:,.2f}"
            best_similar_description = similar_descriptions[idx]
            best_similar_category = shortened_item_names[idx]
            best_similar_url = similar_urls[idx]
            best_similar_score = best_similar_product[1]["similarity"] * 100

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
            chart = fig.to_json()           

            # Percetage difference between the listing price and the best found price
            list_best_context = percentage_difference(float(price), float(best_similar_price.replace(",", "")))
            price_rating = price_difference_rating(float(price), float(best_similar_price.replace(",", "")))

            # Get the unique categories and total number of items
            categories = list(set(shortened_item_names))
            total_items = len(similar_descriptions)

            # Create the context 
            context = {
                'shortened_url': shortened_url,
                'mobile_url': mobile_url,
                'title': title,
                'price': f"{float(price):,.2f}",
                'chart': chart,
                'price_rating': round(price_rating, 1),
                'days': days,
                'hours': hours,
                'image': image,
                'description': description,
                'condition': condition,
                'category': category,
                'city': city,
                'categories': categories,
                'total_items': total_items,
                'best_similar_price': best_similar_price,
                'best_similar_description': best_similar_description,
                'best_similar_category': best_similar_category,
                'best_similar_url': best_similar_url,
                'best_similar_score': f"{best_similar_score:.2f}",
                'list_best_context': list_best_context
            }

            return render(request, 'scraper/result.html', context)