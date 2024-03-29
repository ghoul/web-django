# Generated by Django 4.2.5 on 2024-01-21 16:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('homework_app', '0009_questionanswerpair_qtype_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='QuestionCorrectOption',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('option', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='optionq', to='homework_app.option')),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questiono', to='homework_app.questionanswerpair')),
            ],
        ),
    ]
