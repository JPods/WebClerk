"""Seed Connection records for agent communication channels.

Alice → Claude Code escalation uses the internal connection to route
Action records that exceed Alice's 8B/20B model capability. The connection
carries the protocol: what to include, how to format, where it lands.

WC_HQ connection carries user template contributions and schema feedback
upstream. Bundle records flow through this connection.

Usage:
    ./manage.py seed_connections
    ./manage.py seed_connections --force   # overwrite existing config
"""
from django.core.management.base import BaseCommand
from apps.sync.models.connection import Connection


CONNECTIONS = [
    {
        'ida': 'conn-alice-claude',
        'name': 'Alice → Claude Code',
        'type': 'internal',
        'purpose': 'sync',
        'status': 'active',
        'comment': (
            'Escalation channel. Alice creates Action records when a user '
            'request exceeds her model capability. Claude Code picks them '
            'up at leftshoe (session start). No API call — Actions with '
            'config.escalation.to=claude_code are the queue.'
        ),
        'config': {
            'channel': 'action_queue',
            'from_agent': 'alice',
            'to_agent': 'claude_code',
            'action_filter': {
                'config__escalation__to': 'claude_code',
                'status': 'pending',
            },
            'escalation_protocol': {
                'action_ida_prefix': 'ALICE-ESCALATE',
                'required_fields': [
                    'config.escalation.reason',
                    'config.escalation.user_request',
                    'config.escalation.context',
                ],
                'priority_levels': ['normal', 'urgent'],
                'pickup_trigger': 'leftshoe',
                'resolution': 'Claude Code sets status=complete and writes result to config.escalation.resolution',
            },
            'alice_capabilities': {
                'can_do': [
                    'Answer WC3 feature questions',
                    'Draft simple markdown templates',
                    'Suggest field paths for models',
                    'Review template syntax',
                    'Create Action/Document/Observation records',
                    'Run quiz questions',
                    'Flag data quality issues',
                    'Basic calculations and lookups',
                ],
                'escalate_when': [
                    'Code changes (schema, migration, new fields)',
                    'Complex multi-step logic',
                    'Architecture decisions',
                    'Template system extensions',
                    'Bug diagnosis across multiple files',
                    'Security/permission changes',
                ],
            },
        },
        'rules': {
            'escalation': {
                'alice_tells_user': True,
                'alice_creates_action': True,
                'action_carries_full_context': True,
                'no_degraded_output': True,
                'service_is_free': True,
            },
        },
        'metadata': {
            'established': '2026-08-05',
            'doc': 'readmes/topics/ai/alice-escalation-protocol.md',
        },
    },
    {
        'ida': 'conn-wchq-upstream',
        'name': 'WC_HQ Upstream',
        'type': 'api',
        'purpose': 'sync',
        'status': 'active',
        'comment': (
            'User contributions flow upstream to WC_HQ. Template improvements, '
            'schema feedback, layout submissions. Alice reviews before sending. '
            'WC_HQ reviews before distributing. Wisdom of the Many.'
        ),
        'config': {
            'channel': 'bundle',
            'direction': 'push',
            'endpoint': '',
            'auth_method': 'api_key',
            'api_key_setting': 'wchq_api_key',
            'content_types': [
                'template_contribution',
                'schema_feedback',
                'layout_submission',
                'alice_observation',
            ],
            'review_required': True,
            'reviewer': 'alice',
        },
        'rules': {
            'submission': {
                'alice_reviews_before_send': True,
                'user_sees_status': True,
                'wchq_reviews_before_distribute': True,
                'no_pii_in_templates': True,
            },
        },
        'metadata': {
            'established': '2026-08-05',
            'doc': 'readmes/topics/ai/markdown-templates.md',
        },
    },
    {
        'ida': 'conn-local-server',
        'name': 'Local Server (Andi)',
        'type': 'api',
        'purpose': 'deploy',
        'status': 'draft',
        'comment': (
            'Local server — IT15, Mac Mini, or similar always-on machine. '
            'Runs WC3 Django + React2025 + Alice. Every installation gets one. '
            'User fills in their IP and domain after hardware setup.'
        ),
        'config': {
            'host': '',
            'hostname': '',
            'hardware': {
                'recommended': ['Intel NUC (IT15)', 'Mac Mini'],
                'minimum': {
                    'ram_gb': 8,
                    'storage_gb': 256,
                    'cpu_cores': 4,
                    'os': ['Ubuntu 22.04+', 'macOS 13+'],
                },
                'notes': 'Always-on. Local network. No cloud dependency for core operations.',
            },
            'deploy': {
                'method': 'rsync',
                'react_dist': '/opt/andi/apps/react2025/dist/',
                'django_root': '/opt/andi/apps/webClerk3/',
                'static_root': '/opt/andi/static/',
                'nginx_config': '/etc/nginx/sites-enabled/webclerk',
                'reload_cmd': 'sudo systemctl reload nginx',
                'restart_cmd': 'sudo systemctl restart gunicorn',
            },
            'services': {
                'gunicorn': {'port': 8000, 'workers': 4},
                'redis': {'port': 6379},
                'postgresql': {'port': 5432, 'db': 'commerce_expert'},
                'nginx': {'ports': [80, 443]},
            },
            'tunnel': {
                'provider': '',
                'domains': [],
                'notes': 'Cloudflare tunnel or similar for public access. Optional — WC3 works on local network without it.',
            },
            'alice': {
                'runs_on_server': True,
                'mcp_port': 5010,
                'vector_store': '/opt/andi/alice/.chroma_db_alice/',
                'escalation_connection': 'conn-alice-claude',
            },
        },
        'rules': {
            'deploy': {
                'build_react_first': True,
                'run_migrations': True,
                'seed_after_migrate': 'seed_freshstart --force',
                'collect_static': True,
                'restart_gunicorn': True,
            },
            'ownership': {
                'user_owns_hardware': True,
                'user_owns_data': True,
                'wchq_has_no_access': True,
                'notes': 'Sovereign installation. WC_HQ provides software and data services. The server and its data belong to the user.',
            },
        },
        'metadata': {
            'established': '2026-08-05',
            'doc': 'readmes/topics/infrastructure/',
        },
    },
    # -- Carrier connections (templates — user fills in credentials) ----------
    {
        'ida': 'conn-carrier-ups',
        'name': 'UPS',
        'type': 'api',
        'purpose': 'sync',
        'status': 'draft',
        'comment': 'UPS REST API. Get credentials at developer.ups.com. Set status=active when ready.',
        'config': {
            'carrier_code': 'ups',
            'credentials': {
                'client_id': '',
                'client_secret': '',
                'account_number': '',
            },
            'settings': {
                'test_mode': True,
                'label_format': 'pdf',
                'fuel_factor': 0,
                'handling_charge': 0,
                'markup_percent': 0,
            },
        },
        'metadata': {'established': '2026-08-05', 'doc': 'readmes/topics/transactions/packing.md'},
    },
    {
        'ida': 'conn-carrier-fedex',
        'name': 'FedEx',
        'type': 'api',
        'purpose': 'sync',
        'status': 'draft',
        'comment': 'FedEx REST API. Get credentials at developer.fedex.com. Set status=active when ready.',
        'config': {
            'carrier_code': 'fedex',
            'credentials': {
                'client_id': '',
                'client_secret': '',
                'account_number': '',
            },
            'settings': {
                'test_mode': True,
                'label_format': 'pdf',
                'markup_percent': 0,
            },
        },
        'metadata': {'established': '2026-08-05'},
    },
    {
        'ida': 'conn-carrier-usps',
        'name': 'USPS',
        'type': 'api',
        'purpose': 'sync',
        'status': 'draft',
        'comment': 'USPS REST API. Get credentials at developer.usps.com. Set status=active when ready.',
        'config': {
            'carrier_code': 'usps',
            'credentials': {
                'client_id': '',
                'client_secret': '',
            },
            'settings': {
                'test_mode': True,
                'label_format': 'pdf',
            },
        },
        'metadata': {'established': '2026-08-05'},
    },
    {
        'ida': 'conn-carrier-dhl',
        'name': 'DHL Express',
        'type': 'api',
        'purpose': 'sync',
        'status': 'draft',
        'comment': 'DHL Express REST API. Get credentials at developer.dhl.com. Set status=active when ready.',
        'config': {
            'carrier_code': 'dhl',
            'credentials': {
                'user_id': '',
                'password': '',
                'account_number': '',
            },
            'settings': {
                'test_mode': True,
                'label_format': 'pdf',
            },
        },
        'metadata': {'established': '2026-08-05'},
    },
]


class Command(BaseCommand):
    help = 'Seed Connection records for agent communication channels'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help='Overwrite config on existing records',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        created = updated = skipped = 0

        for spec in CONNECTIONS:
            ida = spec['ida']
            defaults = {
                'name': spec['name'],
                'type': spec['type'],
                'purpose': spec.get('purpose', ''),
                'status': spec.get('status', 'draft'),
                'comment': spec.get('comment', ''),
                'is_active': True,
            }

            conn, was_created = Connection.objects.update_or_create(
                ida=ida, defaults=defaults,
            )

            if was_created:
                conn.config = spec.get('config', {})
                conn.rules = spec.get('rules', {})
                conn.metadata = spec.get('metadata', {})
                conn.save(update_fields=['config', 'rules', 'metadata'])
                created += 1
                self.stdout.write(f'  Created: {spec["name"]} ({ida})')
            else:
                if force:
                    conn.config = spec.get('config', {})
                    conn.rules = spec.get('rules', {})
                    conn.metadata = spec.get('metadata', {})
                    conn.save(update_fields=['config', 'rules', 'metadata'])
                    updated += 1
                    self.stdout.write(f'  Updated: {spec["name"]} ({ida})')
                else:
                    skipped += 1
                    self.stdout.write(f'  Skipped: {spec["name"]} ({ida}) — use --force')

        self.stdout.write(self.style.SUCCESS(
            f'Connections: {created} created, {updated} updated, {skipped} skipped'
        ))
