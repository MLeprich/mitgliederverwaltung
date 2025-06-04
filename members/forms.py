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
            'birth_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
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
            'issued_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'onchange': 'updateValidUntil()'
            }),
            'valid_until': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'manual_validity': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'onchange': 'toggleManualValidity()'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/jpg,image/png'
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
            'profile_picture': 'Profilbild',
            'is_active': 'Aktiv'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
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
    """Form für Datenimport"""
    
    file = forms.FileField(
        label="Import-Datei",
        help_text="CSV oder Excel-Datei mit Mitgliederdaten",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.csv,.xlsx,.xls'
        })
    )
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            if file.size > 10 * 1024 * 1024:
                raise ValidationError("Datei ist zu groß. Maximale Größe: 10MB")
            
            allowed_extensions = ['.csv', '.xlsx', '.xls']
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in allowed_extensions:
                raise ValidationError(f"Nur {', '.join(allowed_extensions)} Dateien erlaubt.")
        
        return file
