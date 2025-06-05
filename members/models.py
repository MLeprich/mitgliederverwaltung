# members/models.py
from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from datetime import date, timedelta
import os
import random
from PIL import Image

def member_image_path(instance, filename):
    ext = filename.split('.')[-1].lower()
    filename = f"{instance.first_name.lower()}.{instance.last_name.lower()}.{ext}"
    return os.path.join('profile_pics', filename)

class Member(models.Model):
    # Mitarbeitertypen
    MEMBER_TYPE_CHOICES = [
        ('BF', 'Berufsfeuerwehr'),
        ('FF', 'Freiwillige Feuerwehr'),
        ('JF', 'Jugendfeuerwehr'),
        ('STADT', 'Stadt'),
        ('EXTERN', 'Extern'),
        ('PRAKTIKANT', 'Praktikant'),
    ]
    
    # Ausweisnummer-Präfixe
    PREFIX_CHOICES = [
        ('', 'Kein Präfix'),
        ('FF', 'FF'),
        ('JF', 'JF'),
    ]
    
    # Persönliche Daten
    first_name = models.CharField(max_length=100, verbose_name="Vorname")
    last_name = models.CharField(max_length=100, verbose_name="Nachname")
    birth_date = models.DateField(verbose_name="Geburtsdatum")
    personnel_number = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name="Personalnummer",
        help_text="Optional - FF Mitglieder haben meist keine Personalnummer"
    )
    
    # Neue Felder
    member_type = models.CharField(
        max_length=20,
        choices=MEMBER_TYPE_CHOICES,
        default='FF',
        verbose_name="Mitarbeitertyp"
    )
    card_number_prefix = models.CharField(
        max_length=10,
        choices=PREFIX_CHOICES,
        blank=True,
        verbose_name="Ausweisnummer-Präfix",
        help_text="Optional - wird automatisch basierend auf Mitarbeitertyp vorgeschlagen"
    )
    card_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Ausweisnummer",
        help_text="Wird automatisch generiert"
    )
    
    # Ausweis-Daten
    issued_date = models.DateField(default=timezone.now, verbose_name="Ausgestellt am")
    valid_until = models.DateField(verbose_name="Gültig bis")
    manual_validity = models.BooleanField(
        default=False,
        verbose_name="Manuelle Gültigkeit",
        help_text="Für Externe und Praktikanten"
    )
    
    # Profilbild
    profile_picture = models.ImageField(
        upload_to=member_image_path,
        blank=True,
        null=True,
        verbose_name="Profilbild"
    )
    
    # Meta-Daten
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    
    class Meta:
        verbose_name = "Mitglied"
        verbose_name_plural = "Mitglieder"
        ordering = ['last_name', 'first_name']
    
    def __str__(self):
        return f"{self.last_name}, {self.first_name} ({self.card_number})"
    
    def save(self, *args, **kwargs):
        """Überschreibt save() für automatische Generierung"""
        
        # Ausweisnummer generieren falls noch nicht vorhanden
        if not self.card_number:
            self.card_number = self.generate_card_number()
        
        # Gültigkeit automatisch setzen (außer bei manueller Eingabe)
        if not self.manual_validity and not self.valid_until:
            if self.member_type in ['EXTERN', 'PRAKTIKANT']:
                # Für Externe und Praktikanten: 1 Jahr
                self.valid_until = self.issued_date + timedelta(days=365)
            else:
                # Für reguläre Mitarbeiter: 5 Jahre
                self.valid_until = self.issued_date + timedelta(days=5*365)
        
        super().save(*args, **kwargs)
        
        # Bildgröße anpassen nach dem Speichern
        if self.profile_picture:
            self.resize_image()
    
    def generate_card_number(self):
        """Generiert eine eindeutige Ausweisnummer"""
        # 6-stellige Zufallszahl
        random_number = str(random.randint(100000, 999999))
        
        # Mit oder ohne Präfix
        if self.card_number_prefix:
            card_number = f"{self.card_number_prefix}{random_number}"
        else:
            card_number = random_number
        
        # Prüfen ob Nummer bereits existiert
        while Member.objects.filter(card_number=card_number).exists():
            random_number = str(random.randint(100000, 999999))
            if self.card_number_prefix:
                card_number = f"{self.card_number_prefix}{random_number}"
            else:
                card_number = random_number
        
        return card_number
    
    def resize_image(self):
        """Passt Profilbild auf maximale Größe an und korrigiert EXIF-Orientierung"""
        try:
            from PIL import Image, ExifTags
            
            img = Image.open(self.profile_picture.path)
            
            # EXIF-Orientierung korrigieren
            try:
                for orientation in ExifTags.TAGS.keys():
                    if ExifTags.TAGS[orientation] == 'Orientation':
                        break
                
                exif = img._getexif()
                if exif is not None:
                    orientation_value = exif.get(orientation)
                    if orientation_value == 3:
                        img = img.rotate(180, expand=True)
                    elif orientation_value == 6:
                        img = img.rotate(270, expand=True)
                    elif orientation_value == 8:
                        img = img.rotate(90, expand=True)
            except (AttributeError, KeyError, TypeError):
                # Keine EXIF-Daten oder Fehler beim Lesen - ignorieren
                pass
            
            max_size = (300, 400)  # Breite x Höhe in Pixeln
            
            if img.height > max_size[1] or img.width > max_size[0]:
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Als JPEG speichern um EXIF-Probleme zu vermeiden
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            img.save(self.profile_picture.path, "JPEG", optimize=True, quality=85)
            
        except Exception as e:
            print(f"Fehler beim Bildverarbeitung für {self}: {e}")
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def age(self):
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
    
    @property
    def is_card_expired(self):
        return date.today() > self.valid_until
    
    @property
    def expires_soon(self):
        return date.today() + timedelta(days=30) > self.valid_until
    
    def get_card_status(self):
        if self.is_card_expired:
            return "Abgelaufen"
        elif self.expires_soon:
            return "Läuft bald ab"
        else:
            return "Gültig"
    
    def get_member_type_display_with_icon(self):
        """Gibt Mitarbeitertyp mit Icon zurück"""
        icons = {
            'BF': '🚒',
            'FF': '🔥',
            'JF': '👦',
            'STADT': '🏛️',
            'EXTERN': '🏢',
            'PRAKTIKANT': '🎓',
        }
        return f"{icons.get(self.member_type, '👤')} {self.get_member_type_display()}"
