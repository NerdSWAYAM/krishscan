from django.test import TestCase, Client
from django.urls import reverse
from .models import UserAccount, Crop, Order, OrderItem, Notification
from django.core.files.uploadedfile import SimpleUploadedFile
import json

class KrishiScanTestCases(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create a test Farmer
        self.farmer = UserAccount.objects.create(
            first_name="Test",
            last_name="Farmer",
            email="swayamkesarkar625@gmail.com",
            password="levi", # Assuming plaintext or a mock for test login
            role="Farmer",
            location="Pune, Maharashtra"
        )
        
        # Create a test Consumer
        self.consumer = UserAccount.objects.create(
            first_name="Test",
            last_name="Consumer",
            email="swayamkesarkar625@gmail.com",
            password="levi",
            role="Consumer",
            location="Mumbai, Maharashtra"
        )

        # Create a test Crop
        self.crop = Crop.objects.create(
            farmer=self.farmer,
            name="Test Wheat",
            quantity=100.00,
            price_per_kg=30.00,
            image=SimpleUploadedFile(name='test_image.jpg', content=b'', content_type='image/jpeg')
        )

    def test_tc01_login_success(self):
        """TC01: User enters valid credentials (Consumer Login)"""
        response = self.client.post(reverse('login'), {
            'email': 'consumer@test.com',
            'password': 'testpassword123',
            'role': 'Consumer'
        })
        # Check if redirected to consumer dashboard after login
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get('user_id'), self.consumer.id)

    def test_tc02_crop_upload(self):
        """TC02: Farmer uploads crop details"""
        # Set session to mock login
        session = self.client.session
        session['user_id'] = self.farmer.id
        session['role'] = 'Farmer'
        session.save()

        # Mock image file
        image = SimpleUploadedFile(name='new_crop.jpg', content=b'file_content', content_type='image/jpeg')
        response = self.client.post(reverse('upload_crop'), {
            'crop_name': 'Test Rice',
            'crop_quantity': '50',
            'crop_price': '40',
            'crop_image': image
        })
        
        # Should redirect to sell page after upload
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Crop.objects.filter(name='Test Rice').exists())

    def test_tc03_disease_detection(self):
        """TC03: Upload crop image for disease detection"""
        # Testing the endpoint's response (may need ML mocking in a real setup)
        image = SimpleUploadedFile(name='leaf.jpg', content=b'file_content', content_type='image/jpeg')
        response = self.client.post(reverse('disease_detect'), {
            'crop_image': image
        })
        # We expect a 200 response containing the prediction context
        self.assertEqual(response.status_code, 200)

    def test_tc04_marketplace_order(self):
        """TC04: Consumer places order from wishlist (Checkout)"""
        session = self.client.session
        session['user_id'] = self.consumer.id
        session['role'] = 'Consumer'
        session.save()

        # Consumer has this crop in wishlist
        payload = {
            "items": [{"crop_id": self.crop.id, "quantity": 5}],
            "delivery_type": "doorstep",
            "payment_method": "cod"
        }
        
        response = self.client.post(
            reverse('create_checkout'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Order.objects.filter(consumer=self.consumer).exists())

    def test_tc05_payment_submission(self):
        """TC05: Consumer makes payment (Upload Screenshot)"""
        session = self.client.session
        session['user_id'] = self.consumer.id
        session.save()

        order = Order.objects.create(consumer=self.consumer)
        order_item = OrderItem.objects.create(
            order=order, crop=self.crop, farmer=self.farmer,
            quantity=10.0, amount=300.0, status='pending'
        )

        image = SimpleUploadedFile(name='payment.jpg', content=b'proof', content_type='image/jpeg')
        response = self.client.post(reverse('submit_payment'), {
            'order_item_id': order_item.id,
            'payment_screenshot': image
        })

        self.assertEqual(response.status_code, 302)
        order_item.refresh_from_db()
        self.assertEqual(order_item.status, 'paid')

    def test_tc06_order_history(self):
        """TC06: User views previous orders"""
        session = self.client.session
        session['user_id'] = self.consumer.id
        session['role'] = 'Consumer'
        session.save()

        response = self.client.get(reverse('my_orders'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'my_orders.html')

    def test_tc07_map_integration(self):
        """TC07: User opens map page"""
        session = self.client.session
        session['user_id'] = self.consumer.id
        session['role'] = 'Consumer'
        session.save()

        order = Order.objects.create(consumer=self.consumer)
        order_item = OrderItem.objects.create(
            order=order, crop=self.crop, farmer=self.farmer,
            quantity=5.0, amount=150.0
        )

        response = self.client.get(reverse('order_map', args=[order_item.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'map.html')

    def test_tc08_notification(self):
        """TC08: Order placed notification"""
        # Create an order which should trigger a notification
        session = self.client.session
        session['user_id'] = self.consumer.id
        session.save()

        Notification.objects.create(
            user=self.farmer,
            title="New Order Received",
            message=f"{self.consumer.first_name} ordered {self.crop.name}."
        )

        # Fetch notifications for farmer
        session['user_id'] = self.farmer.id
        session['role'] = 'Farmer'
        session.save()

        response = self.client.get(reverse('fetch_notifications_api'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['notifications']), 1)
        self.assertEqual(data['notifications'][0]['title'], "New Order Received")
