from django.core.management.base import BaseCommand
from decimal import Decimal
from datetime import datetime, timezone


class Command(BaseCommand):
    help = "Stub: Fetch and store ExchangeRate windows via linked Connection providers."

    def add_arguments(self, parser):  # pragma: no cover
        parser.add_argument('--provider', type=str, help='Restrict to currencies with a given connection provider type.')
        parser.add_argument('--limit', type=int, default=0, help='Process only N currencies (0 = all).')

    def handle(self, *args, **opts):  # pragma: no cover
        from django.apps import apps as dj_apps
        Currency = dj_apps.get_model('accounts', 'Currency')
        ExchangeRate = dj_apps.get_model('accounts', 'ExchangeRate')
        qs = Currency.objects.filter(is_active=True)
        if opts.get('provider'):
            qs = qs.filter(connection__type=opts['provider'])
        count = 0
        now = datetime.now(timezone.utc)
        for cur in qs.iterator(chunk_size=200):
            # Placeholder provider: store 1:1 and a sample cross rate to USD
            base = getattr(cur, 'code', None) or 'USD'
            target = 'USD' if base != 'USD' else 'EUR'
            rate = Decimal('1') if base == target else Decimal('1.100000')
            ExchangeRate.objects.update_or_create(
                currency_base=base,
                currency_target=target,
                dt_start=now.replace(minute=0, second=0, microsecond=0),
                dt_end=None,
                defaults={
                    'rate': rate,
                    'connection_id': getattr(cur, 'connection_id', None),
                    'is_active': True,
                },
            )
            count += 1
            if opts['limit'] and count >= opts['limit']:
                break
        self.stdout.write(self.style.SUCCESS(f"ExchangeRate windows upserted: {count}"))
