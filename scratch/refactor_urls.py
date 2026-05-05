import re

with open('/home/swayam/SWAYAM/krishiscan_v2/krishi/urls.py', 'r') as f:
    content = f.read()

# Replace the login paths
content = content.replace(
    "# path('login/', views.login, name='login'),\n    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),",
    "path('login/', views.login, name='login'),"
)

# Replace the logout path
content = content.replace(
    "path('logout/', auth_views.LogoutView.as_view(), name='logout'),",
    "path('logout/', views.logout_user, name='logout'),"
)

with open('/home/swayam/SWAYAM/krishiscan_v2/krishi/urls.py', 'w') as f:
    f.write(content)

print("urls.py updated successfully.")
