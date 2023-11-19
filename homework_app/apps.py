from django.apps import AppConfig


class HomeworkappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'homework_app'

    # def ready(self):
    #     import management.commands.create_users  # Import your signals module
