import base64
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.core.files.base import ContentFile
import logging
from .models import Member

logger = logging.getLogger(__name__)


@login_required
def image_assignment(request):
    """
    View für die Bildzuweisung - Bilder hochladen und Mitarbeitern zuweisen
    """
    return render(request, 'members/image_assignment.html')


@login_required
def search_members_api(request):
    """
    API-Endpunkt für die Live-Suche von Mitgliedern
    """
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'members': []})
    
    # Suche in Vor- und Nachname
    members = Member.objects.filter(
        Q(first_name__icontains=query) | 
        Q(last_name__icontains=query) |
        Q(personnel_number__icontains=query) |
        Q(card_number__icontains=query)
    ).filter(is_active=True)[:20]
    
    results = []
    for member in members:
        results.append({
            'id': member.id,
            'name': f"{member.first_name} {member.last_name}",
            'personnel_number': member.personnel_number or '-',
            'card_number': member.card_number,
            'member_type': member.get_member_type_display(),
            'has_picture': bool(member.profile_picture),
            'picture_url': member.profile_picture.url if member.profile_picture else None
        })
    
    return JsonResponse({'members': results})


@login_required 
def assign_image_api(request):
    """
    API-Endpunkt zum Zuweisen eines Bildes zu einem Mitglied
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Nur POST erlaubt'}, status=405)
    
    try:
        member_id = request.POST.get('member_id')
        image_data = request.POST.get('image_data')
        
        if not member_id or not image_data:
            return JsonResponse({'error': 'Fehlende Parameter'}, status=400)
        
        member = get_object_or_404(Member, id=member_id)
        
        # Base64-Bild dekodieren
        format, imgstr = image_data.split(';base64,')
        ext = format.split('/')[-1]
        
        # Bild speichern mit automatischer Verarbeitung
        image_file = ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')
        
        # Altes Bild löschen falls vorhanden
        if member.profile_picture:
            member.profile_picture.delete(save=False)
        
        # Neues Bild zuweisen
        member.profile_picture = image_file
        member.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Bild erfolgreich {member.first_name} {member.last_name} zugewiesen',
            'member_id': member.id,
            'picture_url': member.profile_picture.url if member.profile_picture else None
        })
        
    except Exception as e:
        logger.error(f"Fehler bei Bildzuweisung: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)