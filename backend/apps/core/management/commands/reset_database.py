"""
Reset the entire database by clearing all data and resetting sequences.
"""
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connection


class Command(BaseCommand):
    help = "Clear all data from database tables and reset auto-increment sequences"

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm the destructive operation'
        )
        parser.add_argument(
            '--apps',
            nargs='*',
            help='Specific apps to reset (default: all project apps)'
        )
        parser.add_argument(
            '--include-django',
            action='store_true',
            help='Include Django built-in apps (auth, contenttypes, sessions, admin)'
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.ERROR(
                "This command will DELETE ALL DATA from the database. "
                "Use --confirm to proceed."
            ))
            return

        specific_apps = options.get('apps')
        include_django = options['include_django']

        # Get all models
        all_models = []
        exclude_apps = {'contenttypes', 'auth', 'sessions', 'admin'} if not include_django else set()
        for app_config in apps.get_app_configs():
            if app_config.label in exclude_apps:
                continue
            if specific_apps and app_config.label not in specific_apps:
                continue
            for model in app_config.get_models():
                if model._meta.abstract or model._meta.proxy:
                    continue
                all_models.append(model)

        if not all_models:
            self.stdout.write("No models found to reset.")
            return

        self.stdout.write(f"Resetting {len(all_models)} models...")

        # Delete all data
        for model in all_models:
            self.stdout.write(f"Clearing {model._meta.label}...")
            deleted_count = model.objects.all().delete()[0]
            if deleted_count > 0:
                self.stdout.write(f"  Deleted {deleted_count} records")

        # Reset sequences
        self.stdout.write("Resetting sequences...")
        for model in all_models:
            self.reset_sequence(model)

        self.stdout.write(self.style.SUCCESS("Database reset completed"))

    def reset_sequence(self, model):
        """Reset auto increment sequence for the model."""
        table_name = model._meta.db_table
        with connection.cursor() as cursor:
            # PostgreSQL specific
            sequence_name = f"{table_name}_id_seq"
            try:
                cursor.execute(f"ALTER SEQUENCE {sequence_name} RESTART WITH 1")
                self.stdout.write(f"  Reset {sequence_name}")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Could not reset {sequence_name}: {e}"))