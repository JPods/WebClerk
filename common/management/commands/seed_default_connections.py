from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Seed default safety and verification connections (idempotent)."

    def handle(self, *args, **options):  # pragma: no cover
        try:
            from django.apps import apps as dj_apps
            Connection = dj_apps.get_model('sync', 'Connection')
            payload = {
                'name': 'alert',
                'type': 'safety_alert',
                'purpose': 'webclerk.com',
                'status': 'safe',
                'config': {
                    'mode': 'stub',
                    'description': 'Default safety alert connection for incident signaling to webclerk.com',
                },
                'comment': 'Auto-seeded: used to notify central service of local assaults/incidents.',
            }
            obj = Connection.objects.filter(name='alert', type='safety_alert').first()
            if obj:
                for k, v in payload.items():
                    setattr(obj, k, v)
                obj.save()
                self.stdout.write(self.style.SUCCESS(f"Seeded: updated safety Connection id={getattr(obj, 'id', '?')}"))
            else:
                obj = Connection.objects.create(**payload)
                self.stdout.write(self.style.SUCCESS(f"Seeded: created safety Connection id={getattr(obj, 'id', '?')}"))

            defaults = [
                {
                    'name': 'default', 'type': 'email_verification', 'purpose': 'validation', 'status': 'safe',
                    'config': {'provider': 'stub', 'mode': 'stub'}, 'comment': 'Auto-seeded: email verification (stub)'
                },
                {
                    'name': 'default', 'type': 'phone_verification', 'purpose': 'validation', 'status': 'safe',
                    'config': {'provider': 'stub', 'mode': 'stub'}, 'comment': 'Auto-seeded: phone verification (stub)'
                },
                {
                    'name': 'default', 'type': 'location_verification', 'purpose': 'validation', 'status': 'safe',
                    'config': {'provider': 'stub', 'mode': 'stub'}, 'comment': 'Auto-seeded: location verification (stub)'
                },
                {
                    'name': 'default', 'type': 'domain_verification', 'purpose': 'validation', 'status': 'safe',
                    'config': {'provider': 'stub', 'mode': 'stub'}, 'comment': 'Auto-seeded: domain verification (stub)'
                },
            ]
            for p in defaults:
                obj = Connection.objects.filter(name=p['name'], type=p['type']).first()
                if obj:
                    for k, v in p.items():
                        setattr(obj, k, v)
                    obj.save()
                    msg = f"updated {p['type']} Connection id={getattr(obj, 'id', '?')}"
                else:
                    obj = Connection.objects.create(**p)
                    msg = f"created {p['type']} Connection id={getattr(obj, 'id', '?')}"
                self.stdout.write(self.style.SUCCESS(f"Seeded: {msg}"))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"seed_default_connections warning: {e}"))
