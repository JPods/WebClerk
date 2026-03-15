from django.core.management.base import BaseCommand
from django.apps import apps
from django.db.models import Count

class Command(BaseCommand):
    help = 'De-duplicate GL accounts by account_number, keeping the most complete record.'

    def handle(self, *args, **options):
        GlAccount = apps.get_model('accounts', 'GlAccount')
        duplicates = (
            GlAccount.objects.values('account_number')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )
        total_removed = 0
        for dup in duplicates:
            acc_num = dup['account_number']
            records = list(GlAccount.objects.filter(account_number=acc_num))
            # Sort by number of non-null, non-empty fields (most complete first)
            def completeness(obj):
                return sum(
                    bool(getattr(obj, f.attname, None))
                    for f in obj._meta.fields
                    if f.name != 'id' and getattr(obj, f.attname, None) not in [None, '', []]
                )
            records.sort(key=completeness, reverse=True)
            # Keep the most complete, delete the rest
            to_delete = records[1:]
            total_removed += len(to_delete)
            for obj in to_delete:
                obj.delete()
        self.stdout.write(self.style.SUCCESS(f'Removed {total_removed} duplicate GL account records.'))
