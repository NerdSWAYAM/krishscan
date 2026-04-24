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

def marketplace(request):
    crops = Crop.objects.all().order_by('-created_at')
    return render(request, 'marketplace.html', {'crops': crops})

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
            messages.success(request, 'Crop uploaded successfully!')
            return redirect('marketplace')
        except UserAccount.DoesNotExist:
            messages.error(request, 'Account verification failed.')
            return redirect('login')

    return render(request, 'upload_crop.html')

def consumer(request):
    import requests
    from django.core.cache import cache
    import os
    from .models import Order

    # Fetch Real-Time Market Price
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

    # Fetch Recent Orders
    user_id = request.session.get('user_id')
    if user_id:
        recent_orders = Order.objects.filter(consumer_id=user_id).select_related('crop').order_by('-created_at')[:5]
    else:
        recent_orders = []

    context = {
        'market_prices': market_prices,
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
    if user_id:
        crops_uploaded = Crop.objects.filter(farmer_id=user_id).count()
        crops_sold_count = Crop.objects.filter(farmer_id=user_id, orders__status='Sold').distinct().count()
        crops_unsold_count = crops_uploaded - crops_sold_count
        crops_sold = crops_sold_count  # Keep existing variable name if used elsewhere
        uploaded_crops = Crop.objects.filter(farmer_id=user_id).order_by('-created_at')
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
            crop.delete()
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
    grand_total = 0
    
    for crop_id, qty in wishlist.items():
        try:
            crop = Crop.objects.get(id=int(crop_id))
            line_total = float(crop.price_per_kg) * float(qty)
            grand_total += line_total
            cart_items.append({
                'crop': crop,
                'quantity': float(qty),
                'line_total': line_total
            })
        except Crop.DoesNotExist:
            continue
            
    context = {
        'cart_items': cart_items,
        'grand_total': grand_total
    }
    return render(request, 'wishlist.html', context)

# _disease_model = None

# def get_disease_model():
#     import torch
#     import torch.nn as nn
#     import timm
#     from huggingface_hub import hf_hub_download
#     global _disease_model
#     if _disease_model is None:
#         model_path = hf_hub_download(repo_id="VisionaryQuant/5_Crop_Disease_Detection", filename="best_crop_disease_model.pt")
#         model = timm.create_model('efficientnet_b3', pretrained=False)
#         model.classifier = nn.Sequential(
#             nn.Linear(model.classifier.in_features, 17)
#         )
#         state_dict = torch.load(model_path, map_location=torch.device('cpu'))
#         model.load_state_dict(state_dict)
#         model.eval()
#         _disease_model = model
#     return _disease_model

# CLASS_NAMES = [
#     "Corn___Common_Rust", "Corn___Gray_Leaf_Spot", "Corn___Healthy", "Corn___Northern_Leaf_Blight",
#     "Potato___Early_Blight", "Potato___Healthy", "Potato___Late_Blight",
#     "Rice___Brown_Spot", "Rice___Healthy", "Rice___Leaf_Blast", "Rice___Neck_Blast",
#     "Sugarcane___Bacterial_Blight", "Sugarcane___Healthy", "Sugarcane___Red_Rot",
#     "Wheat___Brown_Rust", "Wheat___Healthy", "Wheat___Yellow_Rust"
# ]

def disease_detect(request):
#     import torch
#     from torchvision import transforms
#     from PIL import Image

#     result = None
#     if request.method == 'POST' and request.FILES.get('image'):
#         image_file = request.FILES['image']
#         try:
#             image = Image.open(image_file).convert("RGB")
#             transform = transforms.Compose([
#                 transforms.Resize((300, 300)),
#                 transforms.ToTensor(),
#                 transforms.Normalize(mean=[0.485, 0.456, 0.406],
#                                      std=[0.229, 0.224, 0.225])
#             ])
#             input_tensor = transform(image).unsqueeze(0)
            
#             model = get_disease_model()
#             with torch.no_grad():
#                 logits = model(input_tensor)
#                 probs = torch.nn.functional.softmax(logits, dim=1)
#                 confidence, predicted_idx = torch.max(probs, dim=1)
                
#                 predicted_idx = predicted_idx.item()
#                 confidence_score = confidence.item() * 100
                
#             if predicted_idx < len(CLASS_NAMES):
#                 predicted_label = CLASS_NAMES[predicted_idx]
#             else:
#                 predicted_label = "Unknown"
                
#             result = {
#                 'disease': predicted_label.replace('___', ' - ').replace('_', ' '),
#                 'confidence': confidence_score
#             }
#         except Exception as e:
#             result = {'error': str(e)}

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
        
    from .models import Crop, Order
    
    # Fetch all crops uploaded by this farmer
    crops = Crop.objects.filter(farmer_id=user_id).order_by('-created_at')
    
    # Fetch all orders related to this farmer's crops
    orders = Order.objects.filter(crop__farmer_id=user_id).select_related('crop', 'consumer').order_by('-created_at')
    
    context = {
        'crops': crops,
        'orders': orders
    }
    return render(request, 'crop_history.html', context)