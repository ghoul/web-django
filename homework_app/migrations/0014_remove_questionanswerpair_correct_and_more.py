# Generated by Django 4.2.5 on 2024-03-17 13:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('homework_app', '0013_alter_customuser_school_alter_school_license_end'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='questionanswerpair',
            name='correct',
        ),
        migrations.RemoveField(
            model_name='questionanswerpair',
            name='image',
        ),
    ]
