#!/bin/bash
# Webcam Problem durch inline JavaScript lösen

echo "📷 Webcam Problem durch inline JavaScript lösen..."

cd /home/pi/mitgliederverwaltung

# 1. Template-Dateien finden
echo "=== TEMPLATE-DATEIEN FINDEN ==="
echo "HTML-Templates im Projekt:"
find . -name "*.html" -not -path "./venv/*" | head -10

echo ""
echo "Templates die 'main.js' referenzieren:"
find . -name "*.html" -exec grep -l "main.js" {} \; 2>/dev/null

# 2. Webcam-bezogene Templates finden
echo ""
echo "=== WEBCAM-TEMPLATES FINDEN ==="
echo "Templates mit 'webcam' oder 'camera':"
find . -name "*.html" -exec grep -l -i "webcam\|camera\|video" {} \; 2>/dev/null

echo ""
echo "Templates mit getUserMedia:"
find . -name "*.html" -exec grep -l "getUserMedia" {} \; 2>/dev/null

# 3. Haupttemplate finden (wahrscheinlich add.html basierend auf Console-Logs)
echo ""
echo "=== HAUPTTEMPLATE IDENTIFIZIEREN ==="
echo "Templates mit 'add' im Namen:"
find . -name "*add*.html" -o -name "*camera*.html" -o -name "*webcam*.html"

echo ""
echo "Schauen wir in alle HTML-Dateien nach Video-Elementen:"
for html_file in $(find . -name "*.html" -not -path "./venv/*"); do
    if grep -q "video\|webcam\|camera" "$html_file" 2>/dev/null; then
        echo "=== $html_file ==="
        grep -n -A2 -B2 "video\|webcam\|camera\|main.js" "$html_file" 2>/dev/null || echo "Keine relevanten Matches"
        echo ""
    fi
done

# 4. Backup erstellen und Template modifizieren
echo ""
echo "=== TEMPLATE MODIFIKATION ==="

# Das wahrscheinliche Template finden
TEMPLATE_FILE=""
for possible in $(find . -name "*.html" -exec grep -l "main.js" {} \; 2>/dev/null); do
    echo "Prüfe Template: $possible"
    if grep -q "webcam\|video\|camera" "$possible" 2>/dev/null; then
        TEMPLATE_FILE="$possible"
        echo "✅ Webcam-Template gefunden: $TEMPLATE_FILE"
        break
    fi
done

if [ -z "$TEMPLATE_FILE" ]; then
    echo "Template nicht automatisch gefunden. Schauen wir in templates/:"
    find . -path "*/templates/*" -name "*.html" | head -5
    
    # Fallback: das erste Template mit main.js
    TEMPLATE_FILE=$(find . -name "*.html" -exec grep -l "main.js" {} \; 2>/dev/null | head -1)
    echo "Verwende als Fallback: $TEMPLATE_FILE"
fi

if [ -n "$TEMPLATE_FILE" ] && [ -f "$TEMPLATE_FILE" ]; then
    echo ""
    echo "=== TEMPLATE BACKUP UND PATCH ==="
    
    # Backup erstellen
    cp "$TEMPLATE_FILE" "${TEMPLATE_FILE}.backup"
    echo "✅ Backup erstellt: ${TEMPLATE_FILE}.backup"
    
    echo ""
    echo "Aktueller Template-Inhalt (relevante Teile):"
    grep -n -A5 -B5 "main.js\|video\|webcam" "$TEMPLATE_FILE" || echo "Keine main.js/video Referenzen gefunden"
    
    echo ""
    echo "=== INLINE JAVASCRIPT HINZUFÜGEN ==="
    
    # Inline JavaScript für Webcam erstellen
    cat << 'EOF' > /tmp/webcam_inline.js

<script>
console.log('📷 Inline Webcam Script geladen');

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM geladen, suche Video-Element...');
    
    // Verschiedene mögliche Video-Element Selektoren
    const videoSelectors = [
        'video',
        '#webcam-video', 
        '#video',
        '.webcam',
        '.video',
        '[data-webcam]'
    ];
    
    let video = null;
    for (let selector of videoSelectors) {
        video = document.querySelector(selector);
        if (video) {
            console.log('📹 Video-Element gefunden mit Selector:', selector);
            break;
        }
    }
    
    if (!video) {
        console.log('⚠️ Kein Video-Element gefunden. Erstelle eins...');
        // Video-Element erstellen falls es fehlt
        video = document.createElement('video');
        video.id = 'webcam-video';
        video.autoplay = true;
        video.muted = true;
        video.style.maxWidth = '100%';
        video.style.height = 'auto';
        video.style.border = '2px solid #ccc';
        
        // Webcam-Container finden oder erstellen
        let container = document.querySelector('.webcam-container') || 
                       document.querySelector('#webcam-container') ||
                       document.body;
        
        container.appendChild(video);
        console.log('📹 Video-Element erstellt und hinzugefügt');
    }
    
    // Webcam starten
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        console.log('🎥 Starte Webcam...');
        
        navigator.mediaDevices.getUserMedia({ 
            video: { 
                width: { ideal: 1280 }, 
                height: { ideal: 720 },
                facingMode: 'user'
            } 
        })
        .then(function(stream) {
            console.log('✅ Webcam-Stream erhalten');
            video.srcObject = stream;
            
            video.onloadedmetadata = function() {
                console.log('📷 Video-Metadaten geladen');
                console.log('📐 Tatsächliche Videoauflösung:', video.videoWidth + 'x' + video.videoHeight);
            };
            
            return video.play();
        })
        .then(function() {
            console.log('▶️ Video-Wiedergabe gestartet');
        })
        .catch(function(error) {
            console.error('❌ Webcam-Fehler:', error);
            console.error('Error name:', error.name);
            console.error('Error message:', error.message);
        });
    } else {
        console.error('❌ getUserMedia nicht unterstützt');
        console.log('Available:', {
            navigator: !!navigator,
            mediaDevices: !!navigator.mediaDevices,
            getUserMedia: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)
        });
    }
    
    // Foto-Aufnahme-Funktion (falls Button vorhanden)
    const captureButton = document.querySelector('[data-capture]') || 
                         document.querySelector('#capture') ||
                         document.querySelector('.capture-btn');
    
    if (captureButton) {
        captureButton.addEventListener('click', function() {
            if (video && video.srcObject) {
                const canvas = document.createElement('canvas');
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                
                const ctx = canvas.getContext('2d');
                ctx.drawImage(video, 0, 0);
                
                console.log('📸 Foto aufgenommen:', canvas.width + 'x' + canvas.height);
                
                // Hier können Sie das Foto weiterverarbeiten
                // z.B. als Data-URL: canvas.toDataURL('image/jpeg')
            }
        });
    }
});
</script>

EOF
    
    echo "✅ Inline JavaScript erstellt"
    
    # JavaScript am Ende des Templates einfügen (vor </body> oder </html>)
    if grep -q "</body>" "$TEMPLATE_FILE"; then
        sed -i '/<\/body>/i\
'"$(cat /tmp/webcam_inline.js)" "$TEMPLATE_FILE"
        echo "✅ JavaScript vor </body> eingefügt"
    elif grep -q "</html>" "$TEMPLATE_FILE"; then
        sed -i '/<\/html>/i\
'"$(cat /tmp/webcam_inline.js)" "$TEMPLATE_FILE"
        echo "✅ JavaScript vor </html> eingefügt"
    else
        echo "$(cat $TEMPLATE_FILE)" > /tmp/template_new
        echo "" >> /tmp/template_new
        cat /tmp/webcam_inline.js >> /tmp/template_new
        cp /tmp/template_new "$TEMPLATE_FILE"
        echo "✅ JavaScript am Ende der Datei hinzugefügt"
    fi
    
    echo ""
    echo "=== TEMPLATE MODIFIKATION ABGESCHLOSSEN ==="
    echo "Modifiziertes Template: $TEMPLATE_FILE"
    echo "Backup verfügbar: ${TEMPLATE_FILE}.backup"
    
else
    echo "❌ Kein geeignetes Template gefunden!"
    echo "🔍 Manuelle Suche erforderlich:"
    echo "Schauen Sie in diese Verzeichnisse:"
    find . -type d -name templates
fi

# 5. Django Development Server neu starten
echo ""
echo "🔄 Django Service neu starten..."
sudo systemctl restart mitgliederverwaltung

# 6. Test-Anweisungen
echo ""
echo "=== TESTING ==="
echo "✅ Inline JavaScript wurde hinzugefügt"
echo ""
echo "🧪 JETZT TESTEN:"
echo "1. Browser-Cache KOMPLETT löschen"
echo "2. https://192.168.1.136 aufrufen"
echo "3. F12 → Console öffnen"
echo "4. Schauen Sie nach: '📷 Inline Webcam Script geladen'"
echo "5. Webcam-Permission erneut genehmigen"
echo "6. Video-Preview sollte erscheinen!"
echo ""
echo "🔧 Falls Video-Element fehlt:"
echo "Das Script erstellt automatisch ein Video-Element"
echo ""
echo "🎯 Erwartete Console-Ausgaben:"
echo "- 📷 Inline Webcam Script geladen"
echo "- 🚀 DOM geladen, suche Video-Element..."
echo "- 📹 Video-Element gefunden"
echo "- ✅ Webcam-Stream erhalten"
echo "- ▶️ Video-Wiedergabe gestartet"

# Cleanup
rm -f /tmp/webcam_inline.js /tmp/template_new

echo ""
echo "💡 Falls weiterhin kein Video:"
echo "Teilen Sie die Browser-Console-Ausgaben mit!"
