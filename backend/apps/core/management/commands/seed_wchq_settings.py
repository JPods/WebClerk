"""Seed WCHQ and AI-related Setting records + subscription Item records.

Records seeded:
  1. wc:wchq_connection — Controls all interaction between local WC3 and WCHQ
  2. claude_api — Claude API key and escalation chain configuration
  3. wc:subscription — WCHQ subscription status (controls Tier 2 LLM fallback)
  4. Item: WCHQ-STD — Standard subscription ($4/person/mo, Alice Tier 2)
  5. Item: WCHQ-PRO — Professional subscription ($9/person/mo, Alice+Claude Tier 3)

Subscription Items exist at WCHQ (as products to sell) and at each local WC3
(as products to order). They are normal commerce — orders, invoices, payments.

All new users get 2 months free professional access to harvest episodes and
polish associative recall triggers from a larger base.

Usage:
    python manage.py seed_wchq_settings
"""
from django.core.management.base import BaseCommand
from apps.core.models import Setting
from apps.products.models import Item


WCHQ_CONFIG = {
    # ── Data Sharing — what this instance sends to WCHQ ──────────────
    "sharing": {
        "level": "help_patterns",       # none | help_patterns | aggregate | full
        #   none          = no data leaves this machine
        #   help_patterns = Alice help requests (anonymized) sent for pattern learning
        #   aggregate     = help_patterns + anonymized usage stats (no business data)
        #   full          = aggregate + opted-in catalog/pricing for proximity search
        "share_help_requests": True,     # Alice template help → WCHQ learns common needs
        "share_search_patterns": False,  # anonymized search terms → better keyword suggestions
        "share_coaching_tips": True,     # user-submitted tips → reviewed → shared to all
        "share_catalog": False,          # item catalog → WCHQ proximity search index
        "share_pricing": False,          # pricing → WCHQ proximity search (requires share_catalog)
        "anonymize": True,              # strip business name, contact PII before sending
    },

    # ── Content Receiving — what WCHQ sends to this instance ─────────
    "receiving": {
        "level": "all",                 # none | security_only | coaching | all
        #   none           = no WCHQ content received
        #   security_only  = threat notices + critical updates only
        #   coaching       = security + Alice coaching tips + saved searches
        #   all            = coaching + layouts + templates + keyword suggestions
        "accept_coaching": True,         # Alice tips, field help, onboarding actions
        "accept_layouts": True,          # DataBrowser layouts submitted by other users
        "accept_templates": True,        # letter/email/label templates
        "accept_saved_searches": True,   # community saved search presets
        "accept_keyword_suggestions": True,  # search keyword improvements
    },

    # ── Sync Schedule ────────────────────────────────────────────────
    "sync": {
        "enabled": True,
        "frequency": "daily",           # manual | hourly | daily | weekly
        "time_utc": "03:00",            # UTC time for daily/weekly sync
        "day_of_week": "monday",        # for weekly sync
        "last_sync_utc": "",            # ISO timestamp of last successful sync
        "last_sync_status": "",         # success | partial | failed
        "retry_on_failure": True,
        "max_retries": 3,
    },

    # ── Updates & Version Control ────────────────────────────────────
    "updates": {
        "auto_check": True,             # check WCHQ for new versions
        "auto_install": False,          # never auto-install — user decides
        "channel": "stable",            # stable | beta | nightly
        "current_version": "",          # filled by system
        "available_version": "",        # filled by sync
        "last_check_utc": "",
        "release_notes_url": "",
    },

    # ── Security & Threat Notices ────────────────────────────────────
    "security": {
        "accept_threat_notices": True,   # always accept — critical for safety
        "accept_vulnerability_patches": True,
        "accept_blocklist_updates": True,  # known bad IPs, compromised credentials
        "last_threat_check_utc": "",
        "threat_level": "normal",       # normal | elevated | critical
        "notification_email": "",       # optional — email for critical alerts
    },

    # ── Alice Help → WCHQ Learning Loop ─────────────────────────────
    "alice_learning": {
        "post_help_patterns": True,     # when users ask Alice for help, anonymized pattern → WCHQ
        "post_template_requests": True, # "I need a letter for X" → WCHQ learns what templates to build
        "post_search_gaps": True,       # zero-result searches → WCHQ learns keyword gaps
        "receive_improved_responses": True,  # WCHQ sends back better Alice responses
        "coaching_level": "beginner",   # beginner | intermediate | advanced | expert
    },

    # ── Admin Review — monthly mutual agreement ──────────────────────
    # Alice schedules a monthly review of this record with the system admin.
    # Both parties confirm settings are correct. dt_approved is the proof.
    "admin_review": {
        "frequency": "monthly",         # monthly | quarterly
        "next_review_utc": "",          # ISO date — Alice sets this after each review
        "last_reviewed_utc": "",        # ISO timestamp of last completed review
        "reviewed_by_contact_id": None, # contact.id of the admin who approved
        "dt_approved": "",              # ISO timestamp — admin's explicit approval
        "approval_note": "",            # admin's note on what was reviewed/changed
        "alice_scheduled": True,        # Alice owns scheduling — creates Action for review
    },
}


ESCALATION_CONFIG = {
    # ── Escalation Chain — Alice local → WCHQ Alice → WCHQ+Claude ──
    # Individual installations never need a Claude API key.
    # WCHQ manages the Claude relationship centrally.
    "escalation": {
        "enabled": True,
        "confidence_threshold": 0.40,       # below this → escalate to WCHQ
        "confidence_weights": {
            "context": 0.60,                # RAG retrieval quality
            "answer": 0.40,                 # answer content analysis
        },
        "log_all_escalations": True,        # AliceObservation(category='escalation')
        "tiers": {
            "alice_local": {
                "order": 1,
                "source": "Ollama RAG",
                "always_first": True,
                "cost": "free",
            },
            "wchq_alice": {
                "order": 2,
                "source": "WCHQ shared LLM",
                "trigger": "confidence < threshold",
                "requires": "standard subscription",
                "cost": "subscription",
            },
            "wchq_claude": {
                "order": 3,
                "source": "WCHQ calls Claude",
                "trigger": "WCHQ Alice also low confidence",
                "requires": "professional subscription",
                "cost": "subscription (higher tier)",
            },
        },
    },
    # ── Privacy ─────────────────────────────────────────────────────
    "privacy": {
        "question_only_sent_to_wchq": True, # never raw business data
        "pii_scrubbed_before_send": True,
        "exchanges_logged_locally": True,
        "wchq_does_not_store_questions": True,
    },
}


SUBSCRIPTION_CONFIG = {
    # ── WCHQ Subscription — controls escalation tiers ──────────────
    "subscribed": False,                    # user activates after purchase
    "tier": "community",                    # community | standard | professional
    #   community    = free, run your own Ollama, no WCHQ escalation
    #   standard     = $4/person/mo, WCHQ Alice (Tier 2)
    #   professional = $9/person/mo, WCHQ Alice+Claude (Tier 3)
    "staff_count": 0,                       # auto-counted from is_staff
    "item_ida": "",                         # WCHQ-STD or WCHQ-PRO — the Item being subscribed to
    "billing": {
        "billing_cycle": "monthly",
        "last_payment_utc": "",
        "next_payment_utc": "",
    },
    "trial": {
        "active": False,                    # True during trial period
        "tier_during_trial": "professional",  # full access during trial
        "trial_days": 60,                   # 2 months free
        "start_utc": "",                    # ISO — set when installation first connects to WCHQ
        "end_utc": "",                      # ISO — start + 60 days
        "converted": False,                 # True if user subscribed after trial
    },
    "features": {
        "wchq_alice": False,                # True for standard+ (Tier 2)
        "wchq_alice_claude": False,         # True for professional (Tier 3)
        "cross_instance_queries": False,    # True for professional
        "priority_support": False,          # True for professional
        "coaching_library": True,           # True for all tiers
    },
}


# ── Subscription Items — exist at WCHQ and at each local WC3 ────────
# These are normal commerce Items. Local installations order them from WCHQ.
# WCHQ fulfills by enabling escalation access for the ordering instance.

SUBSCRIPTION_ITEMS = [
    {
        "ida": "WCHQ-STD",
        "name": "WCHQ Alice Standard",
        "kind": "service",
        "uom": "MO",
        "description": (
            "WCHQ Alice Tier 2 — $4/person/month. "
            "Alice escalates questions she can't answer locally to WCHQ's shared LLM. "
            "PII scrubbed before send. All exchanges logged locally. "
            "Includes 2-month free trial with full professional access."
        ),
        "price": {
            "base": "4.00",
            "currency": "USD",
        },
        "cost": {
            "standard": "0.80",
            "currency": "USD",
        },
        "config": {
            "service": {
                "billing": {
                    "currency": "USD",
                    "tiers": [
                        {"unit": "person", "rate": "4.00", "cost": "0.80",
                         "min_minutes": 0, "dt_effective": 0},
                    ],
                    "rounding": {"strategy": "HALF_UP", "places": 2},
                    "version": 1,
                },
                "approach": "itemized",
                "default_duration_minutes": 0,
            },
            "subscription": {
                "tier": "standard",
                "features": ["wchq_alice", "coaching_library"],
                "trial_days": 60,
                "trial_tier": "professional",
            },
        },
        "flags": {
            "not_tracked": True,    # no physical inventory
            "discountable": False,  # price is the price
        },
    },
    {
        "ida": "WCHQ-PRO",
        "name": "WCHQ Alice + Claude Professional",
        "kind": "service",
        "uom": "MO",
        "description": (
            "WCHQ Alice + Claude Tier 3 — $9/person/month. "
            "Alice escalates to WCHQ Alice (Tier 2), and WCHQ Alice can further "
            "escalate to Claude (Tier 3) for complex questions. "
            "Individual installations never need a Claude API key — WCHQ manages centrally. "
            "Includes cross-instance pattern queries and priority support. "
            "Includes 2-month free trial."
        ),
        "price": {
            "base": "9.00",
            "currency": "USD",
        },
        "cost": {
            "standard": "2.50",
            "currency": "USD",
        },
        "config": {
            "service": {
                "billing": {
                    "currency": "USD",
                    "tiers": [
                        {"unit": "person", "rate": "9.00", "cost": "2.50",
                         "min_minutes": 0, "dt_effective": 0},
                    ],
                    "rounding": {"strategy": "HALF_UP", "places": 2},
                    "version": 1,
                },
                "approach": "itemized",
                "default_duration_minutes": 0,
            },
            "subscription": {
                "tier": "professional",
                "features": [
                    "wchq_alice", "wchq_alice_claude",
                    "cross_instance_queries", "priority_support",
                    "coaching_library",
                ],
                "trial_days": 60,
                "trial_tier": "professional",
            },
        },
        "flags": {
            "not_tracked": True,
            "discountable": False,
        },
    },
]


class Command(BaseCommand):
    help = "Seed WCHQ, Claude API, and subscription Setting records"

    def _seed_setting(self, purpose, ida, name, config_data, parent_model='setting'):
        """Seed one Setting record with merge-on-update."""
        setting, created = Setting.objects.get_or_create(
            purpose=purpose,
            parent_model=parent_model,
            defaults={
                'ida': ida,
                'name': name,
                'config': config_data,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"  Created: {name} (#{setting.id})"))
        else:
            config = setting.config or {}
            changed = False
            for section, defaults in config_data.items():
                if section not in config:
                    config[section] = defaults
                    changed = True
                elif isinstance(defaults, dict) and isinstance(config[section], dict):
                    for key, val in defaults.items():
                        if key not in config[section]:
                            config[section][key] = val
                            changed = True
            if changed:
                setting.config = config
                setting._setting_update_authorized = True
                setting.save(update_fields=['config', 'dt_modified', 'version'])
                self.stdout.write(f"  Updated: {name} (#{setting.id}, merged new keys)")
            else:
                self.stdout.write(f"  OK: {name} (#{setting.id}, up to date)")
        return setting

    def _seed_subscription_items(self):
        """Seed WCHQ subscription Items — exist at WCHQ and each local WC3."""
        created = 0
        for it in SUBSCRIPTION_ITEMS:
            if Item.objects.filter(ida=it['ida']).exists():
                item = Item.objects.get(ida=it['ida'])
                # Update config (merge subscription block)
                config = item.config or {}
                if 'subscription' not in config:
                    config['subscription'] = it['config']['subscription']
                    item.config = config
                    item.save(update_fields=['config', 'dt_modified', 'version'])
                    self.stdout.write(f"  Updated: {it['name']} (#{item.id}, added subscription config)")
                else:
                    self.stdout.write(f"  OK: {it['name']} (#{item.id}, up to date)")
                continue
            Item.objects.create(
                ida=it['ida'],
                name=it['name'],
                kind=it['kind'],
                uom=it.get('uom', ''),
                description=it.get('description', ''),
                price=it.get('price', {}),
                cost=it.get('cost', {}),
                config=it.get('config', {}),
                flags=it.get('flags', {}),
                is_active=True,
            )
            created += 1
            self.stdout.write(self.style.SUCCESS(f"  Created: {it['name']} ({it['ida']})"))
        return created

    def handle(self, *args, **options):
        self.stdout.write("Seeding WCHQ + AI settings...")

        # 1. WCHQ connection
        wchq = self._seed_setting(
            'wc:wchq_connection', 'wchq-connection',
            'WCHQ Connection Settings', WCHQ_CONFIG,
        )

        # 2. Escalation chain config
        self._seed_setting(
            'wc:escalation', 'escalation-chain',
            'AI Escalation Chain', ESCALATION_CONFIG,
        )

        # 3. WCHQ subscription
        self._seed_setting(
            'wc:subscription', 'wchq-subscription',
            'WCHQ Subscription', SUBSCRIPTION_CONFIG,
        )

        # 4. Subscription Items
        self.stdout.write("\nSeeding subscription Items...")
        items_created = self._seed_subscription_items()

        cfg = wchq.config or {}
        self.stdout.write(self.style.SUCCESS(
            f"\nWCHQ Settings:\n"
            f"  Sharing level:   {cfg.get('sharing', {}).get('level', '?')}\n"
            f"  Receiving level: {cfg.get('receiving', {}).get('level', '?')}\n"
            f"  Sync frequency:  {cfg.get('sync', {}).get('frequency', '?')}\n"
            f"  Auto-check updates: {cfg.get('updates', {}).get('auto_check', '?')}\n"
            f"  Threat notices:  {cfg.get('security', {}).get('accept_threat_notices', '?')}\n"
            f"  Alice learning:  {cfg.get('alice_learning', {}).get('post_help_patterns', '?')}\n"
            f"  Admin review:    {cfg.get('admin_review', {}).get('frequency', '?')}\n"
            f"  Subscription Items: {items_created} created\n"
            f"  Trial: 60 days free professional access for all new users\n"
        ))
