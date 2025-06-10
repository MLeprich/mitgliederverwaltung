#!/bin/bash
# Installation Script Teil 5: Finale Konfiguration und Production Setup
# Ausführen mit: bash install_part5.sh

set -e

echo "=== Mitgliederverwaltung Dashboard - Teil 5: Finale Konfiguration ==="
echo ""

# Farben für Output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
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

print_status "Führe finale Migrationen durch..."

# Finale Migrationen
python manage.py makemigrations
python manage.py migrate

print_status "Sammle Static Files..."
python manage.py collectstatic --noinput

print_status "Erstelle Nginx Konfiguration..."

# Nginx Site Configuration
sudo tee /etc/nginx/sites-available/mitgliederverwaltung << 'EOF'
server {
    listen 80;
    server_name localhost;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    # Static files
    location /static/ {
        alias /home/pi/mitgliederverwaltung/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files
    location /media/ {
        alias /home/pi/mitgliederverwaltung/media/;
        expires 1y;
        add_header Cache-Control "public";
    }
    
    # Main application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        # File upload size
        client_max_body_size 10M;
    }
    
    # Health check
    location /health/ {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
EOF

print_status "Aktiviere Nginx Site..."

# Nginx Site aktivieren
sudo ln -sf /etc/nginx/sites-available/mitgliederverwaltung /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Nginx testen
sudo nginx -t

print_status "Erstelle Gunicorn Konfiguration..."

# Gunicorn Config
cat > gunicorn.conf.py << 'EOF'
# Gunicorn Configuration für Mitgliederverwaltung

bind = "127.0.0.1:8000"
workers = 3
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 5

# Logging
accesslog = "/home/pi/mitgliederverwaltung/logs/gunicorn-access.log"
errorlog = "/home/pi/mitgliederverwaltung/logs/gunicorn-error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "mitgliederverwaltung"

# Daemonize
daemon = False
pidfile = "/home/pi/mitgliederverwaltung/gunicorn.pid"

# User and group
user = "pi"
group = "pi"

# Preload application
preload_app = True

# Restart workers gracefully
max_requests = 1000
max_requests_jitter = 50

# Worker management
worker_tmp_dir = "/dev/shm"
EOF

print_status "Aktualisiere Systemd Service..."

# Systemd Service aktualisieren
sudo tee /etc/systemd/system/mitgliederverwaltung.service << 'EOF'
[Unit]
Description=Mitgliederverwaltung Django Application
After=network.target
Wants=network.target

[Service]
Type=notify
User=pi
Group=www-data
WorkingDirectory=/home/pi/mitgliederverwaltung
Environment="PATH=/home/pi/mitgliederverwaltung/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=mitgliederverwaltung.settings"
ExecStart=/home/pi/mitgliederverwaltung/venv/bin/gunicorn --config gunicorn.conf.py mitgliederverwaltung.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=3

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/home/pi/mitgliederverwaltung
ProtectHome=true

[Install]
WantedBy=multi-user.target
EOF

print_status "Erstelle Backup-Script..."

# Erweiteres Backup Script
cat > backup_system.sh << 'EOF'
#!/bin/bash
# Erweiteres Backup-Script für Mitgliederverwaltung

# Konfiguration
BACKUP_DIR="/home/pi/backups"
PROJECT_DIR="/home/pi/mitgliederverwaltung"
DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$BACKUP_DIR/backup.log"

# Backup-Verzeichnis erstellen
mkdir -p $BACKUP_DIR

# Logging Funktion
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a $LOG_FILE
}

log "=== Backup gestartet ==="

# 1. Datenbank Backup
log "Erstelle Datenbank-Backup..."
if sqlite3 $PROJECT_DIR/db.sqlite3 ".backup $BACKUP_DIR/db_backup_$DATE.sqlite3"; then
    log "Datenbank-Backup erfolgreich erstellt"
else
    log "FEHLER: Datenbank-Backup fehlgeschlagen"
    exit 1
fi

# 2. Media Files Backup
log "Erstelle Media-Backup..."
if tar -czf $BACKUP_DIR/media_backup_$DATE.tar.gz -C $PROJECT_DIR media/; then
    log "Media-Backup erfolgreich erstellt"
else
    log "FEHLER: Media-Backup fehlgeschlagen"
fi

# 3. Konfiguration Backup
log "Erstelle Konfigurations-Backup..."
tar -czf $BACKUP_DIR/config_backup_$DATE.tar.gz \
    $PROJECT_DIR/.env \
    $PROJECT_DIR/gunicorn.conf.py \
    /etc/nginx/sites-available/mitgliederverwaltung \
    /etc/systemd/system/mitgliederverwaltung.service \
    2>/dev/null || log "Warnung: Einige Konfigurationsdateien konnten nicht gesichert werden"

# 4. Vollständiges Projekt-Backup (wöchentlich)
WEEKDAY=$(date +%u)
if [ $WEEKDAY -eq 7 ]; then  # Sonntag
    log "Erstelle vollständiges Projekt-Backup..."
    tar --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
        -czf $BACKUP_DIR/full_backup_$DATE.tar.gz \
        -C /home/pi mitgliederverwaltung/
    log "Vollständiges Backup erstellt"
fi

# 5. Alte Backups löschen
log "Lösche alte Backups..."
find $BACKUP_DIR -name "db_backup_*.sqlite3" -mtime +30 -delete
find $BACKUP_DIR -name "media_backup_*.tar.gz" -mtime +30 -delete
find $BACKUP_DIR -name "config_backup_*.tar.gz" -mtime +14 -delete
find $BACKUP_DIR -name "full_backup_*.tar.gz" -mtime +90 -delete

# 6. Backup-Größe protokollieren
BACKUP_SIZE=$(du -sh $BACKUP_DIR | cut -f1)
log "Backup-Verzeichnis Größe: $BACKUP_SIZE"

log "=== Backup abgeschlossen ==="
log ""
EOF

chmod +x backup_system.sh

print_status "Erstelle Monitoring-Script..."

# Monitoring Script
cat > monitor_system.sh << 'EOF'
#!/bin/bash
# System-Monitoring für Mitgliederverwaltung

PROJECT_DIR="/home/pi/mitgliederverwaltung"
LOG_FILE="$PROJECT_DIR/logs/monitoring.log"

# Logging
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a $LOG_FILE
}

# Service Status prüfen
check_service() {
    if systemctl is-active --quiet mitgliederverwaltung; then
        log "Service: RUNNING"
    else
        log "Service: STOPPED - Versuche Neustart..."
        sudo systemctl start mitgliederverwaltung
        sleep 5
        if systemctl is-active --quiet mitgliederverwaltung; then
            log "Service erfolgreich neugestartet"
        else
            log "FEHLER: Service konnte nicht gestartet werden"
        fi
    fi
}

# Festplattenplatz prüfen
check_disk_space() {
    USAGE=$(df /home | awk 'NR==2 {print $5}' | sed 's/%//')
    log "Festplattennutzung: $USAGE%"
    
    if [ $USAGE -gt 90 ]; then
        log "WARNUNG: Festplatte fast voll ($USAGE%)"
        # Alte Log-Dateien bereinigen
        find $PROJECT_DIR/logs -name "*.log" -mtime +7 -exec truncate -s 0 {} \;
        log "Alte Log-Dateien bereinigt"
    fi
}

# Speicher prüfen
check_memory() {
    MEM_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    log "Speichernutzung: $MEM_USAGE%"
    
    if [ $MEM_USAGE -gt 85 ]; then
        log "WARNUNG: Hohe Speichernutzung ($MEM_USAGE%)"
    fi
}

# Datenbank-Integrität prüfen
check_database() {
    cd $PROJECT_DIR
    source venv/bin/activate
    
    if python manage.py check --database default >/dev/null 2>&1; then
        log "Datenbank: OK"
    else
        log "WARNUNG: Datenbankprobleme erkannt"
    fi
}

# Log-Rotation
rotate_logs() {
    LOG_SIZE=$(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0)
    if [ $LOG_SIZE -gt 10485760 ]; then  # 10MB
        mv "$LOG_FILE" "$LOG_FILE.old"
        touch "$LOG_FILE"
        log "Log-Datei rotiert"
    fi
}

# Monitoring ausführen
log "=== System-Check gestartet ==="
check_service
check_disk_space
check_memory
check_database
rotate_logs
log "=== System-Check abgeschlossen ==="
EOF

chmod +x monitor_system.sh

print_status "Konfiguriere Cron Jobs..."

# Cron Jobs einrichten
(crontab -l 2>/dev/null; echo "# Mitgliederverwaltung Backups und Monitoring") | crontab -
(crontab -l 2>/dev/null; echo "0 2 * * * /home/pi/mitgliederverwaltung/backup_system.sh") | crontab -
(crontab -l 2>/dev/null; echo "*/15 * * * * /home/pi/mitgliederverwaltung/monitor_system.sh") | crontab -
(crontab -l 2>/dev/null; echo "0 0 * * 0 /home/pi/mitgliederverwaltung/venv/bin/python /home/pi/mitgliederverwaltung/manage.py clearsessions") | crontab -

print_status "Erstelle Management-Commands..."

# Management Command Verzeichnis
mkdir -p members/management/commands

# Command für Datenbereinigung
cat > members/management/__init__.py << 'EOF'
EOF

cat > members/management/commands/__init__.py << 'EOF'
EOF

cat > members/management/commands/cleanup_data.py << 'EOF'
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from members.models import ImportLog
import os


class Command(BaseCommand):
    help = 'Bereinigt alte Daten und temporäre Dateien'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Anzahl Tage für Import-Log Aufbewahrung (Standard: 90)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Zeigt nur an, was gelöscht würde'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Alte Import-Logs löschen
        old_logs = ImportLog.objects.filter(imported_at__lt=cutoff_date)
        count = old_logs.count()
        
        if count > 0:
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f'Würde {count} alte Import-Logs löschen')
                )
            else:
                old_logs.delete()
                self.stdout.write(
                    self.style.SUCCESS(f'{count} alte Import-Logs gelöscht')
                )
        else:
            self.stdout.write('Keine alten Import-Logs gefunden')
        
        # Temporäre Upload-Dateien bereinigen
        uploads_dir = 'uploads'
        if os.path.exists(uploads_dir):
            temp_files = []
            for file in os.listdir(uploads_dir):
                file_path = os.path.join(uploads_dir, file)
                if os.path.isfile(file_path):
                    # Dateien älter als 1 Tag
                    if os.path.getmtime(file_path) < (timezone.now() - timedelta(days=1)).timestamp():
                        temp_files.append(file_path)
            
            if temp_files:
                if dry_run:
                    self.stdout.write(
                        self.style.WARNING(f'Würde {len(temp_files)} temporäre Dateien löschen')
                    )
                else:
                    for file_path in temp_files:
                        os.remove(file_path)
                    self.stdout.write(
                        self.style.SUCCESS(f'{len(temp_files)} temporäre Dateien gelöscht')
                    )
            else:
                self.stdout.write('Keine temporären Dateien gefunden')
EOF

print_status "Erstelle System-Info Command..."

cat > members/management/commands/system_info.py << 'EOF'
from django.core.management.base import BaseCommand
from django.conf import settings
from members.models import Member, ImportLog
import os
import platform
import psutil


class Command(BaseCommand):
    help = 'Zeigt System- und Anwendungsinformationen'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== MITGLIEDERVERWALTUNG SYSTEM-INFO ==='))
        self.stdout.write('')
        
        # System-Informationen
        self.stdout.write(self.style.WARNING('System:'))
        self.stdout.write(f'  OS: {platform.system()} {platform.release()}')
        self.stdout.write(f'  Architektur: {platform.machine()}')
        self.stdout.write(f'  Python: {platform.python_version()}')
        self.stdout.write(f'  Hostname: {platform.node()}')
        self.stdout.write('')
        
        # Hardware-Informationen
        self.stdout.write(self.style.WARNING('Hardware:'))
        self.stdout.write(f'  CPU Kerne: {psutil.cpu_count()}')
        self.stdout.write(f'  RAM: {psutil.virtual_memory().total / (1024**3):.1f} GB')
        self.stdout.write(f'  CPU Auslastung: {psutil.cpu_percent()}%')
        self.stdout.write(f'  RAM Auslastung: {psutil.virtual_memory().percent}%')
        self.stdout.write('')
        
        # Festplatte
        disk = psutil.disk_usage('/')
        self.stdout.write(self.style.WARNING('Festplatte:'))
        self.stdout.write(f'  Gesamt: {disk.total / (1024**3):.1f} GB')
        self.stdout.write(f'  Frei: {disk.free / (1024**3):.1f} GB')
        self.stdout.write(f'  Belegt: {disk.percent}%')
        self.stdout.write('')
        
        # Django-Informationen
        self.stdout.write(self.style.WARNING('Django:'))
        self.stdout.write(f'  Version: {settings.DJANGO_VERSION if hasattr(settings, "DJANGO_VERSION") else "N/A"}')
        self.stdout.write(f'  Debug: {settings.DEBUG}')
        self.stdout.write(f'  Database: {settings.DATABASES["default"]["ENGINE"]}')
        self.stdout.write('')
        
        # Anwendungsdaten
        self.stdout.write(self.style.WARNING('Anwendungsdaten:'))
        total_members = Member.objects.count()
        active_members = Member.objects.filter(is_active=True).count()
        total_imports = ImportLog.objects.count()
        
        self.stdout.write(f'  Mitglieder gesamt: {total_members}')
        self.stdout.write(f'  Aktive Mitglieder: {active_members}')
        self.stdout.write(f'  Import-Protokolle: {total_imports}')
        self.stdout.write('')
        
        # Dateisystem
        self.stdout.write(self.style.WARNING('Dateien:'))
        media_size = self._get_dir_size(settings.MEDIA_ROOT) if os.path.exists(settings.MEDIA_ROOT) else 0
        static_size = self._get_dir_size(settings.STATIC_ROOT) if os.path.exists(settings.STATIC_ROOT) else 0
        
        self.stdout.write(f'  Media Verzeichnis: {media_size / (1024**2):.1f} MB')
        self.stdout.write(f'  Static Verzeichnis: {static_size / (1024**2):.1f} MB')
        
        # Profilbilder zählen
        profile_pics = 0
        if os.path.exists(os.path.join(settings.MEDIA_ROOT, 'profile_pics')):
            profile_pics = len([f for f in os.listdir(os.path.join(settings.MEDIA_ROOT, 'profile_pics')) 
                               if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
        
        self.stdout.write(f'  Profilbilder: {profile_pics}')
        self.stdout.write('')
        
        self.stdout.write(self.style.SUCCESS('=== ENDE SYSTEM-INFO ==='))
    
    def _get_dir_size(self, path):
        """Berechnet die Größe eines Verzeichnisses"""
        total = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    total += os.path.getsize(filepath)
        except (OSError, IOError):
            pass
        return total
EOF

print_status "Setze Berechtigungen..."

# Berechtigungen für Verzeichnisse setzen
sudo chown -R pi:www-data /home/pi/mitgliederverwaltung
sudo chmod -R 755 /home/pi/mitgliederverwaltung
sudo chmod -R 775 /home/pi/mitgliederverwaltung/media
sudo chmod -R 775 /home/pi/mitgliederverwaltung/logs
sudo chmod -R 775 /home/pi/mitgliederverwaltung/uploads

print_status "Erstelle Production .env..."

# Production Environment Variables
cat > .env.production << 'EOF'
# Production Environment Variables für Mitgliederverwaltung

# WICHTIG: Ändern Sie diese Werte vor dem Produktionseinsatz!
SECRET_KEY=production-secret-key-change-this-immediately-123456789
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.100,192.168.1.101

# Database
DATABASE_NAME=db.sqlite3

# Media Settings
MEDIA_ROOT=/home/pi/mitgliederverwaltung/media
STATIC_ROOT=/home/pi/mitgliederverwaltung/staticfiles

# Upload Settings
MAX_UPLOAD_SIZE=10485760
ALLOWED_IMAGE_TYPES=jpg,jpeg,png
ALLOWED_IMPORT_TYPES=csv,xlsx,xls

# Security Settings
SECURE_BROWSER_XSS_FILTER=True
SECURE_CONTENT_TYPE_NOSNIFF=True
X_FRAME_OPTIONS=DENY
EOF

print_status "Erstelle Deployment-Script..."

# Deployment Script
cat > deploy.sh << 'EOF'
#!/bin/bash
# Deployment Script für Mitgliederverwaltung

echo "=== Deployment gestartet ==="

# 1. Virtual Environment aktivieren
source venv/bin/activate

# 2. Dependencies aktualisieren
pip install -r requirements.txt

# 3. Database Migrationen
python manage.py migrate

# 4. Static Files sammeln
python manage.py collectstatic --noinput

# 5. System-Check durchführen
python manage.py check --deploy

# 6. Services neustarten
sudo systemctl restart mitgliederverwaltung
sudo systemctl restart nginx

# 7. Service Status prüfen
sleep 3
if systemctl is-active --quiet mitgliederverwaltung; then
    echo "✓ Mitgliederverwaltung Service läuft"
else
    echo "✗ Mitgliederverwaltung Service Fehler"
    exit 1
fi

if systemctl is-active --quiet nginx; then
    echo "✓ Nginx Service läuft"
else
    echo "✗ Nginx Service Fehler"
    exit 1
fi

echo "=== Deployment erfolgreich abgeschlossen ==="
EOF

chmod +x deploy.sh

print_status "Systemd Services aktivieren..."

# Services aktivieren und starten
sudo systemctl daemon-reload
sudo systemctl enable mitgliederverwaltung
sudo systemctl enable nginx

# Services starten
sudo systemctl start mitgliederverwaltung
sudo systemctl start nginx

print_status "Warte auf Service-Start..."
sleep 5

# Service Status prüfen
if systemctl is-active --quiet mitgliederverwaltung; then
    print_success "Mitgliederverwaltung Service läuft"
else
    print_error "Mitgliederverwaltung Service konnte nicht gestartet werden"
    sudo systemctl status mitgliederverwaltung
fi

if systemctl is-active --quiet nginx; then
    print_success "Nginx Service läuft"
else
    print_error "Nginx Service konnte nicht gestartet werden"
    sudo systemctl status nginx
fi

print_status "Erstelle README..."

# README erstellen
cat > README.md << 'EOF'
# Mitgliederverwaltung Dashboard

Ein Django-basiertes Web-Dashboard für die Verwaltung von Mitgliederdaten zur Erstellung von Dienstausweisen.

## Installation

Die Installation erfolgte automatisch über die Installationsskripts:
- `install_part1.sh` - Django Grundkonfiguration
- `install_part2.sh` - Models und Admin Interface  
- `install_part3.sh` - Templates und Static Files
- `install_part4.sh` - Views und Forms
- `install_part5.sh` - Production Setup

## Verwendung

### Development Server starten
```bash
cd ~/mitgliederverwaltung
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

### Production Server
Der Production Server läuft automatisch über systemd:
```bash
sudo systemctl status mitgliederverwaltung
sudo systemctl restart mitgliederverwaltung
```

### Superuser erstellen
```bash
python manage.py createsuperuser
```

### Backup erstellen
```bash
./backup_system.sh
```

### System-Informationen anzeigen
```bash
python manage.py system_info
```

### Daten bereinigen
```bash
python manage.py cleanup_data
```

## Zugriff

- **Web-Interface**: http://PI-IP-ADRESSE
- **Admin-Interface**: http://PI-IP-ADRESSE/admin/

## Verzeichnisstruktur

```
~/mitgliederverwaltung/
├── mitgliederverwaltung/     # Django Projekt
├── members/                  # Haupt-App
├── templates/               # HTML Templates
├── static/                  # CSS, JS, Images
├── media/                   # Upload-Verzeichnis
├── logs/                    # Log-Dateien
├── backups/                 # Backup-Verzeichnis
├── venv/                    # Virtual Environment
└── manage.py               # Django Management
```

## Wartung

### Log-Dateien
- Django: `logs/django.log`
- Gunicorn: `logs/gunicorn-*.log`
- Nginx: `/var/log/nginx/`
- Monitoring: `logs/monitoring.log`

### Backup
- Automatisch täglich um 2:00 Uhr
- Aufbewahrung: 30 Tage (DB), 90 Tage (Vollbackup)
- Manuell: `./backup_system.sh`

### Monitoring
- Automatisch alle 15 Minuten
- Prüft Service-Status, Speicher, Festplatte
- Manuell: `./monitor_system.sh`

## Troubleshooting

### Service-Probleme
```bash
sudo systemctl status mitgliederverwaltung
sudo journalctl -u mitgliederverwaltung -f
```

### Nginx-Probleme
```bash
sudo nginx -t
sudo systemctl status nginx
```

### Datenbank-Probleme
```bash
python manage.py check
python manage.py migrate
```

## Support

Bei Problemen prüfen Sie:
1. Service-Status: `sudo systemctl status mitgliederverwaltung`
2. Log-Dateien: `tail -f logs/django.log`
3. Nginx-Konfiguration: `sudo nginx -t`
4. Festplattenplatz: `df -h`
5. System-Info: `python manage.py system_info`
EOF

print_success "Installation vollständig abgeschlossen!"
echo ""
print_status "=== ZUSAMMENFASSUNG ==="
echo ""
echo "✅ Django Projekt konfiguriert"
echo "✅ Datenbank-Migrationen durchgeführt"
echo "✅ Nginx als Reverse Proxy konfiguriert"
echo "✅ Systemd Service eingerichtet"
echo "✅ Backup-System aktiviert"
echo "✅ Monitoring eingerichtet"
echo "✅ Cron Jobs konfiguriert"
echo "✅ Management Commands erstellt"
echo ""
print_warning "WICHTIGE NÄCHSTE SCHRITTE:"
echo ""
echo "1. Superuser erstellen:"
echo "   python manage.py createsuperuser"
echo ""
echo "2. Production Secret Key ändern:"
echo "   nano .env.production"
echo "   # Ersetzen Sie SECRET_KEY mit einem sicheren Wert"
echo ""
echo "3. Firewall-Regeln prüfen:"
echo "   sudo ufw status"
echo ""
echo "4. Erste Anmeldung testen:"
echo "   http://$(hostname -I | awk '{print $1}')"
echo ""
print_status "=== VERFÜGBARE BEFEHLE ==="
echo ""
echo "🔧 Management:"
echo "   ./deploy.sh              - Deployment durchführen"
echo "   ./backup_system.sh       - Backup erstellen"
echo "   ./monitor_system.sh      - System-Check"
echo ""
echo "📊 Django Commands:"
echo "   python manage.py system_info     - System-Informationen"
echo "   python manage.py cleanup_data    - Daten bereinigen"
echo "   python manage.py collectstatic   - Static Files sammeln"
echo ""
echo "🎛️  Service Management:"
echo "   sudo systemctl status mitgliederverwaltung    - Service Status"
echo "   sudo systemctl restart mitgliederverwaltung   - Service Neustart"
echo "   sudo systemctl restart nginx                  - Nginx Neustart"
echo ""
echo "📋 Logs:"
echo "   tail -f logs/django.log                - Django Logs"
echo "   tail -f logs/gunicorn-error.log       - Gunicorn Logs"
echo "   sudo tail -f /var/log/nginx/error.log - Nginx Logs"
echo ""
print_status "=== ZUGRIFF ==="
echo ""
PI_IP=$(hostname -I | awk '{print $1}')
echo "🌐 Web-Interface:   http://$PI_IP"
echo "⚙️  Admin-Interface: http://$PI_IP/admin/"
echo "📱 Von anderen Geräten im Netzwerk erreichbar"
echo ""
print_status "=== SECURITY HINWEISE ==="
echo ""
print_warning "⚠️  Ändern Sie unbedingt:"
echo "   - SECRET_KEY in .env.production"
echo "   - Starke Passwörter für Admin-Benutzer"
echo "   - Firewall-Regeln nach Bedarf anpassen"
echo ""
print_status "=== CARDPRESSO INTEGRATION ==="
echo ""
echo "Für die Cardpresso-Anbindung:"
echo "1. SQLite-Datenbank liegt unter: ~/mitgliederverwaltung/db.sqlite3"
echo "2. Profilbilder unter: ~/mitgliederverwaltung/media/profile_pics/"
echo "3. Datenbankstruktur siehe: members_member Tabelle"
echo ""
echo "🎉 Das Mitgliederverwaltung Dashboard ist einsatzbereit!"
echo ""
echo "Erstellen Sie jetzt Ihren ersten Admin-Benutzer:"
echo "python manage.py createsuperuser"