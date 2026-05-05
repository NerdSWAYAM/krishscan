import re

with open('/home/swayam/SWAYAM/krishiscan_v2/krishi/views.py', 'r') as f:
    content = f.read()

# 1. Remove django's login_required import
content = re.sub(r'from django\.contrib\.auth\.decorators import login_required\n?', '', content)

# 2. Add custom decorator at the top after imports
decorator_code = """
from functools import wraps
from django.shortcuts import redirect

def custom_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('user_id'):
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
"""
# find the first empty line after imports to insert
content = content.replace("from .models import UserAccount, Crop, EmailOTP", "from .models import UserAccount, Crop, EmailOTP\n" + decorator_code)

# 3. Replace existing @login_required(...) with @custom_login_required
content = re.sub(r'@login_required\(login_url=[\'"][^\'"]+[\'"]\)', '@custom_login_required', content)

# 4. Add @custom_login_required to specific views if they don't have it
def add_decorator(view_name, text):
    # Find def view_name(request...
    pattern = r'(def ' + view_name + r'\(request.*?\):)'
    # check if it already has the decorator
    if f'@custom_login_required\ndef {view_name}' not in text:
        text = re.sub(pattern, r'@custom_login_required\n\1', text)
    return text

views_to_protect = ['disease_detect', 'experts', 'price_tracker']
for v in views_to_protect:
    content = add_decorator(v, content)

# 5. Add logout view
logout_code = """
def logout_user(request):
    request.session.flush()
    return redirect('login')
"""
content += "\n" + logout_code

with open('/home/swayam/SWAYAM/krishiscan_v2/krishi/views.py', 'w') as f:
    f.write(content)

print("views.py refactored successfully.")
