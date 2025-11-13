"""
Management command to migrate hardcoded frontend dropdowns to Setting records.
"""

from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting
from apps.core.services.frontend_dropdowns import frontend_dropdowns_service


class Command(BaseCommand):
    help = 'Migrate hardcoded frontend dropdowns to Setting records with purpose="front_end-ddl"'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing settings even if they already exist',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        force = options['force']

        self.stdout.write('Migrating frontend dropdowns to Setting records...')

        # Get current hardcoded dropdowns
        dropdowns = frontend_dropdowns_service.get_all_dropdowns()

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for dropdown_name, dropdown_data in dropdowns.items():
            setting_name = f'frontend-dropdown-{dropdown_name}'

            # Check if setting already exists
            existing = Setting.objects.filter(
                purpose='front_end-ddl',
                name=setting_name
            ).first()

            if existing and not force:
                self.stdout.write(f'  - {dropdown_name}: already exists (use --force to overwrite)')
                skipped_count += 1
                continue

            if dry_run:
                action = 'Would create' if not existing else 'Would update'
                self.stdout.write(f'  - {dropdown_name}: {action} with {len(dropdown_data)} items')
                continue

            # Create or update the setting
            if existing:
                existing.data = dropdown_data
                existing.save()
                updated_count += 1
                self.stdout.write(f'  - {dropdown_name}: updated')
            else:
                Setting.objects.create(
                    name=setting_name,
                    purpose='front_end-ddl',
                    data=dropdown_data,
                    is_active=True
                )
                created_count += 1
                self.stdout.write(f'  - {dropdown_name}: created')

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f'Dry run complete: {len(dropdowns)} dropdowns would be processed'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Migration complete: {created_count} created, {updated_count} updated, {skipped_count} skipped'
            ))