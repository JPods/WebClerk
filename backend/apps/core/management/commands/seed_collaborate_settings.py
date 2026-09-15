"""Seed the Collaborate_WebClerk Setting record.

Controls Alice_local ↔ Alice_WCHQ collaboration on best practices.
Each category can be independently enabled/disabled by the user.

When enabled, Alice_WCHQ pushes recommended improvements as sync app records.
Alice_local reviews and accepts/rejects. Nothing is forced — the local
instance is sovereign.

Collaboration categories cover:
  - Print form templates (invoices, proposals, POs, etc.)
  - Payment portal configuration (Stripe, gateway setup)
  - Shipping portal configuration (UPS, FedEx, DHL, USPS)
  - DataBrowser layouts
  - Email/letter templates
  - Saved searches & keyword suggestions
  - Alice coaching tips & onboarding
  - Inventory management best practices
  - Commission & rep management
  - Tax & compliance updates
  - Security hardening recommendations
  - Workflow automation recipes

Usage:
    python manage.py seed_collaborate_settings
"""
from django.core.management.base import BaseCommand
from apps.core.models import Setting


COLLABORATE_CONFIG = {
    # ── Master switch ───────────────────────────────────────────────────
    "enabled": True,              # master on/off for all collaboration
    "auto_accept": False,         # never auto-accept — user always reviews

    # ── Per-category collaboration toggles ──────────────────────────────
    # Each category: enabled (bool), last_sync (ISO timestamp), pending (int)
    "categories": {
        "print_forms": {
            "enabled": True,
            "label": "Print Form Templates",
            "description": "Invoice, proposal, PO, packing slip, pick list, BOL, statement, and other print templates. WCHQ maintains a library of tested layouts.",
            "last_sync_utc": "",
            "pending_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
        },
        "payment_portal": {
            "enabled": True,
            "label": "Payment Portal",
            "description": "Stripe checkout configuration, payment link templates, webhook setup, PCI compliance guidance. WCHQ tracks gateway API changes.",
            "last_sync_utc": "",
            "pending_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
        },
        "shipping_portal": {
            "enabled": True,
            "label": "Shipping Portal",
            "description": "UPS, FedEx, DHL, USPS API configurations, rate shopping setup, label generation, tracking integration. WCHQ tracks carrier API changes.",
            "last_sync_utc": "",
            "pending_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
        },
        "databrowser_layouts": {
            "enabled": True,
            "label": "DataBrowser Layouts",
            "description": "Community-contributed DataBrowser column layouts and saved views for all models.",
            "last_sync_utc": "",
            "pending_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
        },
        "email_templates": {
            "enabled": True,
            "label": "Email & Letter Templates",
            "description": "Order confirmation, invoice sent, payment received, shipping notification, and other email templates.",
            "last_sync_utc": "",
            "pending_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
        },
        "saved_searches": {
            "enabled": True,
            "label": "Saved Searches & Keywords",
            "description": "Pre-built search filters and keyword configurations for common lookups.",
            "last_sync_utc": "",
            "pending_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
        },
        "alice_coaching": {
            "enabled": True,
            "label": "Alice Coaching & Onboarding",
            "description": "Training tips, field help text, onboarding action sequences, quiz questions. WCHQ refines from community patterns.",
            "last_sync_utc": "",
            "pending_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
        },
        "inventory_practices": {
            "enabled": True,
            "label": "Inventory Management",
            "description": "Reorder point formulas, ABC classification rules, cycle count schedules, bin management patterns.",
            "last_sync_utc": "",
            "pending_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
        },
        "commission_management": {
            "enabled": True,
            "label": "Commission & Rep Management",
            "description": "Commission calculation templates, rep assignment rules, split commission patterns, broker report formats.",
            "last_sync_utc": "",
            "pending_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
        },
        "tax_compliance": {
            "enabled": True,
            "label": "Tax & Compliance",
            "description": "Tax jurisdiction configurations, sales tax rate updates, nexus rules, 1099 reporting templates.",
            "last_sync_utc": "",
            "pending_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
        },
        "security_hardening": {
            "enabled": True,
            "label": "Security Hardening",
            "description": "RBAC role templates, API rate limiting configs, audit log retention policies, password policies.",
            "last_sync_utc": "",
            "pending_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
        },
        "workflow_automation": {
            "enabled": True,
            "label": "Workflow Automation",
            "description": "Document conversion chains (proposal→order→invoice), approval workflows, notification triggers, scheduled reports.",
            "last_sync_utc": "",
            "pending_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
        },
        "gl_accounting": {
            "enabled": True,
            "label": "GL & Accounting",
            "description": "Chart of accounts templates, GL posting rules, period close checklists, journal entry patterns.",
            "last_sync_utc": "",
            "pending_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
        },
        "report_definitions": {
            "enabled": True,
            "label": "Report Definitions",
            "description": "Canned report configurations for sales, purchasing, inventory, AR aging, commission, and operational dashboards.",
            "last_sync_utc": "",
            "pending_count": 0,
            "accepted_count": 0,
            "rejected_count": 0,
        },
    },

    # ── Delivery mechanism ──────────────────────────────────────────────
    "delivery": {
        "via": "sync_app_record",      # how recommendations arrive
        "sync_model": "pending",       # arrives as Pending records for review
        "review_action": True,         # Alice_local creates an Action for admin review
        "notification": "alice",       # alice | email | both | none
    },

    # ── Submission — users post forms/templates for review ─────────────
    # Users submit their forms to WCHQ for review. Alice_WCHQ + human
    # reviewers evaluate. Innovative layouts get promoted to the
    # generally available library. Submitters earn credit.
    "submissions": {
        "enabled": True,               # allow submitting forms for review
        "submit_for_review": True,     # post forms to WCHQ for feedback
        "submit_to_library": True,     # nominate forms for the public library
        "anonymize_business_data": True,  # strip customer/transaction data, keep layout
        "require_approval": True,      # user confirms each submission before it sends
        "notification_on_feedback": True,  # notify when WCHQ responds with review
        # Status tracking per submission (stored in the Document/Pending record):
        #   submitted → under_review → feedback_ready → accepted_to_library | declined
        # Credit system:
        #   accepted_to_library → submitter earns credit (tracked in contact.config)
        "categories_submittable": [
            "print_forms",
            "email_templates",
            "databrowser_layouts",
            "workflow_automation",
            "report_definitions",
            "alice_coaching",
        ],
    },

    # ── Library — curated best practices from WCHQ + community ──────
    # The library is the output of the review process. Alice_WCHQ maintains
    # it. Innovative community submissions get promoted here.
    "library": {
        "browse_enabled": True,        # user can browse the WCHQ library
        "auto_notify_new": True,       # Alice_local notifies when new items match enabled categories
        "preview_before_install": True,  # always preview before accepting into local instance
        "track_adoption": True,        # WCHQ tracks which library items are adopted (anonymized)
        "last_browse_utc": "",
    },

    # ── Contribution — what this instance shares back ───────────────────
    "contribute": {
        "enabled": False,              # off by default — user opts in
        "share_custom_templates": False,  # share templates this user created
        "share_workflow_recipes": False,  # share automation patterns
        "share_alice_tips": False,        # share coaching improvements
        "anonymize": True,               # always strip business-identifying data
        "require_approval": True,         # user approves each outgoing share
    },

    # ── Admin review — periodic confirmation ────────────────────────────
    "admin_review": {
        "frequency": "quarterly",      # monthly | quarterly | annual
        "next_review_utc": "",
        "last_reviewed_utc": "",
        "reviewed_by_contact_id": None,
        "dt_approved": "",
        "approval_note": "",
    },
}


class Command(BaseCommand):
    help = "Seed the Collaborate_WebClerk Setting record"

    def handle(self, *args, **options):
        setting, created = Setting.objects.get_or_create(
            purpose='wc:collaborate',
            parent_model='setting',
            defaults={
                'ida': 'collaborate-webclerk',
                'name': 'Collaborate_WebClerk',
                'config': COLLABORATE_CONFIG,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(
                f"Created Collaborate_WebClerk Setting #{setting.id}"
            ))
        else:
            # Merge new categories without overwriting existing user choices
            config = setting.config or {}
            changed = False

            # Merge top-level keys
            for key, default in COLLABORATE_CONFIG.items():
                if key not in config:
                    config[key] = default
                    changed = True

            # Merge new categories into existing categories dict
            if 'categories' in COLLABORATE_CONFIG and 'categories' in config:
                for cat_key, cat_default in COLLABORATE_CONFIG['categories'].items():
                    if cat_key not in config['categories']:
                        config['categories'][cat_key] = cat_default
                        changed = True
                    elif isinstance(cat_default, dict) and isinstance(config['categories'][cat_key], dict):
                        # Add new fields to existing category without overwriting user's enabled setting
                        for field, val in cat_default.items():
                            if field not in config['categories'][cat_key]:
                                config['categories'][cat_key][field] = val
                                changed = True

            if changed:
                setting.config = config
                setting.save(update_fields=['config', 'dt_modified', 'version'])
                self.stdout.write(self.style.SUCCESS(
                    f"Updated Collaborate_WebClerk Setting #{setting.id} (merged new categories)"
                ))
            else:
                self.stdout.write(
                    f"Collaborate_WebClerk Setting #{setting.id} already up to date"
                )

        # Display current state
        cfg = setting.config or {}
        cats = cfg.get('categories', {})
        enabled_count = sum(1 for c in cats.values() if isinstance(c, dict) and c.get('enabled'))
        total_count = len(cats)

        self.stdout.write(self.style.SUCCESS(
            f"\nCollaborate_WebClerk Settings:"
            f"\n  Master enabled:  {cfg.get('enabled', '?')}"
            f"\n  Auto-accept:     {cfg.get('auto_accept', '?')}"
            f"\n  Categories:      {enabled_count}/{total_count} enabled"
            f"\n  Delivery via:    {cfg.get('delivery', {}).get('via', '?')}"
            f"\n  Contribute back: {cfg.get('contribute', {}).get('enabled', '?')}"
            f"\n  Admin review:    {cfg.get('admin_review', {}).get('frequency', '?')}"
        ))

        self.stdout.write("\n  Categories:")
        for key, cat in sorted(cats.items()):
            if isinstance(cat, dict):
                status = "ON" if cat.get('enabled') else "OFF"
                label = cat.get('label', key)
                self.stdout.write(f"    [{status}] {label}")
