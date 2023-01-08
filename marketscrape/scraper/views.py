from django.shortcuts import render
from django.views import View
from .forms import MarketForm
import re

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

        context = {
            'shortened_url': shortened_url,
            'mobile_url': mobile_url,
            'market_id': market_id,
        }
        
        return render(request, 'scraper/result.html', context)
