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
    """Verarbeitung der Import-Datei mit korrekter Excel-Datumsbehandlung"""
    from datetime import datetime, date
    import re
    
    try:
        # Datei lesen mit korrekter Kodierung
        if file.name.endswith('.csv'):
            # Verschiedene Kodierungen probieren
            try:
                df = pd.read_csv(file, encoding='utf-8-sig')  # UTF-8 mit BOM
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(file, encoding='utf-8')
                except UnicodeDecodeError:
                    try:
                        df = pd.read_csv(file, encoding='iso-8859-1')
                    except UnicodeDecodeError:
                        df = pd.read_csv(file, encoding='cp1252')
        else:
            # Excel-Datei mit korrekter Datumsbehandlung
            # parse_dates=True für automatische Datumserkennung
            df = pd.read_excel(file, parse_dates=True)
        
        # Spalten normalisieren (Umlaute und Sonderzeichen berücksichtigen)
        df.columns = df.columns.str.strip()
        
        successful_imports = 0
        failed_imports = 0
        errors = []
        
        print(f"Import gestartet. Gefundene Spalten: {list(df.columns)}")
        
        # VERBESSERTE Datums-Konvertierungsfunktion
        def smart_date_conversion(date_value):
            """Intelligente Datumskonvertierung für verschiedene Formate - gibt IMMER ein date-Objekt zurück"""
            if pd.isna(date_value) or not date_value:
                return None
            
            # Fall 1: Bereits ein date-Objekt
            if isinstance(date_value, date):
                return date_value
            
            # Fall 2: pandas Timestamp - WICHTIGSTER FALL für Excel!
            if isinstance(date_value, pd.Timestamp):
                return date_value.date()
            
            # Fall 3: datetime-Objekt
            if isinstance(date_value, datetime):
                return date_value.date()
            
            # Fall 4: Python datetime-Objekt mit date() Methode
            if hasattr(date_value, 'date') and callable(getattr(date_value, 'date')):
                return date_value.date()
            
            # Fall 5: Excel Datum als Zahl (Serial Number)
            if isinstance(date_value, (int, float)) and 1 <= date_value <= 100000:
                try:
                    # Excel-Datum als Seriennummer (Tage seit 1900-01-01)
                    base_date = datetime(1899, 12, 30)  # Korrigiertes Basisdatum
                    excel_date = base_date + pd.Timedelta(days=date_value)
                    return excel_date.date()
                except:
                    pass
            
            # Fall 6: String-Wert
            date_str = str(date_value).strip()
            
            # Leerer String
            if not date_str or date_str.lower() in ['nan', 'none', 'null', '']:
                return None
            
            # Versuchsreihenfolge für verschiedene String-Formate:
            formats_to_try = [
                # ISO Format (höchste Priorität)
                '%Y-%m-%d',
                # Deutsches Format
                '%d.%m.%Y',
                '%d.%m.%y',
                # Amerikanisches Format (für Excel-Strings)
                '%m/%d/%Y',
                '%m/%d/%y',
                # Weitere Formate
                '%d/%m/%Y',
                '%d/%m/%y',
            ]
            
            for fmt in formats_to_try:
                try:
                    parsed_date = datetime.strptime(date_str, fmt).date()
                    
                    # 2-stellige Jahre korrigieren
                    if parsed_date.year < 1950:  # Vermutlich 20xx gemeint
                        parsed_date = parsed_date.replace(year=parsed_date.year + 100)
                    
                    return parsed_date
                except ValueError:
                    continue
            
            # Letzter Versuch mit pandas - aber IMMER .date() verwenden!
            try:
                # Amerikanisches Format probieren (MM/DD/YY)
                parsed_pd = pd.to_datetime(date_str, format='%m/%d/%y', errors='coerce')
                if not pd.isna(parsed_pd):
                    return parsed_pd.date()  # .date() hinzugefügt!
            except:
                pass
            
            try:
                # Deutsches Format probieren (DD.MM.YYYY)
                parsed_pd = pd.to_datetime(date_str, format='%d.%m.%Y', errors='coerce')
                if not pd.isna(parsed_pd):
                    return parsed_pd.date()  # .date() hinzugefügt!
            except:
                pass
            
            # Allgemeine pandas Konvertierung als letzter Ausweg
            try:
                parsed_pd = pd.to_datetime(date_str, errors='coerce')
                if not pd.isna(parsed_pd):
                    return parsed_pd.date()  # .date() hinzugefügt!
            except:
                pass
            
            print(f"WARNING: Konnte Datum nicht konvertieren: '{date_str}' (Typ: {type(date_value)})")
            return None
        
        for index, row in df.iterrows():
            try:
                member_data = {}
                
                # Grundlegende Datenfelder zuordnen
                basic_mapping = {
                    'Vorname': 'first_name',
                    'Nachname': 'last_name', 
                    'Geburtsdatum': 'birth_date',
                    'Personalnummer': 'personnel_number',
                    'Ausweisnummer_Praefix': 'card_number_prefix',
                    'Ausweisnummer-Präfix': 'card_number_prefix',
                    'Ausgestellt_am': 'issued_date',
                    'Ausgestellt am': 'issued_date',
                    'Gueltig_bis': 'valid_until',
                    'Gültig bis': 'valid_until',
                    'Manuelle_Gueltigkeit': 'manual_validity',
                    'Manuelle Gültigkeit': 'manual_validity',
                }
                
                for col in df.columns:
                    if col in basic_mapping and pd.notna(row[col]):
                        field_name = basic_mapping[col]
                        value = row[col]
                        
                        # Spezielle Behandlung für manual_validity
                        if field_name == 'manual_validity':
                            if isinstance(value, str):
                                member_data[field_name] = value.lower() in ['ja', 'yes', 'true', '1', 'wahr']
                            else:
                                member_data[field_name] = bool(value)
                        else:
                            member_data[field_name] = value
                
                # MITARBEITERTYP-BEHANDLUNG
                member_type_value = 'FF'  # Standard
                
                # 1. Prüfe zuerst Mitarbeitertyp_Code (hat Priorität)  
                if 'Mitarbeitertyp_Code' in df.columns and pd.notna(row['Mitarbeitertyp_Code']):
                    code_value = str(row['Mitarbeitertyp_Code']).upper().strip()
                    valid_types = ['BF', 'FF', 'JF', 'STADT', 'EXTERN', 'PRAKTIKANT']
                    if code_value in valid_types:
                        member_type_value = code_value

                # 2. Falls kein gültiger Code, prüfe Mitarbeitertyp (Text)
                if member_type_value == 'FF' and 'Mitarbeitertyp' in df.columns and pd.notna(row['Mitarbeitertyp']):
                    text_value = str(row['Mitarbeitertyp']).strip()
                    type_mapping = {
                        'Berufsfeuerwehr': 'BF',
                        'Freiwillige Feuerwehr': 'FF',
                        'Jugendfeuerwehr': 'JF', 
                        'Stadt': 'STADT',
                        'Extern': 'EXTERN',
                        'Praktikant': 'PRAKTIKANT'
                    }
                    if text_value in type_mapping:
                        member_type_value = type_mapping[text_value]

                member_data['member_type'] = member_type_value
                
                # Validierung der Pflichtfelder
                if not all(k in member_data for k in ['first_name', 'last_name']):
                    errors.append(f"Zeile {index + 2}: Vor- und Nachname sind Pflichtfelder")
                    failed_imports += 1
                    continue
                
                # GEBURTSDATUM MIT INTELLIGENTER KONVERTIERUNG
                if 'birth_date' in member_data:
                    raw_birth_date = member_data['birth_date']
                    converted_date = smart_date_conversion(raw_birth_date)
                    
                    print(f"Debug: Zeile {index+2} - '{member_data['first_name']} {member_data['last_name']}' - Geburtsdatum: '{raw_birth_date}' (Typ: {type(raw_birth_date)}) → {converted_date}")
                    
                    if converted_date:
                        # Sicherstellen, dass es ein Python date-Objekt ist
                        if not isinstance(converted_date, date):
                            print(f"ERROR: Konvertiertes Datum ist kein date-Objekt: {converted_date} (Typ: {type(converted_date)})")
                            errors.append(f"Zeile {index + 2}: Ungültiges Geburtsdatum: {raw_birth_date}")
                            failed_imports += 1
                            continue
                        
                        # WICHTIG: Datum SOFORT nach Konvertierung setzen
                        member_data['birth_date'] = converted_date
                        
                        # Validierung Geburtsdatum
                        birth_date = converted_date
                        today = date.today()
                        age = today.year - birth_date.year - (
                            (today.month, today.day) < (birth_date.month, birth_date.day)
                        )
                        
                        if age < 14:  # Jugendfeuerwehr ab 14
                            errors.append(f"Zeile {index + 2}: Mitglied muss mindestens 14 Jahre alt sein (Alter: {age})")
                            failed_imports += 1
                            continue
                        if age > 100:
                            errors.append(f"Zeile {index + 2}: Unplausibles Alter: {age} Jahre")
                            failed_imports += 1
                            continue
                        if birth_date > today:
                            errors.append(f"Zeile {index + 2}: Geburtsdatum kann nicht in der Zukunft liegen")
                            failed_imports += 1
                            continue
                    else:
                        errors.append(f"Zeile {index + 2}: Ungültiges Geburtsdatum: {raw_birth_date}")
                        failed_imports += 1
                        continue
                else:
                    errors.append(f"Zeile {index + 2}: Geburtsdatum fehlt")
                    failed_imports += 1
                    continue
                
                # Ausstellungsdatum nur setzen wenn vorhanden
                if 'issued_date' in member_data and member_data['issued_date']:
                    converted_issued = smart_date_conversion(member_data['issued_date'])
                    if converted_issued and isinstance(converted_issued, date):
                        member_data['issued_date'] = converted_issued
                    else:
                        # Ungültiges Datum -> entfernen
                        del member_data['issued_date']
                
                # Gültig bis Datum verarbeiten
                if 'valid_until' in member_data and member_data['valid_until']:
                    converted_valid = smart_date_conversion(member_data['valid_until'])
                    if converted_valid and isinstance(converted_valid, date):
                        member_data['valid_until'] = converted_valid
                    else:
                        del member_data['valid_until']
                
                # Ausweisnummer-Präfix validieren
                if 'card_number_prefix' in member_data:
                    valid_prefixes = ['FF', 'JF', '']
                    prefix_str = str(member_data['card_number_prefix']).upper().strip()
                    if prefix_str in valid_prefixes:
                        member_data['card_number_prefix'] = prefix_str
                    else:
                        member_data['card_number_prefix'] = ''
                
                # Prüfen auf Duplikate - NACH der Datumskonvertierung!
                # Sicherstellen, dass birth_date ein date-Objekt ist
                check_birth_date = member_data['birth_date']
                if not isinstance(check_birth_date, date):
                    print(f"ERROR: birth_date ist noch kein date-Objekt vor Duplikat-Check: {check_birth_date} (Typ: {type(check_birth_date)})")
                    errors.append(f"Zeile {index + 2}: Interner Fehler bei Datumskonvertierung")
                    failed_imports += 1
                    continue
                
                existing = Member.objects.filter(
                    first_name__iexact=member_data['first_name'],
                    last_name__iexact=member_data['last_name'],
                    birth_date=check_birth_date  # Jetzt garantiert ein date-Objekt
                ).first()
                
                if existing:
                    errors.append(f"Duplikat: {member_data['first_name']} {member_data['last_name']} ({member_data['birth_date']}) existiert bereits")
                    failed_imports += 1
                    continue
                
                # Ausweisnummer löschen wenn vorhanden (wird automatisch generiert)
                member_data.pop('card_number', None)
                
                # Debug-Ausgabe
                if successful_imports < 5:
                    print(f"Import {successful_imports + 1}: {member_data}")
                
                # Mitglied erstellen
                Member.objects.create(**member_data)
                successful_imports += 1
                
            except Exception as e:
                import traceback
                print(f"ERROR in row {index + 2}: {str(e)}")
                print(traceback.format_exc())
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
        import traceback
        print(f"CRITICAL ERROR: {str(e)}")
        print(traceback.format_exc())
        messages.error(request, f'Fehler beim Import: {str(e)}')
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
    """Download einer erweiterten Beispiel-CSV für den Import"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="import_vorlage.csv"'
    
    # UTF-8 BOM für Excel-Kompatibilität
    response.write('\ufeff')
    
    # Beispieldaten mit allen neuen Feldern
    template_data = [
        {
            'Vorname': 'Max',
            'Nachname': 'Mustermann',
            'Geburtsdatum': '01.01.1990',
            'Personalnummer': '12345',
            'Mitarbeitertyp_Code': 'BF',
            'Ausweisnummer_Praefix': '',  # BF bekommt keinen Präfix
            'Ausgestellt_am': '01.01.2024',
            'Manuelle_Gueltigkeit': 'Nein'
        },
        {
            'Vorname': 'Maria',
            'Nachname': 'Musterfrau',
            'Geburtsdatum': '15.06.1985',
            'Personalnummer': '',
            'Mitarbeitertyp_Code': 'FF',
            'Ausweisnummer_Praefix': 'FF',  # FF bekommt Präfix
            'Ausgestellt_am': '15.01.2024',
            'Manuelle_Gueltigkeit': 'Nein'
        },
        {
            'Vorname': 'Klaus',
            'Nachname': 'Schmidt',
            'Geburtsdatum': '22.03.1988',
            'Personalnummer': '67890',
            'Mitarbeitertyp_Code': 'STADT',
            'Ausweisnummer_Praefix': '',  # STADT bekommt keinen Präfix
            'Ausgestellt_am': '01.03.2024',
            'Manuelle_Gueltigkeit': 'Nein'
        },
        {
            'Vorname': 'Anna',
            'Nachname': 'Weber',
            'Geburtsdatum': '15.08.1995',
            'Personalnummer': '',
            'Mitarbeitertyp_Code': 'JF',
            'Ausweisnummer_Praefix': 'JF',  # JF bekommt Präfix
            'Ausgestellt_am': '01.03.2024',
            'Manuelle_Gueltigkeit': 'Nein'
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