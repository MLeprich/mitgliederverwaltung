# 🆔 Mitgliederverwaltung Dashboard

Ein Django-basiertes Web-Dashboard für die Verwaltung von Mitgliederdaten zur Erstellung von Dienstausweisen.

![Dashboard Preview](docs/dashboard-preview.png)

## ✨ Features

- **🌐 Moderne Web-Oberfläche** mit Bootstrap 5
- **👥 Vollständige Mitgliederverwaltung** (Erstellen, Bearbeiten, Löschen, Anzeigen)
- **📄 CSV/Excel Import/Export** für Massendatenverarbeitung
- **🖼️ Profilbild-Upload** mit automatischer Umbenennung
- **🔍 Such- und Filterfunktionen**
- **📊 Dashboard mit Statistiken**
- **🔐 Benutzerauthentifizierung**
- **📱 Responsive Design** für alle Geräte
- **🔗 Cardpresso-Integration** vorbereitet

## 🚀 Installation

### Voraussetzungen
- Raspberry Pi 4 (oder Linux Server)
- Python 3.8+
- Git

### Schnellinstallation

```bash
# Repository klonen
git clone https://github.com/DEIN-USERNAME/mitgliederverwaltung.git
cd mitgliederverwaltung

# Virtual Environment erstellen
python3 -m venv venv
source venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt

# Environment-Datei erstellen
cp .env.template .env
# Bearbeite .env mit deinen Einstellungen!

# Datenbank einrichten
python manage.py migrate

# Superuser erstellen
python manage.py createsuperuser

# Static Files sammeln
python manage.py collectstatic

# Development Server starten
python manage.py runserver 0.0.0.0:8000
