from django.contrib import admin
from django.contrib.admin import AdminSite

class MitgliederverwaltungAdminSite(AdminSite):
    site_header = "Mitgliederverwaltung Administration"
    site_title = "Mitgliederverwaltung Admin"
    index_title = "Willkommen zur Mitgliederverwaltung"

admin_site = MitgliederverwaltungAdminSite(name='mitgliederverwaltung_admin')
