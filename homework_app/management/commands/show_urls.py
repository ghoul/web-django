from django.core.management.base import BaseCommand
from django.urls import get_resolver

class Command(BaseCommand):
    help = "Display all URL patterns in a Django project"

    def handle(self, *args, **options):
        resolver = get_resolver()
        for pattern in resolver.url_patterns:
            self.stdout.write(str(pattern))
