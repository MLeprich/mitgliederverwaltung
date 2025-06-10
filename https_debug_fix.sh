#!/bin/bash
# HTTPS Fehlerdiagnose und Reparatur für Mitgliederverwaltung

echo "🔍 Diagnose der HTTPS-Probleme..."

# 1. Service-Status prüfen
echo "=== SERVICE STATUS ==="
echo "Django Service:"
sudo systemctl status mitgliederverwaltung --no-pager -l

echo ""
echo "Nginx Status:"
sudo systemctl status nginx --no-pager -l

# 2. Port-Bindungen prüfen
echo ""
echo "=== PORT BINDUNGEN ==="
echo "Port 8000 (Django):"
sudo netstat -tlnp | grep :8000

echo ""
echo "Port 443 (HTTPS):"
sudo netstat -tlnp | grep :443

echo ""
echo "Port 80 (HTTP):"
sudo netstat -tlnp | grep :80

# 3. Nginx-Konfiguration testen
echo ""
echo "=== NGINX TESTS ==="
sudo nginx -t

# 4. Django Service korrigieren (localhost statt 0.0.0.0)
echo ""
echo "🔧 Django Service korrigieren..."

sudo tee /etc/systemd/system/mitgliederverwaltung.service > /dev/null << 'EOF'
[Unit]
Description=Mitgliederverwaltung Django App
After=network.target

[Service]
User=pi
Group=www-data
WorkingDirectory=/home/pi/mitgliederverwaltung
Environment="PATH=/home/pi/mitgliederverwaltung/venv/bin"
ExecStart=/home/pi/mitgliederverwaltung/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 mitgliederverwaltung.wsgi:application
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# 5. Services neu starten
echo "🔄 Services neu starten..."
sudo systemctl daemon-reload
sudo systemctl restart mitgliederverwaltung
sudo systemctl restart nginx

# 6. Kurz warten und Status prüfen
sleep 3

echo ""
echo "=== FINAL STATUS CHECK ==="
echo "Django Service:"
sudo systemctl is-active mitgliederverwaltung
echo "Nginx Service:"
sudo systemctl is-active nginx

# 7. Verbindungen testen
echo ""
echo "=== VERBINDUNGS-TESTS ==="
echo "Test Django direkt (127.0.0.1:8000):"
timeout 5 curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ || echo "Timeout/Fehler"

echo ""
echo "Test HTTP (Port 80):"
timeout 5 curl -s -o /dev/null -w "%{http_code}" http://192.168.1.136/ || echo "Timeout/Fehler"

echo ""
echo "Test HTTPS (Port 443):"
timeout 5 curl -s -k -o /dev/null -w "%{http_code}" https://192.168.1.136/ || echo "Timeout/Fehler"

# 8. Firewall prüfen
echo ""
echo "=== FIREWALL STATUS ==="
sudo ufw status || echo "UFW nicht aktiv"

# 9. Log-Einträge anzeigen
echo ""
echo "=== AKTUELLE LOGS ==="
echo "Nginx Error Log (letzte 10 Zeilen):"
sudo tail -10 /var/log/nginx/error.log 2>/dev/null || echo "Keine Error-Logs"

echo ""
echo "Django Service Logs (letzte 10 Zeilen):"
sudo journalctl -u mitgliederverwaltung -n 10 --no-pager

echo ""
echo "=== ZUSAMMENFASSUNG ==="
echo "✅ Django Service sollte jetzt auf 127.0.0.1:8000 laufen"
echo "✅ Nginx leitet von Port 80/443 an Django weiter"
echo ""
echo "Wenn immer noch Probleme bestehen:"
echo "1. Prüfen Sie die Logs oben"
echo "2. Firewall-Regeln überprüfen"
echo "3. Django-Anwendung direkt testen: http://127.0.0.1:8000"
echo ""
echo "🌐 Jetzt testen: https://192.168.1.136"
