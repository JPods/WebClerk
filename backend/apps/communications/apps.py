# path: apps/communications/apps.py
from django.apps import AppConfig


class CommunicationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.communications'

    def ready(self):
        from apps.communications.signals import register_communication_signals
        register_communication_signals()
