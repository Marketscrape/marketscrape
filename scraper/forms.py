from django import forms

class MarketForm(forms.Form):
    url = forms.URLField(label=False, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Enter a Facebook Marketplace URL...',
        'autocomplete': 'off'
    }))