import os
import sqlite3
import shutil
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from members.models import Member

class Command(BaseCommand):
    help = 'Create Cardpresso-optimized SQLite database with correct image paths'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            default='cardpresso.sqlite',
            help='Output SQLite file for Cardpresso'
        )
        parser.add_argument(
            '--copy-images',
            action='store_true',
            help='Copy images to cardpresso_images folder'
        )
    
    def handle(self, *args, **options):
        output_path = options['output']
        copy_images = options['copy_images']
        
        # Lösche alte Datenbank
        if os.path.exists(output_path):
            os.remove(output_path)
        
        # Erstelle neue SQLite-Datenbank
        conn = sqlite3.connect(output_path)
        cursor = conn.cursor()
        
        # Cardpresso-optimierte Tabelle
        cursor.execute('''
            CREATE TABLE members (
                id INTEGER PRIMARY KEY,
                personalnummer TEXT,
                vorname TEXT,
                nachname TEXT,
                vollname TEXT,
                kartenprefix TEXT,
                kartennummer TEXT,
                vollkartennummer TEXT,
                mitgliedertyp TEXT,
                geburtsdatum TEXT,
                ausstellungsdatum TEXT,
                gueltig_bis TEXT,
                aktiv TEXT,
                foto_pfad TEXT,
                foto_dateiname TEXT,
                erstellt_am TEXT,
                aktualisiert_am TEXT
            )
        ''')
        
        # Bilder-Verzeichnis vorbereiten
        if copy_images:
            images_dir = 'cardpresso_images'
            if os.path.exists(images_dir):
                shutil.rmtree(images_dir)
            os.makedirs(images_dir, exist_ok=True)
        
        # Mitglieder exportieren
        self.stdout.write("🔄 Exportiere Mitglieder für Cardpresso...")
        
        exported_count = 0
        foto_count = 0
        
        for member in Member.objects.all():
            # Foto-Pfad verarbeiten (profile_picture statt photo!)
            foto_pfad = ""
            foto_dateiname = ""
            
            if member.profile_picture:
                if copy_images:
                    # Kopiere Bild in cardpresso_images/
                    original_path = member.profile_picture.path
                    if os.path.exists(original_path):
                        foto_dateiname = f"member_{member.id}_{os.path.basename(original_path)}"
                        new_path = os.path.join(images_dir, foto_dateiname)
                        shutil.copy2(original_path, new_path)
                        foto_pfad = os.path.abspath(new_path)
                        foto_count += 1
                    else:
                        self.stdout.write(f"⚠️  Foto nicht gefunden: {original_path}")
                else:
                    # Verwende vollständigen Pfad zur Original-Datei
                    if os.path.exists(member.profile_picture.path):
                        foto_pfad = os.path.abspath(member.profile_picture.path)
                        foto_dateiname = os.path.basename(member.profile_picture.path)
                        foto_count += 1
            
            # Vollname und Kartennummer zusammenstellen
            vollname = f"{member.first_name or ''} {member.last_name or ''}".strip()
            vollkartennummer = f"{member.card_number_prefix or ''}{member.card_number or ''}".strip()
            
            # Daten einfügen
            cursor.execute('''
                INSERT INTO members (
                    id, personalnummer, vorname, nachname, vollname,
                    kartenprefix, kartennummer, vollkartennummer, mitgliedertyp,
                    geburtsdatum, ausstellungsdatum, gueltig_bis, aktiv,
                    foto_pfad, foto_dateiname, erstellt_am, aktualisiert_am
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                member.id,
                member.personnel_number or '',
                member.first_name or '',
                member.last_name or '',
                vollname,
                member.card_number_prefix or '',
                member.card_number or '',
                vollkartennummer,
                member.get_member_type_display() if hasattr(member, 'get_member_type_display') else member.member_type,
                member.birth_date.strftime('%Y-%m-%d') if member.birth_date else '',
                member.issued_date.strftime('%Y-%m-%d') if member.issued_date else '',
                member.valid_until.strftime('%Y-%m-%d') if member.valid_until else '',
                'Ja' if member.is_active else 'Nein',
                foto_pfad,
                foto_dateiname,
                member.created_at.strftime('%Y-%m-%d %H:%M:%S') if member.created_at else '',
                member.updated_at.strftime('%Y-%m-%d %H:%M:%S') if member.updated_at else ''
            ))
            
            exported_count += 1
        
        conn.commit()
        conn.close()
        
        # Erfolgs-Meldung
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Cardpresso-Datenbank erstellt!\n"
                f"   📁 Datei: {os.path.abspath(output_path)}\n"
                f"   👥 {exported_count} Mitglieder exportiert\n"
                f"   📸 {foto_count} Fotos gefunden\n"
                f"   📸 Bilder {'kopiert' if copy_images else 'verlinkt'}\n\n"
                f"🎯 In Cardpresso verwenden:\n"
                f"   Tabelle: members\n"
                f"   Foto-Spalte: foto_pfad\n"
            )
        )
