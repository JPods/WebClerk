"""install_chart — build a new database's chart of accounts from a chart file.

    python manage.py install_chart              # apps/accounts/charts/standard.json
    python manage.py install_chart <name>       # apps/accounts/charts/<name>.json

The file is loaded like any other bundle (one Bundle record, one Log row) and only into a new
database: one with no GlAccount rows. Once operating, the company changes its accounts in the
chart and its posting roles in the company profile (config.gl_defaults). See
apps/accounts/services/chart.py.
"""
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models.gl_account import GlAccount
from apps.accounts.services.chart import CHARTS_DIR, standard_chart


class Command(BaseCommand):
    help = 'Build a new database\'s chart of accounts and role map from a chart file'

    def add_arguments(self, parser):
        parser.add_argument('name', nargs='?', default='standard',
                            help='chart file in apps/accounts/charts/ (default: standard)')

    def handle(self, *args, **options):
        if GlAccount.objects.exists():
            self.stdout.write('This database already has a chart of accounts — nothing installed. '
                              'Change accounts in the chart and roles in the company profile.')
            return
        from apps.core.services import bundle_import
        name = options['name']
        try:
            chart = standard_chart(name)
        except ValueError as e:
            raise CommandError(str(e))
        result = bundle_import.run(f'chart_{name}', chart, source=str(CHARTS_DIR / f'{name}.json'),
                                   load='chart')
        if result['errors']:
            raise CommandError(f'Chart "{name}" not installed (bundle #{result["bundle_id"]}):\n  '
                               + '\n  '.join(result['errors']))
        self.stdout.write(self.style.SUCCESS(
            f'Chart "{name}": {result["gl_accounts"]["created"]} accounts, '
            f'{result["roles"]["mapped"]} roles mapped (bundle #{result["bundle_id"]})'))
