"""
Set security_level on every record of every model that carries it.

Bill, 2026-09-23: "We are in our demo data. So I want all the records available.
Default value = 0. We are setting them to 1 so we can access them."

A sweep, so it is dry-run unless --apply is given, and it prints what it would change
per table first. It writes with queryset.update and so does not go through the save door:
it changes one gate field, no money and no derived values, and is run by hand, once, on
Bill's instruction. With every item at 1, every item is public to anonymous visitors
(access.PUBLIC_READ); raise the ones that are not meant to be before real data goes in.

    python manage.py set_security_level --level 1            # dry run
    python manage.py set_security_level --level 1 --apply
"""
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Set security_level on every record of every model that has it (dry run by default)"

    def add_arguments(self, parser):
        parser.add_argument('--level', type=int, required=True)
        parser.add_argument('--apply', action='store_true', help='Write; without it, report only')

    def handle(self, *args, **options):
        level = options['level']
        if not 0 <= level <= 9:
            raise CommandError('level must be 0..9')

        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT table_name, data_type FROM information_schema.columns "
                           "WHERE column_name = 'security_level' AND table_schema = 'public'")
            column_type = dict(cursor.fetchall())

        targets = []
        for model in apps.get_models():
            meta = model._meta
            if meta.proxy or not meta.managed:
                continue
            if not any(f.name == 'security_level' for f in meta.concrete_fields):
                continue
            if column_type.get(meta.db_table) != 'integer':
                # Model and database disagree: report it, never write through the drift.
                self.stdout.write(self.style.WARNING(
                    f"  {meta.db_table:40s} skipped: column is "
                    f"{column_type.get(meta.db_table, 'missing')}, model says integer"))
                continue
            changing = model._base_manager.exclude(security_level=level).count()
            if changing:
                targets.append((model, changing))
                self.stdout.write(f"  {meta.db_table:40s} {changing:7d} → {level}")

        total = sum(n for _m, n in targets)
        if not options['apply']:
            self.stdout.write(f"Dry run: {total} records in {len(targets)} tables would change. "
                              "Add --apply to write.")
            return

        with transaction.atomic():
            for model, _n in targets:
                model._base_manager.exclude(security_level=level).update(security_level=level)
        self.stdout.write(self.style.SUCCESS(
            f"{total} records in {len(targets)} tables set to security_level {level}."))
