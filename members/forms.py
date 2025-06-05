from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, timedelta
from .models import Member
import os

class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            'first_name', 'last_name', 'birth_date', 'personnel_number',
            'member_type', 'card_number_prefix', 'issued_date', 'valid_until',
            'manual_validity', 'profile_picture', 'is_active'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Vorname eingeben'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nachname eingeben'
            }),
            # ✅ KORRIGIERT: DateInput mit HTML5 date type und korrektem Format
            'birth_date': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                },
                format='%Y-%m-%d'  # ✅ HTML5 Format erzwingen
            ),
            'personnel_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional'
            }),
            'member_type': forms.Select(attrs={
                'class': 'form-select',
                'onchange': 'updatePrefixAndValidity()'
            }),
            'card_number_prefix': forms.Select(attrs={
                'class': 'form-select'
            }),
            # ✅ KORRIGIERT: issued_date mit HTML5 Format
            'issued_date': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                    'onchange': 'updateValidUntil()'
                },
                format='%Y-%m-%d'  # ✅ HTML5 Format erzwingen
            ),
            # ✅ KORRIGIERT: valid_until mit HTML5 Format
            'valid_until': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                },
                format='%Y-%m-%d'  # ✅ HTML5 Format erzwingen
            ),
            'manual_validity': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'onchange': 'toggleManualValidity()'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/jpg,image/png,image/tiff,image/bmp',
                'data-max-size': '10485760',  # 10MB in Bytes
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'first_name': 'Vorname',
            'last_name': 'Nachname',
            'birth_date': 'Geburtsdatum',
            'personnel_number': 'Personalnummer',
            'member_type': 'Mitarbeitertyp',
            'card_number_prefix': 'Ausweisnummer-Präfix',
            'issued_date': 'Ausgestellt am',
            'valid_until': 'Gültig bis',
            'manual_validity': 'Manuelle Gültigkeit (für Externe/Praktikanten)',
            'profile_picture': 'Profilbild für Dienstausweis',
            'is_active': 'Aktiv'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # ✅ WICHTIG: HTML5 date format für alle Django Datumsfelder setzen
        self.fields['birth_date'].input_formats = ['%Y-%m-%d']
        self.fields['issued_date'].input_formats = ['%Y-%m-%d'] 
        self.fields['valid_until'].input_formats = ['%Y-%m-%d']
        
        # Bessere Hilftexte für Profilbild
        self.fields['profile_picture'].help_text = (
            "Foto für den Dienstausweis. Wird automatisch auf 267x400 Pixel "
            "bei 300 DPI für optimale Druckqualität angepasst. "
            "Unterstützte Formate: JPEG, PNG, TIFF, BMP. Max. 10MB."
        )
        
        # Standardwerte setzen
        if not self.instance.pk:
            self.fields['issued_date'].initial = timezone.now().date()
        
        # Pflichtfelder markieren
        for field_name, field in self.fields.items():
            if field_name not in ['personnel_number', 'profile_picture', 'is_active', 'manual_validity', 'card_number_prefix']:
                field.required = True
        
        # Valid_until ist nur bei manueller Gültigkeit Pflichtfeld
        if self.instance.pk and self.instance.manual_validity:
            self.fields['valid_until'].required = True
        else:
            self.fields['valid_until'].required = False
    
    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date:
            today = date.today()
            age = today.year - birth_date.year - (
                (today.month, today.day) < (birth_date.month, birth_date.day)
            )
            
            if age < 14:  # Jugendfeuerwehr ab 14
                raise ValidationError("Mitglied muss mindestens 14 Jahre alt sein.")
            if age > 100:
                raise ValidationError("Bitte überprüfen Sie das Geburtsdatum.")
            if birth_date > today:
                raise ValidationError("Geburtsdatum kann nicht in der Zukunft liegen.")
        
        return birth_date
    
    def clean_valid_until(self):
        valid_until = self.cleaned_data.get('valid_until')
        manual_validity = self.cleaned_data.get('manual_validity')
        member_type = self.cleaned_data.get('member_type')
        issued_date = self.cleaned_data.get('issued_date')
        
        # Bei manueller Gültigkeit muss valid_until gesetzt sein
        if manual_validity and not valid_until:
            raise ValidationError("Bei manueller Gültigkeit muss ein Datum angegeben werden.")
        
        # Gültigkeit darf nicht vor Ausstellungsdatum liegen
        if valid_until and issued_date and valid_until <= issued_date:
            raise ValidationError("Gültig bis muss nach dem Ausstellungsdatum liegen.")
        
        return valid_until
    
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
                supported_formats = ['JPEG', 'PNG', 'TIFF', 'BMP']
                if image.format not in supported_formats:
                    raise ValidationError(f"Unsupported format. Erlaubt: {', '.join(supported_formats)}")
                
                # Mindestauflösung prüfen
                min_width, min_height = 200, 300  
                if image.width < min_width or image.height < min_height:
                    raise ValidationError(
                        f"Bild zu klein. Minimum: {min_width}x{min_height}px "
                        f"(Aktuell: {image.width}x{image.height}px)"
                    )
                
                # Maximalgröße prüfen
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
    
    def clean(self):
        cleaned_data = super().clean()
        member_type = cleaned_data.get('member_type')
        manual_validity = cleaned_data.get('manual_validity')
        
        # Für Externe und Praktikanten sollte manuelle Gültigkeit aktiviert sein
        if member_type in ['EXTERN', 'PRAKTIKANT'] and not manual_validity:
            # Automatisch aktivieren
            cleaned_data['manual_validity'] = True
        
        return cleaned_data

class ImportForm(forms.Form):
    """Form für CSV-Datenimport"""
    
    file = forms.FileField(
        label="CSV-Datei",
        help_text="CSV-Datei mit Mitgliederdaten (UTF-8 kodiert)",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv'  # Nur CSV
        })
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            if file.size > 10 * 1024 * 1024:
                raise ValidationError("Datei ist zu groß. Maximale Größe: 10MB")
            
            # Nur CSV erlaubt
            if not file.name.lower().endswith('.csv'):
                raise ValidationError("Nur CSV-Dateien sind erlaubt. Bitte konvertieren Sie Excel-Dateien zu CSV.")
        
        return file