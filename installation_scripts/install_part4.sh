#!/bin/bash
# Installation Script Teil 4: Views, Forms und weitere Templates
# Ausführen mit: bash install_part4.sh

set -e

echo "=== Mitgliederverwaltung Dashboard - Teil 4: Views und Forms ==="
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

print_status "Erstelle Forms..."

# Forms erstellen
cat > members/forms.py << 'EOF'
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, timedelta
from .models import Member
import pandas as pd
import os


class MemberForm(forms.ModelForm):
    """Form für Mitgliederdaten"""
    
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
                'placeholder': 'Optional - nur für nicht-FF Mitglieder'
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
        help_texts = {
            'personnel_number': 'Optional - FF Mitglieder haben keine Personalnummer',
            'issued_date': 'Datum der Ausweiserstellung',
            'profile_picture': 'JPG, JPEG oder PNG - wird automatisch umbenannt',
            'is_active': 'Deaktivierte Mitglieder werden nicht für neue Ausweise verwendet'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Standardwert für issued_date
        if not self.instance.pk:
            self.fields['issued_date'].initial = timezone.now().date()
        
        # Alle Felder außer personnel_number sind Pflichtfelder
        for field_name, field in self.fields.items():
            if field_name != 'personnel_number' and field_name != 'profile_picture':
                field.required = True
    
    def clean_birth_date(self):
        """Validierung des Geburtsdatums"""
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
    
    def clean_issued_date(self):
        """Validierung des Ausstellungsdatums"""
        issued_date = self.cleaned_data.get('issued_date')
        if issued_date:
            today = date.today()
            if issued_date > today:
                raise ValidationError("Ausstellungsdatum kann nicht in der Zukunft liegen.")
            
            # Nicht älter als 1 Jahr in der Vergangenheit
            one_year_ago = today - timedelta(days=365)
            if issued_date < one_year_ago:
                raise ValidationError("Ausstellungsdatum sollte nicht älter als 1 Jahr sein.")
        
        return issued_date
    
    def clean_personnel_number(self):
        """Validierung der Personalnummer"""
        personnel_number = self.cleaned_data.get('personnel_number')
        if personnel_number:
            # Entfernen von Leerzeichen
            personnel_number = personnel_number.strip()
            
            # Prüfen auf Eindeutigkeit (außer für aktuelles Objekt)
            existing = Member.objects.filter(personnel_number=personnel_number)
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError("Diese Personalnummer ist bereits vergeben.")
        
        return personnel_number
    
    def clean_profile_picture(self):
        """Validierung des Profilbilds"""
        picture = self.cleaned_data.get('profile_picture')
        if picture:
            # Dateigröße prüfen (max 5MB)
            if picture.size > 5 * 1024 * 1024:
                raise ValidationError("Bild ist zu groß. Maximale Größe: 5MB")
            
            # Dateiendung prüfen
            allowed_extensions = ['.jpg', '.jpeg', '.png']
            ext = os.path.splitext(picture.name)[1].lower()
            if ext not in allowed_extensions:
                raise ValidationError(f"Nur {', '.join(allowed_extensions)} Dateien erlaubt.")
        
        return picture
    
    def clean(self):
        """Gesamtvalidierung des Forms"""
        cleaned_data = super().clean()
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        birth_date = cleaned_data.get('birth_date')
        
        # Prüfen auf doppelte Einträge (Name + Geburtsdatum)
        if first_name and last_name and birth_date:
            existing = Member.objects.filter(
                first_name__iexact=first_name,
                last_name__iexact=last_name,
                birth_date=birth_date
            )
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError(
                    "Ein Mitglied mit diesem Namen und Geburtsdatum existiert bereits."
                )
        
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
            
            # Versuchen, die Datei zu lesen
            try:
                if ext == '.csv':
                    df = pd.read_csv(file, nrows=0)  # Nur Header lesen
                else:
                    df = pd.read_excel(file, nrows=0)  # Nur Header lesen
                
                # Mindestens eine Spalte muss vorhanden sein
                if df.empty or len(df.columns) == 0:
                    raise ValidationError("Datei enthält keine gültigen Spalten.")
                
            except Exception as e:
                raise ValidationError(f"Fehler beim Lesen der Datei: {str(e)}")
            
            # File pointer zurücksetzen
            file.seek(0)
        
        return file


class SearchForm(forms.Form):
    """Form für Mitgliedersuche"""
    
    search = forms.CharField(
        required=False,
        label="Suche",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Name oder Personalnummer suchen...'
        })
    )
    
    status = forms.ChoiceField(
        required=False,
        label="Status",
        choices=[
            ('', 'Alle'),
            ('active', 'Aktiv'),
            ('inactive', 'Inaktiv'),
            ('valid', 'Gültiger Ausweis'),
            ('expired', 'Abgelaufener Ausweis'),
            ('expiring', 'Läuft bald ab'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    sort = forms.ChoiceField(
        required=False,
        label="Sortierung",
        choices=[
            ('name', 'Name'),
            ('created', 'Erstellt'),
            ('valid_until', 'Gültig bis'),
            ('birth_date', 'Geburtsdatum'),
        ],
        initial='name',
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class ExportForm(forms.Form):
    """Form für Datenexport"""
    
    FORMAT_CHOICES = [
        ('csv', 'CSV-Datei'),
        ('xlsx', 'Excel-Datei'),
    ]
    
    MEMBER_CHOICES = [
        ('all', 'Alle Mitglieder'),
        ('active', 'Nur aktive Mitglieder'),
        ('valid', 'Nur gültige Ausweise'),
        ('expired', 'Nur abgelaufene Ausweise'),
        ('expiring', 'Nur bald ablaufende Ausweise'),
    ]
    
    format = forms.ChoiceField(
        label="Format",
        choices=FORMAT_CHOICES,
        initial='csv',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    members = forms.ChoiceField(
        label="Mitglieder",
        choices=MEMBER_CHOICES,
        initial='active',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    include_images = forms.BooleanField(
        label="Profilbilder einschließen",
        required=False,
        initial=False,
        help_text="Erstellt zusätzlich ein ZIP-Archiv mit allen Profilbildern",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
EOF

print_status "Erstelle Views..."

# Views erstellen
cat > members/views.py << 'EOF'
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.utils import timezone
from datetime import date, timedelta
import pandas as pd
import json
import os
import zipfile
import tempfile
from io import BytesIO

from .models import Member, ImportLog
from .forms import MemberForm, ImportForm, SearchForm, ExportForm


class DashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard Hauptseite"""
    template_name = 'dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistiken berechnen
        today = date.today()
        expiry_threshold = today + timedelta(days=30)
        
        stats = {
            'active_members': Member.objects.filter(is_active=True).count(),
            'valid_cards': Member.objects.filter(
                is_active=True, valid_until__gt=today
            ).count(),
            'expiring_soon': Member.objects.filter(
                is_active=True, 
                valid_until__gt=today,
                valid_until__lte=expiry_threshold
            ).count(),
            'expired_cards': Member.objects.filter(
                is_active=True, valid_until__lte=today
            ).count(),
        }
        
        context['stats'] = stats
        
        # Letzte 5 Mitglieder
        context['recent_members'] = Member.objects.filter(
            is_active=True
        ).order_by('-created_at')[:5]
        
        # Bald ablaufende Ausweise
        context['expiring_members'] = Member.objects.filter(
            is_active=True,
            valid_until__lte=expiry_threshold
        ).order_by('valid_until')[:10]
        
        return context


class MemberListView(LoginRequiredMixin, ListView):
    """Mitgliederliste mit Suche und Filterung"""
    model = Member
    template_name = 'members/member_list.html'
    context_object_name = 'members'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = Member.objects.all()
        
        # Suche
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(personnel_number__icontains=search)
            )
        
        # Status Filter
        status = self.request.GET.get('status')
        today = date.today()
        
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)
        elif status == 'expired':
            queryset = queryset.filter(valid_until__lte=today)
        elif status == 'expiring':
            expiry_threshold = today + timedelta(days=30)
            queryset = queryset.filter(
                valid_until__gt=today,
                valid_until__lte=expiry_threshold
            )
        elif status == 'valid':
            queryset = queryset.filter(valid_until__gt=today)
        
        # Sortierung
        sort = self.request.GET.get('sort', 'name')
        if sort == 'name':
            queryset = queryset.order_by('last_name', 'first_name')
        elif sort == 'created':
            queryset = queryset.order_by('-created_at')
        elif sort == 'valid_until':
            queryset = queryset.order_by('valid_until')
        elif sort == 'birth_date':
            queryset = queryset.order_by('birth_date')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = SearchForm(self.request.GET)
        return context


class MemberDetailView(LoginRequiredMixin, DetailView):
    """Mitgliederdetails"""
    model = Member
    template_name = 'members/member_detail.html'
    context_object_name = 'member'


class MemberCreateView(LoginRequiredMixin, CreateView):
    """Neues Mitglied erstellen"""
    model = Member
    form_class = MemberForm
    template_name = 'members/member_form.html'
    success_url = reverse_lazy('members:member_list')
    
    def form_valid(self, form):
        messages.success(
            self.request, 
            f'Mitglied {form.instance.full_name} wurde erfolgreich erstellt.'
        )
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Neues Mitglied hinzufügen'
        context['submit_text'] = 'Mitglied erstellen'
        return context


class MemberUpdateView(LoginRequiredMixin, UpdateView):
    """Mitglied bearbeiten"""
    model = Member
    form_class = MemberForm
    template_name = 'members/member_form.html'
    
    def get_success_url(self):
        return reverse_lazy('members:member_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(
            self.request, 
            f'Mitglied {form.instance.full_name} wurde erfolgreich aktualisiert.'
        )
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Mitglied bearbeiten: {self.object.full_name}'
        context['submit_text'] = 'Änderungen speichern'
        return context


class MemberDeleteView(LoginRequiredMixin, DeleteView):
    """Mitglied löschen"""
    model = Member
    template_name = 'members/member_confirm_delete.html'
    success_url = reverse_lazy('members:member_list')
    
    def delete(self, request, *args, **kwargs):
        member_name = self.get_object().full_name
        response = super().delete(request, *args, **kwargs)
        messages.success(
            request, 
            f'Mitglied {member_name} wurde erfolgreich gelöscht.'
        )
        return response


class ImportView(LoginRequiredMixin, TemplateView):
    """Datenimport von CSV/Excel"""
    template_name = 'members/import.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ImportForm()
        context['recent_imports'] = ImportLog.objects.filter(
            imported_by=self.request.user
        ).order_by('-imported_at')[:5]
        return context
    
    def post(self, request, *args, **kwargs):
        form = ImportForm(request.POST, request.FILES)
        
        if form.is_valid():
            return self.process_import(request, form.cleaned_data['file'])
        
        context = self.get_context_data()
        context['form'] = form
        return render(request, self.template_name, context)
    
    def process_import(self, request, file):
        """Verarbeitung der Import-Datei"""
        try:
            # Datei lesen
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            
            # Spalten normalisieren
            df.columns = df.columns.str.strip().str.lower()
            
            # Mapping der Spalten
            column_mapping = {
                'vorname': 'first_name',
                'nachname': 'last_name',
                'geburtsdatum': 'birth_date',
                'personalnummer': 'personnel_number',
                'ausgestellt': 'issued_date',
                'first_name': 'first_name',
                'last_name': 'last_name',
                'birth_date': 'birth_date',
                'personnel_number': 'personnel_number',
                'issued_date': 'issued_date',
            }
            
            # DataFrame verarbeiten
            processed_data = []
            errors = []
            
            for index, row in df.iterrows():
                try:
                    member_data = {}
                    
                    # Pflichtfelder zuordnen
                    for col, field in column_mapping.items():
                        if col in df.columns and pd.notna(row[col]):
                            member_data[field] = row[col]
                    
                    # Validierung
                    if not all(k in member_data for k in ['first_name', 'last_name']):
                        errors.append(f"Zeile {index + 2}: Vor- und Nachname sind Pflichtfelder")
                        continue
                    
                    # Datum formatieren
                    if 'birth_date' in member_data:
                        try:
                            if isinstance(member_data['birth_date'], str):
                                member_data['birth_date'] = pd.to_datetime(
                                    member_data['birth_date'], 
                                    dayfirst=True
                                ).date()
                            else:
                                member_data['birth_date'] = pd.to_datetime(
                                    member_data['birth_date']
                                ).date()
                        except:
                            errors.append(f"Zeile {index + 2}: Ungültiges Geburtsdatum")
                            continue
                    else:
                        errors.append(f"Zeile {index + 2}: Geburtsdatum fehlt")
                        continue
                    
                    # Ausstellungsdatum setzen
                    if 'issued_date' not in member_data:
                        member_data['issued_date'] = timezone.now().date()
                    
                    processed_data.append(member_data)
                    
                except Exception as e:
                    errors.append(f"Zeile {index + 2}: {str(e)}")
            
            # Daten in Datenbank speichern
            successful_imports = 0
            failed_imports = 0
            
            for data in processed_data:
                try:
                    # Prüfen auf Duplikate
                    existing = Member.objects.filter(
                        first_name__iexact=data['first_name'],
                        last_name__iexact=data['last_name'],
                        birth_date=data['birth_date']
                    ).first()
                    
                    if existing:
                        errors.append(f"Duplikat: {data['first_name']} {data['last_name']} existiert bereits")
                        failed_imports += 1
                        continue
                    
                    # Mitglied erstellen
                    Member.objects.create(**data)
                    successful_imports += 1
                    
                except Exception as e:
                    errors.append(f"Fehler beim Speichern von {data.get('first_name', '')} {data.get('last_name', '')}: {str(e)}")
                    failed_imports += 1
            
            # Import-Log erstellen
            ImportLog.objects.create(
                filename=file.name,
                total_rows=len(df),
                successful_imports=successful_imports,
                failed_imports=failed_imports,
                error_log='\n'.join(errors) if errors else '',
                imported_by=request.user
            )
            
            # Erfolgsmeldung
            if successful_imports > 0:
                messages.success(
                    request,
                    f'{successful_imports} Mitglieder erfolgreich importiert.'
                )
            
            if failed_imports > 0:
                messages.warning(
                    request,
                    f'{failed_imports} Einträge konnten nicht importiert werden. Siehe Details unten.'
                )
            
            return redirect('members:import_data')
            
        except Exception as e:
            messages.error(request, f'Fehler beim Import: {str(e)}')
            return redirect('members:import_data')


class ExportView(LoginRequiredMixin, TemplateView):
    """Datenexport als CSV/Excel"""
    template_name = 'members/export.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ExportForm()
        return context
    
    def post(self, request, *args, **kwargs):
        form = ExportForm(request.POST)
        
        if form.is_valid():
            return self.process_export(request, form.cleaned_data)
        
        context = self.get_context_data()
        context['form'] = form
        return render(request, self.template_name, context)
    
    def process_export(self, request, form_data):
        """Verarbeitung des Exports"""
        try:
            # Queryset basierend auf Auswahl
            queryset = Member.objects.all()
            
            members_choice = form_data['members']
            today = date.today()
            
            if members_choice == 'active':
                queryset = queryset.filter(is_active=True)
            elif members_choice == 'valid':
                queryset = queryset.filter(valid_until__gt=today)
            elif members_choice == 'expired':
                queryset = queryset.filter(valid_until__lte=today)
            elif members_choice == 'expiring':
                expiry_threshold = today + timedelta(days=30)
                queryset = queryset.filter(
                    valid_until__gt=today,
                    valid_until__lte=expiry_threshold
                )
            
            # Daten für Export vorbereiten
            export_data = []
            for member in queryset:
                export_data.append({
                    'Vorname': member.first_name,
                    'Nachname': member.last_name,
                    'Geburtsdatum': member.birth_date.strftime('%d.%m.%Y'),
                    'Personalnummer': member.personnel_number or '',
                    'Ausgestellt am': member.issued_date.strftime('%d.%m.%Y'),
                    'Gültig bis': member.valid_until.strftime('%d.%m.%Y'),
                    'Alter': member.age,
                    'Status': 'Aktiv' if member.is_active else 'Inaktiv',
                    'Ausweis-Status': member.get_card_status(),
                    'Erstellt am': member.created_at.strftime('%d.%m.%Y %H:%M'),
                })
            
            df = pd.DataFrame(export_data)
            
            # Export basierend auf Format
            if form_data['format'] == 'csv':
                response = HttpResponse(content_type='text/csv; charset=utf-8')
                response['Content-Disposition'] = f'attachment; filename="mitglieder_{today.strftime("%Y%m%d")}.csv"'
                df.to_csv(response, index=False, encoding='utf-8-sig')
                
            else:  # Excel
                response = HttpResponse(
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = f'attachment; filename="mitglieder_{today.strftime("%Y%m%d")}.xlsx"'
                
                with pd.ExcelWriter(response, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Mitglieder', index=False)
            
            messages.success(request, f'{len(export_data)} Mitglieder erfolgreich exportiert.')
            return response
            
        except Exception as e:
            messages.error(request, f'Fehler beim Export: {str(e)}')
            return redirect('members:export_data')


# API Views für AJAX Requests
@login_required
def member_stats_api(request):
    """API für Dashboard-Statistiken"""
    today = date.today()
    expiry_threshold = today + timedelta(days=30)
    
    stats = {
        'active_members': Member.objects.filter(is_active=True).count(),
        'valid_cards': Member.objects.filter(
            is_active=True, valid_until__gt=today
        ).count(),
        'expiring_soon': Member.objects.filter(
            is_active=True, 
            valid_until__gt=today,
            valid_until__lte=expiry_threshold
        ).count(),
        'expired_cards': Member.objects.filter(
            is_active=True, valid_until__lte=today
        ).count(),
    }
    
    return JsonResponse(stats)


@login_required
def search_members_api(request):
    """API für Mitgliedersuche"""
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    members = Member.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(personnel_number__icontains=query)
    ).filter(is_active=True)[:10]
    
    results = []
    for member in members:
        results.append({
            'id': member.id,
            'name': member.full_name,
            'personnel_number': member.personnel_number or '',
            'status': member.get_card_status(),
        })
    
    return JsonResponse({'results': results})
EOF

print_status "Erstelle weitere Templates..."

# Member Form Template
cat > templates/members/member_form.html << 'EOF'
{% extends 'base.html' %}
{% load crispy_forms_tags %}
{% load static %}

{% block title %}{{ title }} - Mitgliederverwaltung{% endblock %}

{% block breadcrumb %}
<nav aria-label="breadcrumb">
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="{% url 'members:dashboard' %}">Dashboard</a></li>
        <li class="breadcrumb-item"><a href="{% url 'members:member_list' %}">Mitglieder</a></li>
        <li class="breadcrumb-item active">
            {% if object %}Bearbeiten{% else %}Hinzufügen{% endif %}
        </li>
    </ol>
</nav>
{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-lg-8">
        <div class="card shadow">
            <div class="card-header">
                <h4 class="mb-0">
                    <i class="fas fa-{% if object %}edit{% else %}user-plus{% endif %} me-2"></i>
                    {{ title }}
                </h4>
            </div>
            <div class="card-body">
                <form method="post" enctype="multipart/form-data" class="needs-validation" novalidate>
                    {% csrf_token %}
                    
                    <div class="row">
                        <!-- Persönliche Daten -->
                        <div class="col-md-8">
                            <h5 class="mb-3">
                                <i class="fas fa-user me-2"></i>Persönliche Daten
                            </h5>
                            
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label for="{{ form.first_name.id_for_label }}" class="form-label">
                                        {{ form.first_name.label }} <span class="text-danger">*</span>
                                    </label>
                                    {{ form.first_name }}
                                    {% if form.first_name.errors %}
                                        <div class="invalid-feedback d-block">
                                            {{ form.first_name.errors.0 }}
                                        </div>
                                    {% endif %}
                                </div>
                                
                                <div class="col-md-6 mb-3">
                                    <label for="{{ form.last_name.id_for_label }}" class="form-label">
                                        {{ form.last_name.label }} <span class="text-danger">*</span>
                                    </label>
                                    {{ form.last_name }}
                                    {% if form.last_name.errors %}
                                        <div class="invalid-feedback d-block">
                                            {{ form.last_name.errors.0 }}
                                        </div>
                                    {% endif %}
                                </div>
                            </div>
                            
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label for="{{ form.birth_date.id_for_label }}" class="form-label">
                                        {{ form.birth_date.label }} <span class="text-danger">*</span>
                                    </label>
                                    {{ form.birth_date }}
                                    {% if form.birth_date.help_text %}
                                        <div class="form-text">{{ form.birth_date.help_text }}</div>
                                    {% endif %}
                                    {% if form.birth_date.errors %}
                                        <div class="invalid-feedback d-block">
                                            {{ form.birth_date.errors.0 }}
                                        </div>
                                    {% endif %}
                                </div>
                                
                                <div class="col-md-6 mb-3">
                                    <label for="{{ form.personnel_number.id_for_label }}" class="form-label">
                                        {{ form.personnel_number.label }}
                                    </label>
                                    {{ form.personnel_number }}
                                    {% if form.personnel_number.help_text %}
                                        <div class="form-text">{{ form.personnel_number.help_text }}</div>
                                    {% endif %}
                                    {% if form.personnel_number.errors %}
                                        <div class="invalid-feedback d-block">
                                            {{ form.personnel_number.errors.0 }}
                                        </div>
                                    {% endif %}
                                </div>
                            </div>
                            
                            <h5 class="mb-3 mt-4">
                                <i class="fas fa-id-card me-2"></i>Ausweis-Daten
                            </h5>
                            
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label for="{{ form.issued_date.id_for_label }}" class="form-label">
                                        {{ form.issued_date.label }} <span class="text-danger">*</span>
                                    </label>
                                    {{ form.issued_date }}
                                    {% if form.issued_date.help_text %}
                                        <div class="form-text">{{ form.issued_date.help_text }}</div>
                                    {% endif %}
                                    {% if form.issued_date.errors %}
                                        <div class="invalid-feedback d-block">
                                            {{ form.issued_date.errors.0 }}
                                        </div>
                                    {% endif %}
                                </div>
                                
                                <div class="col-md-6 mb-3 d-flex align-items-center">
                                    <div class="form-check">
                                        {{ form.is_active }}
                                        <label class="form-check-label" for="{{ form.is_active.id_for_label }}">
                                            {{ form.is_active.label }}
                                        </label>
                                        {% if form.is_active.help_text %}
                                            <div class="form-text">{{ form.is_active.help_text }}</div>
                                        {% endif %}
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Profilbild -->
                        <div class="col-md-4">
                            <h5 class="mb-3">
                                <i class="fas fa-image me-2"></i>Profilbild
                            </h5>
                            
                            <div class="mb-3">
                                <div class="profile-image-container text-center">
                                    {% if object.profile_picture %}
                                        <img src="{{ object.profile_picture.url }}" 
                                             class="profile-image-preview mb-3" 
                                             alt="Aktuelles Profilbild"
                                             id="image-preview">
                                    {% else %}
                                        <div class="profile-image-placeholder mb-3" id="image-preview">
                                            <i class="fas fa-user fa-3x"></i>
                                        </div>
                                    {% endif %}
                                </div>
                                
                                <label for="{{ form.profile_picture.id_for_label }}" class="form-label">
                                    {{ form.profile_picture.label }}
                                </label>
                                {{ form.profile_picture }}
                                {% if form.profile_picture.help_text %}
                                    <div class="form-text">{{ form.profile_picture.help_text }}</div>
                                {% endif %}
                                {% if form.profile_picture.errors %}
                                    <div class="invalid-feedback d-block">
                                        {{ form.profile_picture.errors.0 }}
                                    </div>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                    
                    <!-- Form Errors -->
                    {% if form.non_field_errors %}
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-circle me-2"></i>
                            {{ form.non_field_errors }}
                        </div>
                    {% endif %}
                    
                    <!-- Buttons -->
                    <div class="row">
                        <div class="col-12">
                            <hr>
                            <div class="d-flex justify-content-between">
                                <a href="{% url 'members:member_list' %}" class="btn btn-secondary">
                                    <i class="fas fa-arrow-left me-2"></i>Zurück
                                </a>
                                <button type="submit" class="btn btn-primary">
                                    <i class="fas fa-save me-2"></i>{{ submit_text|default:"Speichern" }}
                                </button>
                            </div>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Image preview functionality
    const imageInput = document.getElementById('{{ form.profile_picture.id_for_label }}');
    const imagePreview = document.getElementById('image-preview');
    
    if (imageInput && imagePreview) {
        imageInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    imagePreview.innerHTML = `
                        <img src="${e.target.result}" 
                             class="profile-image-preview mb-3" 
                             alt="Bildvorschau">
                    `;
                };
                reader.readAsDataURL(file);
            }
        });
    }
    
    // Auto-calculate valid_until date (5 years from issued_date)
    const issuedDateInput = document.getElementById('{{ form.issued_date.id_for_label }}');
    if (issuedDateInput) {
        function updateValidUntil() {
            const issuedDate = new Date(issuedDateInput.value);
            if (issuedDate) {
                const validUntil = new Date(issuedDate);
                validUntil.setFullYear(validUntil.getFullYear() + 5);
                
                // Show calculated date
                const validUntilText = document.getElementById('valid-until-display');
                if (!validUntilText) {
                    const displayDiv = document.createElement('div');
                    displayDiv.id = 'valid-until-display';
                    displayDiv.className = 'form-text text-info';
                    displayDiv.innerHTML = `
                        <i class="fas fa-calendar-check me-1"></i>
                        Gültig bis: ${validUntil.toLocaleDateString('de-DE')}
                    `;
                    issuedDateInput.parentNode.appendChild(displayDiv);
                } else {
                    validUntilText.innerHTML = `
                        <i class="fas fa-calendar-check me-1"></i>
                        Gültig bis: ${validUntil.toLocaleDateString('de-DE')}
                    `;
                }
            }
        }
        
        issuedDateInput.addEventListener('change', updateValidUntil);
        // Initial calculation if date is already set
        if (issuedDateInput.value) {
            updateValidUntil();
        }
    }
    
    // Form validation
    const form = document.querySelector('.needs-validation');
    form.addEventListener('submit', function(event) {
        if (!form.checkValidity()) {
            event.preventDefault();
            event.stopPropagation();
        }
        form.classList.add('was-validated');
    });
});
</script>
{% endblock %}
EOF

print_status "Erstelle Member Detail Template..."

# Member Detail Template
cat > templates/members/member_detail.html << 'EOF'
{% extends 'base.html' %}
{% load static %}

{% block title %}{{ member.full_name }} - Mitgliederverwaltung{% endblock %}

{% block breadcrumb %}
<nav aria-label="breadcrumb">
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="{% url 'members:dashboard' %}">Dashboard</a></li>
        <li class="breadcrumb-item"><a href="{% url 'members:member_list' %}">Mitglieder</a></li>
        <li class="breadcrumb-item active">{{ member.full_name }}</li>
    </ol>
</nav>
{% endblock %}

{% block content %}
<div class="row">
    <div class="col-12">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1 class="h3">
                <i class="fas fa-user me-2"></i>
                {{ member.full_name }}
                {% if not member.is_active %}
                    <span class="badge bg-secondary ms-2">Inaktiv</span>
                {% endif %}
            </h1>
            <div class="btn-group">
                <a href="{% url 'members:member_edit' member.pk %}" class="btn btn-primary">
                    <i class="fas fa-edit me-2"></i>Bearbeiten
                </a>
                <a href="{% url 'members:member_delete' member.pk %}" 
                   class="btn btn-danger"
                   onclick="return confirmDelete('{{ member.full_name }}')">
                    <i class="fas fa-trash me-2"></i>Löschen
                </a>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <!-- Mitgliederdaten -->
    <div class="col-lg-8">
        <div class="card shadow mb-4">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fas fa-info-circle me-2"></i>Mitgliederdaten
                </h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <h6 class="text-muted mb-3">Persönliche Daten</h6>
                        <table class="table table-borderless">
                            <tr>
                                <td class="fw-bold">Vorname:</td>
                                <td>{{ member.first_name }}</td>
                            </tr>
                            <tr>
                                <td class="fw-bold">Nachname:</td>
                                <td>{{ member.last_name }}</td>
                            </tr>
                            <tr>
                                <td class="fw-bold">Geburtsdatum:</td>
                                <td>{{ member.birth_date|date:"d.m.Y" }}</td>
                            </tr>
                            <tr>
                                <td class="fw-bold">Alter:</td>
                                <td>{{ member.age }} Jahre</td>
                            </tr>
                            <tr>
                                <td class="fw-bold">Personalnummer:</td>
                                <td>{{ member.personnel_number|default:"-" }}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <div class="col-md-6">
                        <h6 class="text-muted mb-3">Ausweis-Daten</h6>
                        <table class="table table-borderless">
                            <tr>
                                <td class="fw-bold">Ausgestellt am:</td>
                                <td>{{ member.issued_date|date:"d.m.Y" }}</td>
                            </tr>
                            <tr>
                                <td class="fw-bold">Gültig bis:</td>
                                <td>{{ member.valid_until|date:"d.m.Y" }}</td>
                            </tr>
                            <tr>
                                <td class="fw-bold">Status:</td>
                                <td>
                                    {% if member.is_card_expired %}
                                        <span class="badge bg-danger">Abgelaufen</span>
                                    {% elif member.expires_soon %}
                                        <span class="badge bg-warning">Läuft bald ab</span>
                                    {% else %}
                                        <span class="badge bg-success">Gültig</span>
                                    {% endif %}
                                </td>
                            </tr>
                            <tr>
                                <td class="fw-bold">Mitglied aktiv:</td>
                                <td>
                                    {% if member.is_active %}
                                        <span class="badge bg-success">Ja</span>
                                    {% else %}
                                        <span class="badge bg-secondary">Nein</span>
                                    {% endif %}
                                </td>
                            </tr>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- Meta-Informationen -->
        <div class="card shadow">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fas fa-history me-2"></i>Meta-Informationen
                </h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <p class="mb-2">
                            <strong>Erstellt am:</strong><br>
                            {{ member.created_at|date:"d.m.Y H:i" }}
                        </p>
                    </div>
                    <div class="col-md-6">
                        <p class="mb-2">
                            <strong>Zuletzt aktualisiert:</strong><br>
                            {{ member.updated_at|date:"d.m.Y H:i" }}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Profilbild und Aktionen -->
    <div class="col-lg-4">
        <div class="card shadow mb-4">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fas fa-image me-2"></i>Profilbild
                </h5>
            </div>
            <div class="card-body text-center">
                {% if member.profile_picture %}
                    <img src="{{ member.profile_picture.url }}" 
                         class="img-fluid rounded border" 
                         alt="Profilbild von {{ member.full_name }}"
                         style="max-width: 200px; max-height: 250px;">
                {% else %}
                    <div class="bg-light border rounded d-flex align-items-center justify-content-center" 
                         style="width: 200px; height: 250px; margin: 0 auto;">
                        <i class="fas fa-user fa-4x text-muted"></i>
                    </div>
                    <p class="text-muted mt-3">Kein Profilbild vorhanden</p>
                {% endif %}
            </div>
        </div>

        <!-- Schnellaktionen -->
        <div class="card shadow">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fas fa-bolt me-2"></i>Schnellaktionen
                </h5>
            </div>
            <div class="card-body">
                <div class="d-grid gap-2">
                    <a href="{% url 'members:member_edit' member.pk %}" class="btn btn-primary">
                        <i class="fas fa-edit me-2"></i>Bearbeiten
                    </a>
                    
                    {% if member.is_card_expired or member.expires_soon %}
                    <button class="btn btn-warning" onclick="renewCard()">
                        <i class="fas fa-redo me-2"></i>Ausweis verlängern
                    </button>
                    {% endif %}
                    
                    <button class="btn btn-info" onclick="printCard()">
                        <i class="fas fa-print me-2"></i>Ausweis drucken
                    </button>
                    
                    <hr>
                    
                    <a href="{% url 'members:member_list' %}" class="btn btn-secondary">
                        <i class="fas fa-arrow-left me-2"></i>Zurück zur Liste
                    </a>
                    
                    <a href="{% url 'members:member_delete' member.pk %}" 
                       class="btn btn-danger"
                       onclick="return confirmDelete('{{ member.full_name }}')">
                        <i class="fas fa-trash me-2"></i>Mitglied löschen
                    </a>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
function renewCard() {
    if (confirm('Ausweis für {{ member.full_name }} um 5 Jahre verlängern?')) {
        // Hier könnte eine AJAX-Anfrage implementiert werden
        showAlert('Funktion wird in einer zukünftigen Version implementiert.', 'info');
    }
}

function printCard() {
    showAlert('Druckfunktion wird mit Cardpresso-Integration implementiert.', 'info');
}
</script>
{% endblock %}
EOF

print_status "Erstelle Import Template..."

# Import Template
cat > templates/members/import.html << 'EOF'
{% extends 'base.html' %}
{% load static %}

{% block title %}Datenimport - Mitgliederverwaltung{% endblock %}

{% block breadcrumb %}
<nav aria-label="breadcrumb">
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="{% url 'members:dashboard' %}">Dashboard</a></li>
        <li class="breadcrumb-item active">Import</li>
    </ol>
</nav>
{% endblock %}

{% block content %}
<div class="row">
    <div class="col-12">
        <h1 class="h3 mb-4">
            <i class="fas fa-file-import me-2"></i>
            Datenimport
            <small class="text-muted">CSV oder Excel-Dateien</small>
        </h1>
    </div>
</div>

<div class="row">
    <div class="col-lg-8">
        <!-- Import Form -->
        <div class="card shadow mb-4">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fas fa-upload me-2"></i>Datei hochladen
                </h5>
            </div>
            <div class="card-body">
                <form method="post" enctype="multipart/form-data" id="import-form">
                    {% csrf_token %}
                    
                    <div class="mb-4">
                        <label for="{{ form.file.id_for_label }}" class="form-label">
                            {{ form.file.label }}
                        </label>
                        
                        <div class="file-upload-area" onclick="document.getElementById('{{ form.file.id_for_label }}').click()">
                            <div class="upload-content">
                                <i class="fas fa-cloud-upload-alt file-upload-icon"></i>
                                <h6 class="upload-text">Datei hier ablegen oder klicken zum Auswählen</h6>
                                <p class="text-muted mb-0">
                                    Unterstützte Formate: CSV, Excel (.xlsx, .xls)<br>
                                    Maximale Dateigröße: 10MB
                                </p>
                            </div>
                            <div class="file-preview"></div>
                        </div>
                        
                        {{ form.file }}
                        
                        {% if form.file.help_text %}
                            <div class="form-text">{{ form.file.help_text }}</div>
                        {% endif %}
                        {% if form.file.errors %}
                            <div class="text-danger mt-2">{{ form.file.errors.0 }}</div>
                        {% endif %}
                    </div>
                    
                    <div class="d-grid">
                        <button type="submit" class="btn btn-primary btn-lg">
                            <i class="fas fa-file-import me-2"></i>Daten importieren
                        </button>
                    </div>
                </form>
            </div>
        </div>

        <!-- Import-Verlauf -->
        {% if recent_imports %}
        <div class="card shadow">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fas fa-history me-2"></i>Letzte Imports
                </h5>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead class="table-light">
                            <tr>
                                <th>Datei</th>
                                <th>Datum</th>
                                <th>Erfolgreich</th>
                                <th>Fehler</th>
                                <th>Erfolgsquote</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for import_log in recent_imports %}
                            <tr>
                                <td>{{ import_log.filename }}</td>
                                <td>{{ import_log.imported_at|date:"d.m.Y H:i" }}</td>
                                <td>
                                    <span class="badge bg-success">{{ import_log.successful_imports }}</span>
                                </td>
                                <td>
                                    {% if import_log.failed_imports > 0 %}
                                        <span class="badge bg-danger">{{ import_log.failed_imports }}</span>
                                    {% else %}
                                        <span class="badge bg-secondary">0</span>
                                    {% endif %}
                                </td>
                                <td>
                                    <div class="progress" style="height: 20px;">
                                        <div class="progress-bar {% if import_log.success_rate >= 90 %}bg-success{% elif import_log.success_rate >= 70 %}bg-warning{% else %}bg-danger{% endif %}" 
                                             style="width: {{ import_log.success_rate }}%">
                                            {{ import_log.success_rate }}%
                                        </div>
                                    </div>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        {% endif %}
    </div>
    
    <!-- Anleitung -->
    <div class="col-lg-4">
        <div class="card shadow mb-4">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fas fa-info-circle me-2"></i>Anleitung
                </h5>
            </div>
            <div class="card-body">
                <h6>Unterstützte Spalten:</h6>
                <ul class="list-unstyled">
                    <li><i class="fas fa-check text-success me-2"></i><strong>Vorname</strong> (Pflicht)</li>
                    <li><i class="fas fa-check text-success me-2"></i><strong>Nachname</strong> (Pflicht)</li>
                    <li><i class="fas fa-check text-success me-2"></i><strong>Geburtsdatum</strong> (Pflicht)</li>
                    <li><i class="fas fa-minus text-warning me-2"></i><strong>Personalnummer</strong> (Optional)</li>
                    <li><i class="fas fa-minus text-warning me-2"></i><strong>Ausgestellt</strong> (Optional)</li>
                </ul>
                
                <hr>
                
                <h6>Formathinweise:</h6>
                <ul class="small text-muted">
                    <li>Geburtsdatum: TT.MM.JJJJ oder JJJJ-MM-TT</li>
                    <li>Erste Zeile sollte Spaltenüberschriften enthalten</li>
                    <li>Leere Zeilen werden ignoriert</li>
                    <li>Duplikate werden erkannt und übersprungen</li>
                </ul>
                
                <hr>
                
                <div class="d-grid">
                    <a href="{% static 'files/import_template.csv' %}" class="btn btn-outline-primary btn-sm">
                        <i class="fas fa-download me-2"></i>Vorlage herunterladen
                    </a>
                </div>
            </div>
        </div>

        <div class="card shadow">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fas fa-exclamation-triangle me-2"></i>Wichtige Hinweise
                </h5>
            </div>
            <div class="card-body">
                <div class="alert alert-warning">
                    <small>
                        <strong>Backup erstellen:</strong> Erstellen Sie vor dem Import ein Backup Ihrer Daten.
                    </small>
                </div>
                <div class="alert alert-info">
                    <small>
                        <strong>Große Dateien:</strong> Bei mehr als 1000 Einträgen kann der Import einige Minuten dauern.
                    </small>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('import-form');
    
    form.addEventListener('submit', function(e) {
        const fileInput = document.getElementById('{{ form.file.id_for_label }}');
        
        if (!fileInput.files.length) {
            e.preventDefault();
            showAlert('Bitte wählen Sie eine Datei zum Importieren aus.', 'warning');
            return;
        }
        
        // Loading indicator anzeigen
        showLoading();
        
        // Button deaktivieren
        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Importiere...';
    });
});
</script>
{% endblock %}
EOF

print_status "Erstelle Export Template..."

# Export Template
cat > templates/members/export.html << 'EOF'
{% extends 'base.html' %}
{% load static %}

{% block title %}Datenexport - Mitgliederverwaltung{% endblock %}

{% block breadcrumb %}
<nav aria-label="breadcrumb">
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="{% url 'members:dashboard' %}">Dashboard</a></li>
        <li class="breadcrumb-item active">Export</li>
    </ol>
</nav>
{% endblock %}

{% block content %}
<div class="row">
    <div class="col-12">
        <h1 class="h3 mb-4">
            <i class="fas fa-file-export me-2"></i>
            Datenexport
            <small class="text-muted">CSV oder Excel-Format</small>
        </h1>
    </div>
</div>

<div class="row justify-content-center">
    <div class="col-lg-6">
        <div class="card shadow">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="fas fa-download me-2"></i>Export-Optionen
                </h5>
            </div>
            <div class="card-body">
                <form method="post" id="export-form">
                    {% csrf_token %}
                    
                    <div class="mb-4">
                        <label for="{{ form.format.id_for_label }}" class="form-label">
                            <i class="fas fa-file me-2"></i>{{ form.format.label }}
                        </label>
                        {{ form.format }}
                    </div>
                    
                    <div class="mb-4">
                        <label for="{{ form.members.id_for_label }}" class="form-label">
                            <i class="fas fa-users me-2"></i>{{ form.members.label }}
                        </label>
                        {{ form.members }}
                    </div>
                    
                    <div class="mb-4">
                        <div class="form-check">
                            {{ form.include_images }}
                            <label class="form-check-label" for="{{ form.include_images.id_for_label }}">
                                <i class="fas fa-images me-2"></i>{{ form.include_images.label }}
                            </label>
                            {% if form.include_images.help_text %}
                                <div class="form-text">{{ form.include_images.help_text }}</div>
                            {% endif %}
                        </div>
                    </div>
                    
                    <div class="d-grid">
                        <button type="submit" class="btn btn-success btn-lg">
                            <i class="fas fa-download me-2"></i>Export starten
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('export-form');
    
    form.addEventListener('submit', function(e) {
        // Loading indicator anzeigen
        showLoading();
        
        // Button deaktivieren
        const submitBtn = form.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Exportiere...';
        
        // Nach 3 Sekunden wieder aktivieren (Download startet)
        setTimeout(() => {
            hideLoading();
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-download me-2"></i>Export starten';
        }, 3000);
    });
});
</script>
{% endblock %}
EOF

print_status "Erstelle Delete Confirmation Template..."

# Delete Confirmation Template
cat > templates/members/member_confirm_delete.html << 'EOF'
{% extends 'base.html' %}

{% block title %}Mitglied löschen - Mitgliederverwaltung{% endblock %}

{% block breadcrumb %}
<nav aria-label="breadcrumb">
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="{% url 'members:dashboard' %}">Dashboard</a></li>
        <li class="breadcrumb-item"><a href="{% url 'members:member_list' %}">Mitglieder</a></li>
        <li class="breadcrumb-item"><a href="{% url 'members:member_detail' object.pk %}">{{ object.full_name }}</a></li>
        <li class="breadcrumb-item active">Löschen</li>
    </ol>
</nav>
{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-lg-6">
        <div class="card shadow border-danger">
            <div class="card-header bg-danger text-white">
                <h5 class="mb-0">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Mitglied löschen
                </h5>
            </div>
            <div class="card-body">
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    <strong>Achtung:</strong> Diese Aktion kann nicht rückgängig gemacht werden!
                </div>
                
                <p class="lead">
                    Möchten Sie das Mitglied <strong>{{ object.full_name }}</strong> wirklich löschen?
                </p>
                
                <div class="row">
                    <div class="col-md-4 text-center mb-3">
                        {% if object.profile_picture %}
                            <img src="{{ object.profile_picture.url }}" 
                                 class="img-fluid rounded border" 
                                 style="max-width: 120px; max-height: 150px;"
                                 alt="{{ object.full_name }}">
                        {% else %}
                            <div class="bg-light border rounded d-flex align-items-center justify-content-center" 
                                 style="width: 120px; height: 150px; margin: 0 auto;">
                                <i class="fas fa-user fa-3x text-muted"></i>
                            </div>
                        {% endif %}
                    </div>
                    <div class="col-md-8">
                        <table class="table table-sm">
                            <tr>
                                <td><strong>Name:</strong></td>
                                <td>{{ object.full_name }}</td>
                            </tr>
                            <tr>
                                <td><strong>Geburtsdatum:</strong></td>
                                <td>{{ object.birth_date|date:"d.m.Y" }}</td>
                            </tr>
                            <tr>
                                <td><strong>Personalnummer:</strong></td>
                                <td>{{ object.personnel_number|default:"-" }}</td>
                            </tr>
                            <tr>
                                <td><strong>Erstellt am:</strong></td>
                                <td>{{ object.created_at|date:"d.m.Y" }}</td>
                            </tr>
                        </table>
                    </div>
                </div>
                
                <hr>
                
                <form method="post">
                    {% csrf_token %}
                    <div class="d-flex justify-content-between">
                        <a href="{% url 'members:member_detail' object.pk %}" class="btn btn-secondary">
                            <i class="fas fa-arrow-left me-2"></i>Abbrechen
                        </a>
                        <button type="submit" class="btn btn-danger">
                            <i class="fas fa-trash me-2"></i>Endgültig löschen
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
EOF

print_status "Erstelle CSV Import-Vorlage..."

# CSV Template erstellen
mkdir -p static/files
cat > static/files/import_template.csv << 'EOF'
Vorname,Nachname,Geburtsdatum,Personalnummer,Ausgestellt
Max,Mustermann,01.01.1990,12345,01.01.2024
Maria,Musterfrau,15.06.1985,,15.01.2024
EOF

print_success "Teil 4 abgeschlossen!"
echo ""
echo "Was wurde erstellt:"
echo "✓ Umfangreiche Forms mit Validierung"
echo "✓ Vollständige Views für alle CRUD-Operationen"
echo "✓ Import/Export-Funktionalität"
echo "✓ Alle erforderlichen Templates"
echo "✓ Member Detail, Form, Import und Export Templates"
echo "✓ CSV Import-Vorlage"
echo "✓ JavaScript für erweiterte Funktionalität"
echo ""
echo "Nächster Schritt:"
echo "bash install_part5.sh  # Finale Konfiguration und Tests"
EOF