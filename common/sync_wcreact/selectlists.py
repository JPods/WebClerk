"""
common.sync_wcreact.selectlists — Canonical select list definitions and sync logic.

Defines the master list of r25 dynamic select lists and provides functions
to sync them to/from wc3 Setting records (purpose="wc:selectlist").

Used by:
    python manage.py sync_selectlists

r25 counterpart:
    src/config/selectLists.ts    → DYNAMIC_LISTS, SELECT_LIST_MAP
    src/config/syncSelectLists.ts → fetch/push/merge functions
"""

import logging

logger = logging.getLogger(__name__)

PURPOSE = "wc:selectlist"

# ---------------------------------------------------------------------------
# Canonical r25 dynamic select lists
# Mirrors DYNAMIC_LISTS in r25 selectLists.ts.
# When a new list is added to r25, add it here too, then run:
#     python manage.py sync_selectlists --direction to-wc3
# ---------------------------------------------------------------------------

R25_DYNAMIC_LISTS = [
    {
        "key": "terms",
        "label": "Payment Terms",
        "options": [
            {"value": "N30", "label": "Net 30 days"},
            {"value": "N30_2%N10", "label": "Net 30, 2% discount Net 10"},
            {"value": "3Payments30Days", "label": "3 Payments every 30 days"},
            {"value": "Dec1", "label": "Due Dec 1"},
            {"value": "On Order", "label": "Payment due on order"},
            {"value": "Net 60", "label": "Net 60 days"},
            {"value": "Net 90", "label": "Net 90 days"},
            {"value": "COD", "label": "Cash on Delivery"},
            {"value": "Prepaid", "label": "Payment in advance"},
            {"value": "Due on Receipt", "label": "Due on Receipt"},
        ],
    },
    {
        "key": "status",
        "label": "Record Status",
        "options": [
            {"value": "active", "label": "Active"},
            {"value": "staged", "label": "Staged"},
            {"value": "completed", "label": "Completed"},
            {"value": "cancelled", "label": "Cancelled"},
            {"value": "on_hold", "label": "On Hold"},
        ],
    },
    {
        "key": "priority",
        "label": "Priority",
        "options": [
            {"value": "standard", "label": "Standard"},
            {"value": "rush", "label": "Rush"},
            {"value": "urgent", "label": "Urgent"},
            {"value": "low", "label": "Low"},
        ],
    },
    {
        "key": "price_level",
        "label": "Price Level",
        "options": [
            {"value": "retail", "label": "Retail"},
            {"value": "wholesale", "label": "Wholesale"},
            {"value": "distributor", "label": "Distributor"},
            {"value": "employee", "label": "Employee"},
            {"value": "sample", "label": "Sample"},
        ],
    },
    {
        "key": "sale_juris_source",
        "label": "Sale Jurisdiction Source",
        "options": [
            {"value": "Distributor", "label": "Distributor"},
            {"value": "Retail", "label": "Retail"},
            {"value": "Subcontract", "label": "Subcontract"},
            {"value": "TrucktoCustomer", "label": "Truck to Customer"},
            {"value": "TrucktoTruck", "label": "Truck to Truck"},
            {"value": "Wholesale", "label": "Wholesale"},
        ],
    },
    {"key": "ad_source",           "label": "Ad Source",           "options": []},
    {"key": "type_sale",           "label": "Sale Type",           "options": []},
    {"key": "contract_detail",     "label": "Contract Detail",     "options": []},
    {"key": "reps",                "label": "Sales Reps",          "options": []},
    {"key": "actions_orders",      "label": "Order Actions",       "options": []},
    {"key": "actions_invoices",    "label": "Invoice Actions",     "options": []},
    {"key": "actions_proposals",   "label": "Proposal Actions",    "options": []},
    {"key": "actions_purchases",   "label": "Purchase Actions",    "options": []},
    {"key": "tax_juris",           "label": "Tax Jurisdictions",   "options": []},
    {
        "key": "job_list",
        "label": "Job Types",
        "options": [
            {"value": "Job Class", "label": "Job Class"},
            {"value": "*Estimate Job", "label": "*Estimate Job"},
            {"value": "*Sweeps Service", "label": "*Sweeps Service"},
            {"value": "Attic Insulation Shield/FS", "label": "Attic Insulation Shield/FS"},
            {"value": "Chase Cover", "label": "Chase Cover"},
            {"value": "Chimney Caps", "label": "Chimney Caps"},
            {"value": "Class A Install", "label": "Class A Install"},
            {"value": "Class B Install", "label": "Class B Install"},
            {"value": "Firebox Repairs", "label": "Firebox Repairs"},
            {"value": "FireStop Install", "label": "FireStop Install"},
            {"value": "Flashings/Crickets", "label": "Flashings/Crickets"},
            {"value": "Gas Insert", "label": "Gas Insert"},
            {"value": "Gas Log Installs", "label": "Gas Log Installs"},
            {"value": "Gas Stove", "label": "Gas Stove"},
            {"value": "level Three Inspect", "label": "level Three Inspect"},
            {"value": "New Const Gas FP", "label": "New Const Gas FP"},
            {"value": "New Const Masonry", "label": "New Const Masonry"},
            {"value": "New Const Wood FP", "label": "New Const Wood FP"},
            {"value": "Pellet Insert", "label": "Pellet Insert"},
            {"value": "Pellet Stove", "label": "Pellet Stove"},
            {"value": "Plaster & Paint", "label": "Plaster & Paint"},
            {"value": "R&R Brick Chimneys", "label": "R&R Brick Chimneys"},
            {"value": "R&R Gas FP", "label": "R&R Gas FP"},
            {"value": "R&R Wood Chases", "label": "R&R Wood Chases"},
            {"value": "R&R Wood FP", "label": "R&R Wood FP"},
            {"value": "Recrown", "label": "Recrown"},
            {"value": "Reface FirePlace", "label": "Reface FirePlace"},
            {"value": "Reline Gas", "label": "Reline Gas"},
            {"value": "Reline Wood", "label": "Reline Wood"},
            {"value": "Run Gas Line", "label": "Run Gas Line"},
            {"value": "Water Repellant", "label": "Water Repellant"},
            {"value": "Wood Insert", "label": "Wood Insert"},
            {"value": "Wood Stove", "label": "Wood Stove"},
        ],
    },
    {
        "key": "qa_type",
        "label": "QA Types",
        "options": [
            {"value": "Dryer-Vent", "label": "Dryer-Vent"},
            {"value": "Gas-Service-Call", "label": "Gas-Service-Call"},
            {"value": "Inspection-Level-2", "label": "Inspection-Level-2"},
            {"value": "Job-Setup", "label": "Job-Setup"},
            {"value": "Pellet-Stove", "label": "Pellet-Stove"},
        ],
    },
]

# Build lookup by key
_LIST_BY_KEY = {lst["key"]: lst for lst in R25_DYNAMIC_LISTS}


# ---------------------------------------------------------------------------
# Sync functions (called by management command or programmatically)
# ---------------------------------------------------------------------------

def push_selectlists_to_wc3(stdout, style, keys=None, dry_run=False):
    """
    Push r25 dynamic lists → wc3 Setting records. Idempotent.

    Args:
        stdout:   management command stdout
        style:    management command style helper
        keys:     optional list of specific keys to sync (None = all)
        dry_run:  if True, preview only

    Returns:
        (created, updated, unchanged) counts
    """
    from apps.core.models import Setting

    lists_to_sync = R25_DYNAMIC_LISTS
    if keys:
        lists_to_sync = [lst for lst in R25_DYNAMIC_LISTS if lst["key"] in keys]
        missing = set(keys) - {lst["key"] for lst in lists_to_sync}
        if missing:
            stdout.write(style.ERROR(
                f"Unknown list key(s): {', '.join(sorted(missing))}"
            ))
            return 0, 0, 0

    created = updated = unchanged = 0

    for lst in lists_to_sync:
        key = lst["key"]
        new_data = {"options": lst["options"], "label": lst["label"]}

        try:
            setting = Setting.objects.get(purpose=PURPOSE, name=key)
            old_data = setting.data or {}
            if old_data == new_data:
                stdout.write(f"  Unchanged: '{key}' (id={setting.id})")
                unchanged += 1
            else:
                if not dry_run:
                    setting.data = new_data
                    setting.save(update_fields=["data"])
                tag = "[DRY RUN] " if dry_run else ""
                old_count = len(old_data.get("options", []))
                new_count = len(new_data.get("options", []))
                stdout.write(style.WARNING(
                    f"  {tag}Updated: '{key}' (id={setting.id}) "
                    f"— {old_count} → {new_count} options"
                ))
                updated += 1

        except Setting.DoesNotExist:
            if not dry_run:
                setting = Setting.objects.create(
                    name=key,
                    purpose=PURPOSE,
                    data=new_data,
                )
                stdout.write(style.SUCCESS(
                    f"  Created: '{key}' (id={setting.id}) "
                    f"— {len(lst['options'])} options"
                ))
            else:
                stdout.write(style.SUCCESS(
                    f"  [DRY RUN] Would create: '{key}' "
                    f"— {len(lst['options'])} options"
                ))
            created += 1

    tag = "[DRY RUN] " if dry_run else ""
    stdout.write("")
    stdout.write(style.SUCCESS(
        f"{tag}Sync complete: "
        f"{created} created, {updated} updated, {unchanged} unchanged"
    ))

    return created, updated, unchanged


def show_selectlists_for_r25(stdout, keys=None):
    """
    Output wc3 settings formatted as r25 toOptions() code.

    Args:
        stdout:  management command stdout
        keys:    optional list of specific keys to show
    """
    from apps.core.models import Setting

    qs = Setting.objects.filter(purpose=PURPOSE, is_active=True).order_by("name")
    if keys:
        qs = qs.filter(name__in=keys)

    if not qs.exists():
        stdout.write("No admin_selectlist settings found in wc3.")
        return

    stdout.write("// Paste these into r25 DYNAMIC_LISTS in selectLists.ts:")
    stdout.write("")
    for setting in qs:
        data = setting.data or {}
        options = data.get("options", [])
        label = data.get("label", setting.name)
        stdout.write("  {")
        stdout.write(f"    key: '{setting.name}',")
        stdout.write(f"    label: '{label}',")
        stdout.write("    editable: true,")
        stdout.write("    options: toOptions([")
        for opt in options:
            v = opt.get("value", "")
            lbl = opt.get("label", v)
            stdout.write(f"      ['{v}', '{lbl}'],")
        stdout.write("    ]),")
        stdout.write("  },")
        stdout.write("")


def list_selectlist_settings(stdout, keys=None):
    """
    Display all admin_selectlist settings currently in the database.

    Args:
        stdout:  management command stdout
        keys:    optional list of specific keys to show
    """
    from apps.core.models import Setting

    qs = Setting.objects.filter(purpose=PURPOSE, is_active=True).order_by("name")
    if keys:
        qs = qs.filter(name__in=keys)

    count = qs.count()
    stdout.write(f"admin_selectlist settings in wc3 ({count}):")
    if count == 0:
        stdout.write("  (none — run with --direction to-wc3 to populate)")
        return

    for s in qs:
        data = s.data or {}
        opt_count = len(data.get("options", []))
        label = data.get("label", "")
        stdout.write(
            f"  id={s.id:>3}  {s.name:<25s} "
            f"{opt_count:>3} options  — {label}"
        )
