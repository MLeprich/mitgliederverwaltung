#!/bin/bash
# Installation Script Teil 2: Models und Admin Interface
# Ausführen mit: bash install_part2.sh

set -e

echo "=== Mitgliederverwaltung Dashboard - Teil 2: Models und Admin ==="
echo ""

# Farben für Output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Virtual Environment prüfen
if [[ "$VIRTUAL_ENV" == "" ]]; then
    print_error "Bitte Virtual Environment aktivieren!"
    exit 1
fi

cd ~/mitgliederverwaltung

print_status "Erstelle Member Model..."

# Member Model erstellen
cat > members/models.py << 'EOF'
from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from datetime import date, timedelta
import os
from PIL import Image


def member_image_path(instance, filename):
    """Generiert Pfad für Profilbilder: vorname.nachname.jpg"""
    ext = filename.split('.')[-1].lower()
    filename = f"{instance.first_name.lower()}.{instance.last_name.lower()}.{ext}"
    return os.path.join('profile_pics', filename)


class Member(models.Model):
    """Model für Mitgliederdaten"""
    
    # Persönliche Daten
    first_name = models.CharField(
        max_length=100, 
        verbose_name="Vorname",
        help_text="Vorname des Mitglieds"
    )
    last_name = models.CharField(
        max_length=100, 
        verbose_name="Nachname",
        help_text="Nachname des Mitglieds"
    )
    birth_date = models.DateField(
        verbose_name="Geburtsdatum",
        help_text="Geburtsdatum im Format TT.MM.JJJJ"
    )
    personnel_number = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name="Personalnummer",
        help_text="Optional - FF Mitglieder haben keine Personalnummer"
    )
    
    # Ausweis-Daten
    issued_date = models.DateField(
        default=timezone.now,
        verbose_name="Ausgestellt am",
        help_text="Datum der Ausweiserstellung"
    )
    valid_until = models.DateField(
        verbose_name="Gültig bis",
        help_text="Automatisch: Ausgestellt am + 5 Jahre"
    )
    
    # Profilbild
    profile_picture = models.ImageField(
        upload_to=member_image_path,
        blank=True,
        null=True,
        verbose_name="Profilbild",
        help_text="Wird automatisch zu vorname.nachname.jpg umbenannt",
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])]
    )
    
    # Meta-Daten
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Erstellt am"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Aktualisiert am"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktiv",
        help_text="Deaktivierte Mitglieder werden nicht für neue Ausweise verwendet"
    )
    
    class Meta:
        verbose_name = "Mitglied"
        verbose_name_plural = "Mitglieder"
        ordering = ['last_name', 'first_name']
        unique_together = ['first_name', 'last_name', 'birth_date']
    
    def __str__(self):
        return f"{self.last_name}, {self.first_name}"
    
    def save(self, *args, **kwargs):
        """Überschreibt save() für automatische Berechnung von valid_until"""
        if not self.valid_until:
            # Automatisch 5 Jahre ab issued_date
            self.valid_until = self.issued_date + timedelta(days=5*365)
        
        super().save(*args, **kwargs)
        
        # Bildgröße anpassen nach dem Speichern
        if self.profile_picture:
            self.resize_image()
    
    def resize_image(self):
        """Passt Profilbild auf maximale Größe an"""
        try:
            img = Image.open(self.profile_picture.path)
            
            # Maximale Größe für Ausweisbilder
            max_size = (300, 400)  # Breite x Höhe in Pixeln
            
            if img.height > max_size[1] or img.width > max_size[0]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                img.save(self.profile_picture.path, optimize=True, quality=85)
        except Exception as e:
            print(f"Fehler beim Bildverarbeitung für {self}: {e}")
    
    @property
    def full_name(self):
        """Vollständiger Name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self):
        """Berechnet das aktuelle Alter"""
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
    
    @property
    def is_card_expired(self):
        """Prüft ob der Ausweis abgelaufen ist"""
        return date.today() > self.valid_until
    
    @property
    def expires_soon(self):
        """Prüft ob der Ausweis in den nächsten 30 Tagen abläuft"""
        return date.today() + timedelta(days=30) > self.valid_until
    
    def get_card_status(self):
        """Gibt den Status des Ausweises zurück"""
        if self.is_card_expired:
            return "Abgelaufen"
        elif self.expires_soon:
            return "Läuft bald ab"
        else:
            return "Gültig"


class ImportLog(models.Model):
    """Model für Import-Protokolle"""
    
    filename = models.CharField(max_length=255, verbose_name="Dateiname")
    imported_at = models.DateTimeField(auto_now_add=True, verbose_name="Importiert am")
    total_rows = models.IntegerField(verbose_name="Gesamte Zeilen")
    successful_imports = models.IntegerField(verbose_name="Erfolgreich importiert")
    failed_imports = models.IntegerField(verbose_name="Fehlgeschlagen")
    error_log = models.TextField(blank=True, verbose_name="Fehlerprotokoll")
    imported_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.CASCADE,
        verbose_name="Importiert von"
    )
    
    class Meta:
        verbose_name = "Import-Protokoll"
        verbose_name_plural = "Import-Protokolle"
        ordering = ['-imported_at']
    
    def __str__(self):
        return f"Import {self.filename} - {self.imported_at.strftime('%d.%m.%Y %H:%M')}"
    
    @property
    def success_rate(self):
        """Berechnet die Erfolgsquote in Prozent"""
        if self.total_rows == 0:
            return 0
        return round((self.successful_imports / self.total_rows) * 100, 1)
EOF

print_status "Erstelle Admin Interface..."

# Admin Interface konfigurieren
cat > members/admin.py << 'EOF'
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Member, ImportLog


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    """Admin Interface für Mitglieder"""
    
    list_display = [
        'last_name', 'first_name', 'personnel_number', 
        'birth_date', 'age_display', 'card_status_display', 
        'valid_until', 'is_active', 'profile_image_display'
    ]
    list_filter = [
        'is_active', 'issued_date', 'valid_until', 
        'created_at', 'personnel_number'
    ]
    search_fields = [
        'first_name', 'last_name', 'personnel_number'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'age_display', 
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
        ('Ausweis-Daten', {
            'fields': (
                ('issued_date', 'valid_until'),
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
    date_hierarchy = 'created_at'
    ordering = ['last_name', 'first_name']
    
    actions = ['activate_members', 'deactivate_members', 'extend_validity']
    
    def age_display(self, obj):
        """Zeigt das Alter an"""
        return f"{obj.age} Jahre"
    age_display.short_description = "Alter"
    
    def card_status_display(self, obj):
        """Zeigt den Ausweis-Status mit Farben an"""
        status = obj.get_card_status()
        if status == "Abgelaufen":
            color = "red"
        elif status == "Läuft bald ab":
            color = "orange"
        else:
            color = "green"
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, status
        )
    card_status_display.short_description = "Status"
    
    def profile_image_display(self, obj):
        """Zeigt kleines Profilbild in der Liste"""
        if obj.profile_picture:
            return format_html(
                '<img src="{}" width="30" height="40" style="border-radius: 3px;" />',
                obj.profile_picture.url
            )
        return "Kein Bild"
    profile_image_display.short_description = "Bild"
    
    def profile_image_preview(self, obj):
        """Zeigt Profilbild-Vorschau im Detail"""
        if obj.profile_picture:
            return format_html(
                '<img src="{}" width="150" height="200" style="border-radius: 5px; border: 1px solid #ddd;" />',
                obj.profile_picture.url
            )
        return "Kein Profilbild vorhanden"
    profile_image_preview.short_description = "Bildvorschau"
    
    def activate_members(self, request, queryset):
        """Bulk-Aktion: Mitglieder aktivieren"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} Mitglieder wurden aktiviert.')
    activate_members.short_description = "Ausgewählte Mitglieder aktivieren"
    
    def deactivate_members(self, request, queryset):
        """Bulk-Aktion: Mitglieder deaktivieren"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} Mitglieder wurden deaktiviert.')
    deactivate_members.short_description = "Ausgewählte Mitglieder deaktivieren"
    
    def extend_validity(self, request, queryset):
        """Bulk-Aktion: Gültigkeit um 5 Jahre verlängern"""
        from datetime import timedelta
        count = 0
        for member in queryset:
            member.valid_until = member.valid_until + timedelta(days=5*365)
            member.save()
            count += 1
        self.message_user(request, f'Gültigkeit von {count} Ausweisen um 5 Jahre verlängert.')
    extend_validity.short_description = "Gültigkeit um 5 Jahre verlängern"


@admin.register(ImportLog)
class ImportLogAdmin(admin.ModelAdmin):
    """Admin Interface für Import-Protokolle"""
    
    list_display = [
        'filename', 'imported_at', 'imported_by',
        'total_rows', 'successful_imports', 'failed_imports',
        'success_rate_display'
    ]
    list_filter = ['imported_at', 'imported_by']
    search_fields = ['filename', 'imported_by__username']
    readonly_fields = [
        'filename', 'imported_at', 'total_rows',
        'successful_imports', 'failed_imports', 'imported_by',
        'success_rate_display', 'formatted_error_log'
    ]
    
    fieldsets = (
        ('Import-Informationen', {
            'fields': (
                'filename',
                ('imported_at', 'imported_by'),
            )
        }),
        ('Statistiken', {
            'fields': (
                ('total_rows', 'successful_imports', 'failed_imports'),
                'success_rate_display',
            )
        }),
        ('Fehlerprotokoll', {
            'fields': ('formatted_error_log',),
        }),
    )
    
    def success_rate_display(self, obj):
        """Zeigt Erfolgsquote mit Farben"""
        rate = obj.success_rate
        if rate >= 90:
            color = "green"
        elif rate >= 70:
            color = "orange"
        else:
            color = "red"
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} %</span>',
            color, rate
        )
    success_rate_display.short_description = "Erfolgsquote"
    
    def formatted_error_log(self, obj):
        """Formatiert das Fehlerprotokoll für bessere Lesbarkeit"""
        if obj.error_log:
            return format_html(
                '<pre style="background: #f8f8f8; padding: 10px; border-radius: 5px; max-height: 300px; overflow-y: auto;">{}</pre>',
                obj.error_log
            )
        return "Keine Fehler"
    formatted_error_log.short_description = "Fehlerdetails"
    
    def has_add_permission(self, request):
        """Import-Logs können nicht manuell erstellt werden"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Import-Logs können nicht bearbeitet werden"""
        return False


# Admin Site Konfiguration
admin.site.site_header = "Mitgliederverwaltung Administration"
admin.site.site_title = "Mitgliederverwaltung"
admin.site.index_title = "Dashboard"
EOF

print_status "Erstelle Member URLs..."

# URLs für Members App
cat > members/urls.py << 'EOF'
from django.urls import path
from . import views

app_name = 'members'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Mitgliederverwaltung
    path('members/', views.MemberListView.as_view(), name='member_list'),
    path('members/add/', views.MemberCreateView.as_view(), name='member_add'),
    path('members/<int:pk>/', views.MemberDetailView.as_view(), name='member_detail'),
    path('members/<int:pk>/edit/', views.MemberUpdateView.as_view(), name='member_edit'),
    path('members/<int:pk>/delete/', views.MemberDeleteView.as_view(), name='member_delete'),
    
    # Import/Export
    path('import/', views.ImportView.as_view(), name='import_data'),
    path('export/', views.ExportView.as_view(), name='export_data'),
    
    # API Endpoints für AJAX
    path('api/member-stats/', views.member_stats_api, name='member_stats_api'),
    path('api/search-members/', views.search_members_api, name='search_members_api'),
]
EOF

print_status "Erstelle und führe Migrationen aus..."

# Migrationen erstellen und ausführen
python manage.py makemigrations members
python manage.py migrate

print_status "Sammle Static Files..."
python manage.py collectstatic --noinput

print_success "Teil 2 abgeschlossen!"
echo ""
echo "Was wurde erstellt:"
echo "✓ Member Model mit allen erforderlichen Feldern"
echo "✓ ImportLog Model für Import-Protokolle"
echo "✓ Admin Interface mit erweiterten Funktionen"
echo "✓ URL-Konfiguration für Members App"
echo "✓ Datenbank-Migrationen"
echo ""
echo "Sie können jetzt einen Superuser erstellen:"
echo "python manage.py createsuperuser"
echo ""
echo "Nächster Schritt:"
echo "bash install_part3.sh  # Templates und Static Files"
EOF