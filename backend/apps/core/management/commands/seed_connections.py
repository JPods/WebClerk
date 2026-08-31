"""Seed Connection records for all connection classes.

Each connection class represents a category of external integration:
  - Internal: alice-claude, wchq-upstream, self-connection
  - Deploy: local server (Andi / Mac Mini / IT15)
  - Shipping: UPS, FedEx, USPS, DHL
  - Tax: Avalara, TaxJar, Vertex
  - Communication: Gmail, Outlook (email)
  - Calendar: Google Calendar, Outlook Calendar
  - Payment: Stripe, Square, PayPal
  - Accounting: QuickBooks, Xero (WC3 produces GL journal entries)
  - Banking: bank feed import (Statement Sorter)
  - Identity: MyCarryOn (portable sovereign identity)

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
        'ida': 'wchq-conn-upstream',
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
                'support_qa',
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
        'ida': 'wchq-conn-downstream',
        'name': 'WC_HQ Downstream',
        'type': 'api',
        'purpose': 'sync',
        'status': 'active',
        'comments': {
            'public': [{
                'text': (
                    'Content flows downstream from WC_HQ to this installation. '
                    'Init-bundle (Settings + Reports baseline), coaching updates, '
                    'select list improvements, security notices, version checks. '
                    'No business data — system configuration only. No auth required '
                    'for init-bundle; other content uses installation API key.'
                ),
            }],
        },
        'config': {
            'channel': 'api',
            'direction': 'pull',
            'wchq_base_url': 'https://webclerk.com',
            'endpoints': {
                'init_bundle': '/wcapi/init-bundle/',
                'register': '/wcapi/register-installation/',
                'coaching': '/wcapi/coaching/',
                'security': '/wcapi/security-notices/',
                'version': '/wcapi/version-check/',
            },
            'auth_method': 'api_key',
            'api_key_setting': 'wchq_api_key',
            'content_types': [
                'init_bundle',
                'coaching_updates',
                'select_list_improvements',
                'security_notices',
                'version_check',
            ],
            'auto_apply': {
                'init_bundle': False,
                'coaching_updates': True,
                'select_list_improvements': False,
                'security_notices': True,
            },
        },
        'rules': {
            'receiving': {
                'init_bundle_no_auth': True,
                'user_approves_select_list_changes': True,
                'security_notices_always_accepted': True,
                'coaching_auto_merge': True,
                'no_business_data_ever': True,
            },
        },
        'metadata': {
            'established': '2026-08-28',
            'doc': 'readmes/topics/architecture/wchq.md',
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
    {
        'ida': 'conn-tax-service',
        'name': 'Tax Service',
        'type': 'tax_service',
        'purpose': 'sync',
        'status': 'draft',
        'comment': (
            'External tax calculation service (Avalara, TaxJar, Vertex). '
            'Staged — not wired until a customer needs multi-jurisdiction tax. '
            'Simple case (one jurisdiction, one rate) uses TaxJurisdiction records directly. '
            'Set status=active and fill credentials when ready to go live.'
        ),
        'config': {
            'provider': '',  # 'avalara', 'taxjar', 'vertex'
            'credentials': {
                'api_key': '',
                'account_id': '',
                'url': '',
            },
            'settings': {
                'test_mode': True,
                'company_code': 'DEFAULT',
                'fallback_to_builtin': True,
            },
        },
        'metadata': {'established': '2026-08-09'},
    },
    # -- Communication connections ---------------------------------------------
    {
        'ida': 'conn-comm-gmail',
        'name': 'Gmail',
        'type': 'api',
        'purpose': 'sync',
        'status': 'draft',
        'comment': (
            'Gmail integration via Google Workspace API. Inbound: customer emails '
            'create or update Action records. Outbound: WC3 sends transactional '
            'email (order confirmations, shipping notifications, invoice delivery). '
            'Alice monitors for patterns — unanswered threads, repeat complaints.'
        ),
        'config': {
            'provider': 'google',
            'credentials': {
                'client_id': '',
                'client_secret': '',
                'refresh_token': '',
                'scopes': [
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/gmail.send',
                    'https://www.googleapis.com/auth/gmail.labels',
                ],
            },
            'settings': {
                'watch_labels': ['INBOX'],
                'auto_action': True,
                'action_rules': {
                    'new_thread_from_contact': 'create_action',
                    'reply_to_action_thread': 'update_action',
                },
                'outbound': {
                    'order_confirmation': True,
                    'shipping_notification': True,
                    'invoice_delivery': True,
                    'from_address': '',
                },
            },
        },
        'rules': {
            'privacy': {
                'no_bulk_export': True,
                'pii_stays_local': True,
                'alice_sees_metadata_only': True,
            },
        },
        'metadata': {
            'established': '2026-08-09',
            'class': 'communication',
            'doc': 'readmes/connections/communication.md',
        },
    },
    {
        'ida': 'conn-comm-outlook',
        'name': 'Outlook',
        'type': 'api',
        'purpose': 'sync',
        'status': 'draft',
        'comment': (
            'Outlook / Microsoft 365 email via Microsoft Graph API. Same flow as '
            'Gmail: inbound threads create Actions, outbound sends transactional '
            'email. User chooses Gmail OR Outlook — not both simultaneously.'
        ),
        'config': {
            'provider': 'microsoft',
            'credentials': {
                'client_id': '',
                'client_secret': '',
                'tenant_id': '',
                'scopes': [
                    'https://graph.microsoft.com/Mail.ReadWrite',
                    'https://graph.microsoft.com/Mail.Send',
                ],
            },
            'settings': {
                'watch_folders': ['Inbox'],
                'auto_action': True,
                'action_rules': {
                    'new_thread_from_contact': 'create_action',
                    'reply_to_action_thread': 'update_action',
                },
                'outbound': {
                    'order_confirmation': True,
                    'shipping_notification': True,
                    'invoice_delivery': True,
                    'from_address': '',
                },
            },
        },
        'rules': {
            'privacy': {
                'no_bulk_export': True,
                'pii_stays_local': True,
                'alice_sees_metadata_only': True,
            },
        },
        'metadata': {
            'established': '2026-08-09',
            'class': 'communication',
            'doc': 'readmes/connections/communication.md',
        },
    },
    # -- Calendar connections --------------------------------------------------
    {
        'ida': 'conn-cal-google',
        'name': 'Google Calendar',
        'type': 'api',
        'purpose': 'sync',
        'status': 'draft',
        'comment': (
            'Google Calendar via Google Workspace API. WC3 Actions with due dates '
            'sync to calendar events. Calendar events with WC3 tags sync back as '
            'Actions. Alice monitors for overdue items and scheduling conflicts.'
        ),
        'config': {
            'provider': 'google',
            'credentials': {
                'client_id': '',
                'client_secret': '',
                'refresh_token': '',
                'scopes': [
                    'https://www.googleapis.com/auth/calendar',
                    'https://www.googleapis.com/auth/calendar.events',
                ],
            },
            'settings': {
                'calendar_id': 'primary',
                'sync_direction': 'bidirectional',
                'action_to_event': {
                    'due_date': 'event.start',
                    'name': 'event.summary',
                    'comment': 'event.description',
                    'assigned_to': 'event.attendees',
                },
                'event_prefix': '[WC3]',
            },
        },
        'rules': {
            'sync': {
                'wc3_is_source_of_truth': True,
                'conflict_resolution': 'wc3_wins',
                'delete_sync': False,
            },
        },
        'metadata': {
            'established': '2026-08-09',
            'class': 'calendar',
            'doc': 'readmes/connections/calendar.md',
        },
    },
    {
        'ida': 'conn-cal-outlook',
        'name': 'Outlook Calendar',
        'type': 'api',
        'purpose': 'sync',
        'status': 'draft',
        'comment': (
            'Outlook Calendar via Microsoft Graph API. Same bidirectional Action ↔ '
            'Event sync as Google Calendar. User chooses one calendar provider.'
        ),
        'config': {
            'provider': 'microsoft',
            'credentials': {
                'client_id': '',
                'client_secret': '',
                'tenant_id': '',
                'scopes': [
                    'https://graph.microsoft.com/Calendars.ReadWrite',
                ],
            },
            'settings': {
                'calendar_id': 'primary',
                'sync_direction': 'bidirectional',
                'action_to_event': {
                    'due_date': 'event.start',
                    'name': 'event.summary',
                    'comment': 'event.body',
                    'assigned_to': 'event.attendees',
                },
                'event_prefix': '[WC3]',
            },
        },
        'rules': {
            'sync': {
                'wc3_is_source_of_truth': True,
                'conflict_resolution': 'wc3_wins',
                'delete_sync': False,
            },
        },
        'metadata': {
            'established': '2026-08-09',
            'class': 'calendar',
            'doc': 'readmes/connections/calendar.md',
        },
    },
    # -- Payment connections ---------------------------------------------------
    {
        'ida': 'conn-pay-stripe',
        'name': 'Stripe',
        'type': 'api',
        'purpose': 'sync',
        'status': 'draft',
        'comment': (
            'Stripe payment processing. WC3 creates payment intents, Stripe '
            'processes cards. Webhooks update Payment records. WC3 produces GL '
            'journal entries from completed payments — never holds card data.'
        ),
        'config': {
            'provider': 'stripe',
            'credentials': {
                'publishable_key': '',
                'secret_key': '',
                'webhook_secret': '',
            },
            'settings': {
                'test_mode': True,
                'currency': 'usd',
                'payment_methods': ['card'],
                'webhook_events': [
                    'payment_intent.succeeded',
                    'payment_intent.payment_failed',
                    'charge.refunded',
                    'charge.dispute.created',
                ],
                'auto_journal': True,
            },
        },
        'rules': {
            'pci': {
                'no_card_storage': True,
                'tokenize_only': True,
                'stripe_holds_pci_scope': True,
            },
            'accounting': {
                'wc3_produces_gl_entries': True,
                'debit_cash_credit_ar': True,
                'refund_reverses_entry': True,
            },
        },
        'metadata': {
            'established': '2026-08-09',
            'class': 'payment',
            'doc': 'readmes/connections/payment.md',
        },
    },
    {
        'ida': 'conn-pay-square',
        'name': 'Square',
        'type': 'api',
        'purpose': 'sync',
        'status': 'draft',
        'comment': (
            'Square payment processing. Same pattern as Stripe — WC3 sends '
            'payment requests, Square processes, webhooks update Payment records, '
            'WC3 produces GL journal entries.'
        ),
        'config': {
            'provider': 'square',
            'credentials': {
                'access_token': '',
                'application_id': '',
                'location_id': '',
                'webhook_signature_key': '',
            },
            'settings': {
                'test_mode': True,
                'currency': 'usd',
                'auto_journal': True,
            },
        },
        'rules': {
            'pci': {
                'no_card_storage': True,
                'tokenize_only': True,
            },
            'accounting': {
                'wc3_produces_gl_entries': True,
            },
        },
        'metadata': {
            'established': '2026-08-09',
            'class': 'payment',
            'doc': 'readmes/connections/payment.md',
        },
    },
    {
        'ida': 'conn-pay-paypal',
        'name': 'PayPal',
        'type': 'api',
        'purpose': 'sync',
        'status': 'draft',
        'comment': (
            'PayPal payment processing. Redirect flow — customer pays on PayPal, '
            'IPN/webhook updates WC3 Payment record. WC3 produces GL journal entries.'
        ),
        'config': {
            'provider': 'paypal',
            'credentials': {
                'client_id': '',
                'client_secret': '',
                'webhook_id': '',
            },
            'settings': {
                'test_mode': True,
                'currency': 'usd',
                'auto_journal': True,
            },
        },
        'rules': {
            'pci': {
                'no_card_storage': True,
                'paypal_holds_pci_scope': True,
            },
            'accounting': {
                'wc3_produces_gl_entries': True,
            },
        },
        'metadata': {
            'established': '2026-08-09',
            'class': 'payment',
            'doc': 'readmes/connections/payment.md',
        },
    },
    # -- Accounting connections ------------------------------------------------
    {
        'ida': 'conn-acct-quickbooks',
        'name': 'QuickBooks',
        'type': 'api',
        'purpose': 'export',
        'status': 'draft',
        'comment': (
            'QuickBooks Online integration. WC3 produces GL journal entries from '
            'production data (sales, payments, inventory). Journal entries export '
            'to QuickBooks. WC3 does not do checkbooks, payables, or P&L — '
            'QuickBooks owns that. Payable feedback (purchase receipts) imports '
            'for landed cost tracking.'
        ),
        'config': {
            'provider': 'quickbooks',
            'credentials': {
                'client_id': '',
                'client_secret': '',
                'realm_id': '',
                'refresh_token': '',
            },
            'settings': {
                'test_mode': True,
                'export': {
                    'journal_entries': True,
                    'customers': True,
                    'invoices': True,
                    'items': False,
                },
                'import': {
                    'purchase_receipts': True,
                    'vendor_bills': True,
                    'chart_of_accounts': True,
                },
                'sync_interval_minutes': 60,
            },
        },
        'rules': {
            'boundary': {
                'wc3_produces_gl_entries': True,
                'wc3_does_not_do_checkbooks': True,
                'wc3_does_not_do_payables': True,
                'wc3_does_not_do_pnl': True,
                'accounting_program_consumes_entries': True,
                'payable_feedback_for_landed_cost': True,
            },
        },
        'metadata': {
            'established': '2026-08-09',
            'class': 'accounting',
            'doc': 'readmes/connections/accounting.md',
        },
    },
    {
        'ida': 'conn-acct-xero',
        'name': 'Xero',
        'type': 'api',
        'purpose': 'export',
        'status': 'draft',
        'comment': (
            'Xero integration. Same boundary as QuickBooks — WC3 exports GL '
            'journal entries, imports payable feedback for landed cost. '
            'Xero owns checkbooks, payables, P&L, balance sheet.'
        ),
        'config': {
            'provider': 'xero',
            'credentials': {
                'client_id': '',
                'client_secret': '',
                'tenant_id': '',
            },
            'settings': {
                'test_mode': True,
                'export': {
                    'journal_entries': True,
                    'contacts': True,
                    'invoices': True,
                },
                'import': {
                    'purchase_receipts': True,
                    'bills': True,
                    'chart_of_accounts': True,
                },
            },
        },
        'rules': {
            'boundary': {
                'wc3_produces_gl_entries': True,
                'wc3_does_not_do_checkbooks': True,
                'wc3_does_not_do_payables': True,
                'accounting_program_consumes_entries': True,
                'payable_feedback_for_landed_cost': True,
            },
        },
        'metadata': {
            'established': '2026-08-09',
            'class': 'accounting',
            'doc': 'readmes/connections/accounting.md',
        },
    },
    # -- Banking connections ---------------------------------------------------
    {
        'ida': 'conn-bank-feed',
        'name': 'Bank Feed Import',
        'type': 'manual',
        'purpose': 'ingest',
        'status': 'draft',
        'comment': (
            'Bank statement import via Statement Sorter. User downloads CSV/OFX '
            'from their bank, uploads to WC3. Statement Sorter classifies '
            'transactions, matches to invoices and payments. Alice learns '
            'categorization patterns over time. No direct bank API — user '
            'controls what data enters the system.'
        ),
        'config': {
            'provider': 'manual_upload',
            'formats': ['csv', 'ofx', 'qfx', 'qbo'],
            'settings': {
                'statement_sorter_url': '/sort/',
                'auto_match_payments': True,
                'auto_categorize': True,
                'confidence_threshold': 0.85,
                'alice_learns_categories': True,
            },
        },
        'rules': {
            'privacy': {
                'user_uploads_manually': True,
                'no_direct_bank_api': True,
                'user_controls_data': True,
                'personal_transactions_never_in_db': True,
            },
            'matching': {
                'match_by_amount_and_date': True,
                'match_by_reference_number': True,
                'unmatched_flagged_for_review': True,
            },
        },
        'metadata': {
            'established': '2026-08-09',
            'class': 'banking',
            'doc': 'readmes/connections/banking.md',
        },
    },
    # -- Identity connections --------------------------------------------------
    {
        'ida': 'conn-identity-carryon',
        'name': 'MyCarryOn',
        'type': 'api',
        'purpose': 'sync',
        'status': 'draft',
        'comment': (
            'MyCarryOn portable sovereign identity. Contact records carry a '
            'carryon_uuid — the person owns their identity, WC3 holds a pointer. '
            'Permissions are enumerated, revocable, and sunset. Context travels '
            'with the person, not locked in any one system.'
        ),
        'config': {
            'provider': 'mycarryon',
            'credentials': {
                'api_key': '',
                'instance_url': '',
            },
            'settings': {
                'sync_direction': 'bidirectional',
                'contact_field': 'carryon_uuid',
                'permission_model': {
                    'enumerated': True,
                    'revocable': True,
                    'sunset_required': True,
                },
                'context_portable': True,
            },
        },
        'rules': {
            'sovereignty': {
                'person_owns_identity': True,
                'wc3_holds_pointer_not_identity': True,
                'permissions_expire': True,
                'no_data_hoarding': True,
            },
        },
        'metadata': {
            'established': '2026-08-09',
            'class': 'identity',
            'doc': 'readmes/connections/identity.md',
        },
    },
    # -- Multi-location upstream -----------------------------------------------
    {
        'ida': 'conn-upstream-hq',
        'name': 'Upstream HQ',
        'type': 'api',
        'purpose': 'sync',
        'status': 'draft',
        'comment': (
            'Upstream WC3 instance — this location sends GL journals, Alice '
            'escalations, and other data to HQ for consolidation. HQ does NOT '
            'load GL journals into its own database. Journals arrive as Bundle '
            'records (type=gl_journal) and are curated for accounting program '
            'handoff (QuickBooks, Xero). Same pipe carries Alice escalations '
            'and product data. Fill in endpoint and key when ready.'
        ),
        'config': {
            'endpoint': '',                 # e.g. 'https://hq.example.com'
            'key': '',                      # shared sync key
            'athena_token': '',             # for Alice escalation
            'subscription_tier': 'standard',
            'content_types': [
                'gl_journal',               # journal entries → curated for accounting
                'alice_escalation',         # low-confidence questions → HQ Alice
                'product_data',             # catalog sync from HQ
            ],
            'gl_journal': {
                'auto_send': False,         # manual until verified
                'period_format': 'YYYY-MM',
                'exclude_draft': True,
                'hq_does_not_load': True,   # HQ stores as Bundle, never GL tables
            },
        },
        'rules': {
            'sovereignty': {
                'location_owns_data': True,
                'hq_consolidates_not_stores': True,
                'journals_are_bundles_not_gl': True,
                'accounting_program_is_consumer': True,
            },
        },
        'metadata': {
            'established': '2026-08-31',
            'class': 'multi_location',
            'doc': 'readmes/connections/multi-location.md',
        },
    },
    # -- AI connections --------------------------------------------------------
    {
        'ida': 'conn-ai-escalation',
        'name': 'AI Escalation Chain',
        'type': 'api',
        'purpose': 'sync',
        'status': 'active',
        'comment': (
            'AI Escalation Chain: Alice local → Alice at WCHQ → Alice+Claude at WCHQ. '
            'Tier 1: Alice answers locally via Ollama RAG (always first, free). '
            'Tier 2: If confidence < 40%, escalate to WCHQ Alice — WCHQ runs a '
            'larger model on shared infrastructure (standard subscription). '
            'Tier 3: If WCHQ Alice is also low-confidence, WCHQ internally '
            'escalates to Claude (professional subscription). The individual '
            'installation never needs a Claude API key — WCHQ manages that '
            'relationship centrally. All escalations logged as '
            'AliceObservation(category=escalation).'
        ),
        'config': {
            'escalation_chain': {
                'tiers': [
                    {
                        'name': 'alice_local',
                        'source': 'Ollama RAG',
                        'always_first': True,
                        'cost': 'free',
                        'subscription': 'community',
                    },
                    {
                        'name': 'wchq_alice',
                        'source': 'WCHQ shared Alice',
                        'trigger': 'confidence < 40%',
                        'cost': '$4/person/mo',
                        'subscription': 'standard',
                        'endpoint': '/wcapi/alice/ask/',
                    },
                    {
                        'name': 'wchq_claude',
                        'source': 'WCHQ calls Claude',
                        'trigger': 'WCHQ Alice also low confidence',
                        'cost': '$9/person/mo',
                        'subscription': 'professional',
                        'endpoint': '/wcapi/alice/ask-claude/',
                    },
                ],
                'confidence': {
                    'threshold': 0.40,
                    'weights': {
                        'context_quality': 0.60,
                        'answer_quality': 0.40,
                    },
                    'signals': {
                        'context': 'vector distances + chunk count',
                        'answer': 'length + hedging phrase detection',
                    },
                },
            },
            'settings': {
                'alice_learns_from_escalations': True,
                'log_all_exchanges': True,
            },
        },
        'rules': {
            'sovereignty': {
                'no_api_key_required': True,
                'wchq_manages_claude_relationship': True,
                'question_only_sent_to_wchq': True,
                'no_raw_business_data_sent': True,
                'pii_scrubbed_before_send': True,
                'exchanges_logged_locally': True,
            },
            'escalation': {
                'always_try_local_first': True,
                'log_every_escalation': True,
                'include_local_answer_in_escalation': True,
                'graceful_fallback_to_local': True,
            },
        },
        'metadata': {
            'established': '2026-08-09',
            'updated': '2026-08-31',
            'class': 'ai',
            'doc': 'readmes/connections/connection-classes.md',
            'implementation': 'apps/ai_assistant/services/escalation.py',
        },
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
            # Build comments from spec — 'comment' (string) or 'comments' (dict)
            comments_val = spec.get('comments', {})
            if not comments_val and spec.get('comment'):
                comments_val = {'public': [{'text': spec['comment']}]}

            defaults = {
                'name': spec['name'],
                'type': spec['type'],
                'purpose': spec.get('purpose', ''),
                'status': spec.get('status', 'draft'),
                'comments': comments_val,
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
