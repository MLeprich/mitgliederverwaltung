#!/bin/bash
# HTTPS Setup für Mitgliederverwaltung auf Raspberry Pi

echo "🔒 HTTPS-Zertifikat für Webcam-Funktionalität erstellen..."

# 1. SSL-Verzeichnis erstellen
sudo mkdir -p /etc/ssl/mitgliederverwaltung
cd /etc/ssl/mitgliederverwaltung

# 2. Privaten Schlüssel generieren
sudo openssl genrsa -out mitgliederverwaltung.key 2048

# 3. Selbstsigniertes Zertifikat erstellen (gültig für 1 Jahr)
sudo openssl req -new -x509 -key mitgliederverwaltung.key -out mitgliederverwaltung.crt -days 365 -subj "/C=DE/ST=Lower Saxony/L=Hannover/O=Feuerwehr/OU=IT/CN=192.168.1.136"

# 4. Berechtigungen setzen
sudo chmod 600 /etc/ssl/mitgliederverwaltung/mitgliederverwaltung.key
sudo chmod 644 /etc/ssl/mitgliederverwaltung/mitgliederverwaltung.crt
sudo chown root:root /etc/ssl/mitgliederverwaltung/*

echo "✅ Zertifikat erstellt in /etc/ssl/mitgliederverwaltung/"

# 5. Nginx HTTPS-Konfiguration erstellen
sudo tee /etc/nginx/sites-available/mitgliederverwaltung-https > /dev/null << 'EOF'
# HTTPS Configuration für Mitgliederverwaltung
server {
    listen 80;
    server_name 192.168.1.136;
    
    # HTTP zu HTTPS weiterleiten
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name 192.168.1.136;
    
    # SSL-Zertifikate
    ssl_certificate /etc/ssl/mitgliederverwaltung/mitgliederverwaltung.crt;
    ssl_certificate_key /etc/ssl/mitgliederverwaltung/mitgliederverwaltung.key;
    
    # SSL-Sicherheitseinstellungen
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    
    # Static Files
    location /static/ {
        alias /home/pi/mitgliederverwaltung/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Media Files  
    location /media/ {
        alias /home/pi/mitgliederverwaltung/media/;
        expires 7d;
    }
    
    # Django App
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Host $server_name;
        
        # Webcam-spezifische Headers
        proxy_buffering off;
        proxy_request_buffering off;
    }
}
EOF

# 6. Alte Konfiguration deaktivieren, neue aktivieren
sudo rm -f /etc/nginx/sites-enabled/mitgliederverwaltung
sudo ln -s /etc/nginx/sites-available/mitgliederverwaltung-https /etc/nginx/sites-enabled/

# 7. Nginx-Konfiguration testen
sudo nginx -t

if [ $? -eq 0 ]; then
    echo "✅ Nginx-Konfiguration ist gültig"
    
    # 8. Nginx neu starten
    sudo systemctl reload nginx
    
    echo ""
    echo "🎉 HTTPS ist jetzt aktiv!"
    echo ""
    echo "📋 Nächste Schritte:"
    echo "1. Öffnen Sie: https://192.168.1.136"
    echo "2. Browser wird Sicherheitswarnung zeigen"
    echo "3. Klicken Sie 'Erweitert' → 'Trotzdem fortfahren'"
    echo "4. Webcam-Funktionalität sollte jetzt funktionieren"
    echo ""
    echo "💡 Tipp: Zertifikat dem Browser als vertrauenswürdig hinzufügen:"
    echo "   Chrome: Einstellungen → Datenschutz → Zertifikate verwalten"
    echo "   Firefox: Einstellungen → Datenschutz → Zertifikate anzeigen"
    
else
    echo "❌ Nginx-Konfigurationsfehler - bitte prüfen"
    sudo nginx -t
fi