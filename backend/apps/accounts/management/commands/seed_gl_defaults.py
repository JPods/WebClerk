from __future__ import annotations

from dataclasses import dataclass

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models.gl_account import GlAccount
from apps.accounts.services.gl_defaults import get_item_gl_defaults, get_org_role_gl_defaults
from apps.orgs.models import OrgBase, OrgType
from apps.products.models import Item
@dataclass
class SeedStats:
    items: int = 0
    reps: int = 0


class Command(BaseCommand):
    help = "Seed GL defaults into existing items, reps, and cash methods."

    PURPOSES = ("revenue", "inventory", "cogs", "purchase", "commission", "tax_payable")

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        defaults = self._resolve_defaults()
        stats = SeedStats()

        with transaction.atomic():
            stats.items = self._seed_items(defaults=defaults, dry_run=dry_run)
            stats.reps = self._seed_reps(defaults=defaults, dry_run=dry_run)
            if dry_run:
                transaction.set_rollback(True)

        mode = "DRY RUN" if dry_run else "APPLIED"
        self.stdout.write(self.style.SUCCESS(f"seed_gl_defaults ({mode})"))
        self.stdout.write(f"  items updated: {stats.items}")
        self.stdout.write(f"  reps updated: {stats.reps}")

    def _resolve_defaults(self) -> dict[str, str]:
        """Defaults come from the company GL role map (chart-checked)."""
        defaults = dict(get_item_gl_defaults())
        rep = get_org_role_gl_defaults('rep')
        if rep.get('commission'):
            defaults['commission'] = rep['commission']
        return defaults

    def _seed_items(self, *, defaults: dict[str, str], dry_run: bool) -> int:
        changed = 0
        qs = Item.objects.filter(is_active=True, is_archived=False)
        for item in qs.iterator():
            gls = dict(item.gls or {})
            before = dict(gls)

            if not gls.get("revenue") and defaults.get("revenue"):
                gls["revenue"] = defaults["revenue"]
            if not gls.get("inventory") and defaults.get("inventory"):
                gls["inventory"] = defaults["inventory"]
            if not gls.get("cogs") and defaults.get("cogs"):
                gls["cogs"] = defaults["cogs"]
            if not gls.get("purchase") and defaults.get("purchase"):
                gls["purchase"] = defaults["purchase"]

            if gls != before:
                changed += 1
                if not dry_run:
                    item.gls = gls
                    item.save(update_fields=["gls"])
        return changed

    def _seed_reps(self, *, defaults: dict[str, str], dry_run: bool) -> int:
        changed = 0
        qs = OrgBase.objects.filter(
            org_type=OrgType.REP,
            is_active=True,
            is_archived=False,
        )
        for rep in qs.iterator():
            gl_accounts = dict(rep.gl_accounts or {})
            before = dict(gl_accounts)

            if not gl_accounts.get("commission") and defaults.get("commission"):
                gl_accounts["commission"] = defaults["commission"]

            if gl_accounts != before:
                changed += 1
                if not dry_run:
                    rep.gl_accounts = gl_accounts
                    rep.save(update_fields=["gl_accounts"])
        return changed

