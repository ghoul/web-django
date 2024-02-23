# Generated by Django 4.2.5 on 2024-01-23 10:08

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('homework_app', '0011_alter_questionanswerpairresult_answer_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='class',
            name='teacher',
        ),
        migrations.AddField(
            model_name='class',
            name='school',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='classs', to='homework_app.school'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='school',
            name='license_end',
            field=models.DateField(default=datetime.date(2024, 1, 23)),
        ),
    ]