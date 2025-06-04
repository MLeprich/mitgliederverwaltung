#!/bin/bash
# Komplettes Installationsskript für Mitgliederverwaltung Dashboard
# Führt alle Installationsteile automatisch aus
# 
# Verwendung: bash complete_install.sh

set -e

echo "======================================================================"
echo "     MITGLIEDERVERWALTUNG DASHBOARD - KOMPLETTE INSTALLATION"
echo "======================================================================"
echo ""
echo "Dieses Script installiert das komplette Django Dashboard für die"
echo "Mitgliederverwaltung auf Ihrem Raspberry Pi."
echo ""
echo "Die Installation dauert etwa 10-15 Minuten."
echo ""
read -p "Möchten Sie fortfahren? (j/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[JjYy]$ ]]; then
    echo "Installation abgebrochen."
    exit 1
fi

# Farben
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[SCHRITT]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[ERFOLG]${NC} $1"
}

print_error() {
    echo -e "${RED}[FEHLER]${NC} $1"
}

# Prüfungen vor Installation
print_status "Führe Vorprüfungen durch..."

# Virtual Environment prüfen
if [[ "$VIRTUAL_ENV" == "" ]]; then
    print_error "Virtual Environment ist nicht aktiviert!"
    echo ""
    echo "Bitte führen Sie zuerst folgende Befehle aus:"
    echo "cd ~/mitgliederverwaltung"
    echo "source venv/bin/activate"
    echo ""
    echo "Dann starten Sie das Script erneut."
    exit 1
fi

# Arbeitsverzeichnis prüfen
if [[ ! -d "~/mitgliederverwaltung" ]] && [[ ! $(pwd) =~ mitgliederverwaltung ]]; then
    print_error "Bitte führen Sie das Script im mitgliederverwaltung Verzeichnis aus!"
    exit 1
fi

cd ~/mitgliederverwaltung

print_success "Vorprüfungen erfolgreich"
echo ""

# Installation starten
echo "🚀 Starte Installation..."
sleep 2

# Teil 1: Grundkonfiguration
print_status "Teil 1/5: Django Projekt Grundkonfiguration"
if [ -f "install_part1.sh" ]; then
    bash install_part1.sh
    print_success "Teil 1 abgeschlossen"
else
    print_error "install_part1.sh nicht gefunden!"
    exit 1
fi
echo ""

# Teil 2: Models und Admin
print_status "Teil 2/5: Models und Admin Interface"
if [ -f "install_part2.sh" ]; then
    bash install_part2.sh
    print_success "Teil 2 abgeschlossen"
else
    print_error "install_part2.sh nicht gefunden!"
    exit 1
fi
echo ""

# Teil 3: Templates und Static Files
print_status "Teil 3/5: Templates und Static Files"
if [ -f "install_part3.sh" ]; then
    bash install_part3.sh
    print_success "Teil 3 abgeschlossen"
else
    print_error "install_part3.sh nicht gefunden!"
    exit 1
fi
echo ""

# Teil 4: Views und Forms
print_status "Teil 4/5: Views und Forms"
if [ -f "install_part4.sh" ]; then
    bash install_part4.sh
    print_success "Teil 4 abgeschlossen"
else
    print_error "install_part4.sh nicht gefunden!"
    exit 1
fi
echo ""

# Teil 5: Production Setup
print_status "Teil 5/5: Production Setup und Konfiguration"
if [ -f "install_part5.sh" ]; then
    bash install_part5.sh
    print_success "Teil 5 abgeschlossen"
else
    print_error "install_part5.sh nicht gefunden!"
    exit 1
fi
echo ""

# Finale Schritte
print_status "Führe finale Konfiguration durch..."

# Secret Key generieren
SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env.production

print_success "Sicherer Secret Key generiert"

# Service-Status final prüfen
sleep 3

if systemctl is-active --quiet mitgliederverwaltung; then
    print_success "Mitgliederverwaltung Service läuft"
else
    print_error "Service-Problem erkannt - versuche Neustart..."
    sudo systemctl restart mitgliederverwaltung
    sleep 3
    if systemctl is-active --quiet mitgliederverwaltung; then
        print_success "Service erfolgreich gestartet"
    else
        print_error "Service konnte nicht gestartet werden - prüfen Sie die Logs"
    fi
fi

if systemctl is-active --quiet nginx; then
    print_success "Nginx läuft"
else
    print_error "Nginx-Problem erkannt - versuche Neustart..."
    sudo systemctl restart nginx
fi

echo ""
echo "======================================================================"
echo "                    🎉 INSTALLATION ERFOLGREICH! 🎉"
echo "======================================================================"
echo ""

# Informationen anzeigen
PI_IP=$(hostname -I | awk '{print $1}')

echo "📊 SYSTEM-INFORMATIONEN:"
echo "   Raspberry Pi IP: $PI_IP"
echo "   Django Version: $(python -c 'import django; print(django.get_version())')"
echo "   Python Version: $(python --version | cut -d' ' -f2)"
echo ""

echo "🌐 ZUGRIFF AUF DAS DASHBOARD:"
echo "   Web-Interface:   http://$PI_IP"
echo "   Admin-Interface: http://$PI_IP/admin/"
echo ""

echo "👤 NÄCHSTE SCHRITTE:"
echo "   1. Admin-Benutzer erstellen:"
echo "      python manage.py createsuperuser"
echo ""
echo "   2. Erste Anmeldung testen"
echo "      Öffnen Sie http://$PI_IP in Ihrem Browser"
echo ""
echo "   3. Erstes Mitglied hinzufügen oder Daten importieren"
echo ""

echo "🛠️  VERWALTUNG:"
echo "   Service Status:    sudo systemctl status mitgliederverwaltung"
echo "   Service Neustart:  sudo systemctl restart mitgliederverwaltung"
echo "   Backup erstellen:  ./backup_system.sh"
echo "   System-Check:      ./monitor_system.sh"
echo "   System-Info:       python manage.py system_info"
echo ""

echo "📁 WICHTIGE DATEIEN:"
echo "   Datenbank:        ~/mitgliederverwaltung/db.sqlite3"
echo "   Profilbilder:     ~/mitgliederverwaltung/media/profile_pics/"
echo "   Konfiguration:    ~/mitgliederverwaltung/.env"
echo "   Logs:             ~/mitgliederverwaltung/logs/"
echo "   Backups:          ~/mitgliederverwaltung/backups/"
echo ""

echo "🔧 CARDPRESSO-INTEGRATION:"
echo "   Die SQLite-Datenbank kann direkt mit Cardpresso verbunden werden."
echo "   Datenbankpfad: ~/mitgliederverwaltung/db.sqlite3"
echo "   Haupttabelle: members_member"
echo ""

echo "📚 DOKUMENTATION:"
echo "   README:           ~/mitgliederverwaltung/README.md"
echo "   Admin-Hilfe:      http://$PI_IP/admin/doc/"
echo ""

echo "⚠️  SICHERHEITSHINWEISE:"
echo "   • Erstellen Sie regelmäßig Backups (automatisch täglich um 2:00)"
echo "   • Verwenden Sie starke Passwörter für Admin-Benutzer"
echo "   • Überwachen Sie die Log-Dateien auf Fehler"
echo "   • Halten Sie das System aktuell: sudo apt update && sudo apt upgrade"
echo ""

# Superuser-Erstellung anbieten
echo ""
read -p "Möchten Sie jetzt einen Admin-Benutzer erstellen? (j/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[JjYy]$ ]]; then
    echo ""
    echo "Erstelle Admin-Benutzer..."
    python manage.py createsuperuser
    echo ""
    print_success "Admin-Benutzer erstellt!"
    echo ""
    echo "Sie können sich jetzt anmelden unter:"
    echo "http://$PI_IP/admin/"
fi

echo ""
echo "======================================================================"
echo "        Das Mitgliederverwaltung Dashboard ist einsatzbereit!"
echo ""
echo "           Vielen Dank für die Verwendung dieses Systems!"
echo "======================================================================"

# Optional: Browser öffnen (wenn GUI verfügbar)
if command -v xdg-open &> /dev/null; then
    read -p "Browser öffnen? (j/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[JjYy]$ ]]; then
        xdg-open "http://$PI_IP" &
    fi
fi

# Installation abgeschlossen
exit 0