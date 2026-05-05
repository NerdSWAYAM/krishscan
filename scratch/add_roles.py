import re

with open('/home/swayam/SWAYAM/krishiscan_v2/krishi/views.py', 'r') as f:
    content = f.read()

# Add decorators
decorator_code = """from functools import wraps
from django.http import JsonResponse

def role_required(role):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user_role = request.session.get('role')
            if not user_role and request.user.is_authenticated:
                user_role = getattr(request.user, 'role', None)
                
            if user_role != role:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
                    return JsonResponse({'success': False, 'message': f'Access denied. Restricted to {role}s.'}, status=403)
                messages.error(request, f'Access denied. This page is restricted to {role}s.')
                if user_role == 'Farmer':
                    return redirect('dashboard')
                else:
                    return redirect('marketplace')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

farmer_required = role_required('Farmer')
consumer_required = role_required('Consumer')
"""

content = content.replace("from django.contrib.auth.hashers import check_password", "from django.contrib.auth.hashers import check_password\n" + decorator_code)

def add_decorator(view_name, decorator, text):
    pattern = r'(def ' + view_name + r'\(request.*?\):)'
    if f'@{decorator}\ndef {view_name}' not in text:
        text = re.sub(pattern, f'@{decorator}\n\\1', text)
    return text

# Farmer views
farmer_views = ['dashboard', 'sell', 'upload_crop', 'crop_history', 'wallet_view']
for v in farmer_views:
    content = add_decorator(v, 'farmer_required', content)

# Consumer views
consumer_views = ['consumer', 'cart', 'wishlist_view', 'my_orders']
for v in consumer_views:
    content = add_decorator(v, 'consumer_required', content)

with open('/home/swayam/SWAYAM/krishiscan_v2/krishi/views.py', 'w') as f:
    f.write(content)

print("Roles decorators added successfully.")
