#!/bin/bash
# Installation Script Teil 3: Templates und Static Files
# Ausführen mit: bash install_part3.sh

set -e

echo "=== Mitgliederverwaltung Dashboard - Teil 3: Templates und Static Files ==="
echo ""

# Farben für Output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Virtual Environment prüfen
if [[ "$VIRTUAL_ENV" == "" ]]; then
    print_error "Bitte Virtual Environment aktivieren!"
    exit 1
fi

cd ~/mitgliederverwaltung

print_status "Erstelle Template-Verzeichnisse..."

# Template-Verzeichnisse erstellen
mkdir -p templates/{registration,members,partials}

print_status "Erstelle Base Template..."

# Base Template
cat > templates/base.html << 'EOF'
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Mitgliederverwaltung{% endblock %}</title>
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Font Awesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- Custom CSS -->
    <link rel="stylesheet" href="{% load static %}{% static 'css/style.css' %}">
    
    {% block extra_css %}{% endblock %}
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <div class="container">
            <a class="navbar-brand" href="{% url 'members:dashboard' %}">
                <i class="fas fa-id-card me-2"></i>
                Mitgliederverwaltung
            </a>
            
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">
                    {% if user.is_authenticated %}
                    <li class="nav-item">
                        <a class="nav-link {% if request.resolver_match.url_name == 'dashboard' %}active{% endif %}" 
                           href="{% url 'members:dashboard' %}">
                            <i class="fas fa-tachometer-alt me-1"></i>Dashboard
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.resolver_match.url_name == 'member_list' %}active{% endif %}" 
                           href="{% url 'members:member_list' %}">
                            <i class="fas fa-users me-1"></i>Mitglieder
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.resolver_match.url_name == 'member_add' %}active{% endif %}" 
                           href="{% url 'members:member_add' %}">
                            <i class="fas fa-user-plus me-1"></i>Hinzufügen
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link {% if request.resolver_match.url_name == 'import_data' %}active{% endif %}" 
                           href="{% url 'members:import_data' %}">
                            <i class="fas fa-file-import me-1"></i>Import
                        </a>
                    </li>
                    {% endif %}
                </ul>
                
                <ul class="navbar-nav">
                    {% if user.is_authenticated %}
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="navbarDropdown" role="button" data-bs-toggle="dropdown">
                            <i class="fas fa-user me-1"></i>{{ user.username }}
                        </a>
                        <ul class="dropdown-menu">
                            {% if user.is_staff %}
                            <li><a class="dropdown-item" href="/admin/"><i class="fas fa-cog me-2"></i>Admin</a></li>
                            <li><hr class="dropdown-divider"></li>
                            {% endif %}
                            <li><a class="dropdown-item" href="{% url 'logout' %}"><i class="fas fa-sign-out-alt me-2"></i>Abmelden</a></li>
                        </ul>
                    </li>
                    {% endif %}
                </ul>
            </div>
        </div>
    </nav>

    <!-- Messages -->
    {% if messages %}
    <div class="container mt-3">
        {% for message in messages %}
        <div class="alert alert-{{ message.tags }} alert-dismissible fade show" role="alert">
            {% if message.tags == 'error' %}
                <i class="fas fa-exclamation-circle me-2"></i>
            {% elif message.tags == 'success' %}
                <i class="fas fa-check-circle me-2"></i>
            {% elif message.tags == 'warning' %}
                <i class="fas fa-exclamation-triangle me-2"></i>
            {% else %}
                <i class="fas fa-info-circle me-2"></i>
            {% endif %}
            {{ message }}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        {% endfor %}
    </div>
    {% endif %}

    <!-- Main Content -->
    <main class="container mt-4">
        {% block breadcrumb %}{% endblock %}
        {% block content %}{% endblock %}
    </main>

    <!-- Footer -->
    <footer class="bg-light mt-5 py-4">
        <div class="container">
            <div class="row">
                <div class="col-md-6">
                    <p class="text-muted mb-0">
                        <i class="fas fa-id-card me-1"></i>
                        Mitgliederverwaltung Dashboard
                    </p>
                </div>
                <div class="col-md-6 text-end">
                    <p class="text-muted mb-0">
                        <small>Version 1.0 - {{ "now"|date:"Y" }}</small>
                    </p>
                </div>
            </div>
        </div>
    </footer>

    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <!-- Custom JS -->
    <script src="{% load static %}{% static 'js/main.js' %}"></script>
    
    {% block extra_js %}{% endblock %}
</body>
</html>
EOF

print_status "Erstelle Login Template..."

# Login Template
cat > templates/registration/login.html << 'EOF'
{% extends 'base.html' %}
{% load crispy_forms_tags %}

{% block title %}Anmelden - Mitgliederverwaltung{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6 col-lg-4">
        <div class="card shadow">
            <div class="card-body">
                <div class="text-center mb-4">
                    <i class="fas fa-id-card fa-3x text-primary mb-3"></i>
                    <h2 class="card-title">Anmelden</h2>
                    <p class="text-muted">Mitgliederverwaltung Dashboard</p>
                </div>
                
                <form method="post">
                    {% csrf_token %}
                    {% if form.non_field_errors %}
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-circle me-2"></i>
                            {{ form.non_field_errors }}
                        </div>
                    {% endif %}
                    
                    <div class="mb-3">
                        <label for="{{ form.username.id_for_label }}" class="form-label">
                            <i class="fas fa-user me-1"></i>Benutzername
                        </label>
                        {{ form.username|add_class:"form-control" }}
                        {% if form.username.errors %}
                            <div class="text-danger small mt-1">{{ form.username.errors }}</div>
                        {% endif %}
                    </div>
                    
                    <div class="mb-3">
                        <label for="{{ form.password.id_for_label }}" class="form-label">
                            <i class="fas fa-lock me-1"></i>Passwort
                        </label>
                        {{ form.password|add_class:"form-control" }}
                        {% if form.password.errors %}
                            <div class="text-danger small mt-1">{{ form.password.errors }}</div>
                        {% endif %}
                    </div>
                    
                    <div class="d-grid">
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-sign-in-alt me-2"></i>Anmelden
                        </button>
                    </div>
                </form>
            </div>
        </div>
        
        <div class="text-center mt-3">
            <small class="text-muted">
                <i class="fas fa-shield-alt me-1"></i>
                Sicherer Zugang zur Mitgliederverwaltung
            </small>
        </div>
    </div>
</div>
{% endblock %}
EOF

print_status "Erstelle Dashboard Template..."

# Dashboard Template
cat > templates/dashboard.html << 'EOF'
{% extends 'base.html' %}
{% load static %}

{% block title %}Dashboard - Mitgliederverwaltung{% endblock %}

{% block breadcrumb %}
<nav aria-label="breadcrumb">
    <ol class="breadcrumb">
        <li class="breadcrumb-item active">
            <i class="fas fa-tachometer-alt me-1"></i>Dashboard
        </li>
    </ol>
</nav>
{% endblock %}

{% block content %}
<div class="row">
    <div class="col-12">
        <h1 class="h3 mb-4">
            <i class="fas fa-tachometer-alt me-2"></i>
            Dashboard
            <small class="text-muted">Übersicht</small>
        </h1>
    </div>
</div>

<!-- Statistik Cards -->
<div class="row mb-4">
    <div class="col-xl-3 col-md-6 mb-4">
        <div class="card border-left-primary shadow h-100 py-2">
            <div class="card-body">
                <div class="row no-gutters align-items-center">
                    <div class="col mr-2">
                        <div class="text-xs font-weight-bold text-primary text-uppercase mb-1">
                            Aktive Mitglieder
                        </div>
                        <div class="h5 mb-0 font-weight-bold text-gray-800" id="active-members-count">
                            {{ stats.active_members }}
                        </div>
                    </div>
                    <div class="col-auto">
                        <i class="fas fa-users fa-2x text-gray-300"></i>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="col-xl-3 col-md-6 mb-4">
        <div class="card border-left-success shadow h-100 py-2">
            <div class="card-body">
                <div class="row no-gutters align-items-center">
                    <div class="col mr-2">
                        <div class="text-xs font-weight-bold text-success text-uppercase mb-1">
                            Gültige Ausweise
                        </div>
                        <div class="h5 mb-0 font-weight-bold text-gray-800" id="valid-cards-count">
                            {{ stats.valid_cards }}
                        </div>
                    </div>
                    <div class="col-auto">
                        <i class="fas fa-id-card fa-2x text-gray-300"></i>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="col-xl-3 col-md-6 mb-4">
        <div class="card border-left-warning shadow h-100 py-2">
            <div class="card-body">
                <div class="row no-gutters align-items-center">
                    <div class="col mr-2">
                        <div class="text-xs font-weight-bold text-warning text-uppercase mb-1">
                            Laufen bald ab
                        </div>
                        <div class="h5 mb-0 font-weight-bold text-gray-800" id="expiring-soon-count">
                            {{ stats.expiring_soon }}
                        </div>
                    </div>
                    <div class="col-auto">
                        <i class="fas fa-exclamation-triangle fa-2x text-gray-300"></i>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="col-xl-3 col-md-6 mb-4">
        <div class="card border-left-danger shadow h-100 py-2">
            <div class="card-body">
                <div class="row no-gutters align-items-center">
                    <div class="col mr-2">
                        <div class="text-xs font-weight-bold text-danger text-uppercase mb-1">
                            Abgelaufen
                        </div>
                        <div class="h5 mb-0 font-weight-bold text-gray-800" id="expired-cards-count">
                            {{ stats.expired_cards }}
                        </div>
                    </div>
                    <div class="col-auto">
                        <i class="fas fa-times-circle fa-2x text-gray-300"></i>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="row">
    <!-- Schnellzugriff -->
    <div class="col-lg-6 mb-4">
        <div class="card shadow">
            <div class="card-header py-3">
                <h6 class="m-0 font-weight-bold text-primary">
                    <i class="fas fa-bolt me-2"></i>Schnellzugriff
                </h6>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-sm-6 mb-3">
                        <a href="{% url 'members:member_add' %}" class="btn btn-primary btn-block w-100">
                            <i class="fas fa-user-plus me-2"></i>
                            Neues Mitglied
                        </a>
                    </div>
                    <div class="col-sm-6 mb-3">
                        <a href="{% url 'members:import_data' %}" class="btn btn-success btn-block w-100">
                            <i class="fas fa-file-import me-2"></i>
                            Daten importieren
                        </a>
                    </div>
                    <div class="col-sm-6 mb-3">
                        <a href="{% url 'members:member_list' %}" class="btn btn-info btn-block w-100">
                            <i class="fas fa-list me-2"></i>
                            Alle Mitglieder
                        </a>
                    </div>
                    <div class="col-sm-6 mb-3">
                        <a href="{% url 'members:export_data' %}" class="btn btn-warning btn-block w-100">
                            <i class="fas fa-file-export me-2"></i>
                            Export
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Letzte Aktivitäten -->
    <div class="col-lg-6 mb-4">
        <div class="card shadow">
            <div class="card-header py-3">
                <h6 class="m-0 font-weight-bold text-primary">
                    <i class="fas fa-clock me-2"></i>Letzte Aktivitäten
                </h6>
            </div>
            <div class="card-body">
                {% if recent_members %}
                <div class="list-group list-group-flush">
                    {% for member in recent_members %}
                    <div class="list-group-item d-flex justify-content-between align-items-center px-0">
                        <div>
                            <h6 class="mb-1">{{ member.full_name }}</h6>
                            <small class="text-muted">
                                Hinzugefügt am {{ member.created_at|date:"d.m.Y H:i" }}
                            </small>
                        </div>
                        <a href="{% url 'members:member_detail' member.pk %}" class="btn btn-sm btn-outline-primary">
                            <i class="fas fa-eye"></i>
                        </a>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <p class="text-muted mb-0">Noch keine Mitglieder vorhanden.</p>
                {% endif %}
            </div>
        </div>
    </div>
</div>

<!-- Ablaufende Ausweise -->
{% if expiring_members %}
<div class="row">
    <div class="col-12">
        <div class="card shadow">
            <div class="card-header py-3">
                <h6 class="m-0 font-weight-bold text-warning">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Ausweise die bald ablaufen
                </h6>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-bordered table-hover">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Personalnummer</th>
                                <th>Gültig bis</th>
                                <th>Status</th>
                                <th>Aktionen</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for member in expiring_members %}
                            <tr>
                                <td>{{ member.full_name }}</td>
                                <td>{{ member.personnel_number|default:"-" }}</td>
                                <td>{{ member.valid_until|date:"d.m.Y" }}</td>
                                <td>
                                    {% if member.is_card_expired %}
                                        <span class="badge bg-danger">Abgelaufen</span>
                                    {% else %}
                                        <span class="badge bg-warning">Läuft bald ab</span>
                                    {% endif %}
                                </td>
                                <td>
                                    <a href="{% url 'members:member_edit' member.pk %}" class="btn btn-sm btn-primary">
                                        <i class="fas fa-edit"></i> Bearbeiten
                                    </a>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>
{% endif %}
{% endblock %}

{% block extra_css %}
<style>
.border-left-primary { border-left: 0.25rem solid #4e73df !important; }
.border-left-success { border-left: 0.25rem solid #1cc88a !important; }
.border-left-warning { border-left: 0.25rem solid #f6c23e !important; }
.border-left-danger { border-left: 0.25rem solid #e74a3b !important; }
</style>
{% endblock %}
EOF

print_status "Erstelle Member List Template..."

# Member List Template
cat > templates/members/member_list.html << 'EOF'
{% extends 'base.html' %}
{% load static %}

{% block title %}Mitglieder - Mitgliederverwaltung{% endblock %}

{% block breadcrumb %}
<nav aria-label="breadcrumb">
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="{% url 'members:dashboard' %}">Dashboard</a></li>
        <li class="breadcrumb-item active">Mitglieder</li>
    </ol>
</nav>
{% endblock %}

{% block content %}
<div class="row">
    <div class="col-12">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h1 class="h3">
                <i class="fas fa-users me-2"></i>
                Mitglieder
                <small class="text-muted">({{ object_list.count }} Einträge)</small>
            </h1>
            <a href="{% url 'members:member_add' %}" class="btn btn-primary">
                <i class="fas fa-user-plus me-2"></i>Neues Mitglied
            </a>
        </div>
    </div>
</div>

<!-- Filter und Suche -->
<div class="row mb-4">
    <div class="col-12">
        <div class="card">
            <div class="card-body">
                <form method="get" class="row g-3">
                    <div class="col-md-4">
                        <label for="search" class="form-label">Suche</label>
                        <div class="input-group">
                            <span class="input-group-text"><i class="fas fa-search"></i></span>
                            <input type="text" class="form-control" id="search" name="search" 
                                   value="{{ request.GET.search }}" placeholder="Name oder Personalnummer">
                        </div>
                    </div>
                    <div class="col-md-3">
                        <label for="status" class="form-label">Status</label>
                        <select class="form-select" id="status" name="status">
                            <option value="">Alle</option>
                            <option value="active" {% if request.GET.status == 'active' %}selected{% endif %}>Aktiv</option>
                            <option value="inactive" {% if request.GET.status == 'inactive' %}selected{% endif %}>Inaktiv</option>
                            <option value="expired" {% if request.GET.status == 'expired' %}selected{% endif %}>Abgelaufen</option>
                            <option value="expiring" {% if request.GET.status == 'expiring' %}selected{% endif %}>Läuft bald ab</option>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label for="sort" class="form-label">Sortierung</label>
                        <select class="form-select" id="sort" name="sort">
                            <option value="name" {% if request.GET.sort == 'name' %}selected{% endif %}>Name</option>
                            <option value="created" {% if request.GET.sort == 'created' %}selected{% endif %}>Erstellt</option>
                            <option value="valid_until" {% if request.GET.sort == 'valid_until' %}selected{% endif %}>Gültig bis</option>
                        </select>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">&nbsp;</label>
                        <div class="d-grid">
                            <button type="submit" class="btn btn-outline-primary">
                                <i class="fas fa-filter me-1"></i>Filter
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>

<!-- Mitgliederliste -->
<div class="row">
    <div class="col-12">
        <div class="card shadow">
            <div class="card-body">
                {% if object_list %}
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead class="table-light">
                            <tr>
                                <th>Bild</th>
                                <th>Name</th>
                                <th>Personalnummer</th>
                                <th>Geburtsdatum</th>
                                <th>Gültig bis</th>
                                <th>Status</th>
                                <th>Aktionen</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for member in object_list %}
                            <tr>
                                <td>
                                    {% if member.profile_picture %}
                                        <img src="{{ member.profile_picture.url }}" 
                                             class="rounded" width="40" height="50" 
                                             alt="{{ member.full_name }}">
                                    {% else %}
                                        <div class="bg-secondary rounded d-flex align-items-center justify-content-center" 
                                             style="width: 40px; height: 50px;">
                                            <i class="fas fa-user text-white"></i>
                                        </div>
                                    {% endif %}
                                </td>
                                <td>
                                    <strong>{{ member.full_name }}</strong>
                                    {% if not member.is_active %}
                                        <br><small class="text-muted">(Inaktiv)</small>
                                    {% endif %}
                                </td>
                                <td>{{ member.personnel_number|default:"-" }}</td>
                                <td>{{ member.birth_date|date:"d.m.Y" }}</td>
                                <td>{{ member.valid_until|date:"d.m.Y" }}</td>
                                <td>
                                    {% if member.is_card_expired %}
                                        <span class="badge bg-danger">Abgelaufen</span>
                                    {% elif member.expires_soon %}
                                        <span class="badge bg-warning">Läuft bald ab</span>
                                    {% else %}
                                        <span class="badge bg-success">Gültig</span>
                                    {% endif %}
                                </td>
                                <td>
                                    <div class="btn-group" role="group">
                                        <a href="{% url 'members:member_detail' member.pk %}" 
                                           class="btn btn-sm btn-outline-info" title="Details">
                                            <i class="fas fa-eye"></i>
                                        </a>
                                        <a href="{% url 'members:member_edit' member.pk %}" 
                                           class="btn btn-sm btn-outline-primary" title="Bearbeiten">
                                            <i class="fas fa-edit"></i>
                                        </a>
                                        <a href="{% url 'members:member_delete' member.pk %}" 
                                           class="btn btn-sm btn-outline-danger" title="Löschen"
                                           onclick="return confirm('Mitglied {{ member.full_name }} wirklich löschen?')">
                                            <i class="fas fa-trash"></i>
                                        </a>
                                    </div>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>

                <!-- Pagination -->
                {% if is_paginated %}
                <nav aria-label="Mitglieder Navigation">
                    <ul class="pagination justify-content-center">
                        {% if page_obj.has_previous %}
                            <li class="page-item">
                                <a class="page-link" href="?page=1{% if request.GET.search %}&search={{ request.GET.search }}{% endif %}{% if request.GET.status %}&status={{ request.GET.status }}{% endif %}{% if request.GET.sort %}&sort={{ request.GET.sort }}{% endif %}">Erste</a>
                            </li>
                            <li class="page-item">
                                <a class="page-link" href="?page={{ page_obj.previous_page_number }}{% if request.GET.search %}&search={{ request.GET.search }}{% endif %}{% if request.GET.status %}&status={{ request.GET.status }}{% endif %}{% if request.GET.sort %}&sort={{ request.GET.sort }}{% endif %}">Zurück</a>
                            </li>
                        {% endif %}

                        <li class="page-item active">
                            <span class="page-link">
                                Seite {{ page_obj.number }} von {{ page_obj.paginator.num_pages }}
                            </span>
                        </li>

                        {% if page_obj.has_next %}
                            <li class="page-item">
                                <a class="page-link" href="?page={{ page_obj.next_page_number }}{% if request.GET.search %}&search={{ request.GET.search }}{% endif %}{% if request.GET.status %}&status={{ request.GET.status }}{% endif %}{% if request.GET.sort %}&sort={{ request.GET.sort }}{% endif %}">Weiter</a>
                            </li>
                            <li class="page-item">
                                <a class="page-link" href="?page={{ page_obj.paginator.num_pages }}{% if request.GET.search %}&search={{ request.GET.search }}{% endif %}{% if request.GET.status %}&status={{ request.GET.status }}{% endif %}{% if request.GET.sort %}&sort={{ request.GET.sort }}{% endif %}">Letzte</a>
                            </li>
                        {% endif %}
                    </ul>
                </nav>
                {% endif %}

                {% else %}
                <div class="text-center py-5">
                    <i class="fas fa-users fa-3x text-muted mb-3"></i>
                    <h5 class="text-muted">Keine Mitglieder gefunden</h5>
                    <p class="text-muted">
                        {% if request.GET.search or request.GET.status %}
                            Keine Mitglieder entsprechen den Filterkriterien.
                        {% else %}
                            Noch keine Mitglieder vorhanden.
                        {% endif %}
                    </p>
                    <a href="{% url 'members:member_add' %}" class="btn btn-primary">
                        <i class="fas fa-user-plus me-2"></i>Erstes Mitglied hinzufügen
                    </a>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}
EOF

print_status "Erstelle CSS-Datei..."

# Custom CSS erstellen
cat > static/css/style.css << 'EOF'
/* Custom CSS für Mitgliederverwaltung */

:root {
    --primary-color: #007bff;
    --secondary-color: #6c757d;
    --success-color: #28a745;
    --danger-color: #dc3545;
    --warning-color: #ffc107;
    --info-color: #17a2b8;
    --light-color: #f8f9fa;
    --dark-color: #343a40;
}

/* Layout Improvements */
body {
    background-color: #f8f9fa;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.navbar-brand {
    font-weight: 600;
    font-size: 1.25rem;
}

.card {
    border: none;
    border-radius: 10px;
    box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
    transition: box-shadow 0.15s ease-in-out;
}

.card:hover {
    box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
}

.card-header {
    background-color: transparent;
    border-bottom: 1px solid rgba(0, 0, 0, 0.125);
    font-weight: 600;
}

/* Custom Badge Styles */
.badge {
    font-size: 0.75rem;
    padding: 0.375rem 0.75rem;
    border-radius: 6px;
}

/* Table Improvements */
.table {
    margin-bottom: 0;
}

.table th {
    border-top: none;
    font-weight: 600;
    color: var(--dark-color);
    background-color: var(--light-color);
}

.table-hover tbody tr:hover {
    background-color: rgba(0, 123, 255, 0.05);
}

/* Button Improvements */
.btn {
    border-radius: 6px;
    font-weight: 500;
    transition: all 0.2s ease-in-out;
}

.btn-group .btn {
    margin-right: 2px;
}

.btn-group .btn:last-child {
    margin-right: 0;
}

/* Form Improvements */
.form-control, .form-select {
    border-radius: 6px;
    border: 1px solid #ced4da;
    transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
}

.form-control:focus, .form-select:focus {
    border-color: var(--primary-color);
    box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25);
}

/* File Upload Styling */
.file-upload-area {
    border: 2px dashed #ced4da;
    border-radius: 10px;
    padding: 3rem 2rem;
    text-align: center;
    background-color: #f8f9fa;
    transition: all 0.3s ease;
    cursor: pointer;
}

.file-upload-area:hover {
    border-color: var(--primary-color);
    background-color: rgba(0, 123, 255, 0.05);
}

.file-upload-area.dragover {
    border-color: var(--success-color);
    background-color: rgba(40, 167, 69, 0.05);
}

.file-upload-icon {
    font-size: 3rem;
    color: #6c757d;
    margin-bottom: 1rem;
}

/* Profile Image Styling */
.profile-image-preview {
    max-width: 200px;
    max-height: 250px;
    border-radius: 8px;
    border: 2px solid #dee2e6;
    object-fit: cover;
}

.profile-image-placeholder {
    width: 200px;
    height: 250px;
    background-color: #e9ecef;
    border: 2px dashed #ced4da;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #6c757d;
}

/* Statistics Cards */
.stat-card {
    border-left: 4px solid var(--primary-color);
    background: linear-gradient(135deg, #fff 0%, #f8f9fa 100%);
}

.stat-card.success {
    border-left-color: var(--success-color);
}

.stat-card.warning {
    border-left-color: var(--warning-color);
}

.stat-card.danger {
    border-left-color: var(--danger-color);
}

.stat-number {
    font-size: 2rem;
    font-weight: 700;
    color: var(--dark-color);
}

.stat-label {
    font-size: 0.875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--secondary-color);
}

/* Search and Filter Bar */
.search-filter-bar {
    background-color: white;
    border-radius: 10px;
    padding: 1.5rem;
    margin-bottom: 2rem;
    box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
}

/* Alert Improvements */
.alert {
    border: none;
    border-radius: 8px;
    border-left: 4px solid;
}

.alert-success {
    border-left-color: var(--success-color);
    background-color: rgba(40, 167, 69, 0.1);
}

.alert-danger {
    border-left-color: var(--danger-color);
    background-color: rgba(220, 53, 69, 0.1);
}

.alert-warning {
    border-left-color: var(--warning-color);
    background-color: rgba(255, 193, 7, 0.1);
}

.alert-info {
    border-left-color: var(--info-color);
    background-color: rgba(23, 162, 184, 0.1);
}

/* Loading Spinner */
.loading-spinner {
    display: none;
    text-align: center;
    padding: 2rem;
}

.spinner-border {
    width: 3rem;
    height: 3rem;
}

/* Responsive Improvements */
@media (max-width: 768px) {
    .table-responsive {
        border: none;
    }
    
    .btn-group {
        display: flex;
        flex-direction: column;
        width: 100%;
    }
    
    .btn-group .btn {
        margin: 2px 0;
        border-radius: 6px !important;
    }
    
    .stat-number {
        font-size: 1.5rem;
    }
    
    .card-body {
        padding: 1rem;
    }
}

/* Animation Classes */
.fade-in {
    animation: fadeIn 0.5s ease-in;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.slide-in {
    animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
    from { transform: translateX(-100px); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}

/* Utility Classes */
.text-shadow {
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.border-radius-lg {
    border-radius: 10px !important;
}

.border-radius-xl {
    border-radius: 15px !important;
}

.bg-gradient-primary {
    background: linear-gradient(135deg, #007bff 0%, #0056b3 100%);
}

.bg-gradient-success {
    background: linear-gradient(135deg, #28a745 0%, #1e7e34 100%);
}

.bg-gradient-warning {
    background: linear-gradient(135deg, #ffc107 0%, #e0a800 100%);
}

.bg-gradient-danger {
    background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
}

/* Footer Styling */
footer {
    margin-top: auto;
    background-color: white !important;
    border-top: 1px solid #dee2e6;
}

/* Navigation Active State */
.nav-link.active {
    font-weight: 600;
    background-color: rgba(255, 255, 255, 0.1) !important;
    border-radius: 6px;
}

/* Custom Scrollbar */
::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-track {
    background: #f1f1f1;
}

::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: #a1a1a1;
}

/* Print Styles */
@media print {
    .navbar, .btn, .pagination, footer {
        display: none !important;
    }
    
    .card {
        border: 1px solid #dee2e6 !important;
        box-shadow: none !important;
    }
    
    .table {
        font-size: 12px;
    }
}
EOF

print_status "Erstelle JavaScript-Datei..."

# Main JavaScript
cat > static/js/main.js << 'EOF'
// Main JavaScript für Mitgliederverwaltung

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize file upload handlers
    initializeFileUpload();
    
    // Initialize search functionality
    initializeSearch();
    
    // Initialize form validation
    initializeFormValidation();
    
    // Initialize dashboard stats refresh
    initializeDashboardStats();
    
    console.log('Mitgliederverwaltung Dashboard initialized');
});

// Tooltip Initialization
function initializeTooltips() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// File Upload Handler
function initializeFileUpload() {
    const fileUploadAreas = document.querySelectorAll('.file-upload-area');
    
    fileUploadAreas.forEach(area => {
        const fileInput = area.querySelector('input[type="file"]');
        
        // Drag and drop handlers
        area.addEventListener('dragover', function(e) {
            e.preventDefault();
            area.classList.add('dragover');
        });
        
        area.addEventListener('dragleave', function(e) {
            e.preventDefault();
            area.classList.remove('dragover');
        });
        
        area.addEventListener('drop', function(e) {
            e.preventDefault();
            area.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                handleFileSelection(fileInput, files[0]);
            }
        });
        
        // Click handler
        area.addEventListener('click', function() {
            fileInput.click();
        });
        
        // File input change handler
        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                handleFileSelection(this, this.files[0]);
            }
        });
    });
}

// Handle file selection
function handleFileSelection(input, file) {
    const uploadArea = input.closest('.file-upload-area');
    const preview = uploadArea.querySelector('.file-preview');
    
    // Validate file type
    const allowedTypes = input.accept ? input.accept.split(',').map(t => t.trim()) : [];
    if (allowedTypes.length > 0) {
        const fileType = '.' + file.name.split('.').pop().toLowerCase();
        if (!allowedTypes.includes(fileType)) {
            showAlert('Dateityp nicht erlaubt. Erlaubte Typen: ' + allowedTypes.join(', '), 'danger');
            input.value = '';
            return;
        }
    }
    
    // Validate file size (10MB default)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
        showAlert('Datei zu groß. Maximale Größe: 10MB', 'danger');
        input.value = '';
        return;
    }
    
    // Show preview for images
    if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = function(e) {
            if (preview) {
                preview.innerHTML = `
                    <img src="${e.target.result}" class="profile-image-preview" alt="Vorschau">
                    <p class="mt-2 mb-0"><strong>${file.name}</strong></p>
                    <small class="text-muted">${formatFileSize(file.size)}</small>
                `;
            }
        };
        reader.readAsDataURL(file);
    } else {
        // Show file info for non-images
        if (preview) {
            preview.innerHTML = `
                <i class="fas fa-file fa-3x text-success mb-2"></i>
                <p class="mb-0"><strong>${file.name}</strong></p>
                <small class="text-muted">${formatFileSize(file.size)}</small>
            `;
        }
    }
    
    // Update upload area text
    const uploadText = uploadArea.querySelector('.upload-text');
    if (uploadText) {
        uploadText.innerHTML = `
            <i class="fas fa-check-circle text-success"></i>
            Datei ausgewählt: ${file.name}
        `;
    }
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Search functionality
function initializeSearch() {
    const searchInputs = document.querySelectorAll('input[name="search"]');
    
    searchInputs.forEach(input => {
        let timeout;
        input.addEventListener('input', function() {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                // Auto-submit search after 500ms
                if (this.value.length >= 3 || this.value.length === 0) {
                    this.form.submit();
                }
            }, 500);
        });
    });
}

// Form validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                
                // Focus first invalid field
                const firstInvalid = form.querySelector(':invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                }
            }
            
            form.classList.add('was-validated');
        });
    });
    
    // Real-time validation for specific fields
    const personalNumberInputs = document.querySelectorAll('input[name="personnel_number"]');
    personalNumberInputs.forEach(input => {
        input.addEventListener('input', function() {
            // Remove non-alphanumeric characters
            this.value = this.value.replace(/[^a-zA-Z0-9]/g, '');
        });
    });
    
    // Birth date validation
    const birthDateInputs = document.querySelectorAll('input[name="birth_date"]');
    birthDateInputs.forEach(input => {
        input.addEventListener('change', function() {
            const birthDate = new Date(this.value);
            const today = new Date();
            const age = today.getFullYear() - birthDate.getFullYear();
            
            if (age < 16 || age > 100) {
                this.setCustomValidity('Alter muss zwischen 16 und 100 Jahren liegen');
            } else {
                this.setCustomValidity('');
            }
        });
    });
}

// Dashboard stats refresh
function initializeDashboardStats() {
    const statsElements = {
        'active-members-count': document.getElementById('active-members-count'),
        'valid-cards-count': document.getElementById('valid-cards-count'),
        'expiring-soon-count': document.getElementById('expiring-soon-count'),
        'expired-cards-count': document.getElementById('expired-cards-count')
    };
    
    // Refresh stats every 5 minutes
    if (Object.values(statsElements).some(el => el !== null)) {
        setInterval(refreshStats, 300000); // 5 minutes
    }
}

// Refresh dashboard statistics
function refreshStats() {
    fetch('/api/member-stats/')
        .then(response => response.json())
        .then(data => {
            if (document.getElementById('active-members-count')) {
                document.getElementById('active-members-count').textContent = data.active_members;
            }
            if (document.getElementById('valid-cards-count')) {
                document.getElementById('valid-cards-count').textContent = data.valid_cards;
            }
            if (document.getElementById('expiring-soon-count')) {
                document.getElementById('expiring-soon-count').textContent = data.expiring_soon;
            }
            if (document.getElementById('expired-cards-count')) {
                document.getElementById('expired-cards-count').textContent = data.expired_cards;
            }
        })
        .catch(error => {
            console.error('Error refreshing stats:', error);
        });
}

// Show alert messages
function showAlert(message, type = 'info') {
    const alertsContainer = document.querySelector('.alerts-container') || createAlertsContainer();
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        <i class="fas fa-${getAlertIcon(type)} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertsContainer.appendChild(alert);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        if (alert.parentNode) {
            alert.classList.remove('show');
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.parentNode.removeChild(alert);
                }
            }, 150);
        }
    }, 5000);
}

// Create alerts container if not exists
function createAlertsContainer() {
    const container = document.createElement('div');
    container.className = 'alerts-container container mt-3';
    document.querySelector('main').prepend(container);
    return container;
}

// Get icon for alert type
function getAlertIcon(type) {
    const icons = {
        'success': 'check-circle',
        'danger': 'exclamation-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

// Confirm delete dialog
function confirmDelete(memberName) {
    return confirm(`Mitglied "${memberName}" wirklich löschen?\n\nDiese Aktion kann nicht rückgängig gemacht werden.`);
}

// Loading indicator
function showLoading(target = 'body') {
    const loadingHtml = `
        <div class="loading-overlay">
            <div class="loading-spinner">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Laden...</span>
                </div>
                <p class="mt-2">Bitte warten...</p>
            </div>
        </div>
    `;
    
    if (target === 'body') {
        document.body.insertAdjacentHTML('beforeend', loadingHtml);
    } else {
        document.querySelector(target).insertAdjacentHTML('beforeend', loadingHtml);
    }
}

function hideLoading() {
    const loadingOverlay = document.querySelector('.loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.remove();
    }
}

// Add CSS for loading overlay
const style = document.createElement('style');
style.textContent = `
    .loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    }
    
    .loading-spinner {
        background-color: white;
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
    }
`;
document.head.appendChild(style);

// Export functions for global use
window.showAlert = showAlert;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.confirmDelete = confirmDelete;
EOF

print_success "Teil 3 abgeschlossen!"
echo ""
echo "Was wurde erstellt:"
echo "✓ Base Template mit Navigation und Layout"
echo "✓ Login Template mit Bootstrap Styling"
echo "✓ Dashboard Template mit Statistiken"
echo "✓ Member List Template mit Filtern und Suche"
echo "✓ Custom CSS mit modernem Design"
echo "✓ JavaScript für Interaktivität und File-Upload"
echo ""
echo "Nächster Schritt:"
echo "bash install_part4.sh  # Views und Forms"