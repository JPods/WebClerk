from __future__ import annotations

from dataclasses import dataclass

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models.gl_account import GlAccount
from apps.accounts.services.gl_defaults import FALLBACK_DEFAULTS
from apps.orgs.models import OrgBase, OrgType
from apps.products.models import Item
from apps.transactions.models import PaymentMethod


@dataclass
class SeedStats:
    items: int = 0
    reps: int = 0
    payment_methods: int = 0


class Command(BaseCommand):
    help = "Seed GL defaults into existing items, reps, and payment methods."

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
            stats.payment_methods = self._seed_payment_methods(defaults=defaults, dry_run=dry_run)
            if dry_run:
                transaction.set_rollback(True)

        mode = "DRY RUN" if dry_run else "APPLIED"
        self.stdout.write(self.style.SUCCESS(f"seed_gl_defaults ({mode})"))
        self.stdout.write(f"  items updated: {stats.items}")
        self.stdout.write(f"  reps updated: {stats.reps}")
        self.stdout.write(f"  payment_methods updated: {stats.payment_methods}")

    def _resolve_defaults(self) -> dict[str, str]:
        defaults = dict(FALLBACK_DEFAULTS)

        # Add additional convenience keys used for payment method receipt mapping.
        defaults.setdefault("cash", "ASSET-CASH-000")
        defaults.setdefault("receivables", "ASSET-AR-000")

        purpose_to_used_for = {
            "revenue": ["sales", "revenue"],
            "inventory": ["inventory"],
            "cogs": ["cogs", "expense"],
            "purchase": ["payables", "accounts_payable", "expense"],
            "commission": ["commission", "expense"],
            "tax_payable": ["tax_payable", "tax"],
            "cash": ["cash"],
            "receivables": ["receivables"],
        }

        accounts = list(
            GlAccount.objects.filter(
                is_active=True,
                is_deleted=False,
                is_archived=False,
            ).exclude(account_number__isnull=True)
        )

        for purpose, aliases in purpose_to_used_for.items():
            if purpose in defaults and defaults[purpose]:
                continue
            matched = None
            for alias in aliases:
                matched = next((acc for acc in accounts if (acc.used_for or "").lower() == alias and acc.account_number), None)
                if matched:
                    break
            if matched and matched.account_number:
                defaults[purpose] = matched.account_number

        return defaults

    def _seed_items(self, *, defaults: dict[str, str], dry_run: bool) -> int:
        changed = 0
        qs = Item.objects.filter(is_active=True, is_deleted=False, is_archived=False)
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
            is_deleted=False,
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

    def _seed_payment_methods(self, *, defaults: dict[str, str], dry_run: bool) -> int:
        changed = 0
        qs = PaymentMethod.objects.filter(is_active=True, is_deleted=False, is_archived=False)
        for method in qs.iterator():
            metadata = dict(method.metadata or {})
            gl_accounts = dict((metadata.get("gl_accounts") or {}))
            before = dict(gl_accounts)

            if not gl_accounts.get("receipt"):
                gl_accounts["receipt"] = self._payment_receipt_account(method.name, defaults)

            if gl_accounts != before:
                metadata["gl_accounts"] = gl_accounts
                changed += 1
                if not dry_run:
                    method.metadata = metadata
                    method.save(update_fields=["metadata"])
        return changed

    @staticmethod
    def _payment_receipt_account(method_name: str, defaults: dict[str, str]) -> str:
        lowered = (method_name or "").lower()
        if "cash" in lowered:
            return defaults.get("cash") or defaults.get("receivables") or defaults.get("revenue") or ""
        return defaults.get("receivables") or defaults.get("cash") or defaults.get("revenue") or ""
