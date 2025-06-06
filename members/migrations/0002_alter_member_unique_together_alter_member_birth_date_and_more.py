# Generated by Django 4.2.13 on 2025-06-04 12:38

from django.db import migrations, models
import django.utils.timezone
import members.models


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='member',
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name='member',
            name='birth_date',
            field=models.DateField(verbose_name='Geburtsdatum'),
        ),
        migrations.AlterField(
            model_name='member',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='member',
            name='first_name',
            field=models.CharField(max_length=100, verbose_name='Vorname'),
        ),
        migrations.AlterField(
            model_name='member',
            name='is_active',
            field=models.BooleanField(default=True, verbose_name='Aktiv'),
        ),
        migrations.AlterField(
            model_name='member',
            name='issued_date',
            field=models.DateField(default=django.utils.timezone.now, verbose_name='Ausgestellt am'),
        ),
        migrations.AlterField(
            model_name='member',
            name='last_name',
            field=models.CharField(max_length=100, verbose_name='Nachname'),
        ),
        migrations.AlterField(
            model_name='member',
            name='personnel_number',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Personalnummer'),
        ),
        migrations.AlterField(
            model_name='member',
            name='profile_picture',
            field=models.ImageField(blank=True, null=True, upload_to=members.models.member_image_path, verbose_name='Profilbild'),
        ),
        migrations.AlterField(
            model_name='member',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='member',
            name='valid_until',
            field=models.DateField(verbose_name='Gültig bis'),
        ),
        migrations.DeleteModel(
            name='ImportLog',
        ),
    ]
