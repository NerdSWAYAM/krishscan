import re

with open('/home/swayam/SWAYAM/krishiscan_v2/krishiscan/settings.py', 'r') as f:
    settings_content = f.read()

if 'AUTHENTICATION_BACKENDS' not in settings_content:
    settings_content += "\n# Authentication\nLOGIN_URL = 'login'\nAUTHENTICATION_BACKENDS = ['krishi.views.UserAccountBackend']\n"

with open('/home/swayam/SWAYAM/krishiscan_v2/krishiscan/settings.py', 'w') as f:
    f.write(settings_content)


with open('/home/swayam/SWAYAM/krishiscan_v2/krishi/views.py', 'r') as f:
    views_content = f.read()

# 1. Remove the custom_login_required decorator we added earlier
views_content = re.sub(
    r'from functools import wraps\nfrom django\.shortcuts import redirect\n\ndef custom_login_required\(view_func\):\n.*?return _wrapped_view\n',
    '',
    views_content,
    flags=re.DOTALL
)

# 2. Add Django auth imports and monkey-patch / backend
auth_imports = """from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password

# Monkey-patch UserAccount to work seamlessly with Django Auth
UserAccount.is_active = True
UserAccount.is_authenticated = True
UserAccount.is_anonymous = False
UserAccount.get_session_auth_hash = lambda self: self.password

class UserAccountBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        try:
            user = UserAccount.objects.get(email=email)
            if check_password(password, user.password):
                return user
        except UserAccount.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return UserAccount.objects.get(pk=user_id)
        except UserAccount.DoesNotExist:
            return None
"""
views_content = views_content.replace('from .models import UserAccount, Crop, EmailOTP', 'from .models import UserAccount, Crop, EmailOTP\n' + auth_imports)

# 3. Revert @custom_login_required back to @login_required
views_content = views_content.replace('@custom_login_required', "@login_required(login_url='/login/')")

# 4. Modify signup to call auth_login
signup_pattern = r'(new_user\.save\(\)\s+)(request\.session\[\'user_id\'\] = new_user\.id)'
views_content = re.sub(signup_pattern, r"\1auth_login(request, new_user, backend='krishi.views.UserAccountBackend')\n        \2", views_content)

# 5. Modify login to use authenticate and auth_login
login_pattern_start = r'try:\n\s+user = UserAccount\.objects\.get\(email=email\)\n\s+if check_password\(password, user\.password\):'
login_replacement_start = """user = authenticate(request, email=email, password=password)
        if user is not None:
            auth_login(request, user)"""
views_content = re.sub(login_pattern_start, login_replacement_start, views_content)

login_pattern_end = r'except UserAccount\.DoesNotExist:\n\s+messages\.error\(request, \'No account found with this email\.\'\)'
login_replacement_end = """else:
            messages.error(request, 'Invalid email or password.')"""
views_content = re.sub(login_pattern_end, login_replacement_end, views_content)

# Remove the inner else (Invalid password) since it's merged
inner_else_pattern = r'else:\n\s+messages\.error\(request, \'Invalid password\.\'\)\n\s+'
views_content = re.sub(inner_else_pattern, '', views_content)


# 6. Replace custom logout_user with django's logout
logout_pattern = r'def logout_user\(request\):\n\s+request\.session\.flush\(\)\n\s+return redirect\(\'login\'\)'
logout_replacement = """def logout_user(request):
    auth_logout(request)
    return redirect('login')"""
views_content = re.sub(logout_pattern, logout_replacement, views_content)

with open('/home/swayam/SWAYAM/krishiscan_v2/krishi/views.py', 'w') as f:
    f.write(views_content)


print("Settings and views modified.")
