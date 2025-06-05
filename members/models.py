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
    issued_date = models.DateField(
        verbose_name="Ausgestellt am",
        null=True,      
        blank=True,    
        help_text="Datum der Ausweis-Erstellung (leer = noch nicht erstellt)"
    )
    valid_until = models.DateField(
        verbose_name="Gültig bis",
        null=True, 
        blank=True
    )
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
        """Überschreibt save() für automatische Generierung und Datumsvalidierung"""
        
        # Sicherstellung dass alle Datumsfelder echte date-Objekte sind
        if self.birth_date and isinstance(self.birth_date, str):
            print(f"WARNING: birth_date ist String: {self.birth_date}")
            # Konvertierung von String zu date falls nötig
            from datetime import datetime
            try:
                # Verschiedene Formate probieren
                for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%m/%d/%Y', '%m/%d/%y']:
                    try:
                        self.birth_date = datetime.strptime(self.birth_date, fmt).date()
                        break
                    except ValueError:
                        continue
            except:
                print(f"ERROR: Konnte birth_date nicht konvertieren: {self.birth_date}")
        
        if self.issued_date and isinstance(self.issued_date, str):
            print(f"WARNING: issued_date ist String: {self.issued_date}")
            from datetime import datetime
            try:
                for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%m/%d/%Y', '%m/%d/%y']:
                    try:
                        self.issued_date = datetime.strptime(self.issued_date, fmt).date()
                        break
                    except ValueError:
                        continue
            except:
                print(f"ERROR: Konnte issued_date nicht konvertieren: {self.issued_date}")
        
        if self.valid_until and isinstance(self.valid_until, str):
            print(f"WARNING: valid_until ist String: {self.valid_until}")
            from datetime import datetime
            try:
                for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%m/%d/%Y', '%m/%d/%y']:
                    try:
                        self.valid_until = datetime.strptime(self.valid_until, fmt).date()
                        break
                    except ValueError:
                        continue
            except:
                print(f"ERROR: Konnte valid_until nicht konvertieren: {self.valid_until}")
        
        # Ausweisnummer generieren falls noch nicht vorhanden
        if not self.card_number:
            self.card_number = self.generate_card_number()
        
        # Gültigkeit automatisch setzen nur wenn issued_date vorhanden ist
        if self.issued_date and not self.manual_validity and not self.valid_until:
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
    
    # Verbesserte resize_image Methode für members/models.py

    def resize_image(self):
        """
        Passt Profilbild für Dienstausweis-Druck an:
        - Exakte Größe: 267x400 Pixel (Passbild-Format)
        - 300 DPI für Druckqualität
        - Optimierte Kompression für Druck
        - EXIF-Orientierung korrigieren
        """
        try:
            from PIL import Image, ExifTags
            import os
            
            if not self.profile_picture or not os.path.exists(self.profile_picture.path):
                return
                
            # Bild öffnen
            with Image.open(self.profile_picture.path) as img:
                
                # EXIF-Orientierung korrigieren
                try:
                    # Orientierung aus EXIF-Daten lesen
                    exif_dict = img._getexif()
                    if exif_dict is not None:
                        for tag, value in exif_dict.items():
                            if tag in ExifTags.TAGS and ExifTags.TAGS[tag] == 'Orientation':
                                if value == 3:
                                    img = img.rotate(180, expand=True)
                                elif value == 6:
                                    img = img.rotate(270, expand=True)  
                                elif value == 8:
                                    img = img.rotate(90, expand=True)
                                break
                except (AttributeError, KeyError, TypeError, OSError):
                    # Keine EXIF-Daten oder Fehler - ignorieren
                    pass
                
                # Zielgröße für Dienstausweis (Passbild-Format)
                target_width = 267
                target_height = 400
                target_size = (target_width, target_height)
                
                # Original-Abmessungen
                original_width, original_height = img.size
                
                # Seitenverhältnis berechnen
                original_ratio = original_width / original_height
                target_ratio = target_width / target_height
                
                # Bild zuschneiden um das richtige Seitenverhältnis zu erhalten
                if original_ratio > target_ratio:
                    # Bild ist zu breit - an der Seite beschneiden
                    new_width = int(original_height * target_ratio)
                    left = (original_width - new_width) // 2
                    right = left + new_width
                    img = img.crop((left, 0, right, original_height))
                elif original_ratio < target_ratio:
                    # Bild ist zu hoch - oben/unten beschneiden  
                    new_height = int(original_width / target_ratio)
                    top = (original_height - new_height) // 2
                    bottom = top + new_height
                    img = img.crop((0, top, original_width, bottom))
                
                # Auf finale Größe skalieren mit hochwertiger Interpolation
                img = img.resize(target_size, Image.Resampling.LANCZOS)
                
                # In RGB konvertieren falls nötig (für JPEG)
                if img.mode in ('RGBA', 'P', 'LA'):
                    # Weißer Hintergrund für Transparenz
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # DPI für Druckqualität setzen (300 DPI)
                dpi = (300, 300)
                
                # Optimierte JPEG-Einstellungen für Druck
                save_kwargs = {
                    'format': 'JPEG',
                    'quality': 95,  # Höhere Qualität für Druck
                    'optimize': True,
                    'dpi': dpi,
                    'progressive': True,  # Progressive JPEG für bessere Kompression
                    'subsampling': 0,  # Keine Farbunterabtastung für beste Qualität
                }
                
                # Bild speichern
                img.save(self.profile_picture.path, **save_kwargs)
                
                # Metadaten prüfen (Debug)
                print(f"Bild verarbeitet für {self.full_name}:")
                print(f"- Größe: {target_width}x{target_height}px")
                print(f"- DPI: {dpi[0]}")
                print(f"- Format: JPEG")
                print(f"- Qualität: 95%")
                
        except Exception as e:
            print(f"Fehler bei Bildverarbeitung für {self}: {str(e)}")
            # Log-Eintrag für Debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Bildverarbeitung fehlgeschlagen für Mitglied {self.pk}: {str(e)}")

    def get_image_info(self):
        """
        Gibt Informationen über das gespeicherte Bild zurück
        Nützlich für Debugging und Qualitätskontrolle
        """
        if not self.profile_picture:
            return None
            
        try:
            from PIL import Image
            import os
            
            if not os.path.exists(self.profile_picture.path):
                return None
                
            with Image.open(self.profile_picture.path) as img:
                # Dateigröße
                file_size = os.path.getsize(self.profile_picture.path)
                
                return {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode,
                    'dpi': img.info.get('dpi', (0, 0)),
                    'file_size_kb': round(file_size / 1024, 2),
                    'is_valid_size': img.width == 267 and img.height == 400,
                    'is_print_quality': img.info.get('dpi', (0, 0))[0] >= 300,
                }
        except Exception as e:
            return {'error': str(e)}

    # Zusätzliche Validierung im MemberForm
    def clean_profile_picture(self):
        """Erweiterte Validierung für Profilbilder"""
        picture = self.cleaned_data.get('profile_picture')
        
        if picture:
            # Dateigröße prüfen (max 10MB)
            if picture.size > 10 * 1024 * 1024:
                raise ValidationError("Bilddatei ist zu groß. Maximum: 10MB")
            
            # Bildformat prüfen
            try:
                from PIL import Image
                import io
                
                # Bild öffnen um Format zu validieren
                image = Image.open(io.BytesIO(picture.read()))
                
                # Unterstützte Formate
                supported_formats = ['JPEG', 'JPG', 'PNG', 'TIFF', 'BMP']
                if image.format not in supported_formats:
                    raise ValidationError(f"Unsupported format. Erlaubt: {', '.join(supported_formats)}")
                
                # Mindestauflösung prüfen (sollte mindestens Zielgröße haben)
                min_width, min_height = 200, 300  # Etwas niedriger für Flexibilität
                if image.width < min_width or image.height < min_height:
                    raise ValidationError(
                        f"Bild zu klein. Minimum: {min_width}x{min_height}px "
                        f"(Aktuell: {image.width}x{image.height}px)"
                    )
                
                # Maximalgröße prüfen (sehr große Bilder vermeiden)
                max_width, max_height = 4000, 6000
                if image.width > max_width or image.height > max_height:
                    raise ValidationError(
                        f"Bild zu groß. Maximum: {max_width}x{max_height}px "
                        f"(Aktuell: {image.width}x{image.height}px)"
                    )
                
                # Cursor zurücksetzen für weitere Verarbeitung
                picture.seek(0)
                
            except Exception as e:
                raise ValidationError(f"Ungültige Bilddatei: {str(e)}")
        
        return picture
    
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
