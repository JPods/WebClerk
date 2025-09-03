from django.core.management.base import BaseCommand
from common.rebuild import full_reset_and_seed

class Command(BaseCommand):
    help = "Destructive local reset: drop DB, migrate, seed, create 3 patterned superusers (DEV ONLY)."

    def add_arguments(self, parser):  # pragma: no cover
        parser.add_argument('--no-seed', action='store_true', help='Skip seeding commands (still creates superusers).')
        parser.add_argument('--superusers', type=int, default=3, help='Number of patterned superusers to create.')
        parser.add_argument('--seed-cmd', action='append', dest='seed_cmds', help='Extra seed command(s) to run (can repeat).')
        parser.add_argument('--skip-superusers', action='store_true', help='Do not create any superusers.')
        parser.add_argument('--force', action='store_true', help='Override DEBUG False / safety guard (FORCE_FULL_RESET env also works).')

    def handle(self, *args, **opts):  # pragma: no cover - orchestration
        if not opts.get('force') and not self._okay():
            self.stderr.write(self.style.ERROR('Refusing to run without confirmation (use --force or set FORCE_FULL_RESET=1).'))
            return 2
        seed_cmds = opts.get('seed_cmds') or None
        result = full_reset_and_seed(
            destructive=True,
            seed_commands=seed_cmds,
            create_superusers=0 if opts.get('skip_superusers') else int(opts['superusers']),
            skip_seed=opts['no_seed'],
        )
        self.stdout.write(self.style.SUCCESS(
            f"Reset complete: db={result.db_name} superusers_created={result.superusers} seeds={','.join(result.seed_commands_run) or 'none'}"
        ))
        return 0

    def _okay(self):
        # Light interactive confirmation unless FORCE env set
        import os
        if os.getenv('FORCE_FULL_RESET'):
            return True
        try:
            resp = input('This is DESTRUCTIVE (drops DB). Continue? (y/N) ').strip().lower()
            return resp == 'y'
        except Exception:
            return False
