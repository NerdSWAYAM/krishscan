import os
import django
from django.conf import settings
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'krishiscan.settings')
django.setup()

from krishi.models import UserAccount
from django.contrib.auth import login

# Monkey patch
UserAccount.is_active = True
UserAccount.is_authenticated = True
UserAccount.is_anonymous = False
UserAccount.get_session_auth_hash = lambda self: self.password

class UserAccountBackend:
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            return UserAccount.objects.first()
        except UserAccount.DoesNotExist:
            return None
    def get_user(self, user_id):
        try:
            return UserAccount.objects.get(pk=user_id)
        except UserAccount.DoesNotExist:
            return None

# Add to settings dynamically for test
settings.AUTHENTICATION_BACKENDS = ['__main__.UserAccountBackend']

factory = RequestFactory()
request = factory.get('/')

# Add session
middleware = SessionMiddleware(lambda r: None)
middleware.process_request(request)
request.session.save()

# Add user
user = UserAccount.objects.first()
user.backend = '__main__.UserAccountBackend'

print("Attempting to login...")
try:
    login(request, user)
    print("Login successful!")
    print("Session keys:", request.session.keys())
    print("_auth_user_id:", request.session.get('_auth_user_id'))
except Exception as e:
    print("Error during login:", e)
