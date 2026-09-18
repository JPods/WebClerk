"""
Populate cache with settings data - using working version.
"""
from django.core.management.base import BaseCommand
from django.apps import apps
from apps.core.tasks.working_cache_tasks import update_all_settings_cache_working


class Command(BaseCommand):
    help = "Populate cache with settings and configuration data"

    def add_arguments(self, parser):
        parser.add_argument(
            '--cache-type',
            choices=['all', 'settings', 'constants', 'keywords', 'models', 'access'],
            default='settings',
            help='Type of cache to populate (default: settings)'
        )
        parser.add_argument(
            '--silent',
            action='store_true',
            help='Suppress output for automated runs'
        )

    def handle(self, *args, **options):
        cache_type = options['cache_type']
        silent = options['silent']
        
        if not silent:
            self.stdout.write(f"Populating cache: {cache_type}")
        
        if cache_type in ['all', 'settings']:
            try:
                result = update_all_settings_cache_working()
                if not silent:
                    status = "SUCCESS" if result['status'] == 'completed' else "FAILED"
                    self.stdout.write(self.style.SUCCESS(f"Settings cache: {status}"))
                    if result['status'] == 'completed':
                        self.stdout.write(f"  - Purposes cached: {len(result.get('purposes', []))}")
                        self.stdout.write(f"  - Total settings: {result.get('total_settings', 0)}")
                        self.stdout.write(f"  - Time taken: {result.get('elapsed', 'N/A')}s")
                    else:
                        self.stdout.write(self.style.ERROR(f"  - Error: {result.get('error', 'Unknown')}"))
            except Exception as e:
                if not silent:
                    self.stdout.write(self.style.ERROR(f"Settings cache error: {e}"))

        # Note: Other cache types would go here, but for now focusing on settings
        if cache_type not in ['all', 'settings'] and not silent:
            self.stdout.write(self.style.WARNING(f"Cache type '{cache_type}' not yet implemented"))
        
        if not silent:
            self.stdout.write(self.style.SUCCESS("Cache population completed"))