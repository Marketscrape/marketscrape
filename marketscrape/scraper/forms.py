from django import forms

class MarketForm(forms.Form):
    input_url = forms.URLField()