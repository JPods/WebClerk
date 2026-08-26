"""Seed detail_layout Settings for transaction and org models.

Label convention: labels match the database field name (lowercase).
For dot-path JSON fields, label is ".leaf" (last segment with dot prefix).
Users learn the schema by using the app.

Usage: ./manage.py seed_detail_layouts
       ./manage.py seed_detail_layouts --model order
       ./manage.py seed_detail_layouts --model customer
"""
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting


# ── Label helper ─────────────────────────────────────────────────────

def _f(field, **kwargs):
    """Build a field spec with auto-generated label from the field name.

    Flat fields:     "company"                    → label "company"
    Dot-path fields: "config.ship_to.company"     → label ".company"
                     "financial.customer.sales.ytd" → label ".ytd"
    """
    if '.' in field:
        label = '.' + field.rsplit('.', 1)[1]
    else:
        label = field
    return {"field": field, "label": label, **kwargs}


# ── Shared building blocks — Transactions ────────────────────────────

SELL_HEADER = {
    "type": "header",
    "layout": "three-column",
    "columns": [
        {
            "title": "customer",
            "title_ida": True,
            "fields": [
                _f("company"),
                _f("phone"),
                _f("attention"),
                _f("address_full"),
                _f("email"),
            ],
        },
        {
            "title": "ship_to",
            "fields": [
                _f("config.ship_to.company"),
                _f("config.ship_to.phone"),
                _f("config.ship_to.attention"),
                _f("config.ship_to.address1"),
                _f("config.ship_to.city_state_zip"),
                _f("ship_via"),
            ],
        },
        {
            "title": "order",
            "fields": [
                _f("price_level"),
                _f("terms"),
                _f("status"),
                _f("dt_created"),
                _f("dt_needed"),
                _f("source_name"),
                _f("priority"),
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
            "title": "vendor",
            "title_ida": True,
            "fields": [
                _f("company"),
                _f("phone"),
                _f("attention"),
                _f("address_full"),
                _f("email"),
            ],
        },
        {
            "title": "ship_to",
            "fields": [
                _f("config.ship_to.company"),
                _f("config.ship_to.phone"),
                _f("config.ship_to.attention"),
                _f("config.ship_to.address1"),
                _f("config.ship_to.city_state_zip"),
                _f("ship_via"),
            ],
        },
        {
            "title": "purchase",
            "fields": [
                _f("terms"),
                _f("status"),
                _f("dt_created"),
                _f("dt_needed"),
                _f("source_name"),
                _f("priority"),
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

# Shared panel + json sections for sell transactions
SELL_PANELS = [
    {"type": "panel", "content": "financials", "label": "financials"},
    {"type": "panel", "content": "notes", "label": "comments"},
    {"type": "panel", "content": "related_transactions", "label": "related"},
    {"type": "tabs", "tabs": [
        {"label": "contacts", "content": "contacts"},
        {"label": "qa", "content": "qa"},
        {"label": "actions", "content": "actions"},
        {"label": "documents", "content": "documents"},
    ]},
    {"type": "json_tree", "label": "json", "collapsed": True,
     "fields": ["config", "totals", "sell", "cost", "tax", "metadata", "refs", "prefs"]},
]

EXEC_PANELS = [
    {"type": "panel", "content": "financials", "label": "financials"},
    {"type": "panel", "content": "notes", "label": "comments"},
    {"type": "panel", "content": "related_transactions", "label": "related"},
    {"type": "tabs", "tabs": [
        {"label": "contacts", "content": "contacts"},
        {"label": "qa", "content": "qa"},
        {"label": "actions", "content": "actions"},
        {"label": "documents", "content": "documents"},
    ]},
    {"type": "json_tree", "label": "json", "collapsed": True,
     "fields": ["config", "totals", "cost", "tax", "metadata", "refs", "prefs"]},
]

# ── Shared building blocks — Orgs ────────────────────────────────────

ORG_EDIT_RULES = {
    "locked_statuses": [],
    "status_field": "status",
}

ORG_PANELS = [
    {"type": "panel", "content": "transactions", "label": "transactions"},
    {"type": "panel", "content": "contacts", "label": "contacts"},
    {"type": "panel", "content": "communications", "label": "communications"},
    {"type": "panel", "content": "notes", "label": "comments"},
    {"type": "tabs", "tabs": [
        {"label": "actions", "content": "actions"},
        {"label": "documents", "content": "documents"},
    ]},
    {"type": "json_tree", "label": "json", "collapsed": True,
     "fields": ["financial", "metrics", "connections", "relations",
                "gl_accounts", "config", "metadata", "refs", "prefs"]},
]

ORG_IDENTITY_FIELDS = [
    _f("ida"),
    _f("display_name"),
    _f("type"),
    _f("status"),
]

ORG_CONTACT_FIELDS = [
    _f("attention"),
    _f("email"),
    _f("phone"),
    _f("address_full"),
    _f("domain"),
]


# ── Helpers ──────────────────────────────────────────────────────────

def _sell_header(title_override=None):
    import copy
    h = copy.deepcopy(SELL_HEADER)
    if title_override:
        h["columns"][2]["title"] = title_override
    return h


def _exec_header(title_override=None):
    import copy
    h = copy.deepcopy(EXEC_HEADER)
    if title_override:
        h["columns"][2]["title"] = title_override
    return h


def _org_header(account_fields, title="account"):
    return {
        "type": "header",
        "layout": "three-column",
        "columns": [
            {"title": "identity", "fields": list(ORG_IDENTITY_FIELDS)},
            {"title": "contact", "fields": list(ORG_CONTACT_FIELDS)},
            {"title": title, "fields": account_fields},
        ],
    }


# ── Layouts per model ───────────────────────────────────────────────

LAYOUTS = {
    # ── Sell transactions ──
    "order": {
        "model": "order",
        "family": "sell",
        "sections": [
            SELL_HEADER,
            {"type": "line_card", "family": "sell", "toolbar": ["L", "S", "XR", "M"],
             "actions": ["post_to_invoice", "post_to_po", "clone"]},
            *SELL_PANELS,
        ],
        "edit_rules": SELL_EDIT_RULES,
    },

    "proposal": {
        "model": "proposal",
        "family": "sell",
        "sections": [
            _sell_header("proposal"),
            {"type": "line_card", "family": "sell", "toolbar": ["L", "S", "XR", "M"],
             "actions": ["post_to_order", "post_to_po", "clone"]},
            *SELL_PANELS,
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
            _sell_header("invoice"),
            {"type": "line_card", "family": "sell", "toolbar": ["L", "S", "XR", "M"],
             "actions": ["apply_payment", "post_to_proposal", "post_to_po", "clone"]},
            {"type": "panel", "content": "financials", "label": "financials"},
            {"type": "panel", "content": "notes", "label": "comments"},
            {"type": "panel", "content": "related_transactions", "label": "related"},
            {"type": "tabs", "tabs": [
                {"label": "shipping", "content": "shipping"},
                {"label": "contacts", "content": "contacts"},
                {"label": "qa", "content": "qa"},
                {"label": "actions", "content": "actions"},
                {"label": "documents", "content": "documents"},
            ]},
            {"type": "json_tree", "label": "json", "collapsed": True,
             "fields": ["config", "totals", "sell", "cost", "tax", "metadata", "refs", "prefs"]},
        ],
        "edit_rules": SELL_EDIT_RULES,
    },

    # ── Exec transactions ──
    "purchase": {
        "model": "purchase",
        "family": "exec",
        "sections": [
            EXEC_HEADER,
            {"type": "line_card", "family": "exec", "toolbar": ["L", "S", "XR", "M"],
             "actions": ["receive", "clone"]},
            *EXEC_PANELS,
        ],
        "edit_rules": EXEC_EDIT_RULES,
    },

    "workorder": {
        "model": "workorder",
        "family": "exec",
        "sections": [
            _exec_header("workorder"),
            {"type": "line_card", "family": "exec", "toolbar": ["L", "S", "XR", "M"],
             "actions": ["clone"]},
            *EXEC_PANELS,
        ],
        "edit_rules": EXEC_EDIT_RULES,
    },

    "receipt": {
        "model": "receipt",
        "family": "exec",
        "sections": [
            {
                "type": "header",
                "layout": "three-column",
                "columns": [
                    {
                        "title": "vendor",
                        "title_ida": True,
                        "fields": [
                            _f("purchase.company"),
                            _f("purchase.phone"),
                            _f("purchase.attention"),
                            _f("purchase.address_full"),
                            _f("purchase.email"),
                        ],
                    },
                    {
                        "title": "receiving",
                        "fields": [
                            _f("source_type"),
                            _f("dt_received"),
                            _f("purchase.ida", link=True),
                            _f("config.ship_to.company"),
                            _f("config.ship_to.address1"),
                            _f("config.ship_to.city_state_zip"),
                        ],
                    },
                    {
                        "title": "receipt",
                        "fields": [
                            _f("status"),
                            _f("dt_created"),
                            _f("source_name"),
                            _f("priority"),
                            _f("vendor_invoice_amount", format="currency"),
                            _f("vendor_invoice_freight", format="currency"),
                            _f("duty", format="currency"),
                            _f("handling", format="currency"),
                            _f("vat", format="currency"),
                            _f("allocation_method"),
                        ],
                        "action_summary": True,
                    },
                ],
            },
            {"type": "line_card", "family": "exec", "toolbar": ["L", "S", "XR"],
             "line_columns": [
                 _f("item.description", flex=3),
                 _f("item.item_id", flex=1),
                 _f("quantity.ordered", flex=1, align="right"),
                 _f("quantity.staged", flex=1, align="right"),
                 _f("cost.unit", flex=1, align="right", format="currency"),
                 _f("cost.extended", flex=1, align="right", format="currency"),
                 _f("cost.landed_per_unit", flex=1, align="right", format="currency"),
                 _f("warehouse_name", flex=1),
                 _f("lot", flex=1),
                 _f("serial_batch", flex=1),
             ],
             "actions": []},
            *EXEC_PANELS,
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
            _exec_header("requisition"),
            {"type": "line_card", "family": "exec", "toolbar": ["L", "S", "XR", "M"],
             "actions": ["post_to_po", "clone"]},
            *EXEC_PANELS,
        ],
        "edit_rules": EXEC_EDIT_RULES,
    },

    # ── Org models ──
    "customer": {
        "model": "customer",
        "family": "org",
        "sections": [
            _org_header([
                _f("price_level"),
                _f("terms"),
                _f("tax_exempt_code"),
                _f("financial.customer.sales.ytd", format="currency"),
                _f("financial.customer.sales.mtd", format="currency"),
            ]),
            *ORG_PANELS,
        ],
        "edit_rules": ORG_EDIT_RULES,
    },

    "vendor": {
        "model": "vendor",
        "family": "org",
        "sections": [
            _org_header([
                _f("price_level"),
                _f("terms"),
                _f("tax_exempt_code"),
                _f("financial.vendor.purchases.ytd", format="currency"),
                _f("financial.vendor.purchases.mtd", format="currency"),
            ]),
            *ORG_PANELS,
        ],
        "edit_rules": ORG_EDIT_RULES,
    },

    "manufacturer": {
        "model": "manufacturer",
        "family": "org",
        "sections": [
            _org_header([
                _f("price_level"),
                _f("terms"),
                _f("financial.manufacturer.pricing_tier"),
                _f("financial.manufacturer.lead_time_days"),
                _f("financial.manufacturer.min_order", format="currency"),
            ]),
            *ORG_PANELS,
        ],
        "edit_rules": ORG_EDIT_RULES,
    },

    "employee": {
        "model": "employee",
        "family": "org",
        "sections": [
            _org_header([
                _f("financial.employee.commissions.rate_pct"),
                _f("financial.employee.commissions.ytd", format="currency"),
                _f("financial.employee.expenses.ytd", format="currency"),
            ], title="employment"),
            *ORG_PANELS,
        ],
        "edit_rules": ORG_EDIT_RULES,
    },

    "rep": {
        "model": "rep",
        "family": "org",
        "sections": [
            _org_header([
                _f("financial.rep.commissions.rate_pct"),
                _f("financial.rep.commissions.ytd", format="currency"),
                _f("financial.rep.sales_credited.ytd", format="currency"),
                _f("financial.rep.customers_count"),
            ], title="commission"),
            *ORG_PANELS,
        ],
        "edit_rules": ORG_EDIT_RULES,
    },

    # ── Products ──
    "item": {
        "model": "item",
        "family": "product",
        "sections": [
            {"type": "header", "layout": "three-column", "columns": [
                {"title": "identity", "fields": [
                    _f("ida"),
                    _f("name"),
                    _f("sku"),
                    _f("kind"),
                    _f("uom"),
                    _f("status"),
                ]},
                {"title": "sourcing", "fields": [
                    _f("vendor"),
                    _f("manufacturer"),
                    _f("description"),
                ]},
                {"title": "pricing", "fields": [
                    _f("price.retail", format="currency"),
                    _f("price.wholesale", format="currency"),
                    _f("cost.standard", format="currency"),
                    _f("cost.last", format="currency"),
                    _f("quantity.on_hand"),
                    _f("quantity.on_order"),
                    _f("quantity.committed"),
                    _f("margin_pct"),
                ]},
            ]},
            {"type": "panel", "content": "notes", "label": "comments"},
            {"type": "panel", "content": "related_transactions", "label": "related"},
            {"type": "tabs", "tabs": [
                {"label": "qa", "content": "qa"},
                {"label": "actions", "content": "actions"},
                {"label": "documents", "content": "documents"},
            ]},
            {"type": "json_tree", "label": "json", "collapsed": True,
             "fields": ["price", "cost", "quantity", "catalog", "tax_code",
                        "gls", "flags", "config", "metadata", "refs", "prefs"]},
        ],
        "edit_rules": ORG_EDIT_RULES,
    },

    # ── Core ──
    "contact": {
        "model": "contact",
        "family": "core",
        "sections": [
            {"type": "header", "layout": "three-column", "columns": [
                {"title": "identity", "fields": [
                    _f("ida"),
                    _f("name_first"),
                    _f("name_last"),
                    _f("title"),
                    _f("company"),
                    _f("department"),
                ]},
                {"title": "contact", "fields": [
                    _f("email"),
                    _f("phone"),
                    _f("address_full"),
                    _f("domain"),
                    _f("role"),
                    _f("source_name"),
                ]},
                {"title": "affiliations", "fields": [
                    _f("customer"),
                    _f("vendor"),
                    _f("manufacturer"),
                    _f("employee"),
                    _f("rep"),
                ]},
            ]},
            {"type": "panel", "content": "communications", "label": "communications"},
            {"type": "panel", "content": "notes", "label": "comments"},
            {"type": "tabs", "tabs": [
                {"label": "actions", "content": "actions"},
                {"label": "documents", "content": "documents"},
            ]},
            {"type": "json_tree", "label": "json", "collapsed": True,
             "fields": ["config", "metadata", "refs", "prefs"]},
        ],
        "edit_rules": ORG_EDIT_RULES,
    },

    "action": {
        "model": "action",
        "family": "core",
        "sections": [
            {"type": "header", "layout": "three-column", "columns": [
                {"title": "action", "fields": [
                    _f("ida"),
                    _f("action.en"),
                    _f("description.en"),
                    _f("action_type"),
                    _f("status"),
                    _f("kanban_column"),
                ]},
                {"title": "assignment", "fields": [
                    _f("assigned_to"),
                    _f("project_name"),
                    _f("priority"),
                    _f("difficulty"),
                    _f("percent_complete"),
                    _f("burndown"),
                ]},
                {"title": "schedule", "fields": [
                    _f("dt_start"),
                    _f("dt_deadline"),
                    _f("dt_expected"),
                    _f("dt_completed"),
                    _f("duration"),
                    _f("sequence"),
                ]},
            ]},
            {"type": "panel", "content": "notes", "label": "comments"},
            {"type": "panel", "content": "documents", "label": "documents"},
            {"type": "json_tree", "label": "json", "collapsed": True,
             "fields": ["impact", "retrospection", "project_metadata",
                        "config", "metadata", "refs", "prefs"]},
        ],
        "edit_rules": ORG_EDIT_RULES,
    },

    "project": {
        "model": "project",
        "family": "core",
        "sections": [
            {"type": "header", "layout": "three-column", "columns": [
                {"title": "project", "fields": [
                    _f("ida"),
                    _f("name"),
                    _f("category"),
                    _f("status"),
                    _f("attention"),
                    _f("priority"),
                ]},
                {"title": "objective", "fields": [
                    _f("intent"),
                    _f("situation"),
                    _f("percent_complete"),
                    _f("burndown"),
                ]},
                {"title": "schedule", "fields": [
                    _f("dt_start"),
                    _f("dt_end"),
                    _f("profit", format="currency"),
                    _f("profit_velocity"),
                ]},
            ]},
            {"type": "tabs", "tabs": [
                {"label": "actions", "content": "actions"},
                {"label": "gantt", "content": "gantt"},
                {"label": "documents", "content": "documents"},
                {"label": "notes", "content": "notes"},
            ]},
            {"type": "json_tree", "label": "json", "collapsed": True,
             "fields": ["objective", "tasks", "logistics",
                        "config", "metadata", "refs", "prefs"]},
        ],
        "edit_rules": ORG_EDIT_RULES,
    },

    # ── Transactions (additional) ──
    "payment": {
        "model": "payment",
        "family": "transaction",
        "sections": [
            {"type": "header", "layout": "three-column", "columns": [
                {"title": "payment", "fields": [
                    _f("ida"),
                    _f("type"),
                    _f("amount", format="currency"),
                    _f("method"),
                    _f("status"),
                    _f("category"),
                ]},
                {"title": "applied_to", "fields": [
                    _f("customer"),
                    _f("vendor"),
                    _f("invoice"),
                    _f("purchase"),
                    _f("contact"),
                ]},
                {"title": "details", "fields": [
                    _f("dt_payment"),
                    _f("reference_number"),
                    _f("payment_term"),
                    _f("fee_amount", format="currency"),
                    _f("reconciled"),
                    _f("dt_reconciliation"),
                    _f("notes"),
                ]},
            ]},
            {"type": "panel", "content": "notes", "label": "comments"},
            {"type": "panel", "content": "related_transactions", "label": "related"},
            {"type": "json_tree", "label": "json", "collapsed": True,
             "fields": ["gateway_response", "config", "metadata", "refs", "prefs"]},
        ],
        "edit_rules": {
            "locked_statuses": ["reconciled", "void"],
            "status_field": "status",
        },
    },

    # ── Docs ──
    "document": {
        "model": "document",
        "family": "docs",
        "sections": [
            {"type": "header", "layout": "three-column", "columns": [
                {"title": "document", "fields": [
                    _f("ida"),
                    _f("name"),
                    _f("slug"),
                    _f("status"),
                    _f("confidential"),
                    _f("description"),
                ]},
                {"title": "content", "fields": [
                    _f("mime_type"),
                    _f("size_bytes"),
                    _f("checksum"),
                    _f("count_accessed"),
                    _f("retention_period"),
                ]},
                {"title": "file", "fields": [
                    _f("path.url"),
                    _f("path.filename"),
                    _f("path.storage"),
                ]},
            ]},
            {"type": "panel", "content": "notes", "label": "comments"},
            {"type": "json_tree", "label": "json", "collapsed": True,
             "fields": ["path", "copyright", "config", "metadata", "refs", "prefs"]},
        ],
        "edit_rules": ORG_EDIT_RULES,
    },

    # ── Sync ──
    "connection": {
        "model": "connection",
        "family": "sync",
        "sections": [
            {"type": "header", "layout": "three-column", "columns": [
                {"title": "connection", "fields": [
                    _f("ida"),
                    _f("name"),
                    _f("status"),
                    _f("purpose"),
                ]},
                {"title": "endpoint", "fields": [
                    _f("config.url"),
                    _f("config.type"),
                    _f("config.auth_method"),
                ]},
                {"title": "schedule", "fields": [
                    _f("config.schedule"),
                    _f("config.last_sync"),
                    _f("config.next_sync"),
                ]},
            ]},
            {"type": "panel", "content": "notes", "label": "comments"},
            {"type": "json_tree", "label": "json", "collapsed": True,
             "fields": ["config", "metadata", "refs", "prefs"]},
        ],
        "edit_rules": ORG_EDIT_RULES,
    },
}


class Command(BaseCommand):
    help = "Seed form layouts into wc:model config.layout.form.default"

    def add_arguments(self, parser):
        parser.add_argument(
            '--model', type=str, default=None,
            help='Seed only this model (e.g., order, customer). Default: all.',
        )
        parser.add_argument(
            '--cleanup', action='store_true',
            help='Delete old wc:detail_layout Settings after migration.',
        )

    def handle(self, *args, **options):
        target = options.get('model')
        cleanup = options.get('cleanup', False)
        models_to_seed = {target: LAYOUTS[target]} if target and target in LAYOUTS else LAYOUTS
        updated = skipped = errors = 0

        for model_name, form_config in models_to_seed.items():
            # Find the wc:model Setting for this model
            model_setting = Setting.objects.filter(
                purpose='wc:model',
                parent_model=model_name,
                is_deleted=False,
            ).first()

            if not model_setting:
                self.stderr.write(f'  {model_name}: no wc:model Setting found — skip')
                skipped += 1
                continue

            try:
                config = model_setting.config or {}
                layout = config.get('layout', {})
                layout['form'] = layout.get('form', {})
                layout['form']['default'] = form_config
                config['layout'] = layout
                model_setting.config = config
                model_setting.save()
                updated += 1
                self.stdout.write(f'  {model_name}: form.default written ({len(form_config.get("sections", []))} sections)')
            except Exception as e:
                errors += 1
                self.stderr.write(f'  {model_name}: {e}')

        # Cleanup old wc:detail_layout records
        if cleanup:
            deleted_count, _ = Setting.objects.filter(
                purpose='wc:detail_layout',
            ).delete()
            self.stdout.write(self.style.WARNING(
                f'\nCleanup: deleted {deleted_count} old wc:detail_layout records'
            ))

        self.stdout.write(self.style.SUCCESS(
            f'\nDone: {updated} updated, {skipped} skipped, {errors} errors'
        ))
