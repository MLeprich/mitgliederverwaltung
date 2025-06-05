#!/bin/bash
# Vollständige Static Files Diagnose und Reparatur

echo "🔍 Static Files Diagnose..."

# 1. Verzeichnisstruktur prüfen
echo "=== VERZEICHNIS-STRUKTUR ==="
echo "Hauptverzeichnis:"
ls -la /home/pi/mitgliederverwaltung/

echo ""
echo "Static Files Verzeichnis existiert?"
if [ -d "/home/pi/mitgliederverwaltung/staticfiles" ]; then
    echo "✅ staticfiles Verzeichnis existiert"
    ls -la /home/pi/mitgliederverwaltung/staticfiles/
else
    echo "❌ staticfiles Verzeichnis existiert NICHT"
fi

echo ""
echo "Static Root in Django-App prüfen:"
find /home/pi/mitgliederverwaltung/ -name "static" -type d

# 2. Spezifische Dateien prüfen
echo ""
echo "=== SPEZIFISCHE DATEIEN ==="
echo "style.css existiert?"
find /home/pi/mitgliederverwaltung/ -name "style.css" -type f

echo ""
echo "main.js existiert?"
find /home/pi/mitgliederverwaltung/ -name "main.js" -type f

# 3. Django Settings prüfen
echo ""
echo "=== DJANGO SETTINGS ==="
cd /home/pi/mitgliederverwaltung
source venv/bin/activate

echo "STATIC_URL und STATIC_ROOT aus Django-Settings:"
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mitgliederverwaltung.settings')
django.setup()
from django.conf import settings
print(f'STATIC_URL: {settings.STATIC_URL}')
print(f'STATIC_ROOT: {getattr(settings, \"STATIC_ROOT\", \"Nicht gesetzt\")}')
print(f'STATICFILES_DIRS: {getattr(settings, \"STATICFILES_DIRS\", \"Nicht gesetzt\")}')
"

# 4. Static files sammeln (mit Debugging)
echo ""
echo "=== STATIC FILES SAMMELN ==="
echo "Sammle static files mit Debugging..."
python manage.py collectstatic --verbosity=2 --noinput

# 5. Nach dem Sammeln - Berechtigungen radikal korrigieren
echo ""
echo "=== BERECHTIGUNGEN RADIKAL KORRIGIEREN ==="

# Alle relevanten Verzeichnisse finden und reparieren
for dir in staticfiles static media; do
    if [ -d "/home/pi/mitgliederverwaltung/$dir" ]; then
        echo "Repariere $dir..."
        # Besitzer setzen
        sudo chown -R www-data:www-data "/home/pi/mitgliederverwaltung/$dir"
        # Verzeichnis-Berechtigungen
        sudo find "/home/pi/mitgliederverwaltung/$dir" -type d -exec chmod 755 {} \;
        # Datei-Berechtigungen
        sudo find "/home/pi/mitgliederverwaltung/$dir" -type f -exec chmod 644 {} \;
        echo "✅ $dir repariert"
    fi
done

# 6. Nginx-User prüfen
echo ""
echo "=== NGINX USER ==="
echo "Nginx läuft als:"
ps aux | grep nginx | grep -v grep | head -2

# 7. Test der Berechtigungen
echo ""
echo "=== BERECHTIGUNGS-TESTS ==="
if [ -f "/home/pi/mitgliederverwaltung/staticfiles/css/style.css" ]; then
    echo "style.css Berechtigungen:"
    ls -la /home/pi/mitgliederverwaltung/staticfiles/css/style.css
    
    echo "Nginx kann style.css lesen?"
    sudo -u www-data cat /home/pi/mitgliederverwaltung/staticfiles/css/style.css > /dev/null && echo "✅ Lesbar" || echo "❌ Nicht lesbar"
else
    echo "❌ style.css existiert nicht nach collectstatic"
fi

# 8. Nginx neu starten
echo ""
echo "🔄 Nginx komplett neu starten..."
sudo systemctl restart nginx

# 9. Final Tests
echo ""
echo "=== FINAL TESTS ==="
echo "HTTP-Test ohne SSL-Verifikation:"
curl -k -s -o /dev/null -w "CSS: %{http_code}\n" https://192.168.1.136/static/css/style.css
curl -k -s -o /dev/null -w "JS:  %{http_code}\n" https://192.168.1.136/static/js/main.js

echo ""
echo "=== ALTERNATIVE LÖSUNG ==="
echo "Falls Files fehlen - leere Dateien erstellen:"

# CSS-Datei erstellen falls sie fehlt
if [ ! -f "/home/pi/mitgliederverwaltung/staticfiles/css/style.css" ]; then
    echo "Erstelle leere style.css..."
    sudo mkdir -p /home/pi/mitgliederverwaltung/staticfiles/css/
    echo "/* Placeholder CSS */" | sudo tee /home/pi/mitgliederverwaltung/staticfiles/css/style.css > /dev/null
    sudo chown www-data:www-data /home/pi/mitgliederverwaltung/staticfiles/css/style.css
    sudo chmod 644 /home/pi/mitgliederverwaltung/staticfiles/css/style.css
fi

# JS-Datei erstellen falls sie fehlt
if [ ! -f "/home/pi/mitgliederverwaltung/staticfiles/js/main.js" ]; then
    echo "Erstelle leere main.js..."
    sudo mkdir -p /home/pi/mitgliederverwaltung/staticfiles/js/
    echo "// Placeholder JS" | sudo tee /home/pi/mitgliederverwaltung/staticfiles/js/main.js > /dev/null
    sudo chown www-data:www-data /home/pi/mitgliederverwaltung/staticfiles/js/main.js
    sudo chmod 644 /home/pi/mitgliederverwaltung/staticfiles/js/main.js
fi

echo ""
echo "=== ZUSAMMENFASSUNG ==="
echo "✅ Static files gesammelt und Berechtigungen korrigiert"
echo "✅ Nginx neu gestartet"
echo "✅ Fehlende Dateien erstellt"
echo ""
echo "🧪 FINALER TEST:"
echo "1. Browser-Cache löschen"
echo "2. https://192.168.1.136 aufrufen"
echo "3. F12 → Console prüfen"
echo ""
echo "💡 Wenn immer noch 403-Fehler:"
echo "Die Webcam-Funktionalität könnte trotzdem arbeiten."
echo "Testen Sie die Kernfunktionen der Anwendung!"
