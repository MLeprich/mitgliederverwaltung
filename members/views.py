from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from datetime import date, datetime, timedelta 
import pandas as pd
import csv
import os
import re 
from .models import Member
from .forms import MemberForm, ImportForm

@login_required
def dashboard(request):
    today = date.today()
    expiry_threshold = today + timedelta(days=30)
    
    # Basis-Statistiken
    stats = {
        'total_members': Member.objects.count(),
        'active_members': Member.objects.filter(is_active=True).count(),
        'inactive_members': Member.objects.filter(is_active=False).count(),
        'valid_cards': Member.objects.filter(is_active=True, valid_until__gt=today).count(),
        'expiring_soon': Member.objects.filter(
            is_active=True, 
            valid_until__gt=today,
            valid_until__lte=expiry_threshold
        ).count(),
        'expired_cards': Member.objects.filter(is_active=True, valid_until__lte=today).count(),
        'members_with_cards': Member.objects.exclude(card_number='').count(),
        'manual_validity_count': Member.objects.filter(manual_validity=True).count(),
    }
    
    # Mitarbeitertypen-Statistiken
    member_types_data = Member.objects.values('member_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Icons für Mitarbeitertypen
    type_icons = {
        'BF': '🚒',
        'FF': '🔥',
        'JF': '👦',
        'STADT': '🏛️',
        'EXTERN': '🏢',
        'PRAKTIKANT': '🎓',
    }
    
    type_names = {
        'BF': 'Berufsfeuerwehr',
        'FF': 'Freiwillige Feuerwehr',
        'JF': 'Jugendfeuerwehr',
        'STADT': 'Stadt',
        'EXTERN': 'Extern',
        'PRAKTIKANT': 'Praktikant',
    }
    
    total_active = stats['active_members']
    member_types_stats = []
    
    for type_data in member_types_data:
        member_type = type_data['member_type']
        count = type_data['count']
        percentage = round((count / total_active * 100), 1) if total_active > 0 else 0
        
        member_types_stats.append({
            'type': member_type,
            'display_name': type_names.get(member_type, member_type),
            'icon': type_icons.get(member_type, '👤'),
            'count': count,
            'percentage': percentage
        })
    
    # Neueste Mitglieder
    recent_members = Member.objects.filter(is_active=True).order_by('-created_at')[:5]
    
    # Ablaufende Ausweise (mit Limit für Dashboard)
    expiring_members = Member.objects.filter(
        is_active=True,
        valid_until__lte=expiry_threshold
    ).order_by('valid_until')[:10]
    
    context = {
        'stats': stats,
        'member_types_stats': member_types_stats,
        'recent_members': recent_members,
        'expiring_members': expiring_members,
    }
    return render(request, 'dashboard.html', context)

@login_required
def member_list(request):
    members = Member.objects.all()
    
    # Suche (erweitert um Ausweisnummer)
    search = request.GET.get('search')
    if search:
        members = members.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(personnel_number__icontains=search) |
            Q(card_number__icontains=search)
        )
    
    # Mitarbeitertyp Filter
    member_type = request.GET.get('member_type')
    if member_type:
        members = members.filter(member_type=member_type)
    
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
    elif sort == 'card_number':
        members = members.order_by('card_number')
    
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
    """CSV-Only Import - Einfach und zuverlässig"""
    from datetime import datetime, date
    import csv
    import io
    
    try:
        # NUR CSV-Dateien verarbeiten
        if not file.name.endswith('.csv'):
            messages.error(request, 'Nur CSV-Dateien werden unterstützt. Bitte konvertieren Sie Ihre Excel-Datei zu CSV.')
            return redirect('members:import_data')
        
        # CSV mit verschiedenen Kodierungen probieren
        file_content = None
        encodings_to_try = ['utf-8-sig', 'utf-8', 'iso-8859-1', 'cp1252']
        
        for encoding in encodings_to_try:
            try:
                file.seek(0)  # Zurück zum Anfang
                file_content = file.read().decode(encoding)
                print(f"✅ Erfolgreich gelesen mit Kodierung: {encoding}")
                break
            except UnicodeDecodeError:
                continue
        
        if not file_content:
            messages.error(request, 'Datei konnte nicht gelesen werden. Bitte prüfen Sie die Kodierung.')
            return redirect('members:import_data')
        
        # CSV parsen
        csv_reader = csv.DictReader(io.StringIO(file_content))
        
        # Spalten normalisieren
        fieldnames = [col.strip() for col in csv_reader.fieldnames]
        
        successful_imports = 0
        failed_imports = 0
        errors = []
        
        print(f"CSV Import gestartet. Gefundene Spalten: {fieldnames}")
        
        # Einfache Datums-Konvertierung für CSV
        def parse_csv_date(date_str):
            """Einfache, robuste Datumskonvertierung für CSV-Strings"""
            if not date_str or str(date_str).strip() in ['', 'nan', 'None', 'null']:
                return None
            
            date_str = str(date_str).strip()
            print(f"    Datums-String: '{date_str}'")
            
            # Deutsche Formate probieren (häufigste in CSV)
            formats_to_try = [
                '%d.%m.%Y',      # 15.08.1989
                '%d.%m.%y',      # 15.08.89
                '%d/%m/%Y',      # 15/08/1989
                '%d/%m/%y',      # 15/08/89
                '%Y-%m-%d',      # 1989-08-15 (ISO)
                '%m/%d/%Y',      # 08/15/1989 (US)
                '%m/%d/%y',      # 08/15/89 (US)
            ]
            
            for fmt in formats_to_try:
                try:
                    parsed_date = datetime.strptime(date_str, fmt).date()
                    
                    # 2-stellige Jahre korrigieren
                    if parsed_date.year < 1950:
                        parsed_date = parsed_date.replace(year=parsed_date.year + 100)
                    
                    print(f"    ✅ Erfolgreich geparst mit Format {fmt}: {parsed_date}")
                    return parsed_date
                except ValueError:
                    continue
            
            print(f"    ❌ Konnte nicht geparst werden")
            return None
        
        row_number = 1  # Header ist Zeile 1
        
        for row in csv_reader:
            row_number += 1
            try:
                print(f"\n=== ZEILE {row_number} ===")
                
                # Daten aus CSV extrahieren
                member_data = {}
                
                # Grundlegende Felder mit verschiedenen möglichen Spaltennamen
                field_mappings = {
                    'first_name': ['Vorname', 'vorname', 'First Name', 'FirstName'],
                    'last_name': ['Nachname', 'nachname', 'Last Name', 'LastName'],
                    'birth_date': ['Geburtsdatum', 'geburtsdatum', 'Birth Date', 'BirthDate'],
                    'personnel_number': ['Personalnummer', 'personalnummer', 'Personnel Number', 'PersonnelNumber'],
                    'member_type': ['Mitarbeitertyp_Code', 'Mitarbeitertyp Code', 'Member Type'],
                }
                
                # Felder zuordnen
                for field, possible_names in field_mappings.items():
                    for name in possible_names:
                        if name in row and row[name] and str(row[name]).strip():
                            member_data[field] = str(row[name]).strip()
                            break
                
                print(f"Gefundene Daten: {member_data}")
                
                # Pflichtfelder prüfen
                if not member_data.get('first_name') or not member_data.get('last_name'):
                    errors.append(f"Zeile {row_number}: Vor- und Nachname sind Pflichtfelder")
                    failed_imports += 1
                    continue
                
                # Geburtsdatum konvertieren
                birth_date_str = member_data.get('birth_date')
                if not birth_date_str:
                    errors.append(f"Zeile {row_number}: Geburtsdatum fehlt")
                    failed_imports += 1
                    continue
                
                print(f"  Geburtsdatum roh: '{birth_date_str}'")
                birth_date = parse_csv_date(birth_date_str)
                
                if not birth_date:
                    errors.append(f"Zeile {row_number}: Ungültiges Geburtsdatum: '{birth_date_str}'")
                    failed_imports += 1
                    continue
                
                # Geburtsdatum validieren
                today = date.today()
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                
                if age < 14:
                    errors.append(f"Zeile {row_number}: Mitglied muss mindestens 14 Jahre alt sein (Alter: {age})")
                    failed_imports += 1
                    continue
                
                if age > 100:
                    errors.append(f"Zeile {row_number}: Unplausibles Alter: {age} Jahre")
                    failed_imports += 1
                    continue
                
                if birth_date > today:
                    errors.append(f"Zeile {row_number}: Geburtsdatum kann nicht in der Zukunft liegen")
                    failed_imports += 1
                    continue
                
                # Mitarbeitertyp bestimmen
                member_type = member_data.get('member_type', 'FF')
                
                # Text zu Code konvertieren falls nötig
                type_mapping = {
                    'Berufsfeuerwehr': 'BF',
                    'Freiwillige Feuerwehr': 'FF',
                    'Jugendfeuerwehr': 'JF',
                    'Stadt': 'STADT',
                    'Extern': 'EXTERN',
                    'Praktikant': 'PRAKTIKANT'
                }
                
                if member_type in type_mapping:
                    member_type = type_mapping[member_type]
                elif member_type.upper() in ['BF', 'FF', 'JF', 'STADT', 'EXTERN', 'PRAKTIKANT']:
                    member_type = member_type.upper()
                else:
                    member_type = 'FF'  # Standard
                
                # Duplikat-Prüfung
                existing = Member.objects.filter(
                    first_name__iexact=member_data['first_name'],
                    last_name__iexact=member_data['last_name'],
                    birth_date=birth_date
                ).first()
                
                if existing:
                    errors.append(f"Zeile {row_number}: Duplikat - {member_data['first_name']} {member_data['last_name']} ({birth_date}) existiert bereits")
                    failed_imports += 1
                    continue
                
                # Member-Objekt erstellen
                final_data = {
                    'first_name': member_data['first_name'],
                    'last_name': member_data['last_name'],
                    'birth_date': birth_date,
                    'member_type': member_type,
                    'personnel_number': member_data.get('personnel_number', ''),
                    'is_active': True,
                }
                
                # Leere Strings zu None konvertieren
                if not final_data['personnel_number']:
                    final_data['personnel_number'] = None
                
                print(f"  Finale Daten: {final_data}")
                
                # In Datenbank speichern
                new_member = Member.objects.create(**final_data)
                print(f"  ✅ Erfolgreich erstellt: {new_member}")
                
                successful_imports += 1
                
            except Exception as e:
                import traceback
                print(f"❌ FEHLER in Zeile {row_number}: {str(e)}")
                print(traceback.format_exc())
                errors.append(f"Zeile {row_number}: {str(e)}")
                failed_imports += 1
        
        # Ergebnisse anzeigen
        if successful_imports > 0:
            messages.success(request, f'{successful_imports} Mitglieder erfolgreich importiert.')
        
        if failed_imports > 0:
            error_msg = f'{failed_imports} Einträge konnten nicht importiert werden:\n'
            error_msg += '\n'.join(errors[:10])
            if len(errors) > 10:
                error_msg += f'\n... und {len(errors) - 10} weitere Fehler'
            messages.error(request, error_msg)
        
        return redirect('members:import_data')

@login_required
def export_data(request):
    """Export aller Mitglieder als CSV oder Excel"""
    format_type = request.GET.get('format', 'csv')
    
    # Filter aus Request übernehmen
    members = Member.objects.all().order_by('last_name', 'first_name')
    
    # Suchfilter anwenden wenn vorhanden
    search = request.GET.get('search')
    if search:
        members = members.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(personnel_number__icontains=search) |
            Q(card_number__icontains=search)
        )
    
    member_type = request.GET.get('member_type')
    if member_type:
        members = members.filter(member_type=member_type)
    
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
    
    # Daten für Export vorbereiten
    export_data = []
    for member in members:
        export_data.append({
            'Vorname': member.first_name,
            'Nachname': member.last_name,
            'Geburtsdatum': member.birth_date.strftime('%d.%m.%Y'),
            'Personalnummer': member.personnel_number or '',
            'Mitarbeitertyp': member.get_member_type_display(),
            'Mitarbeitertyp_Code': member.member_type,  # Für Re-Import
            'Ausweisnummer': member.card_number,
            'Ausweisnummer_Praefix': member.card_number_prefix or '',
            'Ausgestellt_am': member.issued_date.strftime('%d.%m.%Y') if member.issued_date else '',
            'Gueltig_bis': member.valid_until.strftime('%d.%m.%Y') if member.valid_until else '',
            'Manuelle_Gueltigkeit': 'Ja' if member.manual_validity else 'Nein',
            'Aktiv': 'Ja' if member.is_active else 'Nein',
            'Erstellt_am': member.created_at.strftime('%d.%m.%Y %H:%M'),
        })
    
    today_str = date.today().strftime('%Y%m%d')
    
    if format_type == 'excel':
        # Excel Export
        df = pd.DataFrame(export_data)
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="mitglieder_{today_str}.xlsx"'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Mitglieder', index=False)
        
        return response
    
    else:
        # CSV Export mit korrekter UTF-8 Kodierung
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="mitglieder_{today_str}.csv"'
        
        # UTF-8 BOM hinzufügen für Excel-Kompatibilität
        response.write('\ufeff')
        
        if export_data:
            writer = csv.DictWriter(response, fieldnames=export_data[0].keys())
            writer.writeheader()
            writer.writerows(export_data)
        
        return response

@login_required
def download_template(request):
    """Download einer CSV-Vorlage für den Import"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="import_vorlage.csv"'
    
    # UTF-8 BOM für Excel-Kompatibilität
    response.write('\ufeff')
    
    # Beispieldaten mit klaren deutschen Spaltennamen
    template_data = [
        {
            'Vorname': 'Max',
            'Nachname': 'Mustermann',
            'Geburtsdatum': '01.01.1990',
            'Personalnummer': '12345',
            'Mitarbeitertyp_Code': 'BF',
        },
        {
            'Vorname': 'Maria',
            'Nachname': 'Musterfrau',
            'Geburtsdatum': '15.06.1985',
            'Personalnummer': '',
            'Mitarbeitertyp_Code': 'FF',
        },
        {
            'Vorname': 'Klaus',
            'Nachname': 'Schmidt',
            'Geburtsdatum': '22.03.1988',
            'Personalnummer': '67890',
            'Mitarbeitertyp_Code': 'STADT',
        },
        {
            'Vorname': 'Anna',
            'Nachname': 'Weber',
            'Geburtsdatum': '15.08.1995',
            'Personalnummer': '',
            'Mitarbeitertyp_Code': 'JF',
        }
    ]
    
    writer = csv.DictWriter(response, fieldnames=template_data[0].keys())
    writer.writeheader()
    writer.writerows(template_data)
    
    return response
    
@login_required
def member_list_valid(request):
    """Zeigt nur Mitglieder mit gültigen Ausweisen"""
    today = date.today()
    members = Member.objects.filter(
        is_active=True,
        valid_until__gt=today
    )
    
    context = _get_filtered_member_context(
        request, 
        members, 
        title="Gültige Ausweise",
        icon="fas fa-check-circle text-success",
        description="Mitglieder mit aktuell gültigen Ausweisen"
    )
    return render(request, 'members/member_list_filtered.html', context)

@login_required
def member_list_expiring(request):
    """Zeigt nur Mitglieder deren Ausweise bald ablaufen"""
    today = date.today()
    expiry_threshold = today + timedelta(days=30)
    
    members = Member.objects.filter(
        is_active=True,
        valid_until__gt=today,
        valid_until__lte=expiry_threshold
    )
    
    context = _get_filtered_member_context(
        request,
        members,
        title="Laufen bald ab",
        icon="fas fa-exclamation-triangle text-warning", 
        description="Ausweise die in den nächsten 30 Tagen ablaufen"
    )
    return render(request, 'members/member_list_filtered.html', context)

@login_required
def member_list_expired(request):
    """Zeigt nur Mitglieder mit abgelaufenen Ausweisen"""
    today = date.today()
    members = Member.objects.filter(
        is_active=True,
        valid_until__lte=today
    )
    
    context = _get_filtered_member_context(
        request,
        members,
        title="Abgelaufene Ausweise",
        icon="fas fa-times-circle text-danger",
        description="Mitglieder mit abgelaufenen Ausweisen"
    )
    return render(request, 'members/member_list_filtered.html', context)

@login_required
def member_list_active(request):
    """Zeigt nur aktive Mitglieder"""
    members = Member.objects.filter(is_active=True)
    
    context = _get_filtered_member_context(
        request,
        members,
        title="Aktive Mitglieder",
        icon="fas fa-users text-primary",
        description="Alle aktiven Mitglieder"
    )
    return render(request, 'members/member_list_filtered.html', context)

@login_required
def member_list_inactive(request):
    """Zeigt nur inaktive Mitglieder"""
    members = Member.objects.filter(is_active=False)
    
    context = _get_filtered_member_context(
        request,
        members,
        title="Inaktive Mitglieder", 
        icon="fas fa-user-slash text-secondary",
        description="Alle inaktiven Mitglieder"
    )
    return render(request, 'members/member_list_filtered.html', context)

def _get_filtered_member_context(request, base_queryset, title, icon, description):
    """Hilfsfunktion für gefilterte Mitgliederansichten mit Suche und Pagination"""
    
    members = base_queryset
    
    # Suche (erweitert um Ausweisnummer)
    search = request.GET.get('search')
    if search:
        members = members.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(personnel_number__icontains=search) |
            Q(card_number__icontains=search)
        )
    
    # Mitarbeitertyp Filter
    member_type = request.GET.get('member_type')
    if member_type:
        members = members.filter(member_type=member_type)
    
    # Sortierung
    sort = request.GET.get('sort', 'name')
    if sort == 'name':
        members = members.order_by('last_name', 'first_name')
    elif sort == 'created':
        members = members.order_by('-created_at')
    elif sort == 'valid_until':
        members = members.order_by('valid_until')
    elif sort == 'card_number':
        members = members.order_by('card_number')
    
    # Pagination
    paginator = Paginator(members, 25)
    page = request.GET.get('page')
    members_page = paginator.get_page(page)
    
    return {
        'object_list': members_page,
        'title': title,
        'icon': icon,
        'description': description,
        'total_count': base_queryset.count(),
        'search_value': search or '',
        'member_type_value': member_type or '',
        'sort_value': sort,
    }

@login_required
def image_quality_check(request, pk):
    """Debug-View um Bildqualität zu überprüfen"""
    member = get_object_or_404(Member, pk=pk)
    
    image_info = member.get_image_info()
    
    context = {
        'member': member,
        'image_info': image_info,
        'requirements': {
            'width': 267,
            'height': 400,
            'dpi': 300,
            'format': 'JPEG',
            'quality': 'Hoch (95%+)',
        }
    }
    
    return render(request, 'members/image_debug.html', context)