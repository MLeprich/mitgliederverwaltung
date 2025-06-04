from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from datetime import timedelta
import os
from PIL import Image

def member_image_path(instance, filename):
    ext = filename.split('.')[-1].lower()
    filename = f"{instance.first_name.lower()}.{instance.last_name.lower()}.{ext}"
    return os.path.join('profile_pics', filename)

class Member(models.Model):
    first_name = models.CharField(max_length=100, verbose_name="Vorname")
    last_name = models.CharField(max_length=100, verbose_name="Nachname")
    birth_date = models.DateField(verbose_name="Geburtsdatum")
    personnel_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="Personalnummer")
    issued_date = models.DateField(default=timezone.now, verbose_name="Ausgestellt am")
    valid_until = models.DateField(verbose_name="Gültig bis")
    profile_picture = models.ImageField(upload_to=member_image_path, blank=True, null=True, verbose_name="Profilbild")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    
    class Meta:
        verbose_name = "Mitglied"
        verbose_name_plural = "Mitglieder"
        ordering = ['last_name', 'first_name']
    
    def __str__(self):
        return f"{self.last_name}, {self.first_name}"
    
    def save(self, *args, **kwargs):
        if not self.valid_until:
            self.valid_until = self.issued_date + timedelta(days=5*365)
        super().save(*args, **kwargs)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
