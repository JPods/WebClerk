"""Seed detail_layout Settings for transaction models.

Usage: ./manage.py seed_detail_layouts
       ./manage.py seed_detail_layouts --model order
"""
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting


# ── Shared building blocks ──────────────────────────────────────────

SELL_HEADER = {
    "type": "header",
    "layout": "three-column",
    "columns": [
        {
            "title": "Customer",
            "title_ida": True,
            "fields": [
                {"field": "company", "label": "Company"},
                {"field": "phone", "label": "Phone"},
                {"field": "attention", "label": "Attn"},
                {"field": "address_full", "label": "Address"},
                {"field": "email", "label": "Email"},
            ],
        },
        {
            "title": "Ship To",
            "fields": [
                {"field": "config.ship_to.company", "label": "Ship To"},
                {"field": "config.ship_to.phone", "label": "Phone"},
                {"field": "config.ship_to.attention", "label": "Attn"},
                {"field": "config.ship_to.address1", "label": "Address"},
                {"field": "config.ship_to.city_state_zip", "label": "City/State"},
                {"field": "ship_via", "label": "ShipVia"},
            ],
        },
        {
            "title": "Order",
            "fields": [
                {"field": "price_level", "label": "Type Sale"},
                {"field": "terms", "label": "Terms"},
                {"field": "status", "label": "Status"},
                {"field": "dt_created", "label": "Date Ord"},
                {"field": "dt_needed", "label": "Need By"},
                {"field": "source_name", "label": "Sales"},
                {"field": "priority", "label": "Priority"},
            ],
            "action_summary": True,
        },
    ],
}

EXEC_HEADER = {
    "type": "header",
    "layout": "three-column",
    "columns": [
        {
            "title": "Vendor",
            "title_ida": True,
            "fields": [
                {"field": "company", "label": "Company"},
                {"field": "phone", "label": "Phone"},
                {"field": "attention", "label": "Attn"},
                {"field": "address_full", "label": "Address"},
                {"field": "email", "label": "Email"},
            ],
        },
        {
            "title": "Ship To",
            "fields": [
                {"field": "config.ship_to.company", "label": "Ship To"},
                {"field": "config.ship_to.phone", "label": "Phone"},
                {"field": "config.ship_to.attention", "label": "Attn"},
                {"field": "config.ship_to.address1", "label": "Address"},
                {"field": "config.ship_to.city_state_zip", "label": "City/State"},
                {"field": "ship_via", "label": "ShipVia"},
            ],
        },
        {
            "title": "Purchase",
            "fields": [
                {"field": "terms", "label": "Terms"},
                {"field": "status", "label": "Status"},
                {"field": "dt_created", "label": "Date Ord"},
                {"field": "dt_needed", "label": "Need By"},
                {"field": "source_name", "label": "Buyer"},
                {"field": "priority", "label": "Priority"},
            ],
            "action_summary": True,
        },
    ],
}

SELL_EDIT_RULES = {
    "open_statuses": ["", "planned", "open", "draft"],
    "pend_statuses": ["journalized", "released", "shipped", "invoiced"],
    "closed_statuses": ["completed", "cancelled", "void"],
    "status_field": "status",
}

EXEC_EDIT_RULES = {
    "open_statuses": ["", "planned", "open", "draft"],
    "pend_statuses": ["journalized", "released", "received"],
    "closed_statuses": ["completed", "cancelled", "void"],
    "status_field": "status",
}


# ── Layouts per model ───────────────────────────────────────────────

def _sell_header(title_override=None):
    h = dict(SELL_HEADER)
    if title_override:
        cols = [dict(c) for c in h["columns"]]
        cols[2] = dict(cols[2])
        cols[2]["title"] = title_override
        h["columns"] = cols
    return h


def _exec_header(title_override=None):
    h = dict(EXEC_HEADER)
    if title_override:
        cols = [dict(c) for c in h["columns"]]
        cols[2] = dict(cols[2])
        cols[2]["title"] = title_override
        h["columns"] = cols
    return h


LAYOUTS = {
    "order": {
        "model": "order",
        "family": "sell",
        "sections": [
            SELL_HEADER,
            {"type": "line_card", "family": "sell", "toolbar": ["L", "S", "XR", "M"],
             "actions": ["post_to_invoice", "post_to_po", "clone"]},
            {"type": "tabs", "tabs": [
                {"label": "Summary", "content": "summary"},
                {"label": "Margins", "content": "margins"},
                {"label": "Contacts", "content": "contacts"},
                {"label": "QA", "content": "qa"},
                {"label": "Actions", "content": "actions"},
                {"label": "Documents", "content": "documents"},
                {"label": "Notes", "content": "notes"},
                {"label": "Related", "content": "related_transactions"},
            ]},
        ],
        "edit_rules": SELL_EDIT_RULES,
    },

    "proposal": {
        "model": "proposal",
        "family": "sell",
        "sections": [
            _sell_header("Proposal"),
            {"type": "line_card", "family": "sell", "toolbar": ["L", "S", "XR", "M"],
             "actions": ["post_to_order", "post_to_po", "clone"]},
            {"type": "tabs", "tabs": [
                {"label": "Summary", "content": "summary"},
                {"label": "Margins", "content": "margins"},
                {"label": "Contacts", "content": "contacts"},
                {"label": "QA", "content": "qa"},
                {"label": "Actions", "content": "actions"},
                {"label": "Documents", "content": "documents"},
                {"label": "Notes", "content": "notes"},
                {"label": "Related", "content": "related_transactions"},
            ]},
        ],
        "edit_rules": {
            **SELL_EDIT_RULES,
            "closed_statuses": ["completed", "cancelled", "void", "expired"],
        },
    },

    "invoice": {
        "model": "invoice",
        "family": "sell",
        "sections": [
            _sell_header("Invoice"),
            {"type": "line_card", "family": "sell", "toolbar": ["L", "S", "XR", "M"],
             "actions": ["apply_payment", "post_to_proposal", "post_to_po", "clone"]},
            {"type": "tabs", "tabs": [
                {"label": "Summary", "content": "summary"},
                {"label": "Margins", "content": "margins"},
                {"label": "Shipping", "content": "shipping"},
                {"label": "Contacts", "content": "contacts"},
                {"label": "QA", "content": "qa"},
                {"label": "Actions", "content": "actions"},
                {"label": "Documents", "content": "documents"},
                {"label": "Notes", "content": "notes"},
                {"label": "Related", "content": "related_transactions"},
            ]},
        ],
        "edit_rules": SELL_EDIT_RULES,
    },

    "purchase": {
        "model": "purchase",
        "family": "exec",
        "sections": [
            EXEC_HEADER,
            {"type": "line_card", "family": "exec", "toolbar": ["L", "S", "XR", "M"],
             "actions": ["receive", "clone"]},
            {"type": "tabs", "tabs": [
                {"label": "Summary", "content": "summary"},
                {"label": "Contacts", "content": "contacts"},
                {"label": "QA", "content": "qa"},
                {"label": "Actions", "content": "actions"},
                {"label": "Documents", "content": "documents"},
                {"label": "Notes", "content": "notes"},
                {"label": "Related", "content": "related_transactions"},
            ]},
        ],
        "edit_rules": EXEC_EDIT_RULES,
    },

    "work_order": {
        "model": "work_order",
        "family": "exec",
        "sections": [
            _exec_header("Work Order"),
            {"type": "line_card", "family": "exec", "toolbar": ["L", "S", "XR", "M"],
             "actions": ["clone"]},
            {"type": "tabs", "tabs": [
                {"label": "Summary", "content": "summary"},
                {"label": "Contacts", "content": "contacts"},
                {"label": "QA", "content": "qa"},
                {"label": "Actions", "content": "actions"},
                {"label": "Documents", "content": "documents"},
                {"label": "Notes", "content": "notes"},
                {"label": "Related", "content": "related_transactions"},
            ]},
        ],
        "edit_rules": EXEC_EDIT_RULES,
    },

    "receipt": {
        "model": "receipt",
        "family": "exec",
        "sections": [
            _exec_header("Receipt"),
            {"type": "line_card", "family": "exec", "toolbar": ["L", "S", "XR"],
             "actions": []},
            {"type": "tabs", "tabs": [
                {"label": "Summary", "content": "summary"},
                {"label": "QA", "content": "qa"},
                {"label": "Documents", "content": "documents"},
                {"label": "Notes", "content": "notes"},
                {"label": "Related", "content": "related_transactions"},
            ]},
        ],
        "edit_rules": {
            **EXEC_EDIT_RULES,
            "closed_statuses": ["completed", "cancelled", "void"],
        },
    },

    "requisition": {
        "model": "requisition",
        "family": "exec",
        "sections": [
            _exec_header("Requisition"),
            {"type": "line_card", "family": "exec", "toolbar": ["L", "S", "XR", "M"],
             "actions": ["post_to_po", "clone"]},
            {"type": "tabs", "tabs": [
                {"label": "Summary", "content": "summary"},
                {"label": "Actions", "content": "actions"},
                {"label": "Documents", "content": "documents"},
                {"label": "Notes", "content": "notes"},
                {"label": "Related", "content": "related_transactions"},
            ]},
        ],
        "edit_rules": EXEC_EDIT_RULES,
    },
}


class Command(BaseCommand):
    help = "Seed detail_layout Settings for transaction models"

    def add_arguments(self, parser):
        parser.add_argument(
            '--model', type=str, default=None,
            help='Seed only this model (e.g., order). Default: all.',
        )

    def handle(self, *args, **options):
        target = options.get('model')
        models_to_seed = {target: LAYOUTS[target]} if target and target in LAYOUTS else LAYOUTS

        for model_name, config in models_to_seed.items():
            setting, created = Setting.objects.update_or_create(
                purpose='detail_layout',
                parent_model=model_name,
                defaults={
                    'ida': f'detail-layout-{model_name}',
                    'name': f'Detail layout for {model_name}',
                    'config': config,
                },
            )

            verb = 'Created' if created else 'Updated'
            self.stdout.write(self.style.SUCCESS(
                f"{verb} detail_layout Setting #{setting.id} for {model_name}"
            ))

        self.stdout.write(self.style.SUCCESS(
            f"\nSeeded {len(models_to_seed)} detail_layout(s). "
            f"View at /td/<model>/<id>"
        ))
