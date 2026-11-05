from django.apps import AppConfig


class OrgsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.orgs'

    def ready(self):
        from .behaviours import register_orgs
        from .services import party_from_contact
        register_orgs()
        party_from_contact.register()
