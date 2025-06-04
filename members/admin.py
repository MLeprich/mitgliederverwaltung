from django.contrib import admin
from .models import Member

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'personnel_number', 'birth_date', 'is_active']
    list_filter = ['is_active', 'issued_date']
    search_fields = ['first_name', 'last_name', 'personnel_number']
    ordering = ['last_name', 'first_name']
