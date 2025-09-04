from django.core.management.base import BaseCommand
from common.rebuild import full_reset_and_seed


class Command(BaseCommand):
    help = "Fast dev cycle: nuke migrations, regenerate 0001_initial, drop/recreate DB, migrate, (optionally) seed, (optionally) create superusers. DEV ONLY."

    def add_arguments(self, parser):  # pragma: no cover
        parser.add_argument('--no-seed', action='store_true', help='Skip seeding commands.')
        parser.add_argument('--seed-cmd', action='append', dest='seed_cmds', help='Extra seed command(s) (repeatable).')
        parser.add_argument('--superusers', type=int, default=0, help='Patterned superusers to create (default 0 for speed).')
        parser.add_argument('--skip-superusers', action='store_true', help='Force 0 superusers regardless of --superusers.')
        parser.add_argument('--force', action='store_true', help='Bypass interactive confirmation (FORCE_FULL_RESET env also works).')

    def handle(self, *args, **opts):  # pragma: no cover
        if not opts.get('force') and not self._okay():
            self.stderr.write(self.style.ERROR('Aborted. Use --force to skip confirmation.'))
            return 2
        seed_cmds = opts.get('seed_cmds') or None
        result = full_reset_and_seed(
            destructive=True,
            seed_commands=seed_cmds,
            create_superusers=0 if opts.get('skip_superusers') else int(opts['superusers']),
            skip_seed=opts['no_seed'],
            nuke_migrations=True,
            auto_make_migrations=True,
        )
        self.stdout.write(self.style.SUCCESS(
            f"Dev nuke complete: db={result.db_name} migrations regenerated, seeds={','.join(result.seed_commands_run) or 'none'} superusers={result.superusers}"
        ))
        return 0

    def _okay(self):  # pragma: no cover
        import os
        if os.getenv('FORCE_FULL_RESET'):
            return True
        try:
            return input('DEV NUKE (destroys DB & rewrites migrations). Continue? (y/N) ').strip().lower() == 'y'
        except Exception:
            return False
