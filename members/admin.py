from django.contrib import admin
from django.utils.html import format_html
from .models import Member

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = [
        'last_name', 'first_name', 'card_number', 'member_type_display', 
        'personnel_number', 'birth_date', 'card_status_display', 
        'valid_until', 'is_active', 'profile_image_display'
    ]
    list_filter = [
        'member_type', 'is_active', 'issued_date', 'valid_until', 
        'card_number_prefix', 'manual_validity'
    ]
    search_fields = [
        'first_name', 'last_name', 'personnel_number', 'card_number'
    ]
    readonly_fields = [
        'card_number', 'created_at', 'updated_at', 'age_display', 
        'card_status_display', 'profile_image_preview'
    ]
    fieldsets = (
        ('Persönliche Daten', {
            'fields': (
                ('first_name', 'last_name'),
                'birth_date',
                'personnel_number',
            )
        }),
        ('Mitarbeiter-Informationen', {
            'fields': (
                'member_type',
                ('card_number_prefix', 'card_number'),
            )
        }),
        ('Ausweis-Daten', {
            'fields': (
                ('issued_date', 'valid_until'),
                'manual_validity',
                'is_active',
            )
        }),
        ('Profilbild', {
            'fields': (
                'profile_picture',
                'profile_image_preview',
            )
        }),
        ('Meta-Informationen', {
            'classes': ('collapse',),
            'fields': (
                ('created_at', 'updated_at'),
                'age_display',
                'card_status_display',
            )
        }),
    )
    
    list_per_page = 25
    ordering = ['last_name', 'first_name']
    
    def member_type_display(self, obj):
        return obj.get_member_type_display_with_icon()
    member_type_display.short_description = "Typ"
    
    def age_display(self, obj):
        return f"{obj.age} Jahre"
    age_display.short_description = "Alter"
    
    def card_status_display(self, obj):
        status = obj.get_card_status()
        colors = {
            "Abgelaufen": "red",
            "Läuft bald ab": "orange", 
            "Gültig": "green"
        }
        color = colors.get(status, "gray")
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, status
        )
    card_status_display.short_description = "Status"
    
    def profile_image_display(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="{}" width="30" height="40" style="border-radius: 3px;" />',
                obj.profile_picture.url
            )
        return "Kein Bild"
    profile_image_display.short_description = "Bild"
    
    def profile_image_preview(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="{}" width="150" height="200" style="border-radius: 5px; border: 1px solid #ddd;" />',
                obj.profile_picture.url
            )
        return "Kein Profilbild vorhanden"
    profile_image_preview.short_description = "Bildvorschau"
