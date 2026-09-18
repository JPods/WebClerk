"""Seed service items with purpose='time_billing' for the billing rate select list.

These items represent billable service types that populate the rate picker
in action.config.billable. Each item carries its rate in price.base,
rate_unit in uom, and skill/activity in config.service.

Usage:
    ./bin/python manage.py seed_time_billing_items
    ./bin/python manage.py seed_time_billing_items --force   # recreate even if they exist
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.products.models import Item


# ── Time billing service items ──────────────────────────────────────────
# Each tuple: (sku, name, description, rate, uom, skill_category, activity, gl_revenue)

TIME_BILLING_ITEMS = [
    # Professional services
    ("SVC-CONSULT-SR", "Senior Consulting", "Senior consultant — on-site or remote",
     175.00, "HR", "senior_consultant", "consultation", "4100-consulting"),
    ("SVC-CONSULT-JR", "Junior Consulting", "Junior consultant — on-site or remote",
     95.00, "HR", "junior_consultant", "consultation", "4100-consulting"),

    # Skilled trades
    ("SVC-ELEC", "Electrician", "Licensed electrician — service or installation",
     125.00, "HR", "electrician", "service", "4110-trades"),
    ("SVC-PLUMB", "Plumber", "Licensed plumber — service or installation",
     120.00, "HR", "plumber", "service", "4110-trades"),
    ("SVC-HVAC", "HVAC Technician", "HVAC service or installation",
     130.00, "HR", "hvac_technician", "service", "4110-trades"),
    ("SVC-CARP", "Carpenter", "Finish or rough carpentry",
     100.00, "HR", "carpenter", "installation", "4110-trades"),

    # General labor
    ("SVC-LABOR", "General Labor", "General labor — hourly",
     55.00, "HR", "general_labor", "labor", "4120-labor"),
    ("SVC-LABOR-OT", "Overtime Labor", "General labor — overtime rate",
     82.50, "HR", "general_labor", "labor_overtime", "4120-labor"),

    # Project management
    ("SVC-PM", "Project Management", "Project manager — planning and oversight",
     150.00, "HR", "project_manager", "management", "4100-consulting"),

    # Travel and expenses (Approach 1 — itemized)
    ("SVC-TRAVEL-MILE", "Travel — Mileage", "Vehicle mileage reimbursement",
     0.70, "MI", "travel", "mileage", "4130-travel"),
    ("SVC-TRAVEL-DIEM", "Travel — Per Diem", "Daily travel per diem",
     175.00, "DAY", "travel", "per_diem", "4130-travel"),

    # Flat-rate services
    ("SVC-INSPECT", "Inspection", "Standard inspection — flat rate",
     350.00, "EA", "inspector", "inspection", "4100-consulting"),
    ("SVC-EMERGENCY", "Emergency Call-Out", "Emergency response — flat rate call-out",
     250.00, "EA", "emergency", "call_out", "4140-emergency"),
]


class Command(BaseCommand):
    help = "Seed service items with purpose='time_billing' for the billing rate select list on actions."

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='Overwrite existing time_billing items')

    def handle(self, *args, **options):
        force = options['force']
        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for sku, name, desc, rate, uom, skill, activity, gl_rev in TIME_BILLING_ITEMS:
                defaults = {
                    "name": name,
                    "description": desc,
                    "kind": Item.KIND_SERVICE,
                    "uom": uom,
                    "purpose": "time-billing",
                    "price": {
                        "base": float(rate),
                        "msrp": float(rate),
                        "retail": float(rate),
                        "wholesale": round(rate * 0.9, 2),
                        "distributor": round(rate * 0.75, 2),
                        "sample": round(rate * 0.7, 2),
                        "qty_breaks": [],
                        "history": [],
                    },
                    "gls": {"revenue": gl_rev},
                    "flags": {
                        "not_tracked": True,
                        "back_order_allowed": False,
                        "discountable": True,
                        "linked": False,
                        "pacing": False,
                        "print_suppressed": False,
                        "serialized": False,
                        "tally_by_type": False,
                    },
                    "config": {
                        "service": {
                            "skill_category": skill,
                            "activity": activity,
                            "billing": {
                                "currency": "USD",
                                "rate": float(rate),
                                "rate_unit": "hour" if uom == "HR" else (
                                    "day" if uom == "DAY" else (
                                        "unit" if uom in ("EA", "MI") else "hour"
                                    )
                                ),
                            },
                        },
                    },
                }

                item, created = Item.objects.get_or_create(
                    sku=sku,
                    defaults=defaults,
                )

                if created:
                    created_count += 1
                    self.stdout.write(f"  + {sku}: {name} @ {rate}/{uom}")
                elif force:
                    for k, v in defaults.items():
                        setattr(item, k, v)
                    item.save()
                    updated_count += 1
                    self.stdout.write(f"  ~ {sku}: {name} (updated)")
                else:
                    self.stdout.write(f"  = {sku}: exists (skip)")

        self.stdout.write(self.style.SUCCESS(
            f"\nTime billing items: {created_count} created, {updated_count} updated, "
            f"{len(TIME_BILLING_ITEMS) - created_count - updated_count} skipped."
        ))
