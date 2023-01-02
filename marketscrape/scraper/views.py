from django.shortcuts import render
from django.views import View
from .forms import MarketForm

class Index(View):
    def get(self, request):
        form = MarketForm()
        return render(request, 'scraper/index.html', {'form': form})

    def post(self, requeset):
        pass