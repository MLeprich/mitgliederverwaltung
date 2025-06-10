# members/utils/cardpresso.py - Utility-Funktionen für Cardpresso-Integration

import os
import logging
import subprocess
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from datetime import datetime

logger = logging.getLogger(__name__)

class CardpressoManager:
    """Manager-Klasse für Cardpresso-Integration"""
    
    def __init__(self):
        self.base_dir = getattr(settings, 'CARDPRESSO_OUTPUT_DIR', '.')
        self.auto_create = getattr(settings, 'CARDPRESSO_AUTO_CREATE', True)
        self.clean_old = getattr(settings, 'CARDPRESSO_CLEAN_OLD', True)
        
    def create_database(self, member_ids=None, clean=True, custom_output=None):
        """
        Erstellt Cardpresso-Datenbank für spezifische Mitglieder oder alle
        
        Args:
            member_ids: Liste von Mitglieder-IDs (None = alle)
            clean: Alte Datenbank löschen
            custom_output: Benutzerdefiniertes Output-Verzeichnis
            
        Returns:
            dict: Ergebnis mit Pfaden und Statistiken
        """
        try:
            # Output-Verzeichnis bestimmen
            if custom_output:
                output_dir = custom_output
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if member_ids:
                    output_dir = f"cardpresso_batch_{timestamp}"
                else:
                    output_dir = f"cardpresso_full_{timestamp}"
            
            # Vollständiger Pfad
            full_output_path = os.path.join(self.base_dir, output_dir)
            
            logger.info(f"Erstelle Cardpresso-Datenbank: {full_output_path}")
            
            # Management Command mit Parametern aufrufen
            command_args = [
                'create_cardpresso_db',
                f'--output-dir={output_dir}',
            ]
            
            if clean:
                command_args.append('--clean')
            
            # Command ausführen und Output erfassen
            call_command(*command_args, verbosity=1)
            
            # Erfolg prüfen
            db_path = os.path.join(full_output_path, 'database', 'cardpresso_indexed.sqlite')
            images_path = os.path.join(full_output_path, 'images')
            
            if not os.path.exists(db_path):
                raise Exception("Datenbank wurde nicht erstellt")
            
            # Statistiken sammeln
            stats = self._collect_stats(full_output_path, db_path, images_path)
            
            logger.info(f"Cardpresso-Datenbank erfolgreich erstellt: {stats}")
            
            return {
                'success': True,
                'path': full_output_path,
                'db_path': db_path,
                'images_path': images_path,
                'stats': stats,
                'message': f'Cardpresso-Datenbank erfolgreich erstellt mit {stats["member_count"]} Mitgliedern'
            }
            
        except CommandError as e:
            logger.error(f"Cardpresso Command Error: {e}")
            return {
                'success': False,
                'error': f'Command-Fehler: {str(e)}',
                'type': 'command_error'
            }
            
        except Exception as e:
            logger.error(f"Unexpected Cardpresso Error: {e}")
            return {
                'success': False,
                'error': str(e),
                'type': 'unexpected_error'
            }
    
    def _collect_stats(self, base_path, db_path, images_path):
        """Sammelt Statistiken über die erstellte Datenbank"""
        import sqlite3
        
        stats = {
            'member_count': 0,
            'image_count': 0,
            'db_size_kb': 0,
            'total_size_kb': 0,
            'has_images': False,
            'created_at': datetime.now().isoformat()
        }
        
        try:
            # Datenbank-Statistiken
            if os.path.exists(db_path):
                stats['db_size_kb'] = round(os.path.getsize(db_path) / 1024, 2)
                
                # Mitglieder zählen
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM members")
                stats['member_count'] = cursor.fetchone()[0]
                conn.close()
            
            # Bilder zählen
            if os.path.exists(images_path):
                image_files = [f for f in os.listdir(images_path) 
                             if f.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff', '.bmp'))]
                stats['image_count'] = len(image_files)
                stats['has_images'] = len(image_files) > 0
            
            # Gesamtgröße berechnen
            total_size = 0
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    total_size += os.path.getsize(os.path.join(root, file))
            stats['total_size_kb'] = round(total_size / 1024, 2)
            
        except Exception as e:
            logger.warning(f"Fehler beim Sammeln der Statistiken: {e}")
        
        return stats
    
    def get_latest_database(self):
        """Findet die neueste Cardpresso-Datenbank"""
        try:
            cardpresso_dirs = [
                d for d in os.listdir(self.base_dir) 
                if d.startswith(('cardpresso_', 'cardpresso_export_', 'cardpresso_batch_', 'cardpresso_full_'))
                and os.path.isdir(os.path.join(self.base_dir, d))
            ]
            
            if not cardpresso_dirs:
                return None
            
            # Nach Datum sortieren (neuestes zuerst)
            cardpresso_dirs.sort(key=lambda x: os.path.getctime(os.path.join(self.base_dir, x)), reverse=True)
            latest_dir = cardpresso_dirs[0]
            
            full_path = os.path.join(self.base_dir, latest_dir)
            db_path = os.path.join(full_path, 'database', 'cardpresso_indexed.sqlite')
            images_path = os.path.join(full_path, 'images')
            
            if os.path.exists(db_path):
                return {
                    'path': full_path,
                    'db_path': db_path,
                    'images_path': images_path,
                    'exists': True,
                    'stats': self._collect_stats(full_path, db_path, images_path)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Fehler beim Suchen der neuesten Datenbank: {e}")
            return None
    
    def cleanup_old_databases(self, keep_count=3):
        """Löscht alte Cardpresso-Datenbanken (behält nur die neuesten)"""
        try:
            cardpresso_dirs = [
                d for d in os.listdir(self.base_dir) 
                if d.startswith(('cardpresso_', 'cardpresso_export_', 'cardpresso_batch_', 'cardpresso_full_'))
                and os.path.isdir(os.path.join(self.base_dir, d))
            ]
            
            if len(cardpresso_dirs) <= keep_count:
                return {'cleaned': 0, 'kept': len(cardpresso_dirs)}
            
            # Nach Datum sortieren (älteste zuerst)
            cardpresso_dirs.sort(key=lambda x: os.path.getctime(os.path.join(self.base_dir, x)))
            
            # Alte löschen
            to_delete = cardpresso_dirs[:-keep_count]
            cleaned_count = 0
            
            for dir_name in to_delete:
                dir_path = os.path.join(self.base_dir, dir_name)
                try:
                    import shutil
                    shutil.rmtree(dir_path)
                    cleaned_count += 1
                    logger.info(f"Alte Cardpresso-Datenbank gelöscht: {dir_path}")
                except Exception as e:
                    logger.warning(f"Konnte {dir_path} nicht löschen: {e}")
            
            return {'cleaned': cleaned_count, 'kept': len(cardpresso_dirs) - cleaned_count}
            
        except Exception as e:
            logger.error(f"Fehler beim Aufräumen alter Datenbanken: {e}")
            return {'cleaned': 0, 'kept': 0, 'error': str(e)}
    
    def open_cardpresso_application(self, database_path=None):
        """
        Versucht Cardpresso zu öffnen (falls installiert)
        Funktioniert nur auf dem lokalen System
        """
        try:
            cardpresso_paths = [
                r"C:\Program Files\Cardpresso\Cardpresso.exe",
                r"C:\Program Files (x86)\Cardpresso\Cardpresso.exe",
                "/Applications/Cardpresso.app/Contents/MacOS/Cardpresso",
                "/usr/bin/cardpresso",
                "/opt/cardpresso/cardpresso"
            ]
            
            cardpresso_exe = None
            for path in cardpresso_paths:
                if os.path.exists(path):
                    cardpresso_exe = path
                    break
            
            if not cardpresso_exe:
                return {
                    'success': False,
                    'error': 'Cardpresso nicht gefunden',
                    'type': 'not_found'
                }
            
            # Cardpresso starten
            cmd = [cardpresso_exe]
            if database_path and os.path.exists(database_path):
                cmd.extend(['--database', database_path])
            
            subprocess.Popen(cmd, start_new_session=True)
            
            return {
                'success': True,
                'message': 'Cardpresso gestartet',
                'application_path': cardpresso_exe
            }
            
        except Exception as e:
            logger.error(f"Fehler beim Starten von Cardpresso: {e}")
            return {
                'success': False,
                'error': str(e),
                'type': 'start_error'
            }


# Singleton Instance
cardpresso_manager = CardpressoManager()


# settings.py - Zusätzliche Einstellungen für Cardpresso
"""
# Füge diese Einstellungen zu deiner settings.py hinzu:

# Cardpresso Integration
CARDPRESSO_OUTPUT_DIR = BASE_DIR / 'cardpresso_exports'  # Wo Cardpresso-Exports gespeichert werden
CARDPRESSO_AUTO_CREATE = True  # Automatisch Cardpresso-DB bei Ausweis-Erstellung erstellen
CARDPRESSO_CLEAN_OLD = True    # Alte Exporte automatisch aufräumen
CARDPRESSO_KEEP_COUNT = 5      # Anzahl der zu behaltenden Export-Verzeichnisse
CARDPRESSO_AUTO_OPEN = False   # Versuchen Cardpresso automatisch zu öffnen (nur lokal)

# Logging für Cardpresso
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'cardpresso_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'cardpresso.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'members.utils.cardpresso': {
            'handlers': ['cardpresso_file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
"""


# members/signals.py - Automatische Cardpresso-Erstellung bei Ausweis-Updates
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Member
from .utils.cardpresso import cardpresso_manager
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Member)
def auto_create_cardpresso_on_card_update(sender, instance, created, **kwargs):
    '''
    Erstellt automatisch Cardpresso-DB wenn ein Ausweis aktualisiert wird
    '''
    # Nur bei Auto-Create und wenn issued_date gesetzt wurde
    if not getattr(settings, 'CARDPRESSO_AUTO_CREATE', False):
        return
    
    # Prüfen ob issued_date heute ist (frisch erstellt/aktualisiert)
    if instance.issued_date and instance.issued_date == timezone.now().date():
        try:
            logger.info(f'Auto-Creating Cardpresso DB for member {instance.id}')
            result = cardpresso_manager.create_database()
            
            if result['success']:
                logger.info(f'Cardpresso DB auto-created: {result["path"]}')
            else:
                logger.warning(f'Cardpresso auto-creation failed: {result["error"]}')
                
        except Exception as e:
            logger.error(f'Cardpresso auto-creation error: {e}')
"""