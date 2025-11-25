"""
Reset all migrations by deleting migration files and truncating django_migrations table.
"""
import os
import shutil
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connection


class Command(BaseCommand):
    help = "Reset all migrations by deleting files and truncating migration table"

    def handle(self, *args, **options):
        # Delete migration files
        for app_config in apps.get_app_configs():
            migrations_dir = os.path.join(app_config.path, 'migrations')
            if os.path.exists(migrations_dir):
                for filename in os.listdir(migrations_dir):
                    if filename != '__init__.py' and filename.endswith('.py'):
                        filepath = os.path.join(migrations_dir, filename)
                        os.remove(filepath)
                        self.stdout.write(f"Deleted {filepath}")

        # Drop all tables
        with connection.cursor() as cursor:
            # Get all table names
            cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            tables = [row[0] for row in cursor.fetchall()]
            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                self.stdout.write(f"Dropped table {table}")

        self.stdout.write("Dropped all tables")

        self.stdout.write(self.style.SUCCESS("Migrations reset. Run makemigrations and migrate."))