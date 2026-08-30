"""
Export all model data to JSON files — one file per model.

Daily rolling backup managed by Alice. Disk space is cheap;
losing data is not. 7-day rolling window, one directory per day.

Usage:
    python manage.py export_data              # today's export
    python manage.py export_data --prune      # export + prune old
    python manage.py export_data --dir /path  # custom output
"""
import os
import subprocess
import shutil
from datetime import datetime, timezone, timedelta

from django.conf import settings as django_settings
from django.core.management.base import BaseCommand
from django.apps import apps
from django.core import serializers
from django.db import connection

EXPORT_KEEP_DAYS = 7


class Command(BaseCommand):
    help = "Export all model data to JSON files (daily rolling backup)"

    def add_arguments(self, parser):
        parser.add_argument('--dir', type=str, help='Custom output directory')
        parser.add_argument('--prune', action='store_true', help='Prune exports older than 7 days')

    def handle(self, *args, **options):
        data_dir = getattr(django_settings, 'DATA_DIR', None)
        base = str(data_dir) if data_dir else os.path.join(os.getcwd(), 'data')
        exports_root = os.path.join(base, 'exports')

        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        target_dir = options.get('dir') or os.path.join(exports_root, today)
        os.makedirs(target_dir, exist_ok=True)

        models = apps.get_models()
        exported = 0
        errors = 0

        for model in models:
            model_name = model.__name__.lower()
            filepath = os.path.join(target_dir, f"{model_name}.json")

            try:
                data = serializers.serialize('json', model.objects.all(), indent=2)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(data)
                exported += 1
            except Exception as e:
                self.stderr.write(f"Error exporting {model._meta.label}: {e}")
                errors += 1

        self.stdout.write(self.style.SUCCESS(
            f"Exported {exported} models to {target_dir} ({errors} errors)"
        ))

        # pg_dump — fast restore path alongside portable JSON
        self._pg_dump(target_dir)

        if options.get('prune'):
            pruned = self._prune_old(exports_root)
            self.stdout.write(f"Pruned {pruned} old export(s)")

    def _pg_dump(self, target_dir: str):
        """Run pg_dump into the same daily directory."""
        db = connection.settings_dict
        db_name = db.get('NAME', '')
        if not db_name:
            self.stderr.write("pg_dump skipped — no database name in settings")
            return

        dump_path = os.path.join(target_dir, f"{db_name}.dump")
        cmd = ['pg_dump', '-Fc', db_name, '-f', dump_path]

        # Add connection params if not default
        host = db.get('HOST', '')
        port = db.get('PORT', '')
        user = db.get('USER', '')
        if host and host != 'localhost':
            cmd.extend(['-h', host])
        if port:
            cmd.extend(['-p', str(port)])
        if user:
            cmd.extend(['-U', user])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                size = os.path.getsize(dump_path)
                self.stdout.write(f"pg_dump: {db_name}.dump ({size:,} bytes)")
            else:
                self.stderr.write(f"pg_dump failed: {result.stderr.strip()}")
        except FileNotFoundError:
            self.stderr.write("pg_dump not found — PostgreSQL client tools not installed")
        except subprocess.TimeoutExpired:
            self.stderr.write("pg_dump timed out after 5 minutes")
        except Exception as e:
            self.stderr.write(f"pg_dump error: {e}")

    def _prune_old(self, exports_root: str) -> int:
        if not os.path.exists(exports_root):
            return 0
        cutoff = datetime.now(timezone.utc) - timedelta(days=EXPORT_KEEP_DAYS)
        pruned = 0
        for dirname in sorted(os.listdir(exports_root)):
            dirpath = os.path.join(exports_root, dirname)
            if not os.path.isdir(dirpath):
                continue
            try:
                dir_date = datetime.strptime(dirname, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                if dir_date < cutoff:
                    shutil.rmtree(dirpath)
                    pruned += 1
            except ValueError:
                pass
        return pruned