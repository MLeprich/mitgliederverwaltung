#!/bin/bash
# Installation Script Teil 1: Django Projekt Grundkonfiguration
# Ausführen mit: bash install_part1.sh

set -e  # Script bei Fehler beenden

echo "=== Mitgliederverwaltung Dashboard - Teil 1: Grundkonfiguration ==="
echo ""

# Farben für Output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Funktion für farbige Ausgabe
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Prüfen ob Virtual Environment aktiv ist
if [[ "$VIRTUAL_ENV" != "" ]]; then
    print_status "Virtual Environment ist aktiv: $VIRTUAL_ENV"
else
    print_error "Bitte Virtual Environment aktivieren:"
    echo "cd ~/mitgliederverwaltung && source venv/bin/activate"
    exit 1
fi

# Arbeitsverzeichnis prüfen
if false; then
    print_error "Verzeichnis ~/mitgliederverwaltung nicht gefunden!"
    exit 1
fi

cd ~/mitgliederverwaltung

print_status "Erstelle Django Projekt..."

# Django Projekt erstellen
django-admin startproject mitgliederverwaltung .

# Haupt-App erstellen
python manage.py startapp members

print_status "Erstelle Verzeichnisstruktur..."

# Verzeichnisse erstellen
mkdir -p {templates,static/{css,js,img},media/profile_pics,uploads,logs}

print_status "Erstelle requirements.txt..."

# Requirements erstellen
cat > requirements.txt << 'EOF'
Django==4.2.13
Pillow==10.0.0
pandas==2.0.3
openpyxl==3.1.2
django-crispy-forms==2.0
crispy-bootstrap4==2022.1
gunicorn==21.2.0
python-decouple==3.8
whitenoise==6.5.0
EOF

print_status "Installiere Python Packages..."
pip install -r requirements.txt

print_status "Erstelle .env Datei für Konfiguration..."

# .env Datei erstellen
cat > .env << 'EOF'
# Django Settings
SECRET_KEY=django-insecure-change-this-in-production-123456789abcdef
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.100,192.168.1.101

# Database
DATABASE_NAME=db.sqlite3

# Media Settings
MEDIA_ROOT=/home/pi/mitgliederverwaltung/media
STATIC_ROOT=/home/pi/mitgliederverwaltung/staticfiles

# Upload Settings
MAX_UPLOAD_SIZE=10485760  # 10MB
ALLOWED_IMAGE_TYPES=jpg,jpeg,png
ALLOWED_IMPORT_TYPES=csv,xlsx,xls
EOF

print_status "Konfiguriere Django Settings..."

# Django Settings überschreiben
cat > mitgliederverwaltung/settings.py << 'EOF'
"""
Django settings for mitgliederverwaltung project.
"""

from pathlib import Path
from decouple import config, Csv
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'crispy_forms',
    'crispy_bootstrap4',
    
    # Local apps
    'members',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mitgliederverwaltung.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mitgliederverwaltung.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / config('DATABASE_NAME', default='db.sqlite3'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'de-de'
TIME_ZONE = 'Europe/Berlin'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = config('STATIC_ROOT', default=BASE_DIR / 'staticfiles')

# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = config('MEDIA_ROOT', default=BASE_DIR / 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4"
CRISPY_TEMPLATE_PACK = "bootstrap4"

# Login/Logout URLs
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = config('MAX_UPLOAD_SIZE', default=10485760, cast=int)
DATA_UPLOAD_MAX_MEMORY_SIZE = config('MAX_UPLOAD_SIZE', default=10485760, cast=int)

# Custom Settings für Mitgliederverwaltung
ALLOWED_IMAGE_TYPES = config('ALLOWED_IMAGE_TYPES', default='jpg,jpeg,png', cast=Csv())
ALLOWED_IMPORT_TYPES = config('ALLOWED_IMPORT_TYPES', default='csv,xlsx,xls', cast=Csv())

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024*1024*5,  # 5MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['file', 'console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'members': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Security Settings (für Production)
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
EOF

print_status "Erstelle Haupt-URLs..."

# Haupt-URLs konfigurieren
cat > mitgliederverwaltung/urls.py << 'EOF'
"""
URL configuration for mitgliederverwaltung project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('members.urls')),
    
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]

# Media files serving (nur für Development)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
EOF

print_status "Konfiguriere Admin Interface..."

# Admin Interface anpassen
cat > mitgliederverwaltung/admin.py << 'EOF'
from django.contrib import admin
from django.contrib.admin import AdminSite

class MitgliederverwaltungAdminSite(AdminSite):
    site_header = "Mitgliederverwaltung Administration"
    site_title = "Mitgliederverwaltung Admin"
    index_title = "Willkommen zur Mitgliederverwaltung"

admin_site = MitgliederverwaltungAdminSite(name='mitgliederverwaltung_admin')
EOF

print_status "Erstelle erste Migration..."

# Erste Migration erstellen
python manage.py migrate

print_status "Erstelle logs/django.log..."
touch logs/django.log

print_success "Teil 1 abgeschlossen!"
echo ""
echo "Nächste Schritte:"
echo "1. bash install_part2.sh  # Models und Admin"
echo "2. bash install_part3.sh  # Templates und Static Files"
echo "3. bash install_part4.sh  # Views und Forms"
echo ""
echo "Zum Testen können Sie bereits das Admin Interface aufrufen:"
echo "python manage.py createsuperuser"
echo "python manage.py runserver 0.0.0.0:8000"
EOF