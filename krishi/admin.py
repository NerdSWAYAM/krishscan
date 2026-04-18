from django.contrib import admin
from .models import UserAccount

@admin.register(UserAccount)
class UserAccountAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'role', 'location', 'created_at')
    search_fields = ('email', 'first_name', 'last_name')
    list_filter = ('role',)
