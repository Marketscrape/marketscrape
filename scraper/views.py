from django.shortcuts import render
from django.views import View
from .forms import MarketForm
from .utils import *
from .shopping_class import GoogleShoppingScraper
from .marketplace_class import FacebookMarketplaceScraper

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
            facebook_instance = FacebookMarketplaceScraper(mobile_soup, base_soup)

            # Check if the listing is missing
            if facebook_instance.is_listing_missing():
                return render(request, 'scraper/missing.html')
            
            # Get the listing data
            image = facebook_instance.get_listing_image()
            days, hours = facebook_instance.get_listing_date()
            description = facebook_instance.get_listing_description()
            title = facebook_instance.get_listing_title()
            condition = facebook_instance.get_listing_condition()
            category = facebook_instance.get_listing_category()
            price = facebook_instance.get_listing_price()
            city = facebook_instance.get_listing_city()
            currency = facebook_instance.get_listing_currency()

            # Create a GoogleShoppingScraper instance
            shopping_instance = GoogleShoppingScraper()

            # Find viable products based on the title
            cleaned_title = remove_illegal_characters(title)
            similar_descriptions, similar_prices, similar_shipping, similar_urls, similar_scores = shopping_instance.find_viable_product(cleaned_title, ramp_down=0.0)
            candidates = shopping_instance.construct_candidates(similar_descriptions, similar_prices, similar_shipping, similar_urls, similar_scores)
            
            # Convert prices to float and shorten the descriptions if necessary
            similar_prices = [float(price.replace(',', '')) for price in similar_prices]

            # Categorize the titles and create the chart and wordcloud
            categorized = categorize_titles(similar_descriptions)
            chart = create_chart(categorized, similar_prices, similar_shipping, similar_descriptions, currency, title)
            wordcloud = create_wordcloud(similar_urls)   

            # Based on the best similar product, get the price, description, category, and URL
            best_product = shopping_instance.lowest_price_highest_similarity(candidates)

            idx = similar_urls.index(best_product[1]["url"])
            best_price = f"{similar_prices[idx]:,.2f}"
            best_shipping = similar_shipping[idx]
            best_title = similar_descriptions[idx]
            best_score = best_product[1]["similarity"] * 100

            # Percetage difference between the listing price and the best found price (including shipping)
            best_total = float(best_price.replace(",", "")) + float(best_shipping.replace(",", ""))
            best_context = percentage_difference(float(price), best_total,)
            price_rating = price_difference_rating(float(price), best_total, days)

            # Get the total number of items
            total_items = len(similar_descriptions)

            # Create the context 
            context = {
                'shortened_url': shortened_url,
                'mobile_url': mobile_url,
                'title': title,
                'price': f"{float(price):,.2f}",
                'chart': chart,
                'wordcloud': wordcloud,
                'price_rating': round(price_rating, 1),
                'days': days,
                'hours': hours,
                'image': image,
                'description': description,
                'condition': condition,
                'category': category,
                'city': city,
                'currency': currency,
                'categorized': categorized,
                'total_items': total_items,
                'best_price': best_price,
                'best_shipping': best_shipping,
                'best_title': best_title.title(),
                'best_score': round(best_score, 2),
                'best_context': best_context
            }

            return render(request, 'scraper/result.html', context)