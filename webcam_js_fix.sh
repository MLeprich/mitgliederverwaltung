#!/bin/bash
# Webcam JavaScript Problem diagnostizieren und lösen

echo "📷 Webcam JavaScript Problem diagnostizieren..."

cd /home/pi/mitgliederverwaltung

# 1. JavaScript-Dateien im Projekt finden
echo "=== JAVASCRIPT-DATEIEN SUCHEN ==="
echo "Alle JS-Dateien im Projekt:"
find . -name "*.js" -type f | head -20

echo ""
echo "main.js Dateien:"
find . -name "main.js" -type f

echo ""
echo "Static-Verzeichnisse im Projekt:"
find . -path "*/static/*" -name "*.js" | head -10

# 2. Django Templates prüfen (wo wird main.js referenziert?)
echo ""
echo "=== TEMPLATES PRÜFEN ==="
echo "Templates die main.js laden:"
find . -name "*.html" -exec grep -l "main.js" {} \; 2>/dev/null

echo ""
echo "JavaScript-Referenzen in Templates:"
find . -name "*.html" -exec grep -H -n "\.js" {} \; 2>/dev/null | head -10

# 3. Django App-Struktur prüfen
echo ""
echo "=== DJANGO APP STRUKTUR ==="
echo "Apps im Projekt:"
ls -la */

echo ""
echo "Static-Verzeichnisse pro App:"
find . -type d -name "static" | head -10

# 4. Webcam-spezifische Dateien finden
echo ""
echo "=== WEBCAM-DATEIEN SUCHEN ==="
echo "Dateien mit 'webcam' im Namen:"
find . -name "*webcam*" -type f

echo ""
echo "Dateien mit 'camera' im Namen:"
find . -name "*camera*" -type f

# 5. Views.py prüfen (welche Templates werden verwendet?)
echo ""
echo "=== VIEWS PRÜFEN ==="
echo "Views-Dateien:"
find . -name "views.py" -exec echo "=== {} ===" \; -exec head -20 {} \;

# 6. URLs prüfen
echo ""
echo "=== URL PATTERNS ==="
echo "URLs.py Dateien:"
find . -name "urls.py" -exec echo "=== {} ===" \; -exec head -10 {} \;

# 7. Aktuelle staticfiles sammeln mit Debugging
echo ""
echo "=== STATIC FILES SAMMELN (mit Details) ==="
source venv/bin/activate
echo "Static files vor collectstatic:"
ls -la staticfiles/ 2>/dev/null || echo "staticfiles existiert nicht"

python manage.py collectstatic --verbosity=2 --noinput

echo ""
echo "Static files nach collectstatic:"
ls -la staticfiles/

# 8. Die richtige main.js finden und kopieren
echo ""
echo "=== MAIN.JS PROBLEM LÖSEN ==="

# Schauen ob main.js in den Apps existiert
MAIN_JS_SOURCE=""
for js_file in $(find . -name "main.js" -not -path "./staticfiles/*" -not -path "./venv/*"); do
    echo "Gefundene main.js: $js_file"
    MAIN_JS_SOURCE="$js_file"
    echo "Inhalt (erste 10 Zeilen):"
    head -10 "$js_file"
    echo "---"
done

if [ -n "$MAIN_JS_SOURCE" ]; then
    echo "✅ main.js gefunden in: $MAIN_JS_SOURCE"
    echo "Kopiere nach staticfiles..."
    
    sudo mkdir -p /home/pi/mitgliederverwaltung/staticfiles/js/
    sudo cp "$MAIN_JS_SOURCE" /home/pi/mitgliederverwaltung/staticfiles/js/main.js
    sudo chown www-data:www-data /home/pi/mitgliederverwaltung/staticfiles/js/main.js
    sudo chmod 644 /home/pi/mitgliederverwaltung/staticfiles/js/main.js
    
    echo "✅ main.js nach staticfiles kopiert"
else
    echo "❌ main.js nicht gefunden - erstelle Webcam-Placeholder..."
    
    sudo mkdir -p /home/pi/mitgliederverwaltung/staticfiles/js/
    
    # Einfacher Webcam-JavaScript-Code als Fallback
    sudo tee /home/pi/mitgliederverwaltung/staticfiles/js/main.js > /dev/null << 'EOF'
// Webcam-Grundfunktionalität
console.log('📷 main.js geladen');

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM geladen, Webcam initialisieren...');
    
    // Webcam-Video-Element finden
    const video = document.querySelector('video') || document.querySelector('#webcam-video') || document.querySelector('.webcam');
    
    if (video) {
        console.log('📹 Video-Element gefunden:', video);
        
        // Webcam-Stream starten
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            navigator.mediaDevices.getUserMedia({ 
                video: { 
                    width: { ideal: 1280 }, 
                    height: { ideal: 720 } 
                } 
            })
            .then(function(stream) {
                console.log('✅ Webcam-Stream erhalten');
                video.srcObject = stream;
                video.play();
            })
            .catch(function(error) {
                console.error('❌ Webcam-Fehler:', error);
            });
        } else {
            console.error('❌ getUserMedia nicht unterstützt');
        }
    } else {
        console.log('⚠️ Kein Video-Element gefunden');
        console.log('Verfügbare Video-Elemente:', document.querySelectorAll('video'));
    }
});
EOF
    
    sudo chown www-data:www-data /home/pi/mitgliederverwaltung/staticfiles/js/main.js
    sudo chmod 644 /home/pi/mitgliederverwaltung/staticfiles/js/main.js
    
    echo "✅ Webcam-Placeholder main.js erstellt"
fi

# 9. CSS auch reparieren
echo ""
echo "=== CSS REPARIEREN ==="
if [ ! -f "/home/pi/mitgliederverwaltung/staticfiles/css/style.css" ]; then
    echo "Erstelle basis style.css..."
    sudo mkdir -p /home/pi/mitgliederverwaltung/staticfiles/css/
    
    sudo tee /home/pi/mitgliederverwaltung/staticfiles/css/style.css > /dev/null << 'EOF'
/* Basis-Styling für Webcam */
video {
    max-width: 100%;
    height: auto;
    border: 2px solid #ccc;
    border-radius: 8px;
}

.webcam-container {
    text-align: center;
    margin: 20px 0;
}

button {
    padding: 10px 20px;
    margin: 5px;
    background: #007cba;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}

button:hover {
    background: #005a87;
}
EOF
    
    sudo chown www-data:www-data /home/pi/mitgliederverwaltung/staticfiles/css/style.css
    sudo chmod 644 /home/pi/mitgliederverwaltung/staticfiles/css/style.css
    
    echo "✅ basis style.css erstellt"
fi

# 10. Nginx neu starten
echo ""
echo "🔄 Nginx neu starten..."
sudo systemctl restart nginx

# 11. Final test
echo ""
echo "=== FINAL TESTS ==="
echo "main.js Test:"
curl -k -s -o /dev/null -w "main.js: %{http_code}\n" https://192.168.1.136/static/js/main.js

echo "style.css Test:"
curl -k -s -o /dev/null -w "style.css: %{http_code}\n" https://192.168.1.136/static/css/style.css

echo ""
echo "=== WEBCAM DEBUGGING ==="
echo "💡 Für weitere Webcam-Diagnose:"
echo "1. Browser: F12 → Console"
echo "2. Schauen Sie nach Video-Elementen: \$('video')"
echo "3. Prüfen Sie getUserMedia: navigator.mediaDevices"
echo ""
echo "🧪 JETZT TESTEN:"
echo "1. Browser-Cache löschen (Strg+Shift+Entf)"
echo "2. https://192.168.1.136 aufrufen"
echo "3. Webcam-Feature testen"
echo "4. F12 → Console für Debug-Meldungen"
