# members/urls.py - KOMPLETTE Datei
from django.urls import path
from . import views

app_name = 'members'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('members/', views.member_list, name='member_list'),
    path('members/add/', views.member_add, name='member_add'),
    path('members/<int:pk>/', views.member_detail, name='member_detail'),
    path('members/<int:pk>/edit/', views.member_edit, name='member_edit'),
    path('members/<int:pk>/delete/', views.member_delete, name='member_delete'),
    
    # Spezielle gefilterte Ansichten für Dashboard-Kacheln
    path('members/valid/', views.member_list_valid, name='member_list_valid'),
    path('members/expiring/', views.member_list_expiring, name='member_list_expiring'),
    path('members/expired/', views.member_list_expired, name='member_list_expired'),
    path('members/active/', views.member_list_active, name='member_list_active'),
    path('members/inactive/', views.member_list_inactive, name='member_list_inactive'),
    path('members/<int:pk>/image-debug/', views.image_quality_check, name='image_quality_check'),
    
    # Import/Export
    path('import/', views.import_data, name='import_data'),
    path('export/', views.export_data, name='export_data'),
    path('download-template/', views.download_template, name='download_template'),
    path('export-cardpresso/', views.export_cardpresso_db, name='export_cardpresso_db'),
    
    # Bildzuweisung
    path('image-assignment/', views.image_assignment, name='image_assignment'),
    path('api/search-members/', views.search_members_api, name='search_members_api'),
    path('api/assign-image/', views.assign_image_api, name='assign_image_api'),
    
    # ✨ NEUE AUSWEIS-ERSTELLUNG URLS
    path('cards/create/', views.card_creation_list, name='card_creation_list'),
    path('cards/process/', views.card_creation_process, name='card_creation_process'),
    path('cards/summary/', views.card_creation_summary, name='card_creation_summary'),
    path('cards/check/<int:pk>/', views.check_member_eligibility, name='check_member_eligibility'),
    path('cardpresso-status/', views.cardpresso_status, name='cardpresso_status'),
    path('create-cardpresso-manual/', views.create_cardpresso_manual, name='create_cardpresso_manual'),
    path('download-cardpresso/', views.download_cardpresso_zip, name='download_cardpresso_zip'),
    path('export-cardpresso-selected/', views.export_cardpresso_selected, name='export_cardpresso_selected'),
]