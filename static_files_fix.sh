#!/bin/bash
# Static Files Berechtigungen für Nginx reparieren

echo "📁 Static Files Berechtigungen korrigieren..."

# 1. Aktuelle Berechtigungen prüfen
echo "=== AKTUELLE BERECHTIGUNGEN ==="
echo "Static Files Verzeichnis:"
ls -la /home/pi/mitgliederverwaltung/staticfiles/ 2>/dev/null || echo "staticfiles Verzeichnis nicht gefunden"

echo ""
echo "Media Files Verzeichnis:"
ls -la /home/pi/mitgliederverwaltung/media/ 2>/dev/null || echo "media Verzeichnis nicht gefunden"

# 2. Django static files sammeln
echo ""
echo "🔄 Django static files sammeln..."
cd /home/pi/mitgliederverwaltung
source venv/bin/activate
python manage.py collectstatic --noinput

# 3. Berechtigungen korrigieren
echo ""
echo "🔧 Berechtigungen setzen..."

# Static files Berechtigungen
if [ -d "/home/pi/mitgliederverwaltung/staticfiles" ]; then
    echo "Static files Berechtigungen setzen..."
    sudo chown -R pi:www-data /home/pi/mitgliederverwaltung/staticfiles/
    sudo chmod -R 755 /home/pi/mitgliederverwaltung/staticfiles/
    sudo find /home/pi/mitgliederverwaltung/staticfiles/ -type f -exec chmod 644 {} \;
else
    echo "❌ staticfiles Verzeichnis nicht gefunden!"
fi

# Media files Berechtigungen
if [ -d "/home/pi/mitgliederverwaltung/media" ]; then
    echo "Media files Berechtigungen setzen..."
    sudo chown -R pi:www-data /home/pi/mitgliederverwaltung/media/
    sudo chmod -R 755 /home/pi/mitgliederverwaltung/media/
    sudo find /home/pi/mitgliederverwaltung/media/ -type f -exec chmod 644 {} \;
else
    echo "Media Verzeichnis erstellen..."
    sudo mkdir -p /home/pi/mitgliederverwaltung/media/
    sudo chown pi:www-data /home/pi/mitgliederverwaltung/media/
    sudo chmod 755 /home/pi/mitgliederverwaltung/media/
fi

# 4. Nginx-Konfiguration überprüfen und korrigieren
echo ""
echo "🔧 Nginx-Konfiguration überprüfen..."

# Aktuelle Nginx-Konfiguration anzeigen
echo "Aktuelle static files Konfiguration:"
sudo grep -A 10 "location /static/" /etc/nginx/sites-enabled/mitgliederverwaltung-https

# 5. Nginx neu laden
echo ""
echo "🔄 Nginx neu laden..."
sudo nginx -t && sudo systemctl reload nginx

# 6. Tests durchführen
echo ""
echo "=== TESTS ==="

echo "Test 1: Static files Verzeichnis-Zugriff"
ls -la /home/pi/mitgliederverwaltung/staticfiles/css/ 2>/dev/null || echo "CSS Verzeichnis nicht gefunden"

echo ""
echo "Test 2: CSS-Datei direkt testen"
curl -s -k -o /dev/null -w "CSS HTTP-Code: %{http_code}\n" https://192.168.1.136/static/css/style.css

echo ""
echo "Test 3: JS-Datei direkt testen"
curl -s -k -o /dev/null -w "JS HTTP-Code: %{http_code}\n" https://192.168.1.136/static/js/main.js

# 7. Neue Berechtigungen anzeigen
echo ""
echo "=== NEUE BERECHTIGUNGEN ==="
echo "Static files:"
ls -la /home/pi/mitgliederverwaltung/staticfiles/ | head -10

echo ""
echo "CSS Verzeichnis:"
ls -la /home/pi/mitgliederverwaltung/staticfiles/css/ 2>/dev/null | head -5

echo ""
echo "JS Verzeichnis:"
ls -la /home/pi/mitgliederverwaltung/staticfiles/js/ 2>/dev/null | head -5

echo ""
echo "=== ZUSAMMENFASSUNG ==="
echo "✅ Static files gesammelt"
echo "✅ Berechtigungen korrigiert (pi:www-data, 755/644)"
echo "✅ Nginx neu geladen"
echo ""
echo "🧪 Browser-Test:"
echo "1. Browser-Cache löschen (Strg+Shift+Entf)"
echo "2. Seite neu laden (Strg+F5)"
echo "3. Prüfen ob CSS/JS geladen wird"
echo ""
echo "Falls weiterhin 403-Fehler:"
echo "• Django DEBUG = True setzen (temporär)"
echo "• Nginx Error-Log prüfen: sudo tail /var/log/nginx/error.log"
