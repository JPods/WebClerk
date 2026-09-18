"""Seed Document records for WC3 System documentation.

Core architecture, API, model registry, conventions — what a developer
or power user needs to understand how WC3 works under the hood.

Usage:
    python manage.py seed_wc3_system_docs
    python manage.py seed_wc3_system_docs --force  # overwrite existing
"""
from django.core.management.base import BaseCommand
from apps.docs.models.document import Document
from ._seed_docs_utils import build_doc_defaults


WC3_SYSTEM_DOCS = [
    {
        'ida': 'WC3-SYS-ARCHITECTURE',
        'name': 'WC3 Architecture Overview',
        'description': 'Core system architecture and design principles — the map of the whole system',
        'git_path': 'readmes/01-architecture-overview.md',
        'sequence': 100,
        'tags': ['wc3', 'system', 'architecture'],
        'qq_movie': 'qq_movie_here_2026-08-12: 3-min overview of WC3 architecture — models, wcapi, React, Alice',
    },
    {
        'ida': 'WC3-SYS-DEV-SETUP',
        'name': 'Developer Setup',
        'description': 'Installation and development environment setup for new team members',
        'git_path': 'readmes/02-dev-setup.md',
        'sequence': 110,
        'tags': ['wc3', 'system', 'setup', 'developer'],
        'qq_movie': 'qq_movie_here_2026-08-12: 4-min dev setup walkthrough — clone, venv, migrate, runserver, first login',
    },
    {
        'ida': 'WC3-SYS-WCAPI-GATEWAY',
        'name': 'wcapi Gateway',
        'description': 'The API gateway layer — how all data flows through wcapi',
        'git_path': 'readmes/03-wcapi-gateway.md',
        'sequence': 120,
        'tags': ['wc3', 'system', 'api', 'wcapi'],
    },
    {
        'ida': 'WC3-SYS-WCAPI-USAGE',
        'name': 'wcapi Usage Guide',
        'description': 'How to use wcapi — REST endpoints, get/save/manage patterns, authentication',
        'git_path': 'readmes/04-wcapi-usage.md',
        'sequence': 130,
        'tags': ['wc3', 'system', 'api', 'wcapi', 'training'],
        'qq_movie': 'qq_movie_here_2026-08-12: 3-min wcapi demo — GET a contact, SAVE changes, MANAGE an action',
    },
    {
        'ida': 'WC3-SYS-MODEL-REGISTRY',
        'name': 'Model Registry',
        'description': 'All data models registered in the system — the canonical list of what WC3 tracks',
        'git_path': 'readmes/05-model-registry.md',
        'sequence': 140,
        'tags': ['wc3', 'system', 'models', 'registry'],
    },
    {
        'ida': 'WC3-SYS-API-CONVENTIONS',
        'name': 'API Conventions',
        'description': 'Universal patterns — naming, pagination, error handling, JSON envelopes',
        'git_path': 'readmes/06-api-conventions.md',
        'sequence': 150,
        'tags': ['wc3', 'system', 'api', 'conventions'],
    },
    {
        'ida': 'WC3-SYS-REACT-INTEGRATION',
        'name': 'React Integration',
        'description': 'How React2025 connects to WC3 transaction models — the frontend/backend bridge',
        'git_path': 'readmes/07-react-integration.md',
        'sequence': 160,
        'tags': ['wc3', 'system', 'react', 'frontend'],
    },
    {
        'ida': 'WC3-SYS-JSON-ENVELOPES',
        'name': 'JSON Envelope Policy',
        'description': 'The three JSON fields on every record — .prefs, .metadata, .refs — what goes where',
        'git_path': 'readmes/json-envelope-policy.md',
        'sequence': 170,
        'tags': ['wc3', 'system', 'architecture', 'json'],
    },
    {
        'ida': 'WC3-SYS-SETTINGS',
        'name': 'Settings System',
        'description': 'Configuration records with scope hierarchy — how WC3 is configured per-installation',
        'git_path': 'readmes/settings.md',
        'sequence': 180,
        'tags': ['wc3', 'system', 'settings', 'configuration'],
    },
    {
        'ida': 'WC3-SYS-SETTING-POLICY',
        'name': 'Setting Policy',
        'description': 'What gets a Setting record and why — governance for the Setting model',
        'git_path': 'readmes/setting-policy.md',
        'sequence': 185,
        'tags': ['wc3', 'system', 'settings', 'policy'],
    },
    {
        'ida': 'WC3-SYS-PREFS',
        'name': 'Prefs Architecture',
        'description': 'Three-tier preference defaults — system, org, user — where defaults come from',
        'git_path': 'readmes/prefs-architecture.md',
        'sequence': 190,
        'tags': ['wc3', 'system', 'prefs', 'architecture'],
    },
    {
        'ida': 'WC3-SYS-QUERY-SCOPING',
        'name': 'Query Scoping',
        'description': 'How external users see only their data — RBAC applied at the wcapi layer',
        'git_path': 'readmes/wcapi-query-scoping.md',
        'sequence': 195,
        'tags': ['wc3', 'system', 'security', 'rbac'],
    },
    {
        'ida': 'WC3-SYS-APP-BOOTSTRAP',
        'name': 'App Bootstrap',
        'description': 'Server-driven startup data — what the React app loads at first paint',
        'git_path': 'readmes/app-bootstrap.md',
        'sequence': 200,
        'tags': ['wc3', 'system', 'react', 'startup'],
    },
    {
        'ida': 'WC3-SYS-REACT-V2',
        'name': 'React v2 Architecture',
        'description': 'React v2 frontend — Data-Driven UI, DynamicDetail, the world-class face for WC3',
        'git_path': 'readmes/react-v2-architecture.md',
        'sequence': 205,
        'tags': ['wc3', 'system', 'react', 'architecture'],
    },
    {
        'ida': 'WC3-SYS-SERVICES',
        'name': 'Services Reference',
        'description': 'Backend service patterns — single-purpose functions, where business logic lives',
        'git_path': 'readmes/services-reference.md',
        'sequence': 210,
        'tags': ['wc3', 'system', 'services', 'reference'],
    },
    {
        'ida': 'WC3-SYS-PENDING',
        'name': 'Pending Policy',
        'description': 'When changes queue vs apply immediately — the post-or-pend rule for financial/inventory',
        'git_path': 'readmes/pending-policy.md',
        'sequence': 215,
        'tags': ['wc3', 'system', 'pending', 'policy'],
    },
    {
        'ida': 'WC3-SYS-DENORM',
        'name': 'Denormalized Fields',
        'description': 'Denormalized snapshots in refs.links — what gets copied at transaction time',
        'git_path': 'readmes/denorm-fields.md',
        'sequence': 220,
        'tags': ['wc3', 'system', 'denormalization', 'refs'],
    },
    {
        'ida': 'WC3-SYS-ONBOARDING',
        'name': 'Onboarding',
        'description': 'New installation and new user onboarding — Alice guides the first session',
        'git_path': 'readmes/onboarding.md',
        'sequence': 225,
        'tags': ['wc3', 'system', 'onboarding', 'training'],
        'qq_movie': 'qq_movie_here_2026-08-12: 4-min first-time user walkthrough — login, dashboard, create first contact, create first order',
    },
    {
        'ida': 'WC3-SYS-MAINTENANCE',
        'name': 'Maintenance',
        'description': 'Centralized maintenance operations — scheduled tasks, database health, cleanup',
        'git_path': 'readmes/maintenance.md',
        'sequence': 230,
        'tags': ['wc3', 'system', 'maintenance', 'operations'],
    },
]


class Command(BaseCommand):
    help = 'Seed Document records for WC3 System documentation'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Overwrite existing records')

    def handle(self, *args, **options):
        force = options['force']
        created = updated = skipped = missing = 0

        for doc in WC3_SYSTEM_DOCS:
            existing = Document.objects.filter(ida=doc['ida']).first()
            if existing and not force:
                skipped += 1
                continue

            defaults = build_doc_defaults(doc, 'wc3-system')
            if not defaults['body']:
                missing += 1
                self.stdout.write(self.style.WARNING(f'  Missing: {doc["git_path"]}'))

            obj, was_created = Document.objects.update_or_create(
                ida=doc['ida'], defaults=defaults,
            )
            if was_created:
                created += 1
                self.stdout.write(f'  Created: {doc["ida"]}')
            else:
                updated += 1
                self.stdout.write(f'  Updated: {doc["ida"]}')

        self.stdout.write(self.style.SUCCESS(
            f'\nWC3 System docs: {created} created, {updated} updated, {skipped} skipped'
            + (f', {missing} missing files' if missing else '')
        ))
