"""
Management command to populate project.refs.links.contact with all active contacts.

This populates each active project's refs.links.contact[] with denormalized contact
objects: [{"id": #, "attention": "..."}, ...]

Usage:
    python manage.py populate_project_contacts
    python manage.py populate_project_contacts --dry-run
    python manage.py populate_project_contacts --project-id=123
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.transactions.models.project import Project
from apps.core.models.contact import Contact


class Command(BaseCommand):
    help = 'Populate project.refs.links.contact with all active contacts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--project-id',
            type=int,
            help='Only update a specific project by ID',
        )
        parser.add_argument(
            '--clear-first',
            action='store_true',
            help='Clear existing contacts before populating',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        project_id = options.get('project_id')
        clear_first = options['clear_first']

        # Get all active contacts with id and attention
        active_contacts = Contact.objects.filter(is_active=True).values('id', 'attention')
        contact_list = [
            {"id": c['id'], "attention": c['attention'] or ''}
            for c in active_contacts
        ]

        self.stdout.write(f"Found {len(contact_list)} active contacts")

        # Get projects to update
        if project_id:
            projects = Project.objects.filter(pk=project_id, is_active=True)
        else:
            projects = Project.objects.filter(is_active=True)

        project_count = projects.count()
        self.stdout.write(f"Found {project_count} active project(s) to update")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be made"))
            for project in projects[:5]:  # Show sample
                self.stdout.write(f"  Would update Project #{project.id}: {project.name or project.intent}")
            if project_count > 5:
                self.stdout.write(f"  ... and {project_count - 5} more")
            return

        updated_count = 0
        with transaction.atomic():
            for project in projects:
                refs = project.refs or {}
                if not isinstance(refs, dict):
                    refs = {}
                
                links = refs.setdefault('links', {})
                if not isinstance(links, dict):
                    links = {}
                    refs['links'] = links

                if clear_first or 'contact' not in links:
                    links['contact'] = contact_list.copy()
                else:
                    # Merge: add contacts not already present
                    existing_ids = {c.get('id') for c in links.get('contact', []) if isinstance(c, dict)}
                    for contact in contact_list:
                        if contact['id'] not in existing_ids:
                            links['contact'].append(contact)

                project.refs = refs
                project.save(update_fields=['refs', 'dt_modified', 'version'])
                updated_count += 1
                
                if updated_count % 50 == 0:
                    self.stdout.write(f"  Updated {updated_count} projects...")

        self.stdout.write(self.style.SUCCESS(
            f"Successfully updated {updated_count} project(s) with {len(contact_list)} contacts each"
        ))
