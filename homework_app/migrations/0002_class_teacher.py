# Generated by Django 4.2.5 on 2023-11-20 22:16

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('homework_app', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='class',
            name='teacher',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='classs', to=settings.AUTH_USER_MODEL),
            preserve_default=False,
        ),
    ]