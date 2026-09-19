"""sync_agent_logins — make the database match .env for Alice, Andi and Athena.

Every WebClerk instance has three agent logins (role 'agent'). .env is the source
(ALICE_WC_*, ANDI_WC_*, ATHENA_WC_* — written by init_instance_env); this command
creates or repairs the three Contacts: active, role 'agent', password set.
Run it at install and at every deploy; after a database restore it brings the agents
back. Without an LLM (OLLAMA_BASE_URL empty) they are passengers — they still log in.

Usage:
    python manage.py sync_agent_logins
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

AGENTS = (('Alice', 'ALICE_WC_EMAIL', 'ALICE_WC_PASSWORD'),
          ('Andi', 'ANDI_WC_EMAIL', 'ANDI_WC_PASSWORD'),
          ('Athena', 'ATHENA_WC_EMAIL', 'ATHENA_WC_PASSWORD'))


class Command(BaseCommand):
    help = 'Create or repair the Alice and Andi agent logins from .env'

    def handle(self, *args, **opts):
        from apps.core.models import Contact
        missing = [k for _, e, p in AGENTS for k in (e, p) if not getattr(settings, k, '')]
        if missing:
            raise CommandError(f'.env is missing {", ".join(missing)} — run: manage.py init_instance_env')
        passenger = not settings.OLLAMA_BASE_URL
        with transaction.atomic():
            for name, email_key, password_key in AGENTS:
                email = getattr(settings, email_key).strip().lower()
                password = getattr(settings, password_key)
                contact = Contact.objects.filter(email__iexact=email).first()
                created = contact is None
                if created:
                    contact = Contact.objects.create_user(email=email, name_first=name, name_last='',
                                                          role='agent', source_name='instance agent')
                changed = []
                if contact.role != 'agent':
                    contact.role = 'agent'; changed.append('role')
                if not contact.is_active:
                    contact.is_active = True; changed.append('is_active')
                if not contact.check_password(password):
                    contact.set_password(password); changed.append('password')
                if changed:
                    contact.save()
                state = 'created' if created else ('repaired: ' + ', '.join(changed) if changed else 'ok')
                self.stdout.write(f'  {name:6} {email}  {state}')
        self.stdout.write(f'  LLM: {"none — the agents are passengers" if passenger else settings.OLLAMA_BASE_URL}')
        from apps.sync.services.connections import wchq_relationship
        self.stdout.write(f'  WC_HQ: {"relationship active" if wchq_relationship() else "mute (no active wchq-conn-upstream)"}')
