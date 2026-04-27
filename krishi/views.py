from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from .models import UserAccount, Crop, EmailOTP

def home(request):
    return render(request, 'index.html')

def signup(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')
        location = request.POST.get('location')
        coordinates = request.POST.get('coordinates')
        user_otp = request.POST.get('otp')
        
        if UserAccount.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered. Please login.')
            return redirect('signup')
            
        stored_otp = EmailOTP.objects.filter(email=email).order_by('-created_at').first()
        if not stored_otp or stored_otp.otp != user_otp:
            messages.error(request, 'Invalid OTP.')
            return redirect('signup')
            
        if not stored_otp.is_valid():
            messages.error(request, 'OTP has expired. Please request a new one.')
            return redirect('signup')
            
        hashed_password = make_password(password)

        new_user = UserAccount(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=hashed_password,
            role=role,
            location=location,
            coordinates=coordinates
        )
        new_user.save()
        
        request.session['user_id'] = new_user.id
        request.session['role'] = new_user.role
        request.session['first_name'] = new_user.first_name
        request.session['last_name'] = new_user.last_name
        request.session['email'] = new_user.email
        request.session['location'] = new_user.location
        request.session['coordinates'] = new_user.coordinates
        
        messages.success(request, 'Account created successfully!')
        return redirect('marketplace')

    return render(request, 'signup.html')

from django.contrib.auth.hashers import check_password

def login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            user = UserAccount.objects.get(email=email)
            if check_password(password, user.password):
                request.session['user_id'] = user.id
                request.session['role'] = user.role
                request.session['first_name'] = user.first_name
                request.session['last_name'] = user.last_name
                request.session['email'] = user.email
                request.session['location'] = user.location
                request.session['coordinates'] = user.coordinates
                
                # Redirect based on role if needed, or marketplace by default
                if user.role == 'Farmer':
                    return redirect('dashboard')
                else:
                    return redirect('marketplace')
            else:
                messages.error(request, 'Invalid password.')
        except UserAccount.DoesNotExist:
            messages.error(request, 'No account found with this email.')
            
    return render(request, 'login.html')

import math

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    return round(distance, 2)

def marketplace(request):
    crops = Crop.objects.select_related('farmer').all().order_by('-created_at')
    
    user_coords = request.session.get('coordinates')
    
    crop_list = []
    for crop in crops:
        distance = None
        if user_coords and crop.farmer.coordinates:
            try:
                lat1, lon1 = map(float, user_coords.split(','))
                lat2, lon2 = map(float, crop.farmer.coordinates.split(','))
                distance = calculate_distance(lat1, lon1, lat2, lon2)
            except ValueError:
                pass
        crop.distance = distance
        crop_list.append(crop)
        
    if user_coords:
        crop_list.sort(key=lambda x: (x.distance is None, x.distance))
        
    return render(request, 'marketplace.html', {'crops': crop_list})

def weather(request):
    return render(request, 'weather.html')

def upload_crop(request):
    if request.session.get('role') != 'Farmer':
        messages.error(request, 'Only farmers can upload crops.')
        return redirect('marketplace')

    if request.method == 'POST':
        name = request.POST.get('name')
        quantity = request.POST.get('quantity')
        price_per_kg = request.POST.get('price_per_kg')
        image = request.FILES.get('image')

        user_id = request.session.get('user_id')
        try:
            farmer = UserAccount.objects.get(id=user_id)
            new_crop = Crop(
                farmer=farmer,
                name=name,
                quantity=quantity,
                price_per_kg=price_per_kg,
                image=image
            )
            new_crop.save()
            
            from .models import Notification
            Notification.objects.create(
                user=farmer,
                title="Crop uploaded successfully",
                message=f"Your crop '{name}' is now live on the marketplace and available to buyers.",
                link="/dashboard/"
            )
            
            messages.success(request, 'Crop uploaded successfully!')
            return redirect('marketplace')
        except UserAccount.DoesNotExist:
            messages.error(request, 'Account verification failed.')
            return redirect('login')

    return render(request, 'upload_crop.html')

def consumer(request):
    import os
    from .models import Order

    # Fetch Recent Orders and Recently Connected Farmers
    user_id = request.session.get('user_id')
    recent_farmers = []
    if user_id:
        from .models import OrderItem, ChatMessage, UserAccount
        recent_orders = (
            OrderItem.objects
            .filter(order__consumer_id=user_id)
            .select_related('crop', 'order__consumer', 'farmer')
            .order_by('-created_at')[:5]
        )
        
        # Get recently connected farmers via chat
        chat_farmer_ids = set(ChatMessage.objects.filter(sender_id=user_id).values_list('receiver_id', flat=True))
        chat_farmer_ids.update(ChatMessage.objects.filter(receiver_id=user_id).values_list('sender_id', flat=True))
        
        recent_farmers = UserAccount.objects.filter(id__in=chat_farmer_ids, role='Farmer')[:5]
    else:
        recent_orders = []

    context = {
        'recent_farmers': recent_farmers,
        'recent_orders': recent_orders,
    }
    return render(request, 'consumerdash.html', context)

from django.core.cache import cache

def dashboard(request):
    import os
    import requests
    from django.utils import timezone
    from .models import Crop, Order
    
    API_KEY = os.getenv("API_KEY", "579b464db66ec23bdd0000014221d4e33efb481147dfeea08b43d410")
    RESOURCE_ID = os.getenv("RESOURCE_ID", "9ef84268-d588-465a-a308-a864a43d0070")
    
    url = f"https://api.data.gov.in/resource/{RESOURCE_ID}"
    
    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": 5
    }
    
    cache_key = 'dashboard_market_prices'
    market_prices = cache.get(cache_key)
    
    if market_prices is None:
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            market_prices = data.get('records', [])
            cache.set(cache_key, market_prices, 60 * 60)
        except requests.exceptions.RequestException as e:
            print("Error fetching data:", e)
            market_prices = []

    # Fetch Real-Time Weather
    weather_data = None
    try:
        w_url = "https://api.openweathermap.org/data/2.5/weather"
        w_params = {
            "appid": os.getenv("WEATHER_API", "ddd2be8826cfdca0b5ed7bea91f2c640"),
            "units": "metric"
        }
        
        coordinates = request.session.get('coordinates')
        if coordinates:
            lat, lon = coordinates.split(',')
            w_params['lat'] = lat.strip()
            w_params['lon'] = lon.strip()
        else:
            location = request.session.get('location', 'Bangalore')
            w_params['q'] = location.split(',')[0] if location else 'Bangalore'
            
        res = requests.get(w_url, params=w_params, timeout=5)
        if res.status_code == 200:
            w_data = res.json()
            weather_data = {
                'temp': w_data['main']['temp'],
                'feels_like': w_data['main']['feels_like'],
                'humidity': w_data['main']['humidity'],
                'wind_speed': w_data['wind']['speed'],
                'description': w_data['weather'][0]['description'].capitalize(),
                'icon': w_data['weather'][0]['icon'],
                'city': w_data['name']
            }
    except Exception as e:
        print("Error fetching weather:", e)

    # Crop Stats
    user_id = request.session.get('user_id')
    recent_consumers = []
    if user_id:
        from .models import OrderItem, ChatMessage, UserAccount
        crops_uploaded = Crop.objects.filter(farmer_id=user_id).count()
        crops_sold_count = Crop.objects.filter(
            farmer_id=user_id,
            order_items__status='verified'
        ).distinct().count()
        crops_unsold_count = crops_uploaded - crops_sold_count
        crops_sold = crops_sold_count
        uploaded_crops = Crop.objects.filter(farmer_id=user_id).order_by('-created_at')

        # Get recently connected consumers via chat
        chat_consumer_ids = set(ChatMessage.objects.filter(sender_id=user_id).values_list('receiver_id', flat=True))
        chat_consumer_ids.update(ChatMessage.objects.filter(receiver_id=user_id).values_list('sender_id', flat=True))
        
        recent_consumers = UserAccount.objects.filter(id__in=chat_consumer_ids, role='Consumer')[:5]
    else:
        crops_uploaded = 0
        crops_sold_count = 0
        crops_unsold_count = 0
        crops_sold = 0
        uploaded_crops = []

    context = {
        'market_prices': market_prices,
        'weather_data': weather_data,
        'crops_uploaded': crops_uploaded,
        'crops_sold': crops_sold,
        'crops_sold_count': crops_sold_count,
        'crops_unsold_count': crops_unsold_count,
        'uploaded_crops': uploaded_crops,
        'recent_consumers': recent_consumers,
    }
    return render(request, 'dashboard.html', context)

def sell(request):
    return render(request, 'sell.html')

def cart(request):
    return render(request, 'cart.html')

def add_to_wishlist(request):
    import json
    from django.http import JsonResponse
    from .models import Crop
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            crop_id = str(data.get('crop_id'))
            quantity = float(data.get('quantity'))
            
            if 'wishlist' not in request.session:
                request.session['wishlist'] = {}
                
            wishlist = request.session['wishlist']
            
            crop = Crop.objects.get(id=int(crop_id))
            if quantity > crop.quantity:
                return JsonResponse({'success': False, 'message': 'Requested quantity exceeds available stock.'})
            
            wishlist[crop_id] = quantity
            request.session.modified = True
            
            return JsonResponse({'success': True, 'message': 'Added to wishlist!'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

def remove_from_wishlist(request):
    import json
    from django.http import JsonResponse
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            crop_id = str(data.get('crop_id'))
            
            if 'wishlist' in request.session and crop_id in request.session['wishlist']:
                del request.session['wishlist'][crop_id]
                request.session.modified = True
                
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request'})


def remove_crop(request):
    import json
    from django.http import JsonResponse
    from .models import Crop

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            crop_id = data.get('crop_id')
            user_id = request.session.get('user_id')

            if not user_id:
                return JsonResponse({'success': False, 'message': 'Authentication required.'}, status=403)

            crop = Crop.objects.get(id=int(crop_id), farmer_id=user_id)
            crop_name = crop.name
            crop.delete()
            
            from .models import Notification
            Notification.objects.create(
                user_id=user_id,
                title="Crop removed",
                message=f"Your listing for '{crop_name}' has been removed from the marketplace.",
                link="/dashboard/"
            )
            
            return JsonResponse({'success': True})
        except Crop.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Crop not found or not owned by you.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Invalid request'})


def wishlist_view(request):
    from .models import Crop
    wishlist = request.session.get('wishlist', {})
    cart_items = []
    farmer_groups = {}
    grand_total = 0
    
    # Get user coordinates for distance calculation
    user_lat = user_lon = None
    coords_str = request.session.get('coordinates')
    if coords_str:
        try:
            user_lat, user_lon = map(float, coords_str.split(','))
        except ValueError:
            pass

    # Optimization: Get all crops in wishlist with one query
    crop_ids = [int(cid) for cid in wishlist.keys()]
    crops = {c.id: c for c in Crop.objects.select_related('farmer').filter(id__in=crop_ids)}
    
    for crop_id_str, qty in wishlist.items():
        crop_id = int(crop_id_str)
        if crop_id in crops:
            crop = crops[crop_id]
            line_total = float(crop.price_per_kg) * float(qty)
            grand_total += line_total
            
            farmer = crop.farmer
            distance = None
            if user_lat and user_lon and farmer.coordinates:
                try:
                    f_lat, f_lon = map(float, farmer.coordinates.split(','))
                    distance = round(calculate_distance(user_lat, user_lon, f_lat, f_lon), 2)
                except ValueError:
                    pass

            if farmer.id not in farmer_groups:
                farmer_groups[farmer.id] = {
                    'farmer': farmer,
                    'items': [],
                    'subtotal': 0
                }
                
            item_data = {
                'crop': crop,
                'quantity': float(qty),
                'line_total': line_total,
                'distance': distance
            }
            farmer_groups[farmer.id]['items'].append(item_data)
            farmer_groups[farmer.id]['subtotal'] += line_total
            cart_items.append(item_data)
            
    context = {
        'cart_items': cart_items,
        'farmer_groups': list(farmer_groups.values()),
        'grand_total': grand_total
    }
    return render(request, 'wishlist.html', context)

_disease_model = None
_resnet_model = None

def get_disease_model():
    import torch
    import torch.nn as nn
    import timm
    from huggingface_hub import hf_hub_download
    global _disease_model
    if _disease_model is None:
        model_path = hf_hub_download(repo_id="VisionaryQuant/5_Crop_Disease_Detection", filename="best_crop_disease_model.pt")
        model = timm.create_model('efficientnet_b3', pretrained=False)
        model.classifier = nn.Sequential(
            nn.Linear(model.classifier.in_features, 17)
        )
        state_dict = torch.load(model_path, map_location=torch.device('cpu'))
        model.load_state_dict(state_dict)
        model.eval()
        _disease_model = model
    return _disease_model

def get_resnet_model():
    import os
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    import tensorflow as tf
    global _resnet_model
    if _resnet_model is None:
        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'MLmodels', 'resnet50_transfer_best.h5')
        _resnet_model = tf.keras.models.load_model(model_path)
    return _resnet_model

CLASS_NAMES = [
    "Corn___Common_Rust", "Corn___Gray_Leaf_Spot", "Corn___Healthy", "Corn___Northern_Leaf_Blight",
    "Potato___Early_Blight", "Potato___Healthy", "Potato___Late_Blight",
    "Rice___Brown_Spot", "Rice___Healthy", "Rice___Leaf_Blast", "Rice___Neck_Blast",
    "Sugarcane___Bacterial_Blight", "Sugarcane___Healthy", "Sugarcane___Red_Rot",
    "Wheat___Brown_Rust", "Wheat___Healthy", "Wheat___Yellow_Rust"
]

def disease_detect(request):
    import torch
    from torchvision import transforms
    from PIL import Image
    import numpy as np
    import base64
    from io import BytesIO

    result = None
    if request.method == 'POST' and request.FILES.get('image'):
        image_file = request.FILES['image']
        try:
            # Save uploaded image as base64 to show in preview
            img = Image.open(image_file).convert("RGB")
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            img_data_uri = f"data:image/jpeg;base64,{img_str}"

            # Transform for HuggingFace model
            transform_hf = transforms.Compose([
                transforms.Resize((300, 300)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std=[0.229, 0.224, 0.225])
            ])
            input_tensor = transform_hf(img).unsqueeze(0)
            
            hf_model = get_disease_model()
            with torch.no_grad():
                logits = hf_model(input_tensor)
                probs = torch.nn.functional.softmax(logits, dim=1)
                confidence, predicted_idx = torch.max(probs, dim=1)
                
                predicted_idx = predicted_idx.item()
                confidence_score_hf = confidence.item() * 100
                
            if predicted_idx < len(CLASS_NAMES):
                predicted_label_hf = CLASS_NAMES[predicted_idx]
            else:
                predicted_label_hf = "Unknown"

            # Transform and infer for Resnet50 Model
            resnet_model = get_resnet_model()
            import tensorflow as tf
            # Resnet50 usually takes 224x224
            img_resized = img.resize((224, 224))
            img_array = tf.keras.preprocessing.image.img_to_array(img_resized)
            img_array = np.expand_dims(img_array, axis=0)
            img_array = tf.keras.applications.resnet50.preprocess_input(img_array)
            
            predictions = resnet_model.predict(img_array)
            # applying softmax to predictions if not already outputting probabilities
            if np.min(predictions[0]) < 0 or np.sum(predictions[0]) > 1.1:
                 predictions_probs = tf.nn.softmax(predictions[0]).numpy()
            else:
                 predictions_probs = predictions[0]

            confidence_score_resnet = np.max(predictions_probs) * 100

            # Ensemble logic
            if confidence_score_hf > 50.0 and confidence_score_resnet > 50.0:
                result = {
                    'disease': predicted_label_hf.replace('___', ' - ').replace('_', ' '),
                    'confidence': confidence_score_hf,
                    'image_uri': img_data_uri
                }
            else:
                result = {
                    'disease': "Can't recognize disease",
                    'confidence': min(confidence_score_hf, confidence_score_resnet),
                    'error': "Can't recognize disease. The uploaded image does not appear to be a known crop disease.",
                    'image_uri': img_data_uri
                }
        except Exception as e:
            result = {'error': str(e)}
            if 'img_data_uri' in locals() and img_data_uri:
                result['image_uri'] = img_data_uri

    return render(request, 'disease_detect.html', {'result': result})

def experts(request):
    return render(request, 'experts.html')

import requests
import os
import dotenv

dotenv.load_dotenv()

def price_tracker(request):
    API_KEY = os.getenv("API_KEY", "579b464db66ec23bdd0000014221d4e33efb481147dfeea08b43d410")
    RESOURCE_ID = os.getenv("RESOURCE_ID", "9ef84268-d588-465a-a308-a864a43d0070")
    
    url = f"https://api.data.gov.in/resource/{RESOURCE_ID}"
    
    # Use Gujarat and Wheat as default since they have guaranteed data in the snapshot
    state = request.GET.get('state', 'Gujarat')
    commodity = request.GET.get('commodity', 'Wheat')
    
    params = {
        "api-key": API_KEY,
        "format": "json",
        "filters[state]": state,
        "filters[commodity]": commodity,
        "limit": 20
    }
    
    cache_key = f'price_tracker_{state}_{commodity}'
    records = cache.get(cache_key)
    
    if records is None:
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            records = data.get('records', [])
            cache.set(cache_key, records, 60 * 60)
        except requests.exceptions.RequestException as e:
            print("Error fetching data:", e)
            records = []
        
    context = {
        'records': records,
        'state': state,
        'commodity': commodity,
    }
    return render(request, 'price_tracker.html', context)


import random
import json
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from .models import EmailOTP

from django.core.mail import EmailMultiAlternatives

def send_otp_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON format'})
            
        if not email:
            return JsonResponse({'success': False, 'message': 'Email is required'})
            
        otp = str(random.randint(1000, 9999))
        
        EmailOTP.objects.create(email=email, otp=otp)

        subject = "Verify your email"
        from_email = "noreply@krishiscan.in"
        to = [email]

        text_content = f"Your OTP is {otp}. Valid for 5 minutes. (Please check your spam folder if you do not see this email)"

        html_content = f"""
        <h2>Email Verification</h2>
        <p>Your OTP is:</p>
        <h1 style="color:#59AC77; text-weight:bold; ">{otp}</h1>
        <p>This OTP is valid for 5 minutes.</p>
        <p><small>(Please check your spam folder if you do not see this email)</small></p>
        <center>
            <h2>From Team - <span style="color:#59AC77;">KrishiScan</span></h2>
        </center>
        """

        msg = EmailMultiAlternatives(subject, text_content, from_email, to)
        msg.attach_alternative(html_content, "text/html")
        try:
            msg.send()
            return JsonResponse({'success': True, 'message': 'OTP sent successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

def crop_history(request):
    user_id = request.session.get('user_id')
    role = request.session.get('role')
    
    if not user_id or role != 'Farmer':
        messages.error(request, 'Please log in as a farmer to view crop history.')
        return redirect('login')
        
    from .models import Crop, OrderItem
    
    # Fetch all crops uploaded by this farmer
    crops = Crop.objects.filter(farmer_id=user_id).order_by('-created_at')
    
    # Fetch all order items related to this farmer's crops
    orders = OrderItem.objects.filter(farmer_id=user_id).select_related('crop', 'order__consumer').order_by('-created_at')
    
    context = {
        'crops': crops,
        'orders': orders
    }
    return render(request, 'crop_history.html', context)

def submit_payment(request):
    """Consumer submits a screenshot proof for a specific OrderItem."""
    import json
    from django.http import JsonResponse
    from .models import Order, OrderItem, Payment, Crop, UserAccount

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request'})

    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': 'Not authenticated'})

    order_item_id = request.POST.get('order_item_id')
    screenshot = request.FILES.get('screenshot')

    if not order_item_id or not screenshot:
        return JsonResponse({'success': False, 'message': 'Missing data'})

    # Validate file type
    allowed_types = ('image/jpeg', 'image/png', 'image/jpg', 'image/webp')
    if screenshot.content_type not in allowed_types:
        return JsonResponse({'success': False, 'message': 'Only JPG/PNG images are accepted'})

    # Max 5MB
    if screenshot.size > 5 * 1024 * 1024:
        return JsonResponse({'success': False, 'message': 'File too large. Max 5MB allowed'})

    try:
        item = OrderItem.objects.get(id=order_item_id, order__consumer_id=user_id)
    except OrderItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order item not found'})

    if hasattr(item, 'payment'):
        return JsonResponse({'success': False, 'message': 'Payment already submitted for this item'})

    Payment.objects.create(order_item=item, screenshot=screenshot, status='pending')
    item.status = 'paid'
    item.save()

    from .models import Notification
    Notification.objects.create(
        user=item.farmer,
        title="Payment verification requested",
        message=f"A payment proof has been submitted for '{item.crop.name}' by {item.order.consumer.first_name}. Please review and confirm.",
        link="/wallet/"
    )

    # Update parent order status
    order = item.order
    statuses = set(order.items.values_list('status', flat=True))
    if statuses == {'verified'}:
        order.status = 'completed'
    elif 'verified' in statuses or 'paid' in statuses:
        order.status = 'partial'
    order.save()

    return JsonResponse({'success': True, 'message': 'Payment proof submitted successfully'})


def verify_order_item(request):
    """Farmer approves or rejects a payment for one of their OrderItems."""
    import json
    from django.http import JsonResponse
    from .models import OrderItem, Payment

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request'})

    user_id = request.session.get('user_id')
    role = request.session.get('role')
    if not user_id or role != 'Farmer':
        return JsonResponse({'success': False, 'message': 'Unauthorized'})

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'})

    item_id = data.get('order_item_id')
    action = data.get('action')  # 'approve' or 'reject'

    if action not in ('approve', 'reject'):
        return JsonResponse({'success': False, 'message': 'Invalid action'})

    try:
        item = OrderItem.objects.select_related('farmer', 'crop', 'order').get(id=item_id, farmer_id=user_id)
    except OrderItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order item not found'})

    if action == 'approve':
        item.status = 'verified'
        item.save()

        # Credit farmer wallet
        farmer = item.farmer
        farmer.wallet_balance += item.amount
        farmer.save()

        # Crop stock was already deducted at checkout

        if hasattr(item, 'payment'):
            item.payment.status = 'approved'
            item.payment.save()
            
        from .models import Notification
        Notification.objects.create(
            user=item.order.consumer,
            title="Payment verified",
            message=f"Your payment for '{item.crop.name}' has been approved by the farmer.",
            link="/my_orders/"
        )
    else:
        item.status = 'rejected'
        item.save()
        
        # Restore crop stock
        crop = item.crop
        crop.quantity += item.quantity
        crop.save()
        if hasattr(item, 'payment'):
            item.payment.status = 'rejected'
            item.payment.save()
            
        from .models import Notification
        Notification.objects.create(
            user=item.order.consumer,
            title="Payment review update",
            message=f"The farmer did not approve payment proof for '{item.crop.name}'. Please get in touch with them for next steps.",
            link="/my_orders/"
        )

    # Update parent order status
    order = item.order
    statuses = set(order.items.values_list('status', flat=True))
    if statuses == {'verified'}:
        order.status = 'completed'
    elif 'verified' in statuses or 'paid' in statuses:
        order.status = 'partial'
    else:
        order.status = 'pending'
    order.save()

    return JsonResponse({'success': True})


def create_checkout(request):
    """Consumer initiates checkout — creates Order + OrderItems, returns grouped data for payment UI."""
    import json
    from django.http import JsonResponse
    from .models import Crop, Order, OrderItem, UserAccount

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request'})

    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': 'Not authenticated'})

    wishlist = request.session.get('wishlist', {})
    if not wishlist:
        return JsonResponse({'success': False, 'message': 'Wishlist is empty'})

    consumer = UserAccount.objects.get(id=user_id)

    # Validate all farmers have UPI IDs before creating anything
    for crop_id, qty in wishlist.items():
        try:
            crop = Crop.objects.get(id=int(crop_id))
            if not crop.farmer.upi_id:
                return JsonResponse({
                    'success': False,
                    'message': f'{crop.farmer.first_name} {crop.farmer.last_name} has not set up their UPI ID yet. Please remove their items and try again.'
                })
        except Crop.DoesNotExist:
            continue

    # Create Order
    order = Order.objects.create(consumer=consumer, status='pending')

    farmer_groups = {}
    for crop_id, qty in wishlist.items():
        try:
            crop = Crop.objects.get(id=int(crop_id))
            amount = float(crop.price_per_kg) * float(qty)
            farmer = crop.farmer

            item = OrderItem.objects.create(
                order=order,
                crop=crop,
                farmer=farmer,
                quantity=float(qty),
                amount=amount,
                status='pending'
            )

            # Deduct stock immediately upon order creation
            crop.quantity -= float(qty)
            crop.save()

            if farmer.id not in farmer_groups:
                farmer_groups[farmer.id] = {
                    'farmer_id': farmer.id,
                    'farmer_name': f'{farmer.first_name} {farmer.last_name}',
                    'upi_id': farmer.upi_id,
                    'subtotal': 0,
                    'items': []
                }
            farmer_groups[farmer.id]['subtotal'] += amount
            farmer_groups[farmer.id]['items'].append({
                'order_item_id': item.id,
                'crop_name': crop.name,
                'quantity': float(qty),
                'amount': amount,
            })
        except Crop.DoesNotExist:
            continue

    # Build UPI deep links
    for fg in farmer_groups.values():
        upi_link = (
            f"upi://pay?pa={fg['upi_id']}"
            f"&pn={fg['farmer_name'].replace(' ', '%20')}"
            f"&am={fg['subtotal']:.2f}"
            f"&cu=INR"
            f"&tn=KrishiScan_Order_{order.id}"
        )
        fg['upi_link'] = upi_link

    # Clear wishlist after order creation
    if 'wishlist' in request.session:
        del request.session['wishlist']
        request.session.modified = True

    return JsonResponse({
        'success': True,
        'order_id': order.id,
        'farmer_groups': list(farmer_groups.values()),
    })


def wallet_view(request):
    if 'email' not in request.session or request.session.get('role') != 'Farmer':
        return redirect('login')

    from .models import UserAccount, OrderItem
    try:
        user = UserAccount.objects.get(email=request.session['email'])
    except UserAccount.DoesNotExist:
        return redirect('login')

    if request.method == 'POST':
        upi_id = request.POST.get('upi_id', '').strip()
        if upi_id:
            user.upi_id = upi_id
            user.save()
        return redirect('wallet')

    # Incoming payments for this farmer — items waiting for verification
    pending_items = (
        OrderItem.objects
        .filter(farmer=user, status='paid')
        .select_related('order', 'order__consumer', 'crop')
        .prefetch_related('payment')
        .order_by('-created_at')
    )

    # Recent verified/rejected items
    history_items = (
        OrderItem.objects
        .filter(farmer=user, status__in=('verified', 'rejected'))
        .select_related('order', 'order__consumer', 'crop')
        .order_by('-created_at')[:20]
    )

    context = {
        'wallet_balance': user.wallet_balance,
        'upi_id': user.upi_id,
        'has_upi': bool(user.upi_id),
        'pending_items': pending_items,
        'history_items': history_items,
    }

    return render(request, 'farmer_wallet.html', context)


def my_orders(request):
    """Consumer's full order history with delivery status estimation."""
    from .models import Order
    from django.utils import timezone

    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please log in to view your orders.')
        return redirect('login')

    orders = (
        Order.objects
        .filter(consumer_id=user_id)
        .prefetch_related('items__crop__farmer', 'items__payment')
        .order_by('-created_at')
    )

    now = timezone.now()
    enriched_orders = []

    for order in orders:
        items_data = []
        for item in order.items.all():
            elapsed_minutes = int((now - item.created_at).total_seconds() / 60)

            if item.status == 'verified':
                minutes_left = max(0, 120 - elapsed_minutes)
                if minutes_left > 0:
                    delivery_label = f'Arriving in ~{minutes_left} min'
                    delivery_state = 'arriving'
                else:
                    delivery_label = 'Delivered'
                    delivery_state = 'delivered'
            elif item.status == 'paid':
                delivery_label = 'Payment under review by farmer'
                delivery_state = 'review'
            elif item.status == 'rejected':
                delivery_label = 'Payment rejected — resubmit proof'
                delivery_state = 'rejected'
            else:
                delivery_label = 'Awaiting payment upload'
                delivery_state = 'pending'

            # Step index for timeline (0–4)
            step_map = {'pending': 0, 'review': 1, 'arriving': 2, 'delivered': 3, 'rejected': -1}
            timeline_step = step_map.get(delivery_state, 0)

            screenshot_url = None
            try:
                if item.payment and item.payment.screenshot:
                    screenshot_url = item.payment.screenshot.url
            except Exception:
                pass

            items_data.append({
                'item': item,
                'delivery_label': delivery_label,
                'delivery_state': delivery_state,
                'timeline_step': timeline_step,
                'elapsed_minutes': elapsed_minutes,
                'screenshot_url': screenshot_url,
            })

        enriched_orders.append({
            'order': order,
            'items': items_data,
        })

    return render(request, 'my_orders.html', {'enriched_orders': enriched_orders})

from cryptography.fernet import Fernet
import os

def get_fernet():
    key = os.getenv('CHAT_ENCRYPTION_KEY')
    if not key:
        key = Fernet.generate_key().decode()
        with open('.env', 'a') as f:
            f.write(f"\nCHAT_ENCRYPTION_KEY='{key}'\n")
        os.environ['CHAT_ENCRYPTION_KEY'] = key
    return Fernet(key.encode() if isinstance(key, str) else key)

def encrypt_message(message):
    f = get_fernet()
    return f.encrypt(message.encode()).decode()

def decrypt_message(encrypted_message):
    f = get_fernet()
    try:
        return f.decrypt(encrypted_message.encode()).decode()
    except Exception:
        return "[Error decrypting message]"

def chat_view(request, user_id):
    from .models import UserAccount, ChatMessage
    from django.db.models import Q
    
    current_user_id = request.session.get('user_id')
    if not current_user_id:
        return redirect('login')
        
    try:
        other_user = UserAccount.objects.get(id=user_id)
    except UserAccount.DoesNotExist:
        return redirect('marketplace')
        
    messages_qs = ChatMessage.objects.filter(
        Q(sender_id=current_user_id, receiver_id=user_id) | 
        Q(sender_id=user_id, receiver_id=current_user_id)
    ).order_by('timestamp')
    
    messages_list = []
    for msg in messages_qs:
        messages_list.append({
            'content': decrypt_message(msg.encrypted_content),
            'timestamp': msg.timestamp,
            'is_sender': msg.sender_id == current_user_id
        })
        
    return render(request, 'chat.html', {'other_user': other_user, 'messages_list': messages_list})

from django.http import JsonResponse
import json

def send_message_api(request):
    if request.method == 'POST':
        from .models import ChatMessage
        current_user_id = request.session.get('user_id')
        if not current_user_id:
            return JsonResponse({'success': False, 'message': 'Not logged in'})
            
        try:
            data = json.loads(request.body)
            receiver_id = data.get('receiver_id')
            content = data.get('content')
            
            if not receiver_id or not content:
                return JsonResponse({'success': False, 'message': 'Missing data'})
                
            encrypted = encrypt_message(content)
            
            msg = ChatMessage.objects.create(
                sender_id=current_user_id,
                receiver_id=receiver_id,
                encrypted_content=encrypted
            )
            
            from .models import UserAccount, Notification
            sender = UserAccount.objects.get(id=current_user_id)
            Notification.objects.create(
                user_id=receiver_id,
                title="New message received",
                message=f"{sender.first_name} {sender.last_name} sent you a new message.",
                link=f"/chat/{current_user_id}/"
            )
            
            time_str = msg.timestamp.strftime("%l:%M %p").strip()
            
            return JsonResponse({'success': True, 'timestamp': time_str})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
            
    return JsonResponse({'success': False, 'message': 'Invalid request'})

def fetch_messages_api(request):
    from .models import ChatMessage
    from django.db.models import Q
    current_user_id = request.session.get('user_id')
    other_user_id = request.GET.get('user_id')
    
    if not current_user_id or not other_user_id:
        return JsonResponse({'success': False, 'message': 'Invalid request'})
        
    messages_qs = ChatMessage.objects.filter(
        Q(sender_id=current_user_id, receiver_id=other_user_id) | 
        Q(sender_id=other_user_id, receiver_id=current_user_id)
    ).order_by('timestamp')
    
    messages_list = []
    for msg in messages_qs:
        time_str = msg.timestamp.strftime("%l:%M %p").strip()
        messages_list.append({
            'content': decrypt_message(msg.encrypted_content),
            'timestamp': time_str,
            'is_sender': msg.sender_id == current_user_id
        })
        
    return JsonResponse({'success': True, 'messages': messages_list})

def fetch_notifications_api(request):
    from .models import Notification
    from django.http import JsonResponse
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': 'Not logged in'})
    
    notifications = Notification.objects.filter(user_id=user_id).order_by('-created_at')[:15]
    unread_count = Notification.objects.filter(user_id=user_id, is_read=False).count()
    
    data = []
    for n in notifications:
        data.append({
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'is_read': n.is_read,
            'link': n.link,
            'time': n.created_at.strftime("%b %d, %I:%M %p")
        })
        
    return JsonResponse({'success': True, 'notifications': data, 'unread_count': unread_count})

def mark_notifications_read_api(request):
    from .models import Notification
    from django.http import JsonResponse
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': 'Not logged in'})
        
    Notification.objects.filter(user_id=user_id, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})
