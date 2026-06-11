from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from .models import UserAccount, Crop, EmailOTP
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from functools import wraps
from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme

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


# Monkey-patch UserAccount to work seamlessly with Django Auth
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.models import update_last_login
user_logged_in.disconnect(update_last_login, dispatch_uid='update_last_login')

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
        coordinates = request.POST.get('coordinates')
        user_otp = request.POST.get('otp')
        
        if UserAccount.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered. Please login.')
            return redirect('signup')
            
        stored_otp = EmailOTP.objects.filter(email=email).order_by('-created_at').first()
        if not stored_otp or stored_otp.otp != user_otp:
            messages.error(request, 'Invalid OTP.')
            return redirect('signup')
            
        if not stored_otp.is_valid():
            messages.error(request, 'OTP has expired. Please request a new one.')
            return redirect('signup')
            
        hashed_password = make_password(password)

        new_user = UserAccount(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=hashed_password,
            role=role,
            location=location,
            coordinates=coordinates
        )
        new_user.save()
        
        auth_login(request, new_user, backend='krishi.views.UserAccountBackend')
        request.session['user_id'] = new_user.id
        request.session['role'] = new_user.role
        request.session['first_name'] = new_user.first_name
        request.session['last_name'] = new_user.last_name
        request.session['email'] = new_user.email
        request.session['location'] = new_user.location
        request.session['coordinates'] = new_user.coordinates
        
        messages.success(request, 'Account created successfully!')
        return redirect('marketplace')

    return render(request, 'signup.html')

from django.contrib.auth.hashers import check_password
from functools import wraps
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


def login(request):
    next_url = request.POST.get('next') or request.GET.get('next')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, email=email, password=password)
        if user is not None:
            auth_login(request, user)
            request.session['user_id'] = user.id
            request.session['role'] = user.role
            request.session['first_name'] = user.first_name
            request.session['last_name'] = user.last_name
            request.session['email'] = user.email
            request.session['location'] = user.location
            request.session['coordinates'] = user.coordinates
            
            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)

            if user.role == 'Farmer':
                return redirect('dashboard')
            return redirect('marketplace')
        else:
            messages.error(request, 'Invalid email or password.')
            
    return render(request, 'login.html', {'next': next_url})

### Distance Calculation
import math

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    return round(distance, 2)



@login_required(login_url='/login/')
def marketplace(request):
    crops = Crop.objects.select_related('farmer').all().order_by('-created_at')
    
    user_coords = request.session.get('coordinates')
    
    crop_list = []
    for crop in crops:
        distance = None
        if user_coords and crop.farmer.coordinates:
            try:
                lat1, lon1 = map(float, user_coords.split(','))
                lat2, lon2 = map(float, crop.farmer.coordinates.split(','))
                distance = calculate_distance(lat1, lon1, lat2, lon2)
            except ValueError:
                pass
        crop.distance = distance
        crop_list.append(crop)
        
    if user_coords:
        crop_list.sort(key=lambda x: (x.distance is None, x.distance))
    
    # Get user's wishlist
    wishlist = {}
    user_id = request.session.get('user_id')
    if user_id:
        try:
            user = UserAccount.objects.get(id=user_id)
            wishlist = user.wishlist or {}
        except UserAccount.DoesNotExist:
            wishlist = {}
        
    return render(request, 'marketplace.html', {
        'crops': crop_list,
        'wishlist': wishlist,
        'user_coords': user_coords or '',
    })

@login_required(login_url='/login/')
def weather(request):
    return render(request, 'weather.html')

@login_required(login_url='/login/')
@farmer_required
def upload_crop(request):
    if request.session.get('role') != 'Farmer':
        messages.error(request, 'Only farmers can upload crops.')
        return redirect('marketplace')

    if request.method == 'POST':
        name = request.POST.get('name')
        quantity = request.POST.get('quantity')
        price_per_kg = request.POST.get('price_per_kg')
        image = request.FILES.get('image')

        user_id = request.session.get('user_id')
        try:
            farmer = UserAccount.objects.get(id=user_id)
            new_crop = Crop(
                farmer=farmer,
                name=name,
                quantity=quantity,
                price_per_kg=price_per_kg,
                image=image
            )
            new_crop.save()
            
            from .models import Notification
            Notification.objects.create(
                user=farmer,
                title="Crop uploaded successfully",
                message=f"Your crop '{name}' is now live on the marketplace and available to buyers.",
                link="/dashboard/"
            )
            
            messages.success(request, 'Crop uploaded successfully!')
            return redirect('marketplace')
        except UserAccount.DoesNotExist:
            messages.error(request, 'Account verification failed.')
            return redirect('login')

    return render(request, 'upload_crop.html')

@login_required(login_url='/login/')
@consumer_required
def consumer(request):
    import os
    from .models import Order

    # Fetch Recent Orders and Recently Connected Farmers
    user_id = request.session.get('user_id')
    recent_farmers = []
    if user_id:
        from .models import OrderItem, ChatMessage, UserAccount
        recent_orders = (
            OrderItem.objects
            .filter(order__consumer_id=user_id)
            .select_related('crop', 'order__consumer', 'farmer')
            .order_by('-created_at')[:5]
        )
        
        # Get recently connected farmers via chat
        chat_farmer_ids = set(ChatMessage.objects.filter(sender_id=user_id).values_list('receiver_id', flat=True))
        chat_farmer_ids.update(ChatMessage.objects.filter(receiver_id=user_id).values_list('sender_id', flat=True))
        
        recent_farmers = UserAccount.objects.filter(id__in=chat_farmer_ids, role='Farmer')[:5]
    else:
        recent_orders = []

    context = {
        'recent_farmers': recent_farmers,
        'recent_orders': recent_orders,
    }
    return render(request, 'consumerdash.html', context)


from django.core.cache import cache
@login_required(login_url='/login/')
@farmer_required
def dashboard(request):
    import os
    import requests
    from django.utils import timezone
    from .models import Crop, Order
    
    # Removed blocking API calls to prevent dashboard slowness.
    # These are now handled via AJAX in dashboard_stats_api.
    market_prices = []

    # Weather is now handled via AJAX
    weather_data = None

    # Crop Stats
    user_id = request.session.get('user_id')
    recent_consumers = []
    if user_id:
        from .models import OrderItem, ChatMessage, UserAccount
        crops_uploaded = Crop.objects.filter(farmer_id=user_id).count()
        crops_sold_count = Crop.objects.filter(
            farmer_id=user_id,
            order_items__status='verified'
        ).distinct().count()
        crops_unsold_count = crops_uploaded - crops_sold_count
        crops_sold = crops_sold_count
        uploaded_crops = Crop.objects.filter(farmer_id=user_id).order_by('-created_at')

        # Get recently connected consumers via chat
        chat_consumer_ids = set(ChatMessage.objects.filter(sender_id=user_id).values_list('receiver_id', flat=True))
        chat_consumer_ids.update(ChatMessage.objects.filter(receiver_id=user_id).values_list('sender_id', flat=True))
        
        recent_consumers = UserAccount.objects.filter(id__in=chat_consumer_ids, role='Consumer')[:5]
        
        user = UserAccount.objects.get(id=user_id)
        wallet_balance = user.wallet_balance
    else:
        crops_uploaded = 0
        crops_sold_count = 0
        crops_unsold_count = 0
        crops_sold = 0
        uploaded_crops = []
        wallet_balance = 0

    context = {
        'market_prices': market_prices,
        'weather_data': weather_data,
        'crops_uploaded': crops_uploaded,
        'crops_sold': crops_sold,
        'crops_sold_count': crops_sold_count,
        'crops_unsold_count': crops_unsold_count,
        'uploaded_crops': uploaded_crops,
        'recent_consumers': recent_consumers,
        'wallet_balance': wallet_balance,
    }
    return render(request, 'dashboard.html', context)

@login_required(login_url='/login/')
@farmer_required
def sell(request):
    return render(request, 'sell.html')

@login_required(login_url='/login/')
@consumer_required
def cart(request):
    return render(request, 'cart.html')

@login_required(login_url='/login/')
def add_to_wishlist(request):
    import json
    from django.http import JsonResponse
    from .models import Crop
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            crop_id = str(data.get('crop_id'))
            quantity = float(data.get('quantity'))
            
            user_id = request.session.get('user_id')
            if not user_id:
                return JsonResponse({'success': False, 'message': 'Not logged in'})
            user = UserAccount.objects.get(id=user_id)
            
            wishlist = user.wishlist if user.wishlist else {}
            if not isinstance(wishlist, dict):
                wishlist = {}
            
            crop = Crop.objects.get(id=int(crop_id))
            if quantity > crop.quantity:
                return JsonResponse({'success': False, 'message': 'Requested quantity exceeds available stock.'})
            
            wishlist[crop_id] = quantity
            user.wishlist = wishlist
            user.save(update_fields=['wishlist'])
            
            from .models import Notification
            Notification.objects.create(
                user=user,
                title="Added to Cart",
                message=f"{crop.name} ({quantity}kg) has been added to your cart.",
                link="/wishlist/"
            )
            
            return JsonResponse({'success': True, 'message': 'Added to wishlist!'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required(login_url='/login/')
def remove_from_wishlist(request):
    import json
    from django.http import JsonResponse
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            crop_id = str(data.get('crop_id'))
            
            user_id = request.session.get('user_id')
            if not user_id:
                return JsonResponse({'success': False, 'message': 'Not logged in'})
            user = UserAccount.objects.get(id=user_id)
            
            wishlist = user.wishlist if user.wishlist else {}
            if crop_id in wishlist:
                del wishlist[crop_id]
                user.wishlist = wishlist
                user.save(update_fields=['wishlist'])
                
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Invalid request'})


@login_required(login_url='/login/')
def remove_crop(request):
    import json
    from django.http import JsonResponse
    from .models import Crop

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            crop_id = data.get('crop_id')
            user_id = request.session.get('user_id')

            if not user_id:
                return JsonResponse({'success': False, 'message': 'Authentication required.'}, status=403)

            crop = Crop.objects.get(id=int(crop_id), farmer_id=user_id)
            crop_name = crop.name
            crop.delete()
            
            from .models import Notification
            Notification.objects.create(
                user_id=user_id,
                title="Crop removed",
                message=f"Your listing for '{crop_name}' has been removed from the marketplace.",
                link="/dashboard/"
            )
            
            return JsonResponse({'success': True})
        except Crop.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Crop not found or not owned by you.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required(login_url='/login/')
@consumer_required
def wishlist_view(request):
    from .models import Crop
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('login')
    user = UserAccount.objects.get(id=user_id)
    wishlist = user.wishlist
    if not isinstance(wishlist, dict):
        wishlist = {}
    cart_items = []
    farmer_groups = {}
    grand_total = 0
    
    # Get user coordinates for distance calculation
    user_lat = user_lon = None
    coords_str = request.session.get('coordinates')
    if coords_str:
        try:
            user_lat, user_lon = map(float, coords_str.split(','))
        except ValueError:
            pass

    # Optimization: Get all crops in wishlist with one query
    crop_ids = []
    for cid in wishlist.keys():
        try:
            crop_ids.append(int(cid))
        except (ValueError, TypeError):
            pass
    crops = {c.id: c for c in Crop.objects.select_related('farmer').filter(id__in=crop_ids)}
    
    for crop_id_str, qty in wishlist.items():
        crop_id = int(crop_id_str)
        if crop_id in crops:
            crop = crops[crop_id]
            line_total = float(crop.price_per_kg) * float(qty)
            grand_total += line_total
            
            farmer = crop.farmer
            distance = None
            if user_lat and user_lon and farmer.coordinates:
                try:
                    f_lat, f_lon = map(float, farmer.coordinates.split(','))
                    distance = round(calculate_distance(user_lat, user_lon, f_lat, f_lon), 2)
                except ValueError:
                    pass

            if farmer.id not in farmer_groups:
                farmer_groups[farmer.id] = {
                    'farmer': farmer,
                    'items': [],
                    'subtotal': 0
                }
                
            item_data = {
                'crop': crop,
                'quantity': float(qty),
                'line_total': line_total,
                'distance': distance
            }
            farmer_groups[farmer.id]['items'].append(item_data)
            farmer_groups[farmer.id]['subtotal'] += line_total
            cart_items.append(item_data)
            
    context = {
        'cart_items': cart_items,
        'farmer_groups': list(farmer_groups.values()),
        'grand_total': grand_total
    }
    return render(request, 'wishlist.html', context)

@login_required(login_url='/login/')
def disease_detect(request):
    from PIL import Image
    import base64
    from io import BytesIO

    result = None
    if request.method == 'POST' and request.FILES.get('image'):
        image_file = request.FILES['image']
        try:
            # Save uploaded image as base64 to show in preview
            img = Image.open(image_file).convert("RGB")
            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            img_data_uri = f"data:image/jpeg;base64,{img_str}"

            from .ml_services import get_disease_model, get_resnet_model, CLASS_NAMES
            import torch
            import tensorflow as tf
            from torchvision import transforms
            import numpy as np

            # 1. HuggingFace PyTorch Model Inference
            disease_model = get_disease_model()
            transform = transforms.Compose([
                transforms.Resize((300, 300)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std=[0.229, 0.224, 0.225])
            ])
            input_tensor = transform(img).unsqueeze(0)

            with torch.no_grad():
                logits = disease_model(input_tensor)
                probs = torch.nn.functional.softmax(logits, dim=1)
                hf_conf, hf_idx = torch.max(probs, dim=1)
                hf_conf = hf_conf.item()
                hf_idx = hf_idx.item()

            if hf_idx < len(CLASS_NAMES):
                hf_label = CLASS_NAMES[hf_idx]
            else:
                hf_label = f"Unknown Class {hf_idx}"

            # 2. ResNet TensorFlow Model Inference
            resnet_model = get_resnet_model()
            img_resized = img.resize((224, 224))
            img_array = np.array(img_resized, dtype=np.float32)
            img_array = np.expand_dims(img_array, axis=0)
            img_array = tf.keras.applications.resnet50.preprocess_input(img_array)

            resnet_preds = resnet_model.predict(img_array, verbose=0)
            resnet_idx = int(np.argmax(resnet_preds[0]))
            resnet_conf = float(resnet_preds[0][resnet_idx])

            if resnet_idx < len(CLASS_NAMES):
                resnet_label = CLASS_NAMES[resnet_idx]
            else:
                resnet_label = f"Unknown Class {resnet_idx}"

            # 3. Decision Logic
            best_conf = 0
            best_label = ""
            
            if hf_conf > 0.60 and resnet_conf > 0.60:
                if hf_conf > resnet_conf:
                    best_conf = hf_conf
                    best_label = hf_label
                else:
                    best_conf = resnet_conf
                    best_label = resnet_label
            
            if best_conf > 0.60:
                clean_label = best_label.replace('___', ' - ').replace('_', ' ')
                if "healthy" in clean_label.lower():
                    result = {
                        'disease': "Healthy Crop",
                        'confidence': best_conf * 100,
                        'image_uri': img_data_uri
                    }
                else:
                    result = {
                        'disease': clean_label,
                        'confidence': best_conf * 100,
                        'image_uri': img_data_uri
                    }
            else:
                result = {
                    'disease': "Failed to detect",
                    'confidence': max(hf_conf, resnet_conf) * 100,
                    'error': "Failed to detect. Confidence scores are below 60%.",
                    'image_uri': img_data_uri
                }

        except Exception as e:
            result = {'error': str(e)}
            if 'img_data_uri' in locals() and img_data_uri:
                result['image_uri'] = img_data_uri

    return render(request, 'disease_detect.html', {'result': result})

@login_required(login_url='/login/')
def experts(request):
    return render(request, 'experts.html')

import requests
import os
import dotenv

dotenv.load_dotenv()

@login_required(login_url='/login/')
def price_tracker(request):
    import json
    import subprocess
    import urllib.parse
    from django.conf import settings
    from django.utils import timezone

    API_KEY = os.getenv("API_KEY")
    RESOURCE_ID = os.getenv("RESOURCE_ID")

    url = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

    state     = request.GET.get('state', '').strip()
    commodity = request.GET.get('commodity', '').strip()
    async_load = request.GET.get('async_load') == '1'

    if not async_load:
        context = {
            'state': state,
            'commodity': commodity,
            'skeleton_only': True
        }
        return render(request, 'price_tracker.html', context)

    # ------------------------------------------------------------------ #
    #  Daily JSON cache (curl fallback — valid for the entire day)        #
    # ------------------------------------------------------------------ #
    def _daily_cache_path():
        cache_dir = os.path.join(settings.BASE_DIR, 'data')
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, 'price_tracker_daily.json')

    def _load_daily_cache():
        today = timezone.localdate().isoformat()
        try:
            with open(_daily_cache_path(), 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('date') == today:
                return data
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass
        return {'date': today, 'fetched_at': None, 'entries': {}}

    def _save_daily_cache(cache_data):
        path = _daily_cache_path()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            print(f"[INFO] Saved daily price cache to {path}")
        except OSError as exc:
            print(f"[ERROR] Failed to save daily price cache: {exc}")

    def _persist_daily_entry(daily_cache, entry_key, records, total, source):
        if not records:
            return
        daily_cache['entries'][entry_key] = {
            'records': records,
            'total': total,
            'source': source,
        }
        daily_cache['fetched_at'] = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')
        _save_daily_cache(daily_cache)

    def _fetch_via_curl(api_url, params, timeout=8):
        full_url = f"{api_url}?{urllib.parse.urlencode(params)}"
        try:
            result = subprocess.run(
                ['curl', '-sS', '--max-time', str(timeout), full_url],
                capture_output=True, text=True, timeout=timeout + 1, check=False,
            )
            if result.returncode != 0:
                print(f"[ERROR] curl exit {result.returncode}: {result.stderr.strip()}")
                return None
            if not result.stdout.strip():
                print("[ERROR] curl returned empty response")
                return None
            data = json.loads(result.stdout)
            if data.get('status') == 'ok':
                return data
            print(f"[ERROR] curl API status not ok: {data.get('status')}")
        except Exception as exc:
            print(f"[ERROR] curl fetch failed: {exc}")
        return None

    def _filter_records(records, state_filter='', commodity_filter=''):
        filtered = records
        if state_filter:
            filtered = [
                r for r in filtered
                if r.get('state', '').strip().lower() == state_filter.lower()
            ]
        if commodity_filter:
            filtered = [
                r for r in filtered
                if r.get('commodity', '').strip().lower() == commodity_filter.lower()
            ]
        return filtered

    def _fetch_mandi_api(api_url, params, entry_key, daily_cache):
        """Try requests → curl → today's JSON file. Returns (records, total, source)."""
        try:
            response = requests.get(api_url, params=params, timeout=8)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok':
                    records = data.get('records', [])
                    total = data.get('total', len(records))
                    if records:
                        _persist_daily_entry(daily_cache, entry_key, records, total, 'live')
                        return records, total, 'live'
                else:
                    print(f"[ERROR] API returned error status: {data}")
            else:
                print(f"[ERROR] API HTTP {response.status_code}")
        except requests.exceptions.RequestException as exc:
            print(f"[ERROR] API unavailable: {exc}")

        print(f"[INFO] Trying curl fallback for {entry_key}...")
        curl_data = _fetch_via_curl(api_url, params)
        if curl_data:
            records = curl_data.get('records', [])
            total = curl_data.get('total', len(records))
            if records:
                _persist_daily_entry(daily_cache, entry_key, records, total, 'cached')
                return records, total, 'cached'

        entry = daily_cache.get('entries', {}).get(entry_key)
        if entry and entry.get('records'):
            print(f"[INFO] Using today's JSON cache for {entry_key}")
            src = entry.get('source', 'cached')
            return entry['records'], entry.get('total', len(entry['records'])), src

        all_entry = daily_cache.get('entries', {}).get('main_all_all')
        if all_entry and all_entry.get('records'):
            state_f = params.get('filters[state.keyword]', '')
            comm_f = params.get('filters[commodity]', '')
            filtered = _filter_records(all_entry['records'], state_f, comm_f)
            if filtered:
                print("[INFO] Using filtered records from today's JSON cache (all_all)")
                src = all_entry.get('source', 'cached')
                return filtered, len(filtered), src

        return None, 0, None

    daily_cache = _load_daily_cache()
    data_source = 'live'
    cache_date = daily_cache.get('date')
    cache_fetched_at = daily_cache.get('fetched_at')

    # ------------------------------------------------------------------ #
    #  Helper: load CSV and return normalised record dicts                 #
    # ------------------------------------------------------------------ #
    def _load_csv(state_filter='', commodity_filter='', limit=100):
        import csv as _csv
        csv_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'mandi_prices.csv'
        )
        results = []
        try:
            with open(csv_path, newline='', encoding='utf-8') as f:
                reader = _csv.DictReader(f)
                for row in reader:
                    if state_filter and row.get('state', '').strip().lower() != state_filter.lower():
                        continue
                    if commodity_filter and row.get('commodity', '').strip().lower() != commodity_filter.lower():
                        continue
                    modal = float(row.get('modal_price', 0) or 0)
                    results.append({
                        'state':        row.get('state', ''),
                        'district':     row.get('district', ''),
                        'market':       row.get('market', ''),
                        'commodity':    row.get('commodity', ''),
                        'variety':      row.get('variety', 'Other'),
                        'arrival_date': row.get('arrival_date', 'N/A'),
                        'min_price':    row.get('min_price') or round(modal * 0.85),
                        'max_price':    row.get('max_price') or round(modal * 1.15),
                        'modal_price':  row.get('modal_price', modal),
                    })
                    if len(results) >= limit:
                        break
        except Exception as exc:
            print("CSV load error:", exc)
        return results

    def _ensure_today_json_cache():
        """Populate today's JSON file if missing (curl-first — API often times out)."""
        nonlocal daily_cache, cache_fetched_at, data_source
        if daily_cache.get('entries'):
            return
        base_params = {
            "api-key": API_KEY,
            "format": "json",
            "limit": 100,
        }
        print("[INFO] Today's JSON cache empty — fetching via curl...")
        curl_data = _fetch_via_curl(url, base_params)
        if curl_data and curl_data.get('records'):
            _persist_daily_entry(
                daily_cache, 'main_all_all',
                curl_data['records'], curl_data.get('total', 0), 'cached',
            )
            data_source = 'cached'
            cache_fetched_at = daily_cache.get('fetched_at')
            return
        api_records, _, source = _fetch_mandi_api(url, base_params, 'main_all_all', daily_cache)
        if api_records:
            data_source = source
            cache_fetched_at = daily_cache.get('fetched_at')
            return
        csv_records = _load_csv(limit=100)
        if csv_records:
            print("[INFO] Saving CSV fallback into today's JSON cache...")
            _persist_daily_entry(
                daily_cache, 'main_all_all', csv_records, len(csv_records), 'csv',
            )
            data_source = 'csv'
            cache_fetched_at = daily_cache.get('fetched_at')

    _ensure_today_json_cache()
    daily_cache = _load_daily_cache()
    cache_date = daily_cache.get('date')
    cache_fetched_at = daily_cache.get('fetched_at') or cache_fetched_at

    # ------------------------------------------------------------------ #
    #  Main records (Market Updates section)                              #
    # ------------------------------------------------------------------ #
    params = {
        "api-key": API_KEY,
        "format":  "json",
        "limit":   100,
    }
    if state:
        params["filters[state.keyword]"] = state
    if commodity:
        params["filters[commodity]"] = commodity

    cache_key = f'price_tracker_{state or "all"}_{commodity or "all"}'
    entry_key = f'main_{state or "all"}_{commodity or "all"}'
    cached_payload = cache.get(cache_key)
    records = None
    total = 0

    if cached_payload is not None:
        if isinstance(cached_payload, dict) and 'records' in cached_payload:
            records = cached_payload['records']
            total = cached_payload.get('total', len(records))
            data_source = cached_payload.get('source', 'live')
            cache_date = cached_payload.get('cache_date', cache_date)
            cache_fetched_at = cached_payload.get('cache_fetched_at', cache_fetched_at)
        else:
            records = cached_payload
            total = len(records)

    if records is None:
        api_records, total, source = _fetch_mandi_api(url, params, entry_key, daily_cache)
        if api_records:
            records = api_records
            data_source = source
            cache_fetched_at = daily_cache.get('fetched_at')
            cache.set(cache_key, {
                'records': records,
                'total': total,
                'source': source,
                'cache_date': daily_cache.get('date'),
                'cache_fetched_at': cache_fetched_at,
            }, 60 * 30)
        else:
            print("[INFO] Falling back to CSV data...")
            records = _load_csv(state_filter=state, commodity_filter=commodity, limit=100)
            total = len(records)
            data_source = 'csv'
            if records:
                _persist_daily_entry(
                    daily_cache, entry_key, records, total, 'csv',
                )
                cache_fetched_at = daily_cache.get('fetched_at')
            cache.set(cache_key, {
                'records': records,
                'total': total,
                'source': 'csv',
                'cache_date': daily_cache.get('date'),
                'cache_fetched_at': cache_fetched_at,
            }, 60 * 15)

    # ------------------------------------------------------------------ #
    #  Top commodity prices (hero ticker + cards — always Karnataka)      #
    # ------------------------------------------------------------------ #
    top_prices_cache_key = 'price_tracker_top_commodities_karnataka'
    top_cached = cache.get(top_prices_cache_key)
    top_commodity_prices = None

    if top_cached is not None:
        if isinstance(top_cached, dict) and 'records' in top_cached:
            top_commodity_prices = top_cached['records']
            if top_cached.get('source') == 'cached':
                data_source = 'cached'
            cache_fetched_at = top_cached.get('cache_fetched_at', cache_fetched_at)
        else:
            top_commodity_prices = top_cached

    if top_commodity_prices is None:
        top_commodity_prices = []
        top_params = {
            "api-key": API_KEY,
            "format":  "json",
            "limit":   50,
            "filters[state.keyword]": "Karnataka",
            "filters[district]": "BELAGAVI",
        }
        top_records, _, top_source = _fetch_mandi_api(
            url, top_params, 'top_karnataka', daily_cache,
        )
        if top_records:
            seen = {}
            for rec in top_records:
                comm = rec.get('commodity', '')
                if comm and comm not in seen:
                    seen[comm] = rec
            top_commodity_prices = list(seen.values())[:12]
            if top_source == 'cached':
                data_source = 'cached'
            cache_fetched_at = daily_cache.get('fetched_at')
            cache.set(top_prices_cache_key, {
                'records': top_commodity_prices,
                'source': top_source,
                'cache_fetched_at': cache_fetched_at,
            }, 60 * 30)

        if not top_commodity_prices:
            print("[INFO] Falling back to CSV data for Top Prices...")
            csv_rows = _load_csv(state_filter='Karnataka', limit=500)
            seen = {}
            for rec in csv_rows:
                comm = rec.get('commodity', '')
                if comm and comm not in seen:
                    seen[comm] = rec
            top_commodity_prices = list(seen.values())[:12]
            if top_commodity_prices:
                _persist_daily_entry(
                    daily_cache, 'top_karnataka',
                    top_commodity_prices, len(top_commodity_prices), 'csv',
                )
                cache_fetched_at = daily_cache.get('fetched_at')
            if not records:
                data_source = 'csv'

    cache_date_display = None
    if cache_date:
        try:
            from datetime import date as date_cls
            parsed = date_cls.fromisoformat(cache_date)
            cache_date_display = parsed.strftime('%B %d, %Y')
        except ValueError:
            cache_date_display = cache_date

    context = {
        'records': records,
        'state': state,
        'commodity': commodity,
        'total': total,
        'top_commodity_prices': top_commodity_prices,
        'skeleton_only': False,
        'data_source': data_source,
        'cache_date': cache_date_display or cache_date,
        'cache_fetched_at': cache_fetched_at,
    }
    return render(request, 'price_tracker.html', context)


import random
import json
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from .models import EmailOTP

from django.core.mail import EmailMultiAlternatives

def send_otp_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON format'})
            
        if not email:
            return JsonResponse({'success': False, 'message': 'Email is required'})
            
        otp = str(random.randint(1000, 9999))
        
        EmailOTP.objects.create(email=email, otp=otp)

        subject = "Verify your email"
        from_email = "noreply@krishiscan.in"
        to = [email]

        text_content = f"Your OTP is {otp}. Valid for 5 minutes. (Please check your spam folder if you do not see this email)"

        html_content = f"""
        <h2>Email Verification</h2>
        <p>Your OTP is:</p>
        <h1 style="color:#014525; text-weight:bold; ">{otp}</h1>
        <p>This OTP is valid for 5 minutes.</p>
        <p><small>(Please check your spam folder if you do not see this email)</small></p>
        <center>
            <h2>From Team - <span style="color:#014525;">KrishiScan</span></h2>
        </center>
        """

        msg = EmailMultiAlternatives(subject, text_content, from_email, to)
        msg.attach_alternative(html_content, "text/html")
        try:
            msg.send()
            return JsonResponse({'success': True, 'message': 'OTP sent successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

def verify_otp_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            otp = data.get('otp')
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON format'})
            
        if not email or not otp:
            return JsonResponse({'success': False, 'message': 'Email and OTP are required'})
            
        stored_otp = EmailOTP.objects.filter(email=email).order_by('-created_at').first()
        if not stored_otp or stored_otp.otp != otp:
            return JsonResponse({'success': False, 'message': 'Invalid OTP'})
            
        if not stored_otp.is_valid():
            return JsonResponse({'success': False, 'message': 'OTP has expired. Please request a new one.'})
            
        return JsonResponse({'success': True, 'message': 'OTP verified successfully'})
        
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required(login_url='/login/')
@farmer_required
def crop_history(request):
    user_id = request.session.get('user_id')
    role = request.session.get('role')
    
    if not user_id or role != 'Farmer':
        messages.error(request, 'Please log in as a farmer to view crop history.')
        return redirect('login')
        
    from .models import Crop, OrderItem
    
    # Fetch all crops uploaded by this farmer
    crops = Crop.objects.filter(farmer_id=user_id).order_by('-created_at')
    
    # Fetch all order items related to this farmer's crops
    orders = OrderItem.objects.filter(farmer_id=user_id).select_related('crop', 'order__consumer').order_by('-created_at')
    
    context = {
        'crops': crops,
        'orders': orders
    }
    return render(request, 'crop_history.html', context)

@login_required(login_url='/login/')
def submit_payment(request):
    """Consumer submits a screenshot proof for a specific OrderItem."""
    import json
    from django.http import JsonResponse
    from .models import Order, OrderItem, Payment, Crop, UserAccount

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request'})

    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': 'Not authenticated'})

    order_item_id = request.POST.get('order_item_id')
    screenshot = request.FILES.get('screenshot')

    if not order_item_id or not screenshot:
        return JsonResponse({'success': False, 'message': 'Missing data'})

    # Validate file type
    allowed_types = ('image/jpeg', 'image/png', 'image/jpg', 'image/webp')
    if screenshot.content_type not in allowed_types:
        return JsonResponse({'success': False, 'message': 'Only JPG/PNG images are accepted'})

    # Max 5MB
    if screenshot.size > 5 * 1024 * 1024:
        return JsonResponse({'success': False, 'message': 'File too large. Max 5MB allowed'})

    try:
        item = OrderItem.objects.get(id=order_item_id, order__consumer_id=user_id)
    except OrderItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order item not found'})

    if hasattr(item, 'payment'):
        return JsonResponse({'success': False, 'message': 'Payment already submitted for this item'})

    Payment.objects.create(order_item=item, screenshot=screenshot, status='pending')
    item.status = 'paid'
    item.save()

    from .models import Notification
    Notification.objects.create(
        user=item.farmer,
        title="Payment verification requested",
        message=f"A payment proof has been submitted for '{item.crop.name}' by {item.order.consumer.first_name}. Please review and confirm.",
        link="/wallet/"
    )
    
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        send_mail(
            subject='Payment Verification Requested',
            message=f"Hello {item.farmer.first_name},\n\n{item.order.consumer.first_name} {item.order.consumer.last_name} has submitted a payment proof for their order of '{item.crop.name}'. Please check your wallet to review and approve the payment.\n\nThank you,\nKrishiScan Team",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[item.farmer.email],
            fail_silently=True,
        )
    except Exception:
        pass

    # Update parent order status
    order = item.order
    statuses = set(order.items.values_list('status', flat=True))
    if statuses == {'verified'}:
        order.status = 'completed'
    elif 'verified' in statuses or 'paid' in statuses:
        order.status = 'partial'
    order.save()

    return JsonResponse({'success': True, 'message': 'Payment proof submitted successfully'})


@login_required(login_url='/login/')
def verify_order_item(request):
    """Farmer approves or rejects a payment for one of their OrderItems."""
    import json
    from django.http import JsonResponse
    from .models import OrderItem, Payment

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request'})

    user_id = request.session.get('user_id')
    role = request.session.get('role')
    if not user_id or role != 'Farmer':
        return JsonResponse({'success': False, 'message': 'Unauthorized'})

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'})

    item_id = data.get('order_item_id')
    action = data.get('action')  # 'approve' or 'reject'

    if action not in ('approve', 'reject'):
        return JsonResponse({'success': False, 'message': 'Invalid action'})

    try:
        item = OrderItem.objects.select_related('farmer', 'crop', 'order').get(id=item_id, farmer_id=user_id)
    except OrderItem.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order item not found'})

    if action == 'approve':
        item.status = 'verified'
        item.save()

        # Deduct crop stock now that payment is verified
        crop = item.crop
        crop.quantity -= item.quantity
        crop.save()

        # Credit farmer wallet
        farmer = item.farmer
        farmer.wallet_balance += item.amount
        farmer.save()

        # Crop stock was already deducted at checkout

        if hasattr(item, 'payment'):
            item.payment.status = 'approved'
            item.payment.save()
            
        from .models import Notification
        Notification.objects.create(
            user=item.order.consumer,
            title="Payment verified",
            message=f"Your payment for '{item.crop.name}' has been approved by the farmer.",
            link="/orders/"
        )
        
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            send_mail(
                subject='Order Payment Approved',
                message=f"Hello {item.order.consumer.first_name},\n\nYour payment for '{item.crop.name}' has been approved by {item.farmer.first_name} {item.farmer.last_name}. Your order is now verified!\n\nThank you,\nKrishiScan Team",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[item.order.consumer.email],
                fail_silently=True,
            )
        except Exception:
            pass
    else:
        item.status = 'rejected'
        item.save()
        
        if hasattr(item, 'payment'):
            item.payment.status = 'rejected'
            item.payment.save()
            
        from .models import Notification
        Notification.objects.create(
            user=item.order.consumer,
            title="Payment review update",
            message=f"The farmer did not approve payment proof for '{item.crop.name}'. Please get in touch with them for next steps.",
            link="/orders/"
        )
        
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            send_mail(
                subject='Order Payment Update',
                message=f"Hello {item.order.consumer.first_name},\n\nUnfortunately, {item.farmer.first_name} {item.farmer.last_name} did not approve your payment proof for '{item.crop.name}'. Please get in touch with them or resubmit your payment proof.\n\nThank you,\nKrishiScan Team",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[item.order.consumer.email],
                fail_silently=True,
            )
        except Exception:
            pass


    # Update parent order status
    order = item.order
    statuses = set(order.items.values_list('status', flat=True))
    if statuses == {'verified'}:
        order.status = 'completed'
        # Clear consumer's wishlist when order is fully completed
        consumer = order.consumer
        consumer.wishlist = {}
        consumer.save(update_fields=['wishlist'])
    elif 'verified' in statuses or 'paid' in statuses:
        order.status = 'partial'
    else:
        order.status = 'pending'
    order.save()

    return JsonResponse({'success': True})


@login_required(login_url='/login/')
def create_checkout(request):
    """Consumer initiates checkout — creates Order + OrderItems, returns grouped data for payment UI."""
    import json
    from django.http import JsonResponse
    from .models import Crop, Order, OrderItem, UserAccount

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request'})

    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': 'Not authenticated'})

    try:
        data = json.loads(request.body)
    except Exception:
        data = {}

    delivery_type = data.get('delivery_type', 'doorstep')
    payment_method = data.get('payment_method', 'online')

    consumer = UserAccount.objects.get(id=user_id)
    wishlist = consumer.wishlist if consumer.wishlist else {}
    if not isinstance(wishlist, dict):
        wishlist = {}
    
    if not wishlist:
        return JsonResponse({'success': False, 'message': 'Wishlist is empty'})

    # Validate all farmers have UPI IDs before creating anything if payment is online
    if payment_method == 'online':
        for crop_id, qty in wishlist.items():
            try:
                crop = Crop.objects.get(id=int(crop_id))
                if not crop.farmer.upi_id:
                    return JsonResponse({
                        'success': False,
                        'message': f'{crop.farmer.first_name} {crop.farmer.last_name} has not set up their UPI ID yet. Please remove their items and try again.'
                    })
            except Crop.DoesNotExist:
                continue

    # Create Order
    order = Order.objects.create(consumer=consumer, status='pending', delivery_type=delivery_type, payment_method=payment_method)

    farmer_groups = {}
    for crop_id, qty in wishlist.items():
        try:
            crop = Crop.objects.get(id=int(crop_id))
            amount = float(crop.price_per_kg) * float(qty)
            farmer = crop.farmer

            item_status = 'pending'
            if payment_method == 'cod':
                item_status = 'cod_pending'
            elif delivery_type == 'pickup':
                item_status = 'pickup_pending'

            item = OrderItem.objects.create(
                order=order,
                crop=crop,
                farmer=farmer,
                quantity=float(qty),
                amount=amount,
                status=item_status
            )

            # Note: Stock will be deducted only after farmer verifies payment for online
            if payment_method != 'online':
                from decimal import Decimal
                crop.quantity -= Decimal(str(item.quantity))
                crop.save()
                
                # Credit farmer wallet as it's not going through UPI online flow?
                # Actually, for COD and Pickup, the farmer gets paid directly. 
                # Wallet balance is basically what's been sold through the platform. 
                # Let's add it to wallet balance so it reflects earnings.
                farmer.wallet_balance += Decimal(str(item.amount))
                farmer.save()

                from .models import Notification
                if delivery_type == 'pickup':
                    Notification.objects.create(
                        user=farmer,
                        title="New Self-Pickup Order",
                        message=f"{consumer.first_name} {consumer.last_name} wants {qty}kg of '{crop.name}'. They will receive it by visiting your farm directly.",
                        link="/wallet/"
                    )
                    try:
                        from django.core.mail import send_mail
                        from django.conf import settings
                        send_mail(
                            subject='New Self-Pickup Order Received',
                            message=f"Hello {farmer.first_name},\n\n{consumer.first_name} {consumer.last_name} has placed a Self-Pickup order for {qty}kg of '{crop.name}'. They will visit your farm to collect it.\n\nThank you,\nKrishiScan Team",
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[farmer.email],
                            fail_silently=True,
                        )
                    except Exception:
                        pass
                elif payment_method == 'cod':
                    Notification.objects.create(
                        user=farmer,
                        title="New Cash on Delivery Order",
                        message=f"{consumer.first_name} {consumer.last_name} has placed a Cash on Delivery order for {qty}kg of '{crop.name}'.",
                        link="/wallet/"
                    )
                    try:
                        from django.core.mail import send_mail
                        from django.conf import settings
                        send_mail(
                            subject='New Cash on Delivery Order Received',
                            message=f"Hello {farmer.first_name},\n\n{consumer.first_name} {consumer.last_name} has placed a Cash on Delivery order for {qty}kg of '{crop.name}'. Please prepare the order for delivery.\n\nThank you,\nKrishiScan Team",
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[farmer.email],
                            fail_silently=True,
                        )
                    except Exception:
                        pass

            if farmer.id not in farmer_groups:
                farmer_groups[farmer.id] = {
                    'farmer_id': farmer.id,
                    'farmer_name': f'{farmer.first_name} {farmer.last_name}',
                    'upi_id': farmer.upi_id,
                    'subtotal': 0,
                    'items': []
                }
            farmer_groups[farmer.id]['subtotal'] += amount
            farmer_groups[farmer.id]['items'].append({
                'order_item_id': item.id,
                'crop_name': crop.name,
                'quantity': float(qty),
                'amount': amount,
            })
        except Crop.DoesNotExist:
            continue

    # Build UPI deep links if online
    if payment_method == 'online':
        for fg in farmer_groups.values():
            upi_link = (
                f"upi://pay?pa={fg['upi_id']}"
                f"&pn={fg['farmer_name'].replace(' ', '%20')}"
                f"&am={fg['subtotal']:.2f}"
                f"&cu=INR"
                f"&tn=KrishiScan_Order_{order.id}"
            )
            fg['upi_link'] = upi_link
            
    # Clear wishlist if not online
    if payment_method != 'online':
        consumer.wishlist = {}
        consumer.save(update_fields=['wishlist'])
        
        # Also mark order as completed if no verification step needed
        order.status = 'completed'
        order.save(update_fields=['status'])

    return JsonResponse({
        'success': True,
        'order_id': order.id,
        'payment_method': payment_method,
        'delivery_type': delivery_type,
        'farmer_groups': list(farmer_groups.values()),
    })


@login_required(login_url='/login/')
@farmer_required
def wallet_view(request):
    if 'email' not in request.session or request.session.get('role') != 'Farmer':
        return redirect('login')

    from .models import UserAccount, OrderItem
    try:
        user = UserAccount.objects.get(email=request.session['email'])
    except UserAccount.DoesNotExist:
        return redirect('login')

    if request.method == 'POST':
        upi_id = request.POST.get('upi_id', '').strip()
        if upi_id:
            user.upi_id = upi_id
            user.save()
        return redirect('wallet')

    # Incoming payments for this farmer — items waiting for verification
    pending_items = (
        OrderItem.objects
        .filter(farmer=user, status='paid')
        .select_related('order', 'order__consumer', 'crop')
        .prefetch_related('payment')
        .order_by('-created_at')
    )

    # Recent verified/rejected items
    history_items = (
        OrderItem.objects
        .filter(farmer=user, status__in=('verified', 'rejected'))
        .select_related('order', 'order__consumer', 'crop')
        .order_by('-created_at')[:20]
    )

    context = {
        'wallet_balance': user.wallet_balance,
        'upi_id': user.upi_id,
        'has_upi': bool(user.upi_id),
        'pending_items': pending_items,
        'history_items': history_items,
    }

    return render(request, 'farmer_wallet.html', context)


@login_required(login_url='/login/')
@consumer_required
def my_orders(request):
    """Consumer's full order history with delivery status estimation."""
    from .models import Order
    from django.utils import timezone

    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, 'Please log in to view your orders.')
        return redirect('login')

    orders = (
        Order.objects
        .filter(consumer_id=user_id)
        .prefetch_related('items__crop__farmer', 'items__payment')
        .order_by('-created_at')
    )

    now = timezone.now()
    enriched_orders = []

    for order in orders:
        items_data = []
        for item in order.items.all():
            elapsed_minutes = int((now - item.created_at).total_seconds() / 60)

            if item.status == 'verified':
                minutes_left = max(0, 120 - elapsed_minutes)
                if minutes_left > 0:
                    delivery_label = f'Arriving in ~{minutes_left} min'
                    delivery_state = 'arriving'
                else:
                    delivery_label = 'Delivered'
                    delivery_state = 'delivered'
            elif item.status == 'paid':
                delivery_label = 'Payment under review by farmer'
                delivery_state = 'review'
            elif item.status == 'rejected':
                delivery_label = 'Payment rejected — resubmit proof'
                delivery_state = 'rejected'
            else:
                delivery_label = 'Awaiting payment upload'
                delivery_state = 'pending'

            # Step index for timeline (0–4)
            step_map = {'pending': 0, 'review': 1, 'arriving': 2, 'delivered': 3, 'rejected': -1}
            timeline_step = step_map.get(delivery_state, 0)

            screenshot_url = None
            try:
                if item.payment and item.payment.screenshot:
                    screenshot_url = item.payment.screenshot.url
            except Exception:
                pass

            items_data.append({
                'item': item,
                'delivery_label': delivery_label,
                'delivery_state': delivery_state,
                'timeline_step': timeline_step,
                'elapsed_minutes': elapsed_minutes,
                'screenshot_url': screenshot_url,
            })

        enriched_orders.append({
            'order': order,
            'items': items_data,
        })

    # Also attach dynamic ETA to items directly for the template
    for order in orders:
        consumer_coords = None
        if order.consumer and order.consumer.coordinates:
            try:
                lat, lon = map(float, order.consumer.coordinates.split(','))
                consumer_coords = (lat, lon)
            except Exception:
                pass
                
        for item in order.items.all():
            farmer_coords = None
            if item.crop and item.crop.farmer and item.crop.farmer.coordinates:
                try:
                    lat, lon = map(float, item.crop.farmer.coordinates.split(','))
                    farmer_coords = (lat, lon)
                except Exception:
                    pass
            
            # Default ETA if coordinates are missing
            item.dynamic_eta = 120 
            
            if consumer_coords and farmer_coords:
                dist = calculate_distance(consumer_coords[0], consumer_coords[1], farmer_coords[0], farmer_coords[1])
                # Assume 40 km/h average speed: (dist / 40) * 60 = dist * 1.5
                item.dynamic_eta = max(15, int(dist * 1.5)) # minimum 15 mins
                
            elapsed_minutes = int((now - item.created_at).total_seconds() / 60)
            item.minutes_left = max(0, item.dynamic_eta - elapsed_minutes)

    return render(request, 'my_orders.html', {'orders': orders, 'enriched_orders': enriched_orders})

@login_required(login_url='/login/')
def api_orders_status(request):
    """JSON API to fetch live order statuses without page reload."""
    from .models import Order
    from django.utils import timezone
    from django.http import JsonResponse

    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': 'Not logged in'})

    orders = Order.objects.filter(consumer_id=user_id).prefetch_related('items__crop__farmer')
    now = timezone.now()
    
    response_data = {'orders': {}}

    for order in orders:
        order_data = {
            'status': order.status,
            'items': {}
        }
        
        consumer_coords = None
        if order.consumer and order.consumer.coordinates:
            try:
                lat, lon = map(float, order.consumer.coordinates.split(','))
                consumer_coords = (lat, lon)
            except Exception:
                pass
                
        for item in order.items.all():
            farmer_coords = None
            if item.crop and item.crop.farmer and item.crop.farmer.coordinates:
                try:
                    lat, lon = map(float, item.crop.farmer.coordinates.split(','))
                    farmer_coords = (lat, lon)
                except Exception:
                    pass
            
            dynamic_eta = 120 
            if consumer_coords and farmer_coords:
                dist = calculate_distance(consumer_coords[0], consumer_coords[1], farmer_coords[0], farmer_coords[1])
                dynamic_eta = max(15, int(dist * 1.5))
                
            elapsed_minutes = int((now - item.created_at).total_seconds() / 60)
            minutes_left = max(0, dynamic_eta - elapsed_minutes)
            
            order_data['items'][item.id] = {
                'status': item.status,
                'status_display': item.get_status_display(),
                'minutes_left': minutes_left
            }
            
        response_data['orders'][order.id] = order_data

    return JsonResponse({'success': True, 'data': response_data})

from cryptography.fernet import Fernet
import os

def get_fernet():
    key = os.getenv('CHAT_ENCRYPTION_KEY')
    if not key:
        key = Fernet.generate_key().decode()
        with open('.env', 'a') as f:
            f.write(f"\nCHAT_ENCRYPTION_KEY='{key}'\n")
        os.environ['CHAT_ENCRYPTION_KEY'] = key
    return Fernet(key.encode() if isinstance(key, str) else key)

def encrypt_message(message):
    f = get_fernet()
    return f.encrypt(message.encode()).decode()

def decrypt_message(encrypted_message):
    f = get_fernet()
    try:
        return f.decrypt(encrypted_message.encode()).decode()
    except Exception:
        return "[Error decrypting message]"

@login_required(login_url='/login/')
def chat_view(request, user_id):
    from .models import UserAccount, ChatMessage
    from django.db.models import Q
    
    current_user_id = request.session.get('user_id')
    if not current_user_id:
        return redirect('login')
        
    try:
        other_user = UserAccount.objects.get(id=user_id)
    except UserAccount.DoesNotExist:
        return redirect('marketplace')
        
    messages_qs = ChatMessage.objects.filter(
        Q(sender_id=current_user_id, receiver_id=user_id) | 
        Q(sender_id=user_id, receiver_id=current_user_id)
    ).order_by('timestamp')
    
    messages_list = []
    for msg in messages_qs:
        messages_list.append({
            'content': decrypt_message(msg.encrypted_content),
            'timestamp': msg.timestamp,
            'is_sender': msg.sender_id == current_user_id
        })
        
    return render(request, 'chat.html', {'other_user': other_user, 'messages_list': messages_list})

from django.http import JsonResponse
import json

@login_required(login_url='/login/')
def send_message_api(request):
    if request.method == 'POST':
        from .models import ChatMessage
        current_user_id = request.session.get('user_id')
        if not current_user_id:
            return JsonResponse({'success': False, 'message': 'Not logged in'})
            
        try:
            data = json.loads(request.body)
            receiver_id = data.get('receiver_id')
            content = data.get('content')
            
            if not receiver_id or not content:
                return JsonResponse({'success': False, 'message': 'Missing data'})
                
            encrypted = encrypt_message(content)
            
            msg = ChatMessage.objects.create(
                sender_id=current_user_id,
                receiver_id=receiver_id,
                encrypted_content=encrypted
            )
            
            from .models import UserAccount, Notification
            sender = UserAccount.objects.get(id=current_user_id)
            Notification.objects.create(
                user_id=receiver_id,
                title="New message received",
                message=f"{sender.first_name} {sender.last_name} sent you a new message.",
                link=f"/chat/{current_user_id}/"
            )
            
            time_str = msg.timestamp.strftime("%l:%M %p").strip()
            
            return JsonResponse({'success': True, 'timestamp': time_str})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
            
    return JsonResponse({'success': False, 'message': 'Invalid request'})

def reset_password_api(request):
    import json
    from django.http import JsonResponse
    from django.contrib.auth.hashers import make_password
    from .models import UserAccount, EmailOTP

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            otp = data.get('otp')
            new_password = data.get('new_password')
            
            if not all([email, otp, new_password]):
                return JsonResponse({'success': False, 'message': 'Missing required fields'})
                
            try:
                user = UserAccount.objects.get(email=email)
            except UserAccount.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'No account found with this email'})
                
            stored_otp = EmailOTP.objects.filter(email=email).order_by('-created_at').first()
            if not stored_otp or stored_otp.otp != otp:
                return JsonResponse({'success': False, 'message': 'Invalid OTP'})
                
            if not stored_otp.is_valid():
                return JsonResponse({'success': False, 'message': 'OTP has expired'})
                
            user.password = make_password(new_password)
            user.save(update_fields=['password'])
            
            return JsonResponse({'success': True, 'message': 'Password reset successfully. You can now login.'})
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON format'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
            
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required(login_url='/login/')
def fetch_messages_api(request):
    from .models import ChatMessage
    from django.db.models import Q
    current_user_id = request.session.get('user_id')
    other_user_id = request.GET.get('user_id')
    
    if not current_user_id or not other_user_id:
        return JsonResponse({'success': False, 'message': 'Invalid request'})
        
    messages_qs = ChatMessage.objects.filter(
        Q(sender_id=current_user_id, receiver_id=other_user_id) | 
        Q(sender_id=other_user_id, receiver_id=current_user_id)
    ).order_by('timestamp')
    
    messages_list = []
    for msg in messages_qs:
        time_str = msg.timestamp.strftime("%l:%M %p").strip()
        messages_list.append({
            'content': decrypt_message(msg.encrypted_content),
            'timestamp': time_str,
            'is_sender': msg.sender_id == current_user_id
        })
        
    return JsonResponse({'success': True, 'messages': messages_list})

@login_required(login_url='/login/')
def fetch_notifications_api(request):
    from .models import Notification
    from django.http import JsonResponse
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': 'Not logged in'})
    
    notifications = Notification.objects.filter(user_id=user_id).order_by('-created_at')[:15]
    unread_count = Notification.objects.filter(user_id=user_id, is_read=False).count()
    
    data = []
    for n in notifications:
        data.append({
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'is_read': n.is_read,
            'link': n.link,
            'time': n.created_at.strftime("%b %d, %I:%M %p")
        })
        
    return JsonResponse({'success': True, 'notifications': data, 'unread_count': unread_count})

@login_required(login_url='/login/')
def mark_notifications_read_api(request):
    from .models import Notification
    from django.http import JsonResponse
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': 'Not logged in'})
        
    Notification.objects.filter(user_id=user_id, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


@login_required(login_url='/login/')
def dashboard_stats_api(request):
    import os
    import requests
    from django.http import JsonResponse
    from django.core.cache import cache

    # 1. Market Prices
    API_KEY = os.getenv("API_KEY")
    RESOURCE_ID = os.getenv("RESOURCE_ID")
    m_url = f"https://api.data.gov.in/resource/{RESOURCE_ID}"
    
    m_cache_key = 'dashboard_market_prices'
    market_prices = cache.get(m_cache_key)
    
    if market_prices is None:
        try:
            # Short timeout for API calls in AJAX
            res = requests.get(m_url, params={"api-key": API_KEY, "format": "json", "limit": 5}, timeout=8)
            if res.status_code == 200:
                market_prices = res.json().get('records', [])
                cache.set(m_cache_key, market_prices, 60 * 60)
        except:
            market_prices = []

    # 2. Weather
    import hashlib
    _w_raw = f'weather_{request.session.get("location", "Bangalore")}_{request.session.get("coordinates", "none")}'
    w_cache_key = 'weather_' + hashlib.md5(_w_raw.encode('utf-8')).hexdigest()
    weather_data = cache.get(w_cache_key)
    
    if weather_data is None:
        try:
            w_url = "https://api.openweathermap.org/data/2.5/weather"
            w_params = {"appid": os.getenv("WEATHER_API"), "units": "metric"}
            
            coords = request.session.get('coordinates')
            if coords:
                lat, lon = coords.split(',')
                w_params['lat'], w_params['lon'] = lat.strip(), lon.strip()
            else:
                loc = request.session.get('location', 'Bangalore')
                w_params['q'] = loc.split(',')[0] if loc else 'Bangalore'
                
            res = requests.get(w_url, params=w_params, timeout=8)
            if res.status_code == 200:
                wd = res.json()
                weather_data = {
                    'temp': wd['main']['temp'],
                    'feels_like': wd['main']['feels_like'],
                    'humidity': wd['main']['humidity'],
                    'wind_speed': wd['wind']['speed'],
                    'description': wd['weather'][0]['description'].capitalize(),
                    'icon': wd['weather'][0]['icon'],
                    'city': wd['name']
                }
                cache.set(w_cache_key, weather_data, 60 * 30)
        except:
            weather_data = None

    # Calculate Avg Market Price for the stat card
    avg_price = 0
    if market_prices:
        try:
            prices = [float(r.get('modal_price', 0)) for r in market_prices if r.get('modal_price')]
            if prices:
                avg_price = int(sum(prices) / len(prices))
        except:
            pass

    # Calculate Farmer's Real Cost (Avg of their uploaded crops)
    real_cost = 0
    wallet_balance = 0
    user_id = request.session.get('user_id')
    if user_id:
        from .models import Crop, UserAccount
        user = UserAccount.objects.get(id=user_id)
        wallet_balance = float(user.wallet_balance)
        farmer_crops = Crop.objects.filter(farmer_id=user_id)
        if farmer_crops.exists():
            from django.db.models import Avg
            real_cost = int(farmer_crops.aggregate(Avg('price_per_kg'))['price_per_kg__avg'] or 0)

    return JsonResponse({
        'market_prices': market_prices,
        'weather_data': weather_data,
        'avg_market_price': avg_price,
        'real_cost': real_cost,
        'wallet_balance': wallet_balance
    })


@login_required(login_url='/login/')
def order_map(request, item_id):
    from .models import OrderItem
    from django.shortcuts import get_object_or_404
    
    item = get_object_or_404(OrderItem, id=item_id)
    
    # Ensure only the consumer or farmer involved can view it
    user_id = request.session.get('user_id')
    if item.order.consumer_id != user_id and item.crop.farmer_id != user_id:
        return redirect('my_orders')

    consumer_coords = item.order.consumer.coordinates if item.order.consumer else None
    farmer_coords = item.crop.farmer.coordinates if item.crop.farmer else None
    
    from django.utils import timezone
    now = timezone.now()
    dynamic_eta = 120
    if consumer_coords and farmer_coords:
        try:
            c_lat, c_lon = map(float, consumer_coords.split(','))
            f_lat, f_lon = map(float, farmer_coords.split(','))
            dist = calculate_distance(c_lat, c_lon, f_lat, f_lon)
            dynamic_eta = max(15, int(dist * 1.5))
        except Exception:
            pass

    elapsed_seconds = int((now - item.created_at).total_seconds())
    total_seconds = dynamic_eta * 60

    context = {
        'item': item,
        'consumer_coords': consumer_coords,
        'farmer_coords': farmer_coords,
        'consumer_name': f"{item.order.consumer.first_name} {item.order.consumer.last_name}",
        'farmer_name': f"{item.crop.farmer.first_name} {item.crop.farmer.last_name}",
        'crop_name': item.crop.name,
        'elapsed_seconds': elapsed_seconds,
        'total_seconds': total_seconds,
    }
    
    return render(request, 'map.html', context)


@login_required(login_url='/login/')
def cancel_order(request):
    import json
    from django.http import JsonResponse
    from .models import Order
    from decimal import Decimal

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request'})

    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': 'Not authenticated'})

    try:
        data = json.loads(request.body)
        order_id = data.get('order_id')
    except Exception:
        return JsonResponse({'success': False, 'message': 'Invalid data'})

    try:
        order = Order.objects.get(id=order_id, consumer_id=user_id)
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Order not found'})

    if order.status == 'completed':
        return JsonResponse({'success': False, 'message': 'Cannot cancel a completed order'})
        
    if order.status == 'cancelled':
        return JsonResponse({'success': False, 'message': 'Order is already cancelled'})

    # Restore stock for items that already deducted stock
    for item in order.items.all():
        if item.status in ['verified', 'cod_pending', 'pickup_pending']:
            crop = item.crop
            crop.quantity += Decimal(str(item.quantity))
            crop.save()
            
            farmer = item.farmer
            farmer.wallet_balance -= Decimal(str(item.amount))
            farmer.save()
            
            from .models import Notification
            Notification.objects.create(
                user=farmer,
                title="Order Cancelled",
                message=f"Order for {item.quantity}kg of '{crop.name}' was cancelled by the consumer.",
                link="/wallet/"
            )

        item.status = 'cancelled'
        item.save()

    order.status = 'cancelled'
    order.save()

    return JsonResponse({'success': True, 'message': 'Order cancelled successfully'})

def logout_user(request):
    auth_logout(request)
    return redirect('login')

def custom_404(request, exception=None):
    return render(request, '404.html', status=404)

def custom_500(request):
    return render(request, '500.html', status=500)

@login_required(login_url='/login/')
def submit_review_api(request):
    import json
    from django.http import JsonResponse
    from .models import Crop, Review, UserAccount
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request'})
        
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': 'Not authenticated'})
        
    try:
        data = json.loads(request.body)
        crop_id = data.get('crop_id')
        rating = int(data.get('rating', 5))
        text = data.get('text', '').strip()
        
        if not crop_id or not text or rating < 1 or rating > 5:
            return JsonResponse({'success': False, 'message': 'Invalid input data'})
            
        crop = Crop.objects.get(id=crop_id)
        user = UserAccount.objects.get(id=user_id)
        
        Review.objects.create(crop=crop, user=user, rating=rating, text=text)
        
        return JsonResponse({'success': True, 'message': 'Review submitted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

def get_reviews_api(request):
    from django.http import JsonResponse
    from .models import Review
    
    crop_id = request.GET.get('crop_id')
    if not crop_id:
        return JsonResponse({'success': False, 'message': 'Missing crop ID'})
        
    reviews = Review.objects.filter(crop_id=crop_id).order_by('-created_at')
    
    user_id = request.session.get('user_id')
    
    data = []
    total_rating = 0
    for r in reviews:
        total_rating += r.rating
        data.append({
            'id': r.id,
            'author': f"{r.user.first_name} {r.user.last_name[0] if r.user.last_name else ''}.",
            'rating': r.rating,
            'text': r.text,
            'date': r.created_at.strftime("%b %d, %Y"),
            'is_author': user_id == r.user_id
        })
        
    avg_rating = round(total_rating / len(reviews), 1) if reviews else 0
    
    return JsonResponse({
        'success': True, 
        'reviews': data,
        'avg_rating': avg_rating,
        'count': len(reviews)
    })

@login_required(login_url='/login/')
def delete_review_api(request):
    import json
    from django.http import JsonResponse
    from .models import Review
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request'})
        
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'success': False, 'message': 'Not authenticated'})
        
    try:
        data = json.loads(request.body)
        review_id = data.get('review_id')
        
        review = Review.objects.get(id=review_id)
        if review.user_id != user_id:
            return JsonResponse({'success': False, 'message': 'Permission denied'})
            
        review.delete()
        return JsonResponse({'success': True, 'message': 'Review deleted'})
    except Review.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Review not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
