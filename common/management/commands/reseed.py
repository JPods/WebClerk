from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = "Unified reseed: full reset+seed or targeted per-model seeding. DEV ONLY."

    def add_arguments(self, parser):  # pragma: no cover
        parser.add_argument('--full', action='store_true', help='Drop DB, migrate, seed defaults, superusers (like nuke_reseed_3).')
        parser.add_argument('--superusers', type=int, default=3, help='Number of superusers to create (full mode).')
        parser.add_argument('--nuke-migrations', action='store_true', help='Full mode: delete migrations before migrate (dev only).')
        parser.add_argument('--auto-makemigrations', action='store_true', help='Full mode: run makemigrations after nuking migrations.')
        parser.add_argument('--seed-cmd', action='append', default=None, help='Extra seed command(s) to run in full mode (repeatable).')
        parser.add_argument('--model', type=str, help='Target a single model (app_label.Model or Model).')
        parser.add_argument('--table', type=str, help='Target by db table name.')
        parser.add_argument('--per-model', type=int, default=5, help='Count for reseed_all_models (non-full).')
        parser.add_argument('--apps', type=str, help='Restrict to app labels (comma-separated) when not targeting a single model.')
        parser.add_argument('--no-flush', action='store_true', help='Do not flush before reseed_all_models (non-full).')

    def handle(self, *args, **opts):  # pragma: no cover
        if opts['full']:
            # Delegate to full_reset_and_seed flow
            from common.rebuild.full_reset import full_reset_and_seed, DEFAULT_SEED_COMMANDS
            seed_cmds = opts['seed_cmd'] if opts['seed_cmd'] else DEFAULT_SEED_COMMANDS
            result = full_reset_and_seed(
                destructive=True,
                seed_commands=seed_cmds,
                seed_command_args=None,
                create_superusers=int(opts['superusers']),
                skip_seed=False,
                nuke_migrations=bool(opts['nuke_migrations']),
                auto_make_migrations=bool(opts['auto_makemigrations']),
            )
            # Seed default connections idempotently (moved out of nuke_reseed_3)
            try:
                call_command('seed_default_connections')
            except Exception:
                pass
            # Backfill Location display metadata (idempotent)
            try:
                from django.apps import apps as dj_apps
                Location = dj_apps.get_model('communications', 'Location')
                cnt = 0
                for loc in Location.objects.only('id', 'address1', 'address2', 'city', 'state', 'zip', 'country', 'metadata').iterator(chunk_size=200):
                    try:
                        loc.save()
                        cnt += 1
                    except Exception:
                        pass
                self.stdout.write(self.style.SUCCESS(f"Backfill: Location display updated ({cnt})."))
            except Exception:
                pass
            self.stdout.write(self.style.SUCCESS(f"Unified reseed complete: db={result.db_name} superusers={result.superusers}"))
            return 0
        # Non-full: delegate to reseed_all_models with extra filters
        args = []
        if opts.get('no_flush'):
            args.append('--no-flush')
        args += ['--per-model', str(int(opts['per_model']))]
        if opts.get('apps'):
            args += ['--apps', opts['apps']]
        if opts.get('model'):
            args += ['--model', opts['model']]
        if opts.get('table'):
            args += ['--table', opts['table']]
        call_command('reseed_all_models', *args)
        # Ensure relationships are built after targeted reseeds as well
        try:
            call_command('seed_relationships')
        except Exception:
            pass
        return 0
