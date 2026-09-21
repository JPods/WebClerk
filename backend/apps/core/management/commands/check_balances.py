"""Does inventory and cash balance? Read-only. Alice runs this; so can anyone.

    manage.py check_balances                         # summary
    manage.py check_balances --json                  # the whole result, for Alice
    manage.py check_balances --item-id 612
    manage.py check_balances --scope inventory pending
    manage.py check_balances --fault                 # write a FAULT to ~/Allie/process/inbox on any finding

Exit status is 1 when anything is out of balance, so a script can act on it.
The checks themselves live in apps/core/services/balance_checker.py.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.core.services.balance_checker import STUCK_MINUTES, check_balances


def write_fault(result) -> Path | None:
    """One FAULT file per unbalanced run, in Allie's inbox (the fault/dnw/tf/tfts protocol)."""
    inbox = Path.home() / 'Allie' / 'process' / 'inbox'
    if not inbox.parent.exists():
        return None
    inbox.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    counts = ', '.join(f'{k} {v}' for k, v in sorted(result['counts'].items()))
    first = '\n'.join(f"  - {f['message']}" for f in result['findings'][:20])
    path = inbox / f"{now.strftime('%Y%m%dT%H%M%S')}-fault.md"
    path.write_text(
        f"# FAULT — {now.strftime('%Y-%m-%dT%H:%M:%SZ')}\n\n"
        f"system:      WC3\n"
        f"detected_by: Alice\n"
        f"fault:       out of balance in {result['database']}: {counts}\n"
        f"context:     check_balances ({', '.join(result['scope'])}); first findings:\n{first}\n"
        f"resolved_at: \n")
    return path


class Command(BaseCommand):
    help = 'Check that inventory and cash balance (read-only).'

    def add_arguments(self, parser):
        parser.add_argument('--scope', nargs='+', default=['inventory', 'cash', 'pending'],
                            choices=['inventory', 'cash', 'pending'])
        parser.add_argument('--item-id', type=int, default=None)
        parser.add_argument('--org-id', type=int, default=None)
        parser.add_argument('--stuck-minutes', type=int, default=STUCK_MINUTES)
        parser.add_argument('--json', action='store_true', help='print the whole result as JSON')
        parser.add_argument('--fault', action='store_true', help='write a FAULT file on any finding')

    def handle(self, *args, **options):
        result = check_balances(scope=tuple(options['scope']), item_id=options['item_id'],
                                org_id=options['org_id'], stuck_minutes=options['stuck_minutes'])
        if options['fault'] and not result['balanced']:
            path = write_fault(result)
            result['fault_file'] = str(path) if path else None

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
