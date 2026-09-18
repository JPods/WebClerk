"""Seed Document records for Alice readmes — one per consolidated doc.

Each Document has body content populated from the git-hosted markdown,
status='published' so HelpDashboard shows it, and git_path for sync.

Usage:
    python manage.py seed_alice_docs
    python manage.py seed_alice_docs --force  # overwrite existing
"""
from django.core.management.base import BaseCommand
from apps.docs.models.document import Document
from ._seed_docs_utils import build_doc_defaults


ALICE_DOCS = [
    {
        'ida': 'ALICE-README',
        'name': 'Alice — Overview',
        'description': 'Master index of Alice capabilities, Document record map, deployment guide',
        'git_path': 'readmes/alice/README.md',
        'sequence': 0,
        'tags': ['alice', 'readme', 'overview'],
    },
    {
        'ida': 'ALICE-PATTERN-RECOGNITION',
        'name': 'Alice — Pattern Recognition',
        'description': 'Observe > log > pattern > recommend > promote pipeline; Setting promotion; friction signals; happiness metric',
        'git_path': 'readmes/alice/pattern-recognition.md',
        'sequence': 10,
        'tags': ['alice', 'readme', 'training', 'patterns'],
    },
    {
        'ida': 'ALICE-OBSERVATION-SETUP',
        'name': 'Alice — Observation Setup',
        'description': 'AliceObservation, AlicePreset, AliceCoachingLog models; console capture; wcapi access; coaching UI; quiz engine',
        'git_path': 'readmes/alice/observation-setup.md',
        'sequence': 20,
        'tags': ['alice', 'readme', 'training', 'observations'],
    },
    {
        'ida': 'ALICE-DATA-QUALITY',
        'name': 'Alice — Data Quality',
        'description': 'Three-tier processing; data polishing (guess/review/validate); field size discipline; file storage enforcement',
        'git_path': 'readmes/alice/data-quality.md',
        'sequence': 30,
        'tags': ['alice', 'readme', 'training', 'data-quality'],
    },
    {
        'ida': 'ALICE-DEDUP',
        'name': 'Alice — Dedup',
        'description': 'Duplicate detection and extraction; matching strategies; bundle files; user operations; Claude escalation',
        'git_path': 'readmes/alice/dedup.md',
        'sequence': 40,
        'tags': ['alice', 'readme', 'training', 'dedup'],
    },
    {
        'ida': 'ALICE-ESCALATION',
        'name': 'Alice — Escalation Protocol',
        'description': 'What Alice can do vs. what needs Claude Code; Action-based handoff; capability gap tracking',
        'git_path': 'readmes/alice/escalation.md',
        'sequence': 50,
        'tags': ['alice', 'readme', 'training', 'escalation'],
    },
    {
        'ida': 'ALICE-TOOLKIT',
        'name': 'Alice — Toolkit',
        'description': 'Vector stores, MCP servers, quiz engine, diagramming, PDF generation, data conversion (Ingrid), Chrome DevTools',
        'git_path': 'readmes/alice/toolkit.md',
        'sequence': 60,
        'tags': ['alice', 'readme', 'reference', 'tools'],
    },
    {
        'ida': 'ALICE-LEARNING',
        'name': 'Alice — How Alice Learns',
        'description': '5 learning pathways; what does NOT teach Alice; memory architecture; MCP servers; failure modes',
        'git_path': 'readmes/alice/learning.md',
        'sequence': 70,
        'tags': ['alice', 'readme', 'training', 'learning'],
    },
    {
        'ida': 'ALICE-SUPPORT-QA',
        'name': 'Alice — Support Q&A System',
        'description': 'Full help lifecycle: search, ask, answer, score, WCHQ escalation; diagnostic context; quiz training; ~300 seeded Q&A',
        'git_path': 'readmes/alice/support-qa-system.md',
        'sequence': 75,
        'tags': ['alice', 'readme', 'training', 'support', 'qa'],
    },
    {
        'ida': 'ALICE-TSX-ARCHIVE',
        'name': 'Alice — TSX Archive',
        'description': 'File replacement study protocol; layout evolution tracking; field density analysis',
        'git_path': 'readmes/alice/tsx-archive.md',
        'sequence': 80,
        'tags': ['alice', 'readme', 'reference', 'archive'],
    },
    {
        'ida': 'ALICE-SETUP-GUIDE',
        'name': 'Alice — Setup Guide',
        'description': 'One-command setup; manual steps; AI modes; console capture; index management; troubleshooting',
        'git_path': 'readmes/alice/setup-guide.md',
        'sequence': 90,
        'tags': ['alice', 'readme', 'deployment', 'setup'],
    },
]


class Command(BaseCommand):
    help = 'Seed Document records for Alice readmes — body from git, status published'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Overwrite existing records')

    def handle(self, *args, **options):
        force = options['force']
        created = updated = skipped = missing = 0

        for doc in ALICE_DOCS:
            existing = Document.objects.filter(ida=doc['ida']).first()
            if existing and not force:
                skipped += 1
                continue

            defaults = build_doc_defaults(doc, 'alice-readmes')
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
            f'\nAlice docs: {created} created, {updated} updated, {skipped} skipped'
            + (f', {missing} missing files' if missing else '')
        ))
