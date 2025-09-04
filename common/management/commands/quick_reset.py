from django.core.management.base import BaseCommand
from common.rebuild import full_reset_and_seed


class Command(BaseCommand):
    help = (
        "Quick local reset: nuke migrations, regenerate single 0001_initial, drop/recreate DB, migrate, "
        "create 3 patterned superusers (no seeding by default). DEV ONLY."
    )

    def add_arguments(self, parser):  # pragma: no cover
        parser.add_argument('--seed', action='store_true', help='Also run default seed commands.')
        parser.add_argument('--superusers', type=int, default=3, help='Number of patterned superusers to create (default 3).')
        parser.add_argument('--no-nuke', action='store_true', help='Skip deleting migration files (just reset DB).')
        parser.add_argument('--force', action='store_true', help='Skip confirmation prompt.')

    def handle(self, *args, **opts):  # pragma: no cover
        if not opts.get('force') and not self._okay():
            self.stderr.write(self.style.ERROR('Aborted. Use --force to skip confirmation.'))
            return 2
        result = full_reset_and_seed(
            destructive=True,
            seed_commands=None,
            create_superusers=int(opts['superusers']),
            skip_seed=not opts['seed'],
            nuke_migrations=not opts['no_nuke'],
            auto_make_migrations=not opts['no_nuke'],
        )
        self.stdout.write(self.style.SUCCESS(
            f"Quick reset complete: db={result.db_name} migrations={'nuked' if not opts['no_nuke'] else 'kept'} "
            f"superusers={result.superusers} seeds={','.join(result.seed_commands_run) or 'none'}"
        ))
        return 0

    def _okay(self):  # pragma: no cover
        try:
            return input('Quick reset will DROP DB and NUKE migrations. Continue? (y/N) ').strip().lower() == 'y'
        except Exception:
            return False
