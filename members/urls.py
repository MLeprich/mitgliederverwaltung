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
    
    # Import/Export
    path('import/', views.import_data, name='import_data'),
    path('export/', views.export_data, name='export_data'),
    path('download-template/', views.download_template, name='download_template'),
]
