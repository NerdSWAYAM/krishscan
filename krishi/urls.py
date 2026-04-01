from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    # path('kishiscan/', views.kishiscan, name='kishiscan'),
    path('sell/', views.sell, name='sell'),
    path('cart/', views.cart, name='cart'),
]