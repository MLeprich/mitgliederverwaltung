#!/bin/bash
# Firewall für HTTPS reparieren

echo "🔥 Firewall-Regeln für HTTPS korrigieren..."

# 1. Port 443 zur Firewall hinzufügen
echo "Port 443 (HTTPS) hinzufügen..."
sudo ufw allow 443

# 2. Aktuelle Firewall-Regeln anzeigen
echo ""
echo "=== AKTUELLE FIREWALL-REGELN ==="
sudo ufw status numbered

# 3. Services-Status prüfen
echo ""
echo "=== SERVICE STATUS ==="
echo "Django läuft auf:"
sudo netstat -tlnp | grep :8000

echo ""
echo "Nginx läuft auf:"
sudo netstat -tlnp | grep -E ":(80|443)"

# 4. Direkte Verbindungstests
echo ""
echo "=== VERBINDUNGSTESTS ==="

echo "Test 1: Django direkt (localhost:8000)"
curl -s -o /dev/null -w "HTTP-Code: %{http_code}, Zeit: %{time_total}s\n" http://127.0.0.1:8000/ || echo "Fehler beim Django-Test"

echo ""
echo "Test 2: HTTP über Nginx (Port 80)"
curl -s -o /dev/null -w "HTTP-Code: %{http_code}, Zeit: %{time_total}s\n" http://192.168.1.136/ || echo "Fehler beim HTTP-Test"

echo ""
echo "Test 3: HTTPS über Nginx (Port 443)"
curl -s -k -o /dev/null -w "HTTP-Code: %{http_code}, Zeit: %{time_total}s\n" https://192.168.1.136/ || echo "Fehler beim HTTPS-Test"

# 5. Nginx-Konfiguration prüfen
echo ""
echo "=== NGINX KONFIGURATION ==="
echo "Aktive Nginx-Sites:"
ls -la /etc/nginx/sites-enabled/

echo ""
echo "Nginx-Konfiguration testen:"
sudo nginx -t

# 6. Prozesse prüfen
echo ""
echo "=== AKTIVE PROZESSE ==="
echo "Nginx-Prozesse:"
ps aux | grep nginx | grep -v grep

echo ""
echo "Django/Gunicorn-Prozesse:"
ps aux | grep gunicorn | grep -v grep

# 7. Aktuelle Logs
echo ""
echo "=== AKTUELLE LOGS ==="
echo "Nginx Access Log (letzte 5 Zeilen):"
sudo tail -5 /var/log/nginx/access.log 2>/dev/null || echo "Keine Access-Logs"

echo ""
echo "Nginx Error Log (letzte 5 Zeilen):"
sudo tail -5 /var/log/nginx/error.log 2>/dev/null || echo "Keine Error-Logs"

echo ""
echo "=== LÖSUNGSSCHRITTE ==="
echo "✅ Port 443 zur Firewall hinzugefügt"
echo ""
echo "🧪 Jetzt testen:"
echo "1. HTTP:  http://192.168.1.136"
echo "2. HTTPS: https://192.168.1.136"
echo ""
echo "Falls weiterhin Probleme:"
echo "• Browser-Cache löschen"
echo "• Anderen Browser versuchen"
echo "• Inkognito-Modus verwenden"
