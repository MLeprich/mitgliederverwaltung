from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import date, timedelta
import pandas as pd
import csv
import os
from .models import Member
from .forms import MemberForm, ImportForm

@login_required
def dashboard(request):
    today = date.today()
    expiry_threshold = today + timedelta(days=30)
    
    stats = {
        'total_members': Member.objects.count(),
        'active_members': Member.objects.filter(is_active=True).count(),
        'valid_cards': Member.objects.filter(is_active=True, valid_until__gt=today).count(),
        'expiring_soon': Member.objects.filter(
            is_active=True, 
            valid_until__gt=today,
            valid_until__lte=expiry_threshold
        ).count(),
        'expired_cards': Member.objects.filter(is_active=True, valid_until__lte=today).count(),
    }
    
    recent_members = Member.objects.filter(is_active=True).order_by('-created_at')[:5]
    expiring_members = Member.objects.filter(
        is_active=True,
        valid_until__lte=expiry_threshold
    ).order_by('valid_until')[:10]
    
    context = {
        'stats': stats,
        'recent_members': recent_members,
        'expiring_members': expiring_members,
    }
    return render(request, 'dashboard.html', context)

@login_required
def member_list(request):
    members = Member.objects.all()
    
    # Suche
    search = request.GET.get('search')
    if search:
        members = members.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(personnel_number__icontains=search)
        )
    
    # Status Filter
    status = request.GET.get('status')
    today = date.today()
    
    if status == 'active':
        members = members.filter(is_active=True)
    elif status == 'inactive':
        members = members.filter(is_active=False)
    elif status == 'expired':
        members = members.filter(valid_until__lte=today)
    elif status == 'expiring':
        expiry_threshold = today + timedelta(days=30)
        members = members.filter(valid_until__gt=today, valid_until__lte=expiry_threshold)
    
    # Sortierung
    sort = request.GET.get('sort', 'name')
    if sort == 'name':
        members = members.order_by('last_name', 'first_name')
    elif sort == 'created':
        members = members.order_by('-created_at')
    elif sort == 'valid_until':
        members = members.order_by('valid_until')
    
    # Pagination
    paginator = Paginator(members, 25)
    page = request.GET.get('page')
    members = paginator.get_page(page)
    
    return render(request, 'members/member_list.html', {'object_list': members})

@login_required
def member_add(request):
    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES)
        if form.is_valid():
            member = form.save()
            messages.success(request, f'Mitglied {member.full_name} wurde erfolgreich erstellt.')
            return redirect('members:member_detail', pk=member.pk)
    else:
        form = MemberForm()
    
    return render(request, 'members/member_form.html', {
        'form': form,
        'title': 'Neues Mitglied hinzufügen',
        'submit_text': 'Mitglied erstellen'
    })

@login_required
def member_detail(request, pk):
    member = get_object_or_404(Member, pk=pk)
    return render(request, 'members/member_detail.html', {'member': member})

@login_required
def member_edit(request, pk):
    member = get_object_or_404(Member, pk=pk)
    
    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES, instance=member)
        if form.is_valid():
            member = form.save()
            messages.success(request, f'Mitglied {member.full_name} wurde aktualisiert.')
            return redirect('members:member_detail', pk=member.pk)
    else:
        form = MemberForm(instance=member)
    
    return render(request, 'members/member_form.html', {
        'form': form,
        'object': member,
        'title': f'Mitglied bearbeiten: {member.full_name}',
        'submit_text': 'Änderungen speichern'
    })

@login_required
def member_delete(request, pk):
    member = get_object_or_404(Member, pk=pk)
    
    if request.method == 'POST':
        member_name = member.full_name
        member.delete()
        messages.success(request, f'Mitglied {member_name} wurde gelöscht.')
        return redirect('members:member_list')
    
    return render(request, 'members/member_confirm_delete.html', {'object': member})

@login_required
def import_data(request):
    if request.method == 'POST':
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            return process_import(request, form.cleaned_data['file'])
    else:
        form = ImportForm()
    
    return render(request, 'members/import.html', {'form': form})

def process_import(request, file):
    """Verarbeitung der Import-Datei"""
    try:
        # Datei lesen
        if file.name.endswith('.csv'):
            df = pd.read_csv(file, encoding='utf-8')
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
        
        successful_imports = 0
        failed_imports = 0
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
                    failed_imports += 1
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
                        failed_imports += 1
                        continue
                else:
                    errors.append(f"Zeile {index + 2}: Geburtsdatum fehlt")
                    failed_imports += 1
                    continue
                
                # Ausstellungsdatum setzen
                if 'issued_date' not in member_data:
                    member_data['issued_date'] = timezone.now().date()
                
                # Prüfen auf Duplikate
                existing = Member.objects.filter(
                    first_name__iexact=member_data['first_name'],
                    last_name__iexact=member_data['last_name'],
                    birth_date=member_data['birth_date']
                ).first()
                
                if existing:
                    errors.append(f"Duplikat: {member_data['first_name']} {member_data['last_name']} existiert bereits")
                    failed_imports += 1
                    continue
                
                # Mitglied erstellen
                Member.objects.create(**member_data)
                successful_imports += 1
                
            except Exception as e:
                errors.append(f"Zeile {index + 2}: {str(e)}")
                failed_imports += 1
        
        # Erfolgsmeldung
        if successful_imports > 0:
            messages.success(request, f'{successful_imports} Mitglieder erfolgreich importiert.')
        
        if failed_imports > 0:
            error_msg = f'{failed_imports} Einträge konnten nicht importiert werden:\n' + '\n'.join(errors[:10])
            if len(errors) > 10:
                error_msg += f'\n... und {len(errors) - 10} weitere Fehler'
            messages.error(request, error_msg)
        
        return redirect('members:import_data')
        
    except Exception as e:
        messages.error(request, f'Fehler beim Import: {str(e)}')
        return redirect('members:import_data')

@login_required
def export_data(request):
    """Export aller Mitglieder als CSV oder Excel"""
    format_type = request.GET.get('format', 'csv')
    
    # Alle Mitglieder holen
    members = Member.objects.all().order_by('last_name', 'first_name')
    
    # Daten für Export vorbereiten
    export_data = []
    for member in members:
        export_data.append({
            'Vorname': member.first_name,
            'Nachname': member.last_name,
            'Geburtsdatum': member.birth_date.strftime('%d.%m.%Y'),
            'Personalnummer': member.personnel_number or '',
            'Ausgestellt am': member.issued_date.strftime('%d.%m.%Y'),
            'Gültig bis': member.valid_until.strftime('%d.%m.%Y'),
            'Aktiv': 'Ja' if member.is_active else 'Nein',
            'Erstellt am': member.created_at.strftime('%d.%m.%Y %H:%M'),
        })
    
    today = date.today().strftime('%Y%m%d')
    
    if format_type == 'excel':
        # Excel Export
        df = pd.DataFrame(export_data)
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="mitglieder_{today}.xlsx"'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Mitglieder', index=False)
        
        messages.success(request, f'{len(export_data)} Mitglieder als Excel exportiert.')
        return response
    
    else:
        # CSV Export
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="mitglieder_{today}.csv"'
        
        writer = csv.DictWriter(response, fieldnames=export_data[0].keys() if export_data else [])
        writer.writeheader()
        writer.writerows(export_data)
        
        messages.success(request, f'{len(export_data)} Mitglieder als CSV exportiert.')
        return response

@login_required
def download_template(request):
    """Download einer Beispiel-CSV für den Import"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="import_vorlage.csv"'
    
    # Beispieldaten
    template_data = [
        {
            'Vorname': 'Max',
            'Nachname': 'Mustermann',
            'Geburtsdatum': '01.01.1990',
            'Personalnummer': '12345',
            'Ausgestellt': '01.01.2024'
        },
        {
            'Vorname': 'Maria',
            'Nachname': 'Musterfrau',
            'Geburtsdatum': '15.06.1985',
            'Personalnummer': '',
            'Ausgestellt': '15.01.2024'
        },
        {
            'Vorname': 'John',
            'Nachname': 'Doe',
            'Geburtsdatum': '22.03.1988',
            'Personalnummer': '67890',
            'Ausgestellt': ''
        }
    ]
    
    writer = csv.DictWriter(response, fieldnames=template_data[0].keys())
    writer.writeheader()
    writer.writerows(template_data)
    
    return response
