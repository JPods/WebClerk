"""Clear stale inventory layer locks older than timeout threshold."""
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.products.models import InventoryLayer


class Command(BaseCommand):
    help = "Clear stale inventory layer locks older than 5 minutes (or --minutes N)"

    def add_arguments(self, parser):
        parser.add_argument("--minutes", type=int, default=5, help="Lock age threshold in minutes (default: 5)")
        parser.add_argument("--dry-run", action="store_true", help="Report stale locks without clearing them")

    def handle(self, *args, **options):
        cutoff = timezone.now() - datetime.timedelta(minutes=options["minutes"])

        # Stale locks (locked before cutoff)
        stale = InventoryLayer.objects.filter(is_locked=True, dt_locked__lt=cutoff)
        # Orphaned locks (no dt_locked — from before the field existed)
        orphaned = InventoryLayer.objects.filter(is_locked=True, dt_locked__isnull=True)

        stale_ids = list(stale.values_list('pk', flat=True))
        orphan_ids = list(orphaned.values_list('pk', flat=True))
        total = len(stale_ids) + len(orphan_ids)

        if total == 0:
            self.stdout.write("No stale locks found.")
            return

        if options["dry_run"]:
            self.stdout.write(f"Would clear {len(stale_ids)} stale + {len(orphan_ids)} orphaned lock(s):")
            for layer in stale:
                self.stdout.write(f"  Stack#{layer.pk} locked since {layer.dt_locked}")
            for layer in orphaned:
                self.stdout.write(f"  Stack#{layer.pk} orphaned (no dt_locked)")
            return

        # Release each lock individually so pending adjustments drain properly
        cleared = 0
        for layer in InventoryLayer.objects.filter(pk__in=stale_ids + orphan_ids):
            layer.release_lock()
            cleared += 1

        self.stdout.write(f"Released {cleared} lock(s). Pending adjustments drained per stack.")
