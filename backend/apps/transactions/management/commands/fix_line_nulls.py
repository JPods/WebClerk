"""
Fix legacy quantity keys and null values in transaction line JSONB fields.

Walks every line record across all transaction types (Proposal, Order, Invoice,
Purchase, WorkOrder, Requisition, Receipt) and:
  1. Normalizes quantity: maps legacy keys (ordered → staged, shipped → transferred, etc.),
     fills missing canonical keys (staged/active/remaining), replaces null numerics with 0.
  2. Normalizes cost: ensures all keys exist, replaces nulls with 0.
  3. Normalizes price (sell-side only): ensures all keys, replaces nulls with 0.
  4. Recalculates extended values (price.extended, cost.extended) from normalized data.

All normalization happens via the model's ensure_json_defaults() → save() path.

Usage:
    python manage.py fix_line_nulls
    python manage.py fix_line_nulls --dry-run
    python manage.py fix_line_nulls --model ProposalLine
    python manage.py fix_line_nulls --line-id 42
"""
from django.core.management.base import BaseCommand
from apps.transactions.models import (
    ProposalLine, OrderLine, InvoiceLine,
    PurchaseLine, WorkOrderLine,
)
from apps.transactions.models.base_line_model import (
    normalize_quantity_map, normalize_cost_map, normalize_price_map,
)

# All concrete line models keyed by friendly name
LINE_MODELS = {
    "ProposalLine": ProposalLine,
    "OrderLine": OrderLine,
    "InvoiceLine": InvoiceLine,
    "PurchaseLine": PurchaseLine,
    "WorkOrderLine": WorkOrderLine,
}

# Sell-side models have a price field
SELL_MODELS = {"ProposalLine", "OrderLine", "InvoiceLine"}

# Legacy quantity keys that should have been 'staged' or 'active'
LEGACY_QTY_KEYS = {"ordered", "quantity", "qty", "shipped", "invoiced", "received", "packed", "completed", "placed", "actioned"}


def _needs_quantity_fix(q: dict | None) -> bool:
    """Return True if quantity dict has legacy keys or null numeric values."""
    if not isinstance(q, dict):
        return True
    if not q:
        return True
    # Has any legacy key?
    if LEGACY_QTY_KEYS & set(q.keys()):
        return True
    # Missing canonical keys?
    for k in ("staged", "active", "remaining"):
        if k not in q or q[k] is None:
            return True
    return False


def _needs_cost_fix(c: dict | None) -> bool:
    """Return True if cost dict has null numeric values or missing keys."""
    if not isinstance(c, dict) or not c:
        return True
    for k in ("unit", "extended", "discount_amount", "discount_percent",
              "shipping", "handling", "freight", "commissions", "tax", "tax_rate"):
        if k not in c or c[k] is None:
            return True
    return False


def _needs_price_fix(p: dict | None) -> bool:
    """Return True if price dict has null numeric values or missing keys."""
    if not isinstance(p, dict) or not p:
        return True
    for k in ("unit", "extended", "discount_amount", "discount_percent"):
        if k not in p or p[k] is None:
            return True
    return False


class Command(BaseCommand):
    help = "Fix legacy quantity keys and null numerics in transaction line JSONB fields"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without saving",
        )
        parser.add_argument(
            "--model",
            choices=list(LINE_MODELS.keys()),
            help="Limit to a single line model (default: all)",
        )
        parser.add_argument(
            "--line-id",
            type=int,
            help="Fix a single line by ID",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        model_filter = options.get("model")
        line_id = options.get("line_id")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be saved"))

        models_to_check = (
            {model_filter: LINE_MODELS[model_filter]}
            if model_filter
            else LINE_MODELS
        )

        grand_total = 0
        grand_fixed = 0
        grand_errors = 0

        for model_name, Model in models_to_check.items():
            is_sell = model_name in SELL_MODELS

            qs = Model.objects.all()
            if line_id:
                qs = qs.filter(id=line_id)

            total = qs.count()
            fixed = 0
            skipped = 0
            errors = 0
            qty_fixes = 0
            cost_fixes = 0
            price_fixes = 0

            self.stdout.write(f"\n{'─'*50}")
            self.stdout.write(f"Processing {model_name} ({total} records)...")

            for line in qs.iterator():
                try:
                    needs_fix = False
                    changes = []

                    # Check quantity
                    if _needs_quantity_fix(line.quantity):
                        needs_fix = True
                        old_qty = dict(line.quantity) if isinstance(line.quantity, dict) else line.quantity
                        changes.append(f"qty: {old_qty}")
                        qty_fixes += 1

                    # Check cost
                    if _needs_cost_fix(line.cost):
                        needs_fix = True
                        cost_fixes += 1

                    # Check price (sell-side only)
                    if is_sell and _needs_price_fix(getattr(line, "price", None)):
                        needs_fix = True
                        price_fixes += 1

                    if needs_fix:
                        if dry_run:
                            parent_id = getattr(line, "parent_id", "?")
                            self.stdout.write(
                                f"  Line {line.id} (parent={parent_id}): {', '.join(changes) if changes else 'cost/price nulls'}"
                            )
                        else:
                            # save() triggers ensure_json_defaults() which normalizes
                            # quantity, cost, price and recalculates extended
                            line.save()
                        fixed += 1
                    else:
                        skipped += 1

                except Exception as exc:
                    errors += 1
                    self.stderr.write(
                        self.style.ERROR(f"  Error on {model_name} id={line.id}: {exc}")
                    )

            self.stdout.write(f"  Total:   {total}")
            self.stdout.write(f"  Fixed:   {fixed}")
            self.stdout.write(f"  Skipped: {skipped} (already clean)")
            self.stdout.write(f"  Errors:  {errors}")
            if qty_fixes:
                self.stdout.write(f"  → qty fixes:   {qty_fixes}")
            if cost_fixes:
                self.stdout.write(f"  → cost fixes:  {cost_fixes}")
            if price_fixes:
                self.stdout.write(f"  → price fixes: {price_fixes}")

            grand_total += total
            grand_fixed += fixed
            grand_errors += errors

        # Summary
        self.stdout.write(f"\n{'═'*50}")
        self.stdout.write(self.style.SUCCESS("Done."))
        self.stdout.write(f"  Total lines:  {grand_total}")
        self.stdout.write(f"  Fixed:        {grand_fixed}")
        self.stdout.write(f"  Errors:       {grand_errors}")

        if dry_run:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING("Run without --dry-run to apply changes"))
