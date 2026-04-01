from django.shortcuts import render

def home(request):
    return render(request, 'index.html')

def signup(request):
    return render(request, 'signup.html')

def login(request):
    return render(request, 'login.html')

def dashboard(request):
    return render(request, 'dashboard.html')

def sell(request):
    return render(request, 'sell.html')

def cart(request):
    return render(request, 'cart.html')