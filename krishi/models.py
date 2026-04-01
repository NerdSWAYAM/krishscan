from django.db import models
from django.utils import timezone
from datetime import timedelta

# Create your models here.

### For the mobile otp -- (Future use case)
# class PhoneOTP(models.Model):
#     phone = models.CharField(max_length=15)
#     otp = models.CharField(max_length=6)
#     created_at = models.DateTimeField(auto_now_add=True)
#     expires_at = models.DateTimeField()
#     is_verified = models.BooleanField(default=False)
#     attempts = models.IntegerField(default=0)

#     def is_expired(self):
#         return timezone.now() > self.expires_at

#     @staticmethod
#     def get_expiry_time():
#         return timezone.now() + timedelta(minutes=5)
