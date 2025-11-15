"""
Management command to manage Setting records for model configurations.
Important: 2025-11-14
"""

import json
import os
from django.core.management.base import BaseCommand
from apps.core.models.setting import Setting


class Command(BaseCommand):
    help = 'Manage Setting records for model configurations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all settings',
        )
        parser.add_argument(
            '--model',
            type=str,
            help='Filter by model name',
        )
        parser.add_argument(
            '--purpose',
            type=str,
            help='Filter by purpose',
        )
        parser.add_argument(
            '--view',
            action='store_true',
            help='View setting data for specified model/purpose',
        )
        parser.add_argument(
            '--update-baseline',
            action='store_true',
            help='Update setting from baseline file',
        )
        parser.add_argument(
            '--baseline-dir',
            type=str,
            default='readmes/refs_setting_by_model',
            help='Directory containing baseline files (default: readmes/refs_setting_by_model)',
        )
        parser.add_argument(
            '--models-dir',
            type=str,
            default='readmes/refs_setting_by_model/models',
            help='Directory containing model-specific baseline files (default: readmes/refs_setting_by_model/models)',
        )
        parser.add_argument(
            '--all-models',
            action='store_true',
            help='Process all models found in baseline directory',
        )

    def handle(self, *args, **options):
        if options['list']:
            self._list_settings(options.get('model'), options.get('purpose'))
        elif options['view']:
            if not options.get('model') or not options.get('purpose'):
                self.stderr.write('Error: --view requires --model and --purpose')
                return
            self._view_setting(options['model'], options['purpose'])
        elif options['update_baseline']:
            if options['all_models']:
                self._update_all_baselines(options['baseline_dir'], options['models_dir'])
            elif options.get('model') and options.get('purpose'):
                self._update_baseline(options['model'], options['purpose'], options['baseline_dir'])
            else:
                self.stderr.write('Error: --update-baseline requires --model and --purpose, or --all-models')
        else:
            self.stdout.write('Use --list, --view, or --update-baseline option')

    def _list_settings(self, model_filter=None, purpose_filter=None):
        """List all settings with optional filters."""
        queryset = Setting.objects.all()

        if model_filter:
            queryset = queryset.filter(model_name=model_filter)
        if purpose_filter:
            queryset = queryset.filter(purpose=purpose_filter)

        settings = queryset.order_by('model_name', 'purpose')

        if not settings:
            self.stdout.write('No settings found.')
            return

        self.stdout.write(f'Found {settings.count()} setting(s):')
        for setting in settings:
            self.stdout.write(f'  {setting.model_name}.{setting.purpose} (ID: {setting.id}, Active: {setting.is_active})')

    def _view_setting(self, model_name, purpose):
        """View the data for a specific setting."""
        try:
            setting = Setting.objects.get(model_name=model_name, purpose=purpose)
            self.stdout.write(f'Setting: {model_name}.{purpose}')
            self.stdout.write(f'ID: {setting.id}')
            self.stdout.write(f'Active: {setting.is_active}')
            self.stdout.write('Data:')
            self.stdout.write(json.dumps(setting.data, indent=2))
        except Setting.DoesNotExist:
            self.stderr.write(f'Error: Setting {model_name}.{purpose} not found')

    def _update_baseline(self, model_name, purpose, baseline_dir):
        """Update a single setting from its baseline file."""
        baseline_file = os.path.join(baseline_dir, f'{purpose}.txt')

        if not os.path.exists(baseline_file):
            self.stderr.write(f'Error: Baseline file {baseline_file} not found')
            return

        try:
            with open(baseline_file, 'r') as f:
                content = f.read()

            # Parse the baseline file format
            # Expected format: "setting model_name="X" purpose="Y"\n{...}"
            lines = content.strip().split('\n')
            if len(lines) < 2:
                self.stderr.write(f'Error: Invalid baseline file format in {baseline_file}')
                return

            # Extract model_name and purpose from first line
            first_line = lines[0]
            if not first_line.startswith('setting model_name=') or 'purpose=' not in first_line:
                self.stderr.write(f'Error: Invalid header format in {baseline_file}')
                return

            # Parse the JSON data (everything after the header line)
            data_str = '\n'.join(lines[1:])
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError as e:
                self.stderr.write(f'Error: Invalid JSON in {baseline_file}: {e}')
                return

            # Create or update the setting
            setting, created = Setting.objects.update_or_create(
                model_name=model_name,
                purpose=purpose,
                defaults={'data': data, 'is_active': True}
            )

            self.stdout.write(
                self.style.SUCCESS(f'Setting {model_name}.{purpose} {"created" if created else "updated"} from baseline')
            )

        except Exception as e:
            self.stderr.write(f'Error processing baseline file: {e}')

    def _update_all_baselines(self, baseline_dir, models_dir=None):
        """Update all settings from baseline files in both main and models directories."""
        if models_dir is None:
            models_dir = os.path.join(baseline_dir, 'models')

        directories = [baseline_dir]
        if os.path.exists(models_dir):
            directories.append(models_dir)

        processed = 0

        for directory in directories:
            if not os.path.exists(directory):
                continue

            for filename in os.listdir(directory):
                if not filename.endswith('.txt'):
                    continue

                baseline_file = os.path.join(directory, filename)

                try:
                    with open(baseline_file, 'r') as f:
                        content = f.read()

                    lines = content.strip().split('\n')
                    if len(lines) < 2:
                        continue

                    first_line = lines[0]
                    if not first_line.startswith('setting model_name=') or 'purpose=' not in first_line:
                        continue

                    # Extract model_name and purpose from header
                    # Format: setting model_name="contact" purpose="refs_setup"
                    import re
                    model_match = re.search(r'model_name="([^"]+)"', first_line)
                    purpose_match = re.search(r'purpose="([^"]+)"', first_line)

                    if not model_match or not purpose_match:
                        continue

                    model_name = model_match.group(1)
                    purpose = purpose_match.group(1)

                    # Parse JSON data
                    data_str = '\n'.join(lines[1:])
                    data = json.loads(data_str)

                    # Create or update setting
                    setting, created = Setting.objects.update_or_create(
                        model_name=model_name,
                        purpose=purpose,
                        defaults={'data': data, 'is_active': True}
                    )

                    self.stdout.write(f'  {model_name}.{purpose}: {"created" if created else "updated"}')
                    processed += 1

                except Exception as e:
                    self.stderr.write(f'Error processing {filename}: {e}')

        self.stdout.write(
            self.style.SUCCESS(f'Processed {processed} baseline file(s)')
        )