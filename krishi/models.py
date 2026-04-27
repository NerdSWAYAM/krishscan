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
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    upi_id = models.CharField(max_length=100, blank=True, null=True)
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

    def is_valid(self):
        return timezone.now() < self.created_at + timedelta(minutes=5)

class Order(models.Model):
    """Represents a consumer's complete checkout session."""
    consumer = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='orders')
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('partial', 'Partial'),
        ('completed', 'Completed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} by {self.consumer.first_name}"

class OrderItem(models.Model):
    """A single line item within an order — one crop from one farmer."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE, related_name='order_items')
    farmer = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='incoming_items')
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"OrderItem #{self.id} – {self.crop.name} x {self.quantity}kg"

class Payment(models.Model):
    """Screenshot proof submitted by consumer for a specific OrderItem."""
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE, related_name='payment')
    screenshot = models.ImageField(upload_to='payment_proofs/')
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment for OrderItem #{self.order_item.id}"

class ChatMessage(models.Model):
    sender = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='received_messages')
    encrypted_content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"From {self.sender.first_name} to {self.receiver.first_name} at {self.timestamp}"

class Notification(models.Model):
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=500, blank=True, null=True)

    def __str__(self):
        return f"Notification for {self.user.first_name}: {self.title}"
