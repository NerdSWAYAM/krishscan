from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('farmer-dashboard/', views.dashboard, name='dashboard'),
    path('sell/', views.sell, name='sell'),
    path('cart/', views.cart, name='cart'),
    path('price-tracker/', views.price_tracker, name='price_tracker'),
    path('consumer-dashboard/', views.consumer, name='consumerdash'),
    path('marketplace/', views.marketplace, name='marketplace'),
    path('disease-detect/', views.disease_detect, name='disease_detect'),
    path('experts/', views.experts, name='experts'),
    path('upload-crop/', views.upload_crop, name='upload_crop'),
    path('send-otp/', views.send_otp_api, name='send_otp'),
    path('weather/', views.weather, name='weather'),
    path('crop-history/', views.crop_history, name='crop_history'),
    
]