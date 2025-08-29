from django.core.management.base import BaseCommand
from apps.docs.models.document import Document
from django.db import transaction

SAMPLE_DOCS = [
    {
        'name': 'Spec Sheet A',
        'status': 'draft',
        'description': 'Initial specification for component A',
        'body': 'Component A specification including dimensions, tolerances, and materials.',
        'security_level': 1,
        'copyright': {'level':1,'path':'/legal/licenses/spec_a.txt','holder':'Acme','notes':[]},
        'data': {'category': 'spec', 'version': '1.0'},
    },
    {
        'name': 'User Guide',
        'status': 'published',
        'description': 'End-user installation and usage instructions',
        'body': 'Welcome to the user guide. This document explains how to install and operate the system.',
        'security_level': 0,
        'copyright': {'level':0,'path':'/legal/licenses/user_guide.txt','holder':'Acme','notes':[]},
        'data': {'category': 'manual', 'audience': 'end-user'},
    },
    {
        'name': 'API Reference',
        'status': 'published',
        'description': 'Comprehensive API endpoint reference',
        'body': 'API endpoints:\nGET /v1/resources\nPOST /v1/resources',
        'security_level': 1,
        'copyright': {'level':1,'path':'/legal/licenses/api_ref.txt','holder':'Acme','notes':[]},
        'data': {'category': 'api-docs', 'format': 'markdown'},
    },
    {
        'name': 'Release Notes 1.0',
        'status': 'archived',
        'description': 'Change log for release 1.0',
        'body': 'Version 1.0 introduces the initial feature set.',
        'security_level': 0,
        'copyright': {'level':0,'path':'/legal/licenses/release_1_0.txt','holder':'Acme','notes':[]},
        'data': {'category': 'release-notes', 'version': '1.0'},
    },
    {
        'name': 'Internal Roadmap',
        'status': 'internal',
        'description': 'Forward-looking internal planning document',
        'body': 'Q1: Core platform stabilization. Q2: Feature expansion.',
        'security_level': 2,
        'copyright': {'level':2,'path':'/legal/licenses/roadmap.txt','holder':'Acme','notes':[]},
        'data': {'category': 'roadmap', 'confidential': True},
    },
]

class Command(BaseCommand):
    help = 'Seed sample Document records (5). Skips existing names.'

    def handle(self, *args, **options):
        created = 0
        with transaction.atomic():
            for doc in SAMPLE_DOCS:
                if Document.objects.filter(name=doc['name']).exists():
                    self.stdout.write(self.style.WARNING(f"Skipping existing: {doc['name']}") )
                    continue
                instance = Document.objects.create(**doc)
                created += 1
                self.stdout.write(self.style.SUCCESS(f"Created: {instance.name}"))
        self.stdout.write(self.style.NOTICE(f"Seed complete. Created {created} new documents."))
