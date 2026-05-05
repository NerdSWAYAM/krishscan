import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "krishiscan.settings")
django.setup()

from django.test import RequestFactory
from django.contrib.auth import authenticate
from krishi.models import UserAccount

print("Testing user authentication...")
user = UserAccount.objects.first()
if user:
    print(f"Found user: {user.email}")
    # We don't know the password, let's just test if authenticate() with wrong password behaves as expected, 
    # but wait, can we change a user's password temporarily?
    old_pw = user.password
    from django.contrib.auth.hashers import make_password
    user.password = make_password('testpass')
    user.save()

    factory = RequestFactory()
    request = factory.get('/login')
    
    # Test authenticate
    auth_user = authenticate(request, email=user.email, password='testpass')
    print("auth_user:", auth_user)
    if auth_user:
        print("Backend:", getattr(auth_user, 'backend', None))
        
    user.password = old_pw
    user.save()
else:
    print("No users in db.")
