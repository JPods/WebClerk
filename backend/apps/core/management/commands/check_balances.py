"""Does inventory and cash balance? Read-only. Alice runs this; so can anyone.

    manage.py check_balances                         # summary
    manage.py check_balances --json                  # the whole result, for Alice
    manage.py check_balances --item-id 612
    manage.py check_balances --scope inventory pending

Exit status is 1 when anything is out of balance, so a script can act on it.
The checks themselves live in apps/core/services/balance_checker.py. Alice (Allie's
scripts/wc_balance.py) turns new findings into observations and FAULT files.
"""
import json
import sys

from django.core.management.base import BaseCommand

from apps.core.services.balance_checker import STUCK_MINUTES, check_balances


class Command(BaseCommand):
    help = 'Check that inventory and cash balance (read-only).'

    def add_arguments(self, parser):
        parser.add_argument('--scope', nargs='+', default=['inventory', 'cash', 'pending'],
                            choices=['inventory', 'cash', 'pending'])
        parser.add_argument('--item-id', type=int, default=None)
        parser.add_argument('--org-id', type=int, default=None)
        parser.add_argument('--stuck-minutes', type=int, default=STUCK_MINUTES)
        parser.add_argument('--json', action='store_true', help='print the whole result as JSON')

    def handle(self, *args, **options):
        result = check_balances(scope=tuple(options['scope']), item_id=options['item_id'],
                                org_id=options['org_id'], stuck_minutes=options['stuck_minutes'])
        if options['json']:
            self.stdout.write(json.dumps(result, indent=2, default=str))
        else:
            verdict = 'BALANCED' if result['balanced'] else 'OUT OF BALANCE'
            self.stdout.write(f"{verdict} — {result['database']} at {result['dt_checked']}")
            self.stdout.write(f"checked: {json.dumps(result['checked'])}")
            for check, n in sorted(result['counts'].items()):
                self.stdout.write(f"  {check}: {n}")
            for f in result['findings'][:40]:
                self.stdout.write(f"    {f['message']}")
            if len(result['findings']) > 40:
                self.stdout.write(f"    … {len(result['findings']) - 40} more (use --json)")
        if not result['balanced']:
            sys.exit(1)
