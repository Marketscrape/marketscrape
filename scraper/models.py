from django.db import models

class Item(models.Model):
    title = models.CharField(max_length=1000)
    rating = models.DecimalField(max_digits=8, decimal_places=1)
    url = models.CharField(max_length=1000)
    image = models.CharField(max_length=1000)

    def __str__(self):
        return self.title




