"""Seed Document records for WC3 Operations documentation.

databrowser, email, saved searches, source attribution, coaching,
QA, community contributions — how users operate the system daily.

Usage:
    python manage.py seed_wc3_operations_docs
    python manage.py seed_wc3_operations_docs --force  # overwrite existing
"""
from django.core.management.base import BaseCommand
from apps.docs.models.document import Document
from ._seed_docs_utils import build_doc_defaults


WC3_OPERATIONS_DOCS = [
    {
        'ida': 'WC3-OPS-DATABROWSER',
        'name': 'databrowser Guide',
        'description': 'Admin data browser — list/detail for any model, column management, saved layouts',
        'git_path': 'readmes/databrowser-guide.md',
        'sequence': 500,
        'tags': ['wc3', 'operations', 'databrowser', 'training'],
        'qq_movie': 'qq_movie_here_2026-08-12: 3-min databrowser tour — navigate models, resize columns, save a layout, dark/light mode',
    },
    {
        'ida': 'WC3-OPS-DATABROWSER-LAYOUTS',
        'name': 'databrowser Initial Layouts',
        'description': 'Seeded layouts and column configurations — the starting point for every model',
        'git_path': 'readmes/databrowser-initial-layouts.md',
        'sequence': 510,
        'tags': ['wc3', 'operations', 'databrowser', 'layouts'],
    },
    {
        'ida': 'WC3-OPS-SAVED-SEARCHES',
        'name': 'Saved Searches',
        'description': 'Save and retrieve custom search queries — named presets for recurring lookups',
        'git_path': 'readmes/saved-searches.md',
        'sequence': 520,
        'tags': ['wc3', 'operations', 'search', 'presets'],
        'qq_movie': 'qq_movie_here_2026-08-12: 2-min saved searches — create a search, name it, share it, use the preset dropdown',
    },
    {
        'ida': 'WC3-OPS-EMAIL',
        'name': 'Email Operations',
        'description': 'Email system — send from transactions, templates, tracking, provider connections',
        'git_path': 'readmes/email-operations.md',
        'sequence': 530,
        'tags': ['wc3', 'operations', 'email', 'communications'],
    },
    {
        'ida': 'WC3-OPS-SOURCE-ATTRIBUTION',
        'name': 'Source Attribution',
        'description': 'Track where data came from — import, manual, sync, API — audit trail per record',
        'git_path': 'readmes/source-attribution.md',
        'sequence': 540,
        'tags': ['wc3', 'operations', 'attribution', 'audit'],
    },
    {
        'ida': 'WC3-OPS-COACHING',
        'name': 'Alice Coaching',
        'description': 'Real-time user coaching — hints, tips, drills, per-model guidance from Alice',
        'git_path': 'readmes/alice-coaching.md',
        'sequence': 550,
        'tags': ['wc3', 'operations', 'alice', 'coaching', 'training'],
        'qq_movie': 'qq_movie_here_2026-08-12: 2-min Alice coaching demo — hint bar appears, acknowledge a tip, run a quiz drill',
    },
    {
        'ida': 'WC3-OPS-QA',
        'name': 'QA Question Groups',
        'description': 'Quality inspection questions — 3-tier scoping, ASTM/FTA specs, per-item configuration',
        'git_path': 'readmes/qa-question-groups.md',
        'sequence': 560,
        'tags': ['wc3', 'operations', 'qa', 'quality'],
    },
    {
        'ida': 'WC3-OPS-COMMUNITY',
        'name': 'Community Contributions',
        'description': 'Marketplace and sharing — users submit layouts, presets, templates for credit/cash',
        'git_path': 'readmes/community-contributions.md',
        'sequence': 570,
        'tags': ['wc3', 'operations', 'community', 'marketplace'],
    },
    {
        'ida': 'WC3-OPS-RESET',
        'name': 'Reset & Rebuild',
        'description': 'Full system reset and baseline rebuild — destructive, for dev/demo only',
        'git_path': 'readmes/reset.md',
        'sequence': 580,
        'tags': ['wc3', 'operations', 'reset', 'maintenance'],
    },
]


class Command(BaseCommand):
    help = 'Seed Document records for WC3 Operations documentation'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Overwrite existing records')

    def handle(self, *args, **options):
        force = options['force']
        created = updated = skipped = missing = 0

        for doc in WC3_OPERATIONS_DOCS:
            existing = Document.objects.filter(ida=doc['ida']).first()
            if existing and not force:
                skipped += 1
                continue

            defaults = build_doc_defaults(doc, 'wc3-operations')
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
            f'\nWC3 Operations docs: {created} created, {updated} updated, {skipped} skipped'
            + (f', {missing} missing files' if missing else '')
        ))
