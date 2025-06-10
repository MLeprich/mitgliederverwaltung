#!/bin/bash
# Media-Ordner Berechtigungen für Webcam-Upload reparieren

echo "📁 Media-Ordner Berechtigungen reparieren..."

cd /home/pi/mitgliederverwaltung

# 1. Media-Ordner erstellen (falls nicht vorhanden)
echo "Erstelle Media-Verzeichnisse..."
sudo mkdir -p media/profile_pics
sudo mkdir -p staticfiles

# 2. Besitzer und Gruppe korrekt setzen
echo "Setze Besitzer und Gruppen..."
sudo chown -R pi:www-data media/
sudo chown -R pi:www-data staticfiles/

# 3. Korrekte Berechtigungen setzen
echo "Setze Berechtigungen..."
# Verzeichnisse: 755 (rwxr-xr-x)
sudo find media/ -type d -exec chmod 755 {} \;
sudo find staticfiles/ -type d -exec chmod 755 {} \;

# Dateien: 644 (rw-r--r--)
sudo find media/ -type f -exec chmod 644 {} \;
sudo find staticfiles/ -type f -exec chmod 644 {} \;

# 4. Spezielle Berechtigungen für profile_pics
sudo chmod 755 media/profile_pics/

# 5. Setgid-Bit für automatische Gruppenzuweisung
sudo chmod g+s media/profile_pics/

# 6. Status prüfen
echo ""
echo "=== BERECHTIGUNGEN PRÜFEN ==="
echo "Media-Ordner:"
ls -la media/

echo ""
echo "Profile-Pics Ordner:"
ls -la media/profile_pics/

echo ""
echo "Besitzer von media/:"
stat -c '%U:%G %a' media/

echo ""
echo "Besitzer von media/profile_pics/:"
stat -c '%U:%G %a' media/profile_pics/

# 7. Test: Datei erstellen
echo ""
echo "=== TEST: Datei-Erstellung ==="
echo "Test als pi-User:"
touch media/profile_pics/test_pi.txt 2>/dev/null && echo "✅ Pi kann schreiben" || echo "❌ Pi kann nicht schreiben"

echo "Test als www-data:"
sudo -u www-data touch media/profile_pics/test_www-data.txt 2>/dev/null && echo "✅ www-data kann schreiben" || echo "❌ www-data kann nicht schreiben"

# Testdateien löschen
rm -f media/profile_pics/test_*.txt

# 8. Django Service neu starten (für neue Berechtigungen)
echo ""
echo "🔄 Django Service neu starten..."
sudo systemctl restart mitgliederverwaltung

echo ""
echo "=== ZUSAMMENFASSUNG ==="
echo "✅ Media-Ordner erstellt"
echo "✅ Berechtigungen gesetzt (pi:www-data, 755/644)" 
echo "✅ Setgid-Bit aktiviert"
echo "✅ Django Service neu gestartet"
echo ""
echo "🧪 JETZT TESTEN:"
echo "1. Webcam-Foto aufnehmen"
echo "2. Mitglied speichern"
echo "3. Sollte ohne Permission-Error funktionieren"
