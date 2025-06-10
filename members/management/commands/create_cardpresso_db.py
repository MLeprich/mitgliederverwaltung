# members/management/commands/create_cardpresso_db.py

import os
import sqlite3
import shutil
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from members.models import Member

class Command(BaseCommand):
    help = 'Erstellt erweiterte Cardpresso-SQLite-Datenbank mit korrekter Struktur'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            default='cardpresso_project',
            help='Output-Verzeichnis für Cardpresso-Projekt'
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Lösche existierendes Verzeichnis vor Erstellung'
        )
    
    def handle(self, *args, **options):
        output_dir = options['output_dir']
        clean = options['clean']
        
        self.stdout.write("🔄 Erstelle erweiterte Cardpresso-Datenbank...")
        
        # 1. Verzeichnisstruktur erstellen
        if clean and os.path.exists(output_dir):
            self.stdout.write(f"🗑️  Lösche existierendes Verzeichnis: {output_dir}")
            shutil.rmtree(output_dir)
        
        # Verzeichnisse erstellen
        database_dir = os.path.join(output_dir, 'database')
        images_dir = os.path.join(output_dir, 'images')
        
        os.makedirs(database_dir, exist_ok=True)
        os.makedirs(images_dir, exist_ok=True)
        
        self.stdout.write(f"📁 Verzeichnisse erstellt: {output_dir}")
        
        # 2. SQLite-Datenbank erstellen
        db_path = os.path.join(database_dir, 'cardpresso_indexed.sqlite')
        
        if os.path.exists(db_path):
            os.remove(db_path)
            self.stdout.write("🗑️  Alte Datenbank gelöscht")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 3. Erweiterte Tabelle mit ALLEN Spalten erstellen (GENAU WIE IM ORIGINAL)
        self.stdout.write("📊 Erstelle Tabelle mit erweiterter Struktur...")
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
        
        # 4. Mitglieder aus Django-Modell exportieren
        count = 0
        foto_count = 0
        
        self.stdout.write("👥 Exportiere Mitglieder...")
        
        try:
            for member in Member.objects.all():
                photo_name = ""
                
                # Foto-Verarbeitung (erweitert wie im Original)
                if member.profile_picture and os.path.exists(member.profile_picture.path):
                    original_filename = os.path.basename(member.profile_picture.path)
                    photo_name = os.path.splitext(original_filename)[0]
                    
                    source_path = member.profile_picture.path
                    target_path = os.path.join(images_dir, original_filename)
                    
                    try:
                        shutil.copy2(source_path, target_path)
                        foto_count += 1
                        self.stdout.write(f"📸 Foto kopiert: {original_filename}")
                    except Exception as e:
                        self.stdout.write(f"❌ Fehler bei {original_filename}: {e}")
                        photo_name = ""
                else:
                    # Suche nach Bildern im Format vorname.nachname (wie im Original)
                    if member.first_name and member.last_name:
                        possible_names = [
                            f"{member.first_name.lower()}.{member.last_name.lower()}",
                            f"{member.first_name}.{member.last_name}",
                        ]
                        
                        for base_name in possible_names:
                            for ext in ['.jpg', '.jpeg', '.png']:
                                test_filename = f"{base_name}{ext}"
                                # Prüfe in MEDIA_ROOT/profile_pics/
                                test_path = os.path.join(settings.MEDIA_ROOT, 'profile_pics', test_filename)
                                
                                if os.path.exists(test_path):
                                    photo_name = base_name
                                    target_path = os.path.join(images_dir, test_filename)
                                    
                                    try:
                                        shutil.copy2(test_path, target_path)
                                        foto_count += 1
                                        self.stdout.write(f"📸 Foto gefunden und kopiert: {test_filename}")
                                        break
                                    except Exception as e:
                                        self.stdout.write(f"❌ Fehler beim Kopieren von {test_filename}: {e}")
                            
                            if photo_name:
                                break
                
                # Vollständige Ausweisnummer erstellen (wie im Original)
                ausweisnummer = f"{member.card_number_prefix or ''}{member.card_number or ''}".strip()
                
                # Vollname erstellen
                vollname = f"{member.first_name or ''} {member.last_name or ''}".strip()
                
                # Daten in SQLite einfügen (ERWEITERT mit ALLEN Spalten wie im Original!)
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
                    '123-456-789',  # Dummy-Telefon (falls nicht vorhanden) - wie im Original
                    member.birth_date.strftime('%d.%m.%Y') if member.birth_date else '',
                    ausweisnummer,  # Vollständige Ausweisnummer
                    member.card_number_prefix or '',
                    member.card_number or '',
                    member.issued_date.strftime('%d.%m.%Y') if member.issued_date else '',
                    member.valid_until.strftime('%d.%m.%Y') if member.valid_until else '',
                    member.get_member_type_display() if hasattr(member, 'get_member_type_display') else member.member_type,
                    'JA' if member.is_active else 'NEIN',
                    photo_name
                ))
                count += 1
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Fehler beim Exportieren der Mitglieder: {e}"))
            conn.close()
            return
        
        conn.commit()
        
        # 5. Erfolgs-Meldung und Statistiken (wie im Original)
        self.stdout.write(self.style.SUCCESS(f"\n✅ Erweiterte Cardpresso-Datenbank erstellt!"))
        self.stdout.write(f"📊 {count} Mitglieder exportiert")
        self.stdout.write(f"📸 {foto_count} Fotos kopiert")
        
        # 6. Beispiel-Daten anzeigen (wie im Original)
        cursor.execute("""
            SELECT vollname, ausweisnummer, ausstellungsdatum, gueltig_bis, photo 
            FROM members 
            WHERE ausweisnummer != '' OR photo != '' 
            LIMIT 5
        """)
        
        self.stdout.write(f"\n📋 Beispiel-Daten:")
        self.stdout.write(f"{'Name':<20} {'Ausweis':<15} {'Ausgestellt':<12} {'Gültig bis':<12} {'Foto'}")
        self.stdout.write("-" * 80)
        
        for row in cursor.fetchall():
            name = (row[0] or '')[:19]
            ausweis = (row[1] or '')[:14] 
            ausgestellt = (row[2] or '')[:11]
            gueltig = (row[3] or '')[:11]
            foto = '✅' if row[4] else '❌'
            self.stdout.write(f"{name:<20} {ausweis:<15} {ausgestellt:<12} {gueltig:<12} {foto}")
        
        # 7. Statistiken (wie im Original)
        cursor.execute("SELECT COUNT(*) FROM members WHERE ausweisnummer != ''")
        mit_ausweis = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM members WHERE photo != ''")
        mit_foto = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM members WHERE gueltig_bis != ''")
        mit_gueltigkeitsdatum = cursor.fetchone()[0]
        
        self.stdout.write(f"\n📊 Statistiken:")
        self.stdout.write(f"  👤 Mitglieder gesamt: {count}")
        self.stdout.write(f"  🆔 Mit Ausweisnummer: {mit_ausweis}")
        self.stdout.write(f"  📸 Mit Foto: {mit_foto}")
        self.stdout.write(f"  📅 Mit Gültigkeitsdatum: {mit_gueltigkeitsdatum}")
        
        conn.close()
        
        # 8. Abschlussinformationen (wie im Original)
        self.stdout.write(self.style.SUCCESS(f"\n🎯 Cardpresso-Projekt bereit:"))
        self.stdout.write(f"   📁 Pfad: {os.path.abspath(output_dir)}/")
        self.stdout.write(f"   💾 Datenbank: database/cardpresso_indexed.sqlite")
        self.stdout.write(f"   🖼️  Bilder: images/")
        self.stdout.write(f"\n📋 Verfügbare Spalten für Cardpresso:")
        self.stdout.write(f"   - personalnummer")
        self.stdout.write(f"   - vorname, nachname, vollname")
        self.stdout.write(f"   - ausweisnummer (Vollständig)")
        self.stdout.write(f"   - kartenprefix, kartennummer (Einzeln)")
        self.stdout.write(f"   - ausstellungsdatum")
        self.stdout.write(f"   - gueltig_bis")
        self.stdout.write(f"   - mitgliedertyp")
        self.stdout.write(f"   - aktiv")
        self.stdout.write(f"   - photo (für Bildverknüpfung)")
        
        self.stdout.write(self.style.SUCCESS(f"\n🚀 Verwendung in Cardpresso:"))
        self.stdout.write(f"   1. Cardpresso öffnen")
        self.stdout.write(f"   2. Datenbank verbinden: {os.path.abspath(db_path)}")
        self.stdout.write(f"   3. Tabelle auswählen: members")
        self.stdout.write(f"   4. Spalten zuordnen nach Bedarf")
        self.stdout.write(f"   5. Bildpfad: {os.path.abspath(images_dir)}/")