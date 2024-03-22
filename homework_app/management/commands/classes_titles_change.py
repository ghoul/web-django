from django.core.management.base import BaseCommand
from homework_app.models import Class
import re

class Command(BaseCommand):
    help = 'Update classes titles once a year'

    def handle(self, *args, **kwargs):
        classes = Class.objects.all()
        for classs in classes:
            old_title = classs.title
            match = re.match(r'(\d+)(\D*)', old_title)
            
            if match:
                numeric_part, non_numeric_part = match.groups()

                new_numeric_part = str(int(numeric_part) + 1)
                if int(numeric_part) > 12:
                    classs.delete()
                else:               
                    new_title = new_numeric_part + non_numeric_part
                    classs.title = new_title
                    classs.save()