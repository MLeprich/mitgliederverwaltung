# members/models.py
from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
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
        
        # ❌ ENTFERNT: Überflüssige String-zu-Date Konvertierung
        # Diese Konvertierung ist nicht nötig, da Django und unser Import bereits 
        # echte date-Objekte liefern sollten
        
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
    - Exakte Größe: 267x400 Pixel (Passbild-Format im Hochformat)
    - 300 DPI für Druckqualität
    - Optimierte Kompression für Druck
    - EXIF-Orientierung KORREKT handhaben
    """
    try:
        from PIL import Image, ExifTags
        import os
        
        if not self.profile_picture or not os.path.exists(self.profile_picture.path):
            return
            
        # Bild öffnen
        with Image.open(self.profile_picture.path) as img:
            
            # ✅ KORRIGIERTE EXIF-Orientierung - NUR bei falscher Orientierung rotieren
            try:
                # EXIF-Daten lesen
                exif_dict = img._getexif()
                if exif_dict is not None:
                    for tag, value in exif_dict.items():
                        if tag in ExifTags.TAGS and ExifTags.TAGS[tag] == 'Orientation':
                            print(f"🔍 EXIF-Orientierung gefunden: {value}")
                            
                            # NUR rotieren wenn das Bild wirklich falsch orientiert ist
                            if value == 3:  # 180° gedreht
                                img = img.rotate(180, expand=True)
                                print("🔄 Bild um 180° gedreht")
                            elif value == 6:  # 90° im Uhrzeigersinn gedreht (von Kamera falsch gespeichert)
                                img = img.rotate(270, expand=True)  # Gegen den Uhrzeigersinn zurückdrehen
                                print("🔄 Bild um 270° gedreht (EXIF-Korrektur)")
                            elif value == 8:  # 90° gegen Uhrzeigersinn gedreht (von Kamera falsch gespeichert)
                                img = img.rotate(90, expand=True)   # Im Uhrzeigersinn zurückdrehen
                                print("🔄 Bild um 90° gedreht (EXIF-Korrektur)")
                            elif value == 1:  # Normale Orientierung
                                print("✅ Bild hat bereits korrekte Orientierung")
                            else:
                                print(f"ℹ️ Unbekannte EXIF-Orientierung: {value} - keine Rotation")
                            break
                else:
                    print("ℹ️ Keine EXIF-Orientierungsdaten gefunden")
                    
            except (AttributeError, KeyError, TypeError, OSError) as e:
                print(f"ℹ️ EXIF-Verarbeitung übersprungen: {e}")
                pass
            
            # Zielgröße für Dienstausweis (HOCHFORMAT Passbild)
            target_width = 267   # Breite
            target_height = 400  # Höhe (länger = Hochformat)
            target_size = (target_width, target_height)
            
            print(f"📐 Originalgröße: {img.size[0]}x{img.size[1]}px")
            print(f"🎯 Zielgröße: {target_width}x{target_height}px (Hochformat)")
            
            # Original-Abmessungen nach EXIF-Korrektur
            original_width, original_height = img.size
            
            # ✅ PRÜFUNG: Ist das Bild im Querformat? Dann automatisch um 90° drehen
            if original_width > original_height:
                print("🔄 Querformat erkannt - drehe zu Hochformat")
                img = img.rotate(90, expand=True)
                original_width, original_height = img.size
                print(f"📐 Nach Hochformat-Korrektur: {original_width}x{original_height}px")
            
            # Seitenverhältnis berechnen
            original_ratio = original_width / original_height
            target_ratio = target_width / target_height
            
            print(f"📊 Original-Verhältnis: {original_ratio:.3f}")
            print(f"📊 Ziel-Verhältnis: {target_ratio:.3f}")
            
            # Bild zuschneiden um das richtige Seitenverhältnis zu erhalten
            if original_ratio > target_ratio:
                # Bild ist zu breit - an den Seiten beschneiden
                new_width = int(original_height * target_ratio)
                left = (original_width - new_width) // 2
                right = left + new_width
                img = img.crop((left, 0, right, original_height))
                print(f"✂️ Seitlich beschnitten: {new_width}x{original_height}px")
            elif original_ratio < target_ratio:
                # Bild ist zu hoch - oben/unten beschneiden  
                new_height = int(original_width / target_ratio)
                top = (original_height - new_height) // 2
                bottom = top + new_height
                img = img.crop((0, top, original_width, bottom))
                print(f"✂️ Vertikal beschnitten: {original_width}x{new_height}px")
            else:
                print("✅ Seitenverhältnis bereits korrekt")
            
            # Auf finale Größe skalieren mit hochwertiger Interpolation
            img = img.resize(target_size, Image.Resampling.LANCZOS)
            print(f"🔧 Skaliert auf: {img.size[0]}x{img.size[1]}px")
            
            # In RGB konvertieren falls nötig (für JPEG)
            if img.mode in ('RGBA', 'P', 'LA'):
                # Weißer Hintergrund für Transparenz
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
                print("🎨 RGB-Konvertierung mit weißem Hintergrund")
            elif img.mode != 'RGB':
                img = img.convert('RGB')
                print("🎨 RGB-Konvertierung")
            
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
            
            # Erfolgsmeldung
            print(f"✅ Passbild erstellt für {self.full_name}:")
            print(f"   📐 Größe: {target_width}x{target_height}px (Hochformat)")
            print(f"   🖨️ DPI: {dpi[0]}")
            print(f"   📁 Format: JPEG (95% Qualität)")
            print(f"   🎯 Bereit für Dienstausweis-Druck")
            
    except Exception as e:
        print(f"❌ Fehler bei Bildverarbeitung für {self}: {str(e)}")
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

    # Validierung des Profilbilds auf Model-Ebene
    def clean_profile_picture(self):
        """Erweiterte Validierung für Profilbilder auf Model-Ebene"""
        picture = self.profile_picture

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
        if not self.birth_date:
            return 0
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
    
    @property
    def is_card_expired(self):
        # ✅ KORRIGIERT: None-Check hinzugefügt
        if not self.valid_until:
            return False  # Kein Ablaufdatum = nicht abgelaufen
        return date.today() > self.valid_until
    
    @property
    def expires_soon(self):
        # ✅ KORRIGIERT: None-Check hinzugefügt
        if not self.valid_until:
            return False  # Kein Ablaufdatum = läuft nicht bald ab
        return date.today() + timedelta(days=30) > self.valid_until
    
    def get_card_status(self):
        # ✅ KORRIGIERT: None-Check hinzugefügt
        if not self.valid_until:
            return "Kein Ablaufdatum"
        elif self.is_card_expired:
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
