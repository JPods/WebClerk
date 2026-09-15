"""
common.sync_wcreact.terms — Canonical payment term definitions and sync logic.

Defines the master list of payment terms (mirroring r25 TERM_RECORDS in
selectLists.ts) and provides functions to create/update wc3 Term model
records to match.

Used by:
    python manage.py sync_terms

r25 counterpart:
    src/config/selectLists.ts  → TERM_RECORDS, getTermByName(), getTermById()
"""

import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical term definitions — mirrors r25 selectLists.ts TERM_RECORDS
# ---------------------------------------------------------------------------

TERM_DEFS = [
    {
        "name": "N30",
        "description": "Net 30 days",
        "days_due": 30,
        "period_count": 1,
    },
    {
        "name": "N30_2%N10",
        "description": "Net 30, 2% discount Net 10",
        "days_due": 30,
        "discount_rate": 2.0,
        "days_discount": 10,
        "period_count": 1,
    },
    {
        "name": "3Payments30Days",
        "description": "3 Payments every 30 days",
        "days_due": 30,
        "period_count": 3,
        "days_in_period": 30,
    },
    {
        "name": "Dec1",
        "description": "Due Dec 1",
        "days_due": 1,
        "period_count": 1,
    },
    {
        "name": "On Order",
        "description": "Payment due on order",
        "days_due": 0,
        "period_count": 1,
    },
    {
        "name": "Net 60",
        "description": "Net 60 days",
        "days_due": 60,
        "period_count": 1,
    },
    {
        "name": "Net 90",
        "description": "Net 90 days",
        "days_due": 90,
        "period_count": 1,
    },
    {
        "name": "COD",
        "description": "Cash on Delivery",
        "days_due": 0,
        "period_count": 1,
    },
    {
        "name": "Prepaid",
        "description": "Payment in advance",
        "days_due": 0,
        "period_count": 1,
    },
    {
        "name": "Due on Receipt",
        "description": "Due on Receipt",
        "days_due": 0,
        "period_count": 1,
    },
]

# Fields that get set/updated on each term
SYNC_FIELDS = [
    "description", "days_due", "discount_rate", "days_discount",
    "period_count", "days_in_period",
]


# ---------------------------------------------------------------------------
# Sync functions (called by management command or programmatically)
# ---------------------------------------------------------------------------

def sync_terms(stdout, style, dry_run=False):
    """
    Create/update Term records to match TERM_DEFS. Idempotent.

    Args:
        stdout:  management command stdout (or sys.stdout)
        style:   management command style helper (for colored output)
        dry_run: if True, preview only

    Returns:
        (created, updated, unchanged) counts
    """
    from apps.accounts.models import Term

    created_count = 0
    updated_count = 0
    unchanged_count = 0

    for defn in TERM_DEFS:
        name = defn["name"]
        try:
            term = Term.objects.get(name=name)
            changes = []
            for field in SYNC_FIELDS:
                new_val = defn.get(field)
                old_val = getattr(term, field)
                if new_val != old_val:
                    changes.append((field, old_val, new_val))

            if changes:
                for field, old_val, new_val in changes:
                    setattr(term, field, new_val)
                if not dry_run:
                    term.save(update_fields=[f for f, _, _ in changes])
                tag = "[DRY RUN] " if dry_run else ""
                stdout.write(style.WARNING(
                    f"  {tag}Updated '{name}': "
                    + ", ".join(f"{f}: {o} → {n}" for f, o, n in changes)
                ))
                updated_count += 1
            else:
                stdout.write(f"  Unchanged: '{name}' (id={term.id})")
                unchanged_count += 1

        except Term.DoesNotExist:
            if not dry_run:
                term = Term.objects.create(**defn)
                stdout.write(style.SUCCESS(
                    f"  Created: '{name}' (id={term.id})"
                ))
            else:
                stdout.write(style.SUCCESS(
                    f"  [DRY RUN] Would create: '{name}'"
                ))
            created_count += 1

    # Summary
    stdout.write("")
    tag = "[DRY RUN] " if dry_run else ""
    stdout.write(style.SUCCESS(
        f"{tag}Sync complete: "
        f"{created_count} created, {updated_count} updated, "
        f"{unchanged_count} unchanged"
    ))

    return created_count, updated_count, unchanged_count


def list_terms(stdout):
    """Display all terms currently in the database."""
    from apps.accounts.models import Term

    terms = Term.objects.all().order_by("id")
    stdout.write(f"Terms in database ({terms.count()}):")
    for t in terms:
        disc = ""
        if t.discount_rate:
            disc = f", {t.discount_rate}% in {t.days_discount}d"
        periods = ""
        if t.period_count and t.period_count > 1:
            periods = f", {t.period_count} payments q/{t.days_in_period}d"
        stdout.write(
            f"  id={t.id:>3}  {t.name:<20s} "
            f"due={t.days_due or 0}d{disc}{periods}  "
            f"— {t.description}"
        )
