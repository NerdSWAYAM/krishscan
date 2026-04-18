from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from .models import UserAccount

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
        
        if UserAccount.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered. Please login.')
            return redirect('signup')
            
        hashed_password = make_password(password)

        new_user = UserAccount(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=hashed_password,
            role=role,
            location=location
        )
        new_user.save()
        messages.success(request, 'Account created successfully! Please login.')
        return redirect('login')

    return render(request, 'signup.html')

def login(request):
    return render(request, 'login.html')

def dashboard(request):
    return render(request, 'dashboard.html')

def sell(request):
    return render(request, 'sell.html')

def cart(request):
    return render(request, 'cart.html')

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
    
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        records = data.get('records', [])
    except requests.exceptions.RequestException as e:
        print("Error fetching data:", e)
        records = []
        
    context = {
        'records': records,
        'state': state,
        'commodity': commodity,
    }
    return render(request, 'price_tracker.html', context)