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
            'issued_date', 'profile_picture', 'is_active'
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
            'issued_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
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
            'issued_date': 'Ausgestellt am',
            'profile_picture': 'Profilbild',
            'is_active': 'Aktiv'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['issued_date'].initial = timezone.now().date()
        
        for field_name, field in self.fields.items():
            if field_name not in ['personnel_number', 'profile_picture', 'is_active']:
                field.required = True
    
    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date:
            today = date.today()
            age = today.year - birth_date.year - (
                (today.month, today.day) < (birth_date.month, birth_date.day)
            )
            
            if age < 16:
                raise ValidationError("Mitglied muss mindestens 16 Jahre alt sein.")
            if age > 100:
                raise ValidationError("Bitte überprüfen Sie das Geburtsdatum.")
            if birth_date > today:
                raise ValidationError("Geburtsdatum kann nicht in der Zukunft liegen.")
        
        return birth_date

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
        """Validierung der Import-Datei"""
        file = self.cleaned_data.get('file')
        if file:
            # Dateigröße prüfen (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError("Datei ist zu groß. Maximale Größe: 10MB")
            
            # Dateiendung prüfen
            allowed_extensions = ['.csv', '.xlsx', '.xls']
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in allowed_extensions:
                raise ValidationError(f"Nur {', '.join(allowed_extensions)} Dateien erlaubt.")
        
        return file
