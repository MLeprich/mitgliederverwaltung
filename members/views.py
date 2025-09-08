import base64
from django.urls import reverse
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
import tempfile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.conf import settings
import os
import re
import logging 
from django.core.files.base import ContentFile
from io import BytesIO
from PIL import Image
from .models import Member
from .forms import MemberForm, ImportForm
from django.db import transaction
import zipfile
import shutil
from django.http import FileResponse, HttpResponse
import sqlite3
from .views_image_assignment import image_assignment, search_members_api, assign_image_api

logger = logging.getLogger(__name__)


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
        
        # NEUE AUSWEIS-STATISTIKEN
        'members_with_pictures': Member.objects.filter(
            is_active=True,
            profile_picture__isnull=False
        ).exclude(profile_picture__exact='').count(),
        
        'pending_cards': Member.objects.filter(
            is_active=True,
            profile_picture__isnull=False,
            issued_date__isnull=True
        ).exclude(profile_picture__exact='').count(),
        
        'cards_created_today': Member.objects.filter(
            issued_date=today
        ).count(),
        
        'cards_created_this_week': Member.objects.filter(
            issued_date__gte=today - timedelta(days=7)
        ).count(),
        
        'cards_created_this_month': Member.objects.filter(
            issued_date__gte=today.replace(day=1)
        ).count(),
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
            member = form.save(commit=False)
            
            # Webcam-Daten verarbeiten falls vorhanden
            webcam_data = request.POST.get('webcam_data')
            if webcam_data and webcam_data.startswith('data:image'):
                try:
                    # Base64 zu Bilddatei konvertieren
                    image_file = process_webcam_image(webcam_data, member.first_name, member.last_name)
                    member.profile_picture = image_file
                    print(f"✅ Webcam-Bild verarbeitet für {member.full_name}")
                except Exception as e:
                    print(f"❌ Webcam-Bildverarbeitung fehlgeschlagen: {str(e)}")
                    messages.warning(request, f'Webcam-Bild konnte nicht verarbeitet werden: {str(e)}')
            
            member.save()
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
            member = form.save(commit=False)
            
            # Webcam-Daten verarbeiten falls vorhanden
            webcam_data = request.POST.get('webcam_data')
            if webcam_data and webcam_data.startswith('data:image'):
                try:
                    # Base64 zu Bilddatei konvertieren
                    image_file = process_webcam_image(webcam_data, member.first_name, member.last_name)
                    member.profile_picture = image_file
                    print(f"✅ Webcam-Bild aktualisiert für {member.full_name}")
                except Exception as e:
                    print(f"❌ Webcam-Bildverarbeitung fehlgeschlagen: {str(e)}")
                    messages.warning(request, f'Webcam-Bild konnte nicht verarbeitet werden: {str(e)}')
            
            member.save()
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

def process_webcam_image(data_url, first_name, last_name):
    """
    Konvertiert Base64 Webcam-Daten zu Django-Bilddatei
    
    Args:
        data_url: Base64 data URL vom Webcam-Capture
        first_name: Vorname für Dateinamen
        last_name: Nachname für Dateinamen
    
    Returns:
        ContentFile: Django-kompatible Bilddatei
    """
    try:
        # Data URL aufteilen (data:image/jpeg;base64,...)
        header, data = data_url.split(',', 1)
        
        # Base64 dekodieren
        image_data = base64.b64decode(data)
        
        # PIL Image erstellen
        image = Image.open(BytesIO(image_data))
        
        # Sicherstellen dass es RGB ist (für JPEG)
        if image.mode in ('RGBA', 'P', 'LA'):
            # Weißer Hintergrund für Transparenz
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Auf Dienstausweis-Format optimieren (267x400px)
        target_width = 267
        target_height = 400
        
        # Bereits die richtige Größe vom JavaScript, aber sicherheitshalber prüfen
        if image.size != (target_width, target_height):
            # Resize mit hochwertiger Interpolation
            image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        
        # In BytesIO speichern
        output = BytesIO()
        image.save(output, format='JPEG', quality=95, optimize=True, dpi=(300, 300))
        output.seek(0)
        
        # Dateiname generieren
        filename = f"{first_name.lower()}.{last_name.lower()}.webcam.jpg"
        
        # Django ContentFile erstellen
        return ContentFile(output.read(), name=filename)
        
    except Exception as e:
        print(f"❌ Fehler bei Webcam-Bildverarbeitung: {str(e)}")
        raise Exception(f"Webcam-Bild konnte nicht verarbeitet werden: {str(e)}")

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
    """CSV-Only Import - Einfach und zuverlässig mit korrigierter Datumsbehandlung"""
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
        
        # Verbesserte Datums-Konvertierung für CSV
        def parse_csv_date(date_str):
            """Robuste Datumskonvertierung - gibt echtes date-Objekt zurück"""
            if not date_str or str(date_str).strip() in ['', 'nan', 'None', 'null']:
                return None
            
            date_str = str(date_str).strip()
            print(f"    Datums-String: '{date_str}'")
            
            # Deutsche Formate probieren (häufigste in CSV)
            formats_to_try = [
                '%d.%m.%Y',      # 02.06.1977
                '%d.%m.%y',      # 02.06.77
                '%d/%m/%Y',      # 02/06/1977
                '%d/%m/%y',      # 02/06/77
                '%Y-%m-%d',      # 1977-06-02 (ISO)
                '%m/%d/%Y',      # 06/02/1977 (US)
                '%m/%d/%y',      # 06/02/77 (US)
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
                
                # Erweiterte Spaltenzuordnung für deine CSV
                field_mappings = {
                    'first_name': ['Vorname', 'vorname', 'First Name', 'FirstName'],
                    'last_name': ['Nachname', 'nachname', 'Last Name', 'LastName'],
                    'birth_date': ['Geburtsdatum', 'geburtsdatum', 'Birth Date', 'BirthDate'],
                    'personnel_number': ['Personalnummer', 'personalnummer', 'Personnel Number', 'PersonnelNumber'],
                    'member_type': ['Mitarbeitertyp_Code', 'Mitarbeitertyp Code', 'Member Type'],
                    'card_number_prefix': ['Ausweisnummer_Praefix', 'Ausweisnummer Praefix', 'Card Number Prefix'],
                    'issued_date': ['Ausgestellt_am', 'Ausgestellt am', 'Issued Date'],
                    'valid_until': ['Gueltig_bis', 'Gueltig bis', 'Valid Until'],
                    'manual_validity': ['Manuelle_Gueltigkeit', 'Manuelle Gueltigkeit', 'Manual Validity'],
                    'is_active': ['Aktiv', 'aktiv', 'Active', 'Is Active'],
                }
                
                # Felder zuordnen
                for field, possible_names in field_mappings.items():
                    for name in possible_names:
                        if name in row and row[name] and str(row[name]).strip():
                            value = str(row[name]).strip()
                            if value.lower() not in ['', 'nan', 'none', 'null']:
                                member_data[field] = value
                            break
                
                print(f"Gefundene Daten: {member_data}")
                
                # Pflichtfelder prüfen
                if not member_data.get('first_name') or not member_data.get('last_name'):
                    errors.append(f"Zeile {row_number}: Vor- und Nachname sind Pflichtfelder")
                    failed_imports += 1
                    continue
                
                # Geburtsdatum konvertieren - WICHTIG: Als date-Objekt speichern
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
                
                # Optional: Andere Datumsfelder konvertieren
                issued_date = None
                if member_data.get('issued_date'):
                    issued_date = parse_csv_date(member_data['issued_date'])
                
                valid_until = None
                if member_data.get('valid_until'):
                    valid_until = parse_csv_date(member_data['valid_until'])
                
                # Boolean-Felder konvertieren
                manual_validity = False
                if member_data.get('manual_validity'):
                    manual_validity = member_data['manual_validity'].lower() in ['ja', 'yes', 'true', '1']
                
                is_active = True  # Standard
                if member_data.get('is_active'):
                    is_active = member_data['is_active'].lower() in ['ja', 'yes', 'true', '1']
                
                # Member-Objekt erstellen mit ALLEN verfügbaren Daten
                final_data = {
                    'first_name': member_data['first_name'],
                    'last_name': member_data['last_name'],
                    'birth_date': birth_date,  # ✅ Echtes date-Objekt!
                    'member_type': member_type,
                    'personnel_number': member_data.get('personnel_number') or None,
                    'card_number_prefix': member_data.get('card_number_prefix', ''),
                    'issued_date': issued_date,  # ✅ Echtes date-Objekt oder None!
                    'valid_until': valid_until,  # ✅ Echtes date-Objekt oder None!
                    'manual_validity': manual_validity,
                    'is_active': is_active,
                }
                
                print(f"  Finale Daten: {final_data}")
                print(f"  Geburtsdatum Typ: {type(final_data['birth_date'])}")
                
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
        
    except Exception as e:
        import traceback
        print(f"❌ KRITISCHER FEHLER beim CSV-Import: {str(e)}")
        print(traceback.format_exc())
        messages.error(request, f'Kritischer Fehler beim Import: {str(e)}')
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
def export_cardpresso_selected(request):
    """
    Exportiert ausgewählte Mitglieder als CardPresso ZIP - VEREINFACHT
    """
    if request.method != 'POST':
        messages.error(request, 'Ungültige Anfrage.')
        return redirect('members:card_creation_list')
    
    # Hole ausgewählte Mitglieder-IDs
    selected_ids = request.POST.getlist('selected_members[]')
    
    if not selected_ids:
        messages.error(request, 'Keine Mitglieder ausgewählt.')
        return redirect('members:card_creation_list')
    
    try:
        # Lade Mitglieder
        members = Member.objects.filter(
            id__in=selected_ids,
            is_active=True,
            profile_picture__isnull=False
        ).exclude(profile_picture__exact='')
        
        if not members.exists():
            messages.error(request, 'Keine gültigen Mitglieder gefunden.')
            return redirect('members:card_creation_list')
        
        # Erstelle temporäre Verzeichnisse
        temp_dir = tempfile.mkdtemp()
        cardpresso_dir = os.path.join(temp_dir, 'cardpresso_export')
        database_dir = os.path.join(cardpresso_dir, 'database')
        images_dir = os.path.join(cardpresso_dir, 'images')
        
        os.makedirs(database_dir, exist_ok=True)
        os.makedirs(images_dir, exist_ok=True)
        
        # SQLite Datenbank erstellen
        db_path = os.path.join(database_dir, 'cardpresso.sqlite')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Tabelle erstellen mit ALLEN wichtigen Feldern
        cursor.execute('''
            CREATE TABLE members (
                id INTEGER PRIMARY KEY,
                personalnummer TEXT,
                vorname TEXT,
                nachname TEXT,
                vollname TEXT,
                geburtsdatum TEXT,
                ausweisnummer TEXT,
                kartenprefix TEXT,
                kartennummer TEXT,
                ausstellungsdatum TEXT,
                gueltig_bis TEXT,
                mitgliedertyp TEXT,
                aktiv TEXT,
                photo TEXT
            )
        ''')
        
        # Mitglieder exportieren
        foto_count = 0
        for member in members:
            photo_name = ""
            
            # Foto kopieren
            if member.profile_picture and os.path.exists(member.profile_picture.path):
                original_filename = os.path.basename(member.profile_picture.path)
                photo_name = os.path.splitext(original_filename)[0]
                
                try:
                    shutil.copy2(member.profile_picture.path, 
                                os.path.join(images_dir, original_filename))
                    foto_count += 1
                except Exception as e:
                    print(f"Fehler beim Kopieren: {e}")
            
            # In DB einfügen mit ALLEN Feldern
            vollname = f"{member.first_name or ''} {member.last_name or ''}".strip()
            ausweisnummer = f"{member.card_number_prefix or ''}{member.card_number or ''}".strip()
            
            cursor.execute('''
                INSERT INTO members 
                (id, personalnummer, vorname, nachname, vollname, geburtsdatum,
                 ausweisnummer, kartenprefix, kartennummer, ausstellungsdatum, 
                 gueltig_bis, mitgliedertyp, aktiv, photo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                member.id,
                member.personnel_number or '',
                member.first_name or '',
                member.last_name or '',
                vollname,
                member.birth_date.strftime('%d.%m.%Y') if member.birth_date else '',
                ausweisnummer,
                member.card_number_prefix or '',
                member.card_number or '',
                member.issued_date.strftime('%d.%m.%Y') if member.issued_date else '',
                member.valid_until.strftime('%d.%m.%Y') if member.valid_until else '',
                member.get_member_type_display() if hasattr(member, 'get_member_type_display') else member.member_type,
                'JA' if member.is_active else 'NEIN',
                photo_name
            ))
        
        conn.commit()
        conn.close()
        
        # ZIP-Archiv erstellen
        zip_filename = f'cardpresso_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        zip_path = os.path.join(temp_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(cardpresso_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
        
        # Datei lesen und Response erstellen
        with open(zip_path, 'rb') as f:
            zip_data = f.read()
        
        # Aufräumen
        shutil.rmtree(temp_dir)
        
        # HTTP Response mit ZIP-Datei
        response = HttpResponse(zip_data, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        response['Content-Length'] = len(zip_data)
        
        return response
        
    except Exception as e:
        logger.error(f"CardPresso Export Fehler: {str(e)}")
        messages.error(request, f'Fehler beim Export: {str(e)}')
        return redirect('members:card_creation_list')

@login_required
def download_cardpresso_zip(request):
    """Download der in der Session gespeicherten CardPresso ZIP-Datei"""
    zip_path = request.session.get('cardpresso_zip_path')
    zip_filename = request.session.get('cardpresso_zip_filename')
    
    if not zip_path or not os.path.exists(zip_path):
        messages.error(request, 'Keine CardPresso-Datei zum Download verfügbar.')
        return redirect('members:card_creation_list')
    
    try:
        response = FileResponse(
            open(zip_path, 'rb'),
            content_type='application/zip'
        )
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        
        # Session-Daten löschen nach Download
        del request.session['cardpresso_zip_path']
        del request.session['cardpresso_zip_filename']
        if 'cardpresso_member_count' in request.session:
            del request.session['cardpresso_member_count']
        if 'cardpresso_foto_count' in request.session:
            del request.session['cardpresso_foto_count']
        
        # Temporäre Datei nach Download löschen
        def cleanup():
            try:
                if os.path.exists(zip_path):
                    os.remove(zip_path)
                    # Auch das temp-Verzeichnis löschen
                    temp_dir = os.path.dirname(zip_path)
                    if temp_dir and os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
            except:
                pass
        
        response.close_callback = cleanup
        return response
        
    except Exception as e:
        logger.error(f"Fehler beim CardPresso-Download: {str(e)}")
        messages.error(request, f'Fehler beim Download: {str(e)}')
        return redirect('members:card_creation_list')

@login_required
def export_cardpresso_db(request):
    """Erstellt CardPresso-Datenbank und bietet sie als ZIP-Download an"""
    try:
        # Temporäre Verzeichnisse erstellen
        temp_dir = tempfile.mkdtemp()
        cardpresso_dir = os.path.join(temp_dir, 'cardpresso_export')
        database_dir = os.path.join(cardpresso_dir, 'database')
        images_dir = os.path.join(cardpresso_dir, 'images')
        
        os.makedirs(database_dir, exist_ok=True)
        os.makedirs(images_dir, exist_ok=True)
        
        # Management Command ausführen
        from io import StringIO
        from django.core.management import call_command
        
        out = StringIO()
        call_command('create_cardpresso_db', 
                    output_dir=cardpresso_dir,
                    clean=True,
                    stdout=out)
        
        # ZIP-Archiv erstellen
        zip_filename = f'cardpresso_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        zip_path = os.path.join(temp_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Alle Dateien zum ZIP hinzufügen
            for root, dirs, files in os.walk(cardpresso_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
        
        # Datei zum Download anbieten
        response = FileResponse(
            open(zip_path, 'rb'),
            content_type='application/zip'
        )
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        
        # Aufräumen nach dem Response (wird automatisch gemacht)
        def cleanup():
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        
        response.close_callback = cleanup
        
        messages.success(request, 'CardPresso-Export wurde erfolgreich erstellt!')
        return response
        
    except Exception as e:
        logger.error(f"Fehler beim CardPresso-Export: {str(e)}")
        messages.error(request, f'Fehler beim Export: {str(e)}')
        return redirect('members:dashboard')
    
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

@login_required
def card_creation_list(request):
    """
    Zeigt alle Mitglieder an, die für die Ausweis-Erstellung bereit sind
    (haben Profilbild und sind aktiv)
    """
    # Nur aktive Mitglieder mit Profilbild
    eligible_members = Member.objects.filter(
        is_active=True,
        profile_picture__isnull=False
    ).exclude(
        profile_picture__exact=''
    ).order_by('last_name', 'first_name')
    
    # Filter nach Mitarbeitertyp
    member_type = request.GET.get('member_type')
    if member_type:
        eligible_members = eligible_members.filter(member_type=member_type)
    
    # Filter nach Status (bereits ausgestellte/nicht ausgestellte Ausweise)
    status = request.GET.get('status')
    today = date.today()
    
    if status == 'new':
        # Noch nie einen Ausweis bekommen
        eligible_members = eligible_members.filter(issued_date__isnull=True)
    elif status == 'renewal':
        # Bestehende Ausweise (für Verlängerung)
        eligible_members = eligible_members.filter(issued_date__isnull=False)
    elif status == 'expired':
        # Abgelaufene Ausweise
        eligible_members = eligible_members.filter(
            issued_date__isnull=False,
            valid_until__lte=today
        )
    elif status == 'expiring':
        # Bald ablaufende Ausweise (nächste 30 Tage)
        expiry_threshold = today + timedelta(days=30)
        eligible_members = eligible_members.filter(
            issued_date__isnull=False,
            valid_until__gt=today,
            valid_until__lte=expiry_threshold
        )
    
    # Suche
    search = request.GET.get('search')
    if search:
        eligible_members = eligible_members.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(personnel_number__icontains=search) |
            Q(card_number__icontains=search)
        )
    
    # Statistiken für die Anzeige
    stats = {
        'total_eligible': Member.objects.filter(
            is_active=True,
            profile_picture__isnull=False
        ).exclude(profile_picture__exact='').count(),
        'new_cards': Member.objects.filter(
            is_active=True,
            profile_picture__isnull=False,
            issued_date__isnull=True
        ).exclude(profile_picture__exact='').count(),
        'renewal_cards': Member.objects.filter(
            is_active=True,
            profile_picture__isnull=False,
            issued_date__isnull=False
        ).exclude(profile_picture__exact='').count(),
        'expired_cards': Member.objects.filter(
            is_active=True,
            profile_picture__isnull=False,
            valid_until__lte=today
        ).exclude(profile_picture__exact='').count(),
        'expiring_cards': Member.objects.filter(
            is_active=True,
            profile_picture__isnull=False,
            valid_until__gt=today,
            valid_until__lte=today + timedelta(days=30)
        ).exclude(profile_picture__exact='').count(),
    }
    
    context = {
        'eligible_members': eligible_members,
        'stats': stats,
        'current_filters': {
            'member_type': member_type or '',
            'status': status or '',
            'search': search or '',
        },
        # ✅ Füge diese Zeile hinzu:
        'eligible_member_ids': ','.join(str(m.id) for m in eligible_members),
        'today': date.today(),  # ✅ HINZUGEFÜGT für das Template
    }
    
    return render(request, 'members/card_creation_list.html', context)

@login_required
def card_creation_process(request):
    """
    Verarbeitet die ausgewählten Mitglieder für die Ausweis-Erstellung
    und erstellt automatisch eine Cardpresso-Datenbank
    """
    if request.method != 'POST':
        messages.error(request, 'Ungültige Anfrage.')
        return redirect('members:card_creation_list')
    
    selected_member_ids = request.POST.getlist('selected_members[]')
    # CardPresso wird erstellt wenn Checkbox vorhanden (standard: checked)
    create_cardpresso = 'create_cardpresso' in request.POST
    
    if not selected_member_ids:
        messages.error(request, 'Bitte wählen Sie mindestens ein Mitglied aus.')
        return redirect('members:card_creation_list')
    
    # Heute als Ausstellungsdatum
    issue_date = date.today()
    
    # Mitglieder laden und validieren
    members_to_update = Member.objects.filter(
        id__in=selected_member_ids,
        is_active=True,
        profile_picture__isnull=False
    ).exclude(profile_picture__exact='')
    
    if not members_to_update.exists():
        messages.error(request, 'Keine gültigen Mitglieder für die Ausweis-Erstellung gefunden.')
        return redirect('members:card_creation_list')
    
    # Batch-Update mit Transaktion
    updated_count = 0
    updated_members = []
    cardpresso_success = False
    cardpresso_path = None
    
    try:
        with transaction.atomic():
            for member in members_to_update:
                # Ausstellungsdatum setzen
                member.issued_date = issue_date
                
                # Gültigkeitsdatum automatisch berechnen (falls nicht manuell gesetzt)
                if not member.manual_validity:
                    if member.member_type in ['EXTERN', 'PRAKTIKANT']:
                        # Externe und Praktikanten: 1 Jahr
                        member.valid_until = issue_date + timedelta(days=365)
                    else:
                        # Reguläre Mitarbeiter: 5 Jahre
                        member.valid_until = issue_date + timedelta(days=5*365)
                
                member.save()
                updated_members.append(member)
                updated_count += 1
        
        # Erfolgsmeldung für Ausweis-Erstellung
        if updated_count == 1:
            messages.success(
                request, 
                f'Ausweis für {updated_members[0].full_name} wurde erfolgreich erstellt.'
            )
        else:
            messages.success(
                request, 
                f'{updated_count} Ausweise wurden erfolgreich erstellt.'
            )
        
        # Cardpresso-Datenbank erstellen wenn gewünscht
        print(f"DEBUG: CardPresso Option: {create_cardpresso}, POST data: {request.POST.get('create_cardpresso')}")
        logger.info(f"CardPresso Option: {create_cardpresso}, POST data: {request.POST.get('create_cardpresso')}")
        messages.info(request, f"CardPresso-Export: {'Ja' if create_cardpresso else 'Nein'}")
        if create_cardpresso:
            try:
                logger.info("Starte Cardpresso-Datenbank Erstellung für ausgewählte Mitglieder...")
                
                # Temporäre Verzeichnisse erstellen
                temp_dir = tempfile.mkdtemp()
                cardpresso_dir = os.path.join(temp_dir, 'cardpresso_export')
                database_dir = os.path.join(cardpresso_dir, 'database')
                images_dir = os.path.join(cardpresso_dir, 'images')
                
                os.makedirs(database_dir, exist_ok=True)
                os.makedirs(images_dir, exist_ok=True)
                
                # SQLite-Datenbank erstellen
                db_path = os.path.join(database_dir, 'cardpresso_selected.sqlite')
                
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Tabelle erstellen
                cursor.execute('''
                    CREATE TABLE members (
                        id INTEGER PRIMARY KEY,
                        personalnummer TEXT,
                        vorname TEXT,
                        nachname TEXT,
                        vollname TEXT,
                        telefon TEXT,
                        geburtsdatum TEXT,
                        ausweisnummer TEXT,
                        kartenprefix TEXT,
                        kartennummer TEXT,
                        ausstellungsdatum TEXT,
                        gueltig_bis TEXT,
                        mitgliedertyp TEXT,
                        aktiv TEXT,
                        photo TEXT
                    )
                ''')
                
                # Nur die ausgewählten Mitglieder exportieren
                foto_count = 0
                for member in updated_members:
                    photo_name = ""
                    
                    # Foto kopieren
                    if member.profile_picture and os.path.exists(member.profile_picture.path):
                        original_filename = os.path.basename(member.profile_picture.path)
                        photo_name = os.path.splitext(original_filename)[0]
                        
                        source_path = member.profile_picture.path
                        target_path = os.path.join(images_dir, original_filename)
                        
                        try:
                            shutil.copy2(source_path, target_path)
                            foto_count += 1
                        except Exception as e:
                            logger.error(f"Fehler beim Kopieren des Fotos: {e}")
                            photo_name = ""
                    
                    # Daten in SQLite einfügen
                    ausweisnummer = f"{member.card_number_prefix or ''}{member.card_number or ''}".strip()
                    vollname = f"{member.first_name or ''} {member.last_name or ''}".strip()
                    
                    cursor.execute('''
                        INSERT INTO members 
                        (id, personalnummer, vorname, nachname, vollname, telefon, geburtsdatum,
                         ausweisnummer, kartenprefix, kartennummer, ausstellungsdatum, gueltig_bis,
                         mitgliedertyp, aktiv, photo)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        member.id,
                        member.personnel_number or '',
                        member.first_name or '',
                        member.last_name or '',
                        vollname,
                        '',  # Telefon (nicht im Model)
                        member.birth_date.strftime('%d.%m.%Y') if member.birth_date else '',
                        ausweisnummer,
                        member.card_number_prefix or '',
                        member.card_number or '',
                        member.issued_date.strftime('%d.%m.%Y') if member.issued_date else '',
                        member.valid_until.strftime('%d.%m.%Y') if member.valid_until else '',
                        member.get_member_type_display() if hasattr(member, 'get_member_type_display') else member.member_type,
                        'JA' if member.is_active else 'NEIN',
                        photo_name
                    ))
                
                conn.commit()
                conn.close()
                
                # ZIP-Archiv erstellen
                zip_filename = f'cardpresso_ausweise_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
                zip_path = os.path.join(temp_dir, zip_filename)
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(cardpresso_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, temp_dir)
                            zipf.write(file_path, arcname)
                
                # Als Session-Variable speichern für Download
                request.session['cardpresso_zip_path'] = zip_path
                request.session['cardpresso_zip_filename'] = zip_filename
                request.session['cardpresso_member_count'] = updated_count
                request.session['cardpresso_foto_count'] = foto_count
                request.session.save()  # Explizit speichern
                
                cardpresso_success = True
                cardpresso_path = zip_path
                
                logger.info(f"Cardpresso-ZIP erstellt: {zip_path}")
                print(f"DEBUG: ZIP erstellt: {zip_path}, existiert: {os.path.exists(zip_path)}")
                
                messages.success(
                    request,
                    f'Cardpresso-Datenbank wurde erfolgreich erstellt! '
                    f'{updated_count} Mitglieder und {foto_count} Fotos exportiert.'
                )
                
                # Direkt die Datei zurückgeben statt Weiterleitung
                from django.http import FileResponse
                response = FileResponse(
                    open(zip_path, 'rb'),
                    content_type='application/zip'
                )
                response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
                return response
                
            except Exception as e:
                logger.error(f"Cardpresso Export Fehler: {e}")
                messages.warning(
                    request,
                    f'Ausweise wurden erstellt, aber Cardpresso-Export fehlgeschlagen: {str(e)}'
                )
        
        # Zur Übersicht weiterleiten mit zusätzlichen Parametern
        redirect_params = f"member_ids={','.join(str(m.id) for m in updated_members)}"
        if cardpresso_success and cardpresso_path:
            redirect_params += f"&cardpresso_path={cardpresso_path}"
        
        return redirect(f"{reverse('members:card_creation_summary')}?{redirect_params}")
    
    except Exception as e:
        logger.error(f"Fehler bei der Ausweis-Erstellung: {e}")
        messages.error(request, f'Fehler bei der Ausweis-Erstellung: {str(e)}')
        return redirect('members:card_creation_list')
        
        

@login_required
def card_creation_summary(request):
    """
    Zeigt eine Zusammenfassung der erstellten Ausweise mit Cardpresso-Info
    """
    member_ids = request.GET.get('member_ids', '')
    cardpresso_path = request.GET.get('cardpresso_path', '')
    
    if not member_ids:
        messages.error(request, 'Keine Mitglieder-IDs gefunden.')
        return redirect('members:card_creation_list')
    
    try:
        member_id_list = [int(id.strip()) for id in member_ids.split(',') if id.strip()]
        created_members = Member.objects.filter(id__in=member_id_list).order_by('last_name', 'first_name')
        
        if not created_members.exists():
            messages.error(request, 'Keine Mitglieder gefunden.')
            return redirect('members:card_creation_list')
        
        # Cardpresso-Info vorbereiten
        cardpresso_info = None
        # Prüfe ob ZIP in Session gespeichert ist
        if request.session.get('cardpresso_zip_path'):
            cardpresso_info = {
                'path': request.session.get('cardpresso_zip_path'),
                'is_zip': True,
                'member_count': request.session.get('cardpresso_member_count', 0),
                'foto_count': request.session.get('cardpresso_foto_count', 0),
                'ready_for_cardpresso': True
            }
        
        context = {
            'created_members': created_members,
            'creation_date': timezone.now().date(),
            'total_count': created_members.count(),
            'cardpresso_info': cardpresso_info,
        }
        
        return render(request, 'members/card_creation_summary.html', context)
        
    except ValueError:
        messages.error(request, 'Ungültige Mitglieder-IDs.')
        return redirect('members:card_creation_list')


# Neue AJAX-View für Cardpresso-Status
@login_required
def cardpresso_status(request):
    """
    AJAX-Endpoint für Cardpresso-Datenbank Status
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Nur GET erlaubt'}, status=405)
    
    try:
        # Letztes Cardpresso-Verzeichnis finden
        cardpresso_dirs = [d for d in os.listdir('.') if d.startswith('cardpresso_export_')]
        
        if not cardpresso_dirs:
            return JsonResponse({
                'exists': False,
                'message': 'Keine Cardpresso-Datenbank gefunden'
            })
        
        # Neuestes Verzeichnis
        latest_dir = sorted(cardpresso_dirs)[-1]
        db_path = os.path.join(latest_dir, 'database', 'cardpresso_indexed.sqlite')
        images_path = os.path.join(latest_dir, 'images')
        
        return JsonResponse({
            'exists': os.path.exists(db_path),
            'path': os.path.abspath(latest_dir),
            'db_path': os.path.abspath(db_path) if os.path.exists(db_path) else None,
            'images_count': len([f for f in os.listdir(images_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]) if os.path.exists(images_path) else 0,
            'created': os.path.getctime(latest_dir) if os.path.exists(latest_dir) else None
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Neue View für manuellen Cardpresso-Export
@login_required 
def create_cardpresso_manual(request):
    """
    Manuelle Cardpresso-Datenbank Erstellung (ohne Ausweis-Update)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Nur POST erlaubt'}, status=405)
    
    try:
        # Eindeutiges Ausgabeverzeichnis
        from django.utils import timezone
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"cardpresso_manual_{timestamp}"
        
        # Command aufrufen
        call_command(
            'create_cardpresso_db',
            output_dir=output_dir,
            clean=True,
            verbosity=1
        )
        
        cardpresso_path = os.path.abspath(output_dir)
        
        return JsonResponse({
            'success': True,
            'path': cardpresso_path,
            'message': f'Cardpresso-Datenbank erfolgreich erstellt: {cardpresso_path}'
        })
        
    except Exception as e:
        logger.error(f"Manueller Cardpresso-Export Fehler: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def check_member_eligibility(request, pk):
    """
    AJAX-Endpoint zur Überprüfung der Berechtigung eines Mitglieds für Ausweis-Erstellung
    """
    try:
        member = get_object_or_404(Member, pk=pk)
        
        # Berechtigung prüfen
        is_eligible = (
            member.is_active and 
            member.profile_picture and 
            bool(member.profile_picture.name)
        )
        
        # Grund für Nicht-Berechtigung
        issues = []
        if not member.is_active:
            issues.append('Mitglied ist inaktiv')
        if not member.profile_picture or not member.profile_picture.name:
            issues.append('Kein Profilbild vorhanden')
        
        # Bildqualität prüfen (optional)
        image_info = member.get_image_info() if member.profile_picture else None
        if image_info and 'error' in image_info:
            issues.append(f'Bildproblem: {image_info["error"]}')
        
        return JsonResponse({
            'eligible': is_eligible,
            'issues': issues,
            'member_name': member.full_name,
            'card_number': member.card_number,
            'member_type': member.get_member_type_display(),
            'has_existing_card': bool(member.issued_date),
            'existing_valid_until': member.valid_until.isoformat() if member.valid_until else None,
            'image_info': image_info
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

# ERWEITERE AUCH DEINE BESTEHENDE dashboard VIEW:
@login_required
def dashboard(request):
    today = date.today()
    expiry_threshold = today + timedelta(days=30)
    
    # Erweiterte Statistiken
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
        
        # ✨ NEUE AUSWEIS-STATISTIKEN
        'members_with_pictures': Member.objects.filter(
            is_active=True,
            profile_picture__isnull=False
        ).exclude(profile_picture__exact='').count(),
        
        'pending_cards': Member.objects.filter(
            is_active=True,
            profile_picture__isnull=False,
            issued_date__isnull=True
        ).exclude(profile_picture__exact='').count(),
    }
    
    # Rest deiner bestehenden Dashboard-Logik...
    # (member_types_data, recent_members, expiring_members, etc.)
    
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
    
    # Ablaufende Ausweise
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
