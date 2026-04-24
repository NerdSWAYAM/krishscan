from django.urls import path
from . import views
# from .email import SendOTPView, VerifyOTPView

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('farmer-dashboard/', views.dashboard, name='dashboard'),
    path('sell/', views.sell, name='sell'),
    path('cart/', views.cart, name='cart'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('api/add-to-wishlist/', views.add_to_wishlist, name='add_to_wishlist'),
    path('api/remove-from-wishlist/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('api/remove-crop/', views.remove_crop, name='remove_crop'),
    path('price-tracker/', views.price_tracker, name='price_tracker'),
    path('consumer-dashboard/', views.consumer, name='consumerdash'),
    path('marketplace/', views.marketplace, name='marketplace'),
    path('disease-detect/', views.disease_detect, name='disease_detect'),
    path('experts/', views.experts, name='experts'),
    path('upload-crop/', views.upload_crop, name='upload_crop'),
    path('send-otp/', views.send_otp_api, name='send_otp'),
    # path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('weather/', views.weather, name='weather'),
    path('crop-history/', views.crop_history, name='crop_history'),
    
]