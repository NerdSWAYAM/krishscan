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
            messages.error(request, 'Invalid or expired OTP.')
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
    return render(request, 'consumerdash.html')

from django.core.cache import cache

def dashboard(request):
    import os
    import requests
    
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

    # Mock dynamic data for disease detections (since there is no model yet)
    recent_diseases = [
        {
            "icon": "🍅",
            "crop": "Tomato Leaf",
            "issue": "Early Blight detected in Sector 4.",
            "risk": "High Risk",
            "risk_class": "risk-high"
        },
        {
            "icon": "🌽",
            "crop": "Corn Stalk",
            "issue": "Signs of rust spotted during last scan.",
            "risk": "Medium Risk",
            "risk_class": "risk-med"
        },
        {
            "icon": "🥔",
            "crop": "Potato Field",
            "issue": "Scan complete. No issues found.",
            "risk": "Healthy",
            "risk_class": "risk-low"
        }
    ]

    context = {
        'market_prices': market_prices,
        'recent_diseases': recent_diseases,
    }
    return render(request, 'dashboard.html', context)

def sell(request):
    return render(request, 'sell.html')

def cart(request):
    return render(request, 'cart.html')

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

def send_otp_api(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            email = data.get('email')
        except:
            email = request.POST.get('email')
            
        if not email:
            return JsonResponse({'success': False, 'message': 'Email required'}, status=400)
            
        otp = str(random.randint(1000, 9999))
        EmailOTP.objects.create(email=email, otp=otp)
        
        try:
            send_mail(
                'KrishiScan - Verify Your Account',
                f'Your verification code is: {otp}',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            return JsonResponse({'success': True, 'message': 'OTP sent successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)