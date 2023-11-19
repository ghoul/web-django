from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Create admin and two simple users'

    def handle(self, *args, **options):
        # Check if users already exist
        if User.objects.filter(username='admin').exists() or \
           User.objects.filter(username='agne').exists() or \
           User.objects.filter(username='noob').exists():
            self.stdout.write(self.style.SUCCESS('Users already exist.'))
        else:
            # Create admin user
            User.objects.create_user(username ='admin', email='admin@gmail.com', password='admin', is_staff = True)

            # Create simple users
            User.objects.create_user(username='agne', email='agne@gmail.com', password='agne', is_staff=False)
            User.objects.create_user(username='noob', email='noob@gmail.com', password='noob', is_staff=False)

            self.stdout.write(self.style.SUCCESS('Successfully created users.'))
