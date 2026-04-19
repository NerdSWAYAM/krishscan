from django.db import models
from django.utils import timezone
from datetime import timedelta

class UserAccount(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=50, choices=[('Farmer', 'Farmer'), ('Consumer', 'Consumer')])
    location = models.CharField(max_length=255)
    coordinates = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

class Crop(models.Model):
    farmer = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='crops')
    name = models.CharField(max_length=150)
    image = models.ImageField(upload_to='crop_images/')
    quantity = models.DecimalField(max_digits=10, decimal_places=2) # in kg
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.farmer.first_name}"

class EmailOTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)


