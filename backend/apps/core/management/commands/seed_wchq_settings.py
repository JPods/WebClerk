"""Seed the WCHQ (WebClerk Headquarters) connection Setting record.

Controls all interaction between the local WC3 instance and WCHQ:
  - Data sharing level (what flows up to WCHQ)
  - Content receiving level (what flows down from WCHQ)
  - Sync schedule
  - Update/version control
  - Threat/security notices
  - Alice help patterns → WCHQ learning loop

Usage:
    python manage.py seed_wchq_settings
"""
from django.core.management.base import BaseCommand
from apps.core.models import Setting


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


class Command(BaseCommand):
    help = "Seed the WCHQ connection Setting record"

    def handle(self, *args, **options):
        setting, created = Setting.objects.get_or_create(
            purpose='wc:wchq_connection',
            parent_model='setting',
            defaults={
                'ida': 'wchq-connection',
                'name': 'WCHQ Connection Settings',
                'config': WCHQ_CONFIG,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(
                f"Created wchq_connection Setting #{setting.id}"
            ))
        else:
            # Merge new sections without overwriting existing values
            config = setting.config or {}
            changed = False
            for section, defaults in WCHQ_CONFIG.items():
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
                setting.save(update_fields=['config', 'dt_modified', 'version'])
                self.stdout.write(self.style.SUCCESS(
                    f"Updated wchq_connection Setting #{setting.id} (merged new keys)"
                ))
            else:
                self.stdout.write(
                    f"wchq_connection Setting #{setting.id} already up to date"
                )

        cfg = setting.config or {}
        self.stdout.write(self.style.SUCCESS(
            f"\nWCHQ Settings:\n"
            f"  Sharing level:   {cfg.get('sharing', {}).get('level', '?')}\n"
            f"  Receiving level: {cfg.get('receiving', {}).get('level', '?')}\n"
            f"  Sync frequency:  {cfg.get('sync', {}).get('frequency', '?')}\n"
            f"  Auto-check updates: {cfg.get('updates', {}).get('auto_check', '?')}\n"
            f"  Threat notices:  {cfg.get('security', {}).get('accept_threat_notices', '?')}\n"
            f"  Alice learning:  {cfg.get('alice_learning', {}).get('post_help_patterns', '?')}\n"
            f"  Admin review:    {cfg.get('admin_review', {}).get('frequency', '?')}\n"
        ))
