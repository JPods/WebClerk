"""
Management command to manage save hooks.
"""

from django.core.management.base import BaseCommand
from apps.core.constants.save_hooks import get_all_save_hooks, invalidate_save_hooks_cache


class Command(BaseCommand):
    help = 'Manage save hooks configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all save hooks',
        )
        parser.add_argument(
            '--invalidate-cache',
            action='store_true',
            help='Invalidate save hooks cache',
        )
        parser.add_argument(
            '--model',
            type=str,
            help='Filter by model name',
        )

    def handle(self, *args, **options):
        if options['list']:
            self._list_hooks(options.get('model'))
        elif options['invalidate_cache']:
            self._invalidate_cache()
        else:
            self.stdout.write('Use --list or --invalidate-cache option')

    def _list_hooks(self, model_filter=None):
        """List all save hooks."""
        hooks = get_all_save_hooks()

        if not hooks:
            self.stdout.write('No save hooks found.')
            return

        for model_name, model_hooks in hooks.items():
            if model_filter and model_name != model_filter:
                continue

            self.stdout.write(f'\nModel: {model_name}')
            for hook_name, hook_data in model_hooks.items():
                self.stdout.write(f'  Hook: {hook_name}')
                if 'save_pre' in hook_data:
                    self.stdout.write(f'    Pre-save: {len(hook_data["save_pre"])} chars')
                if 'save_post' in hook_data:
                    self.stdout.write(f'    Post-save: {len(hook_data["save_post"])} chars')

    def _invalidate_cache(self):
        """Invalidate save hooks cache."""
        invalidate_save_hooks_cache()
        self.stdout.write(
            self.style.SUCCESS('Save hooks cache invalidated.')
        )