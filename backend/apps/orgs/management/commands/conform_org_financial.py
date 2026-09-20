"""Recompute every org's financial block in the OrgFinancial layout.

Dry run by default: reports, per org, the paths that would be removed (keys the
schema does not declare) and the values that would change. --apply saves.

    python manage.py conform_org_financial            # report only
    python manage.py conform_org_financial --apply
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction


def _leaves(value, prefix=''):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            out.update(_leaves(v, f'{prefix}.{k}' if prefix else k))
        return out
    return {prefix: value}


class Command(BaseCommand):
    help = "Recompute org.financial in the OrgFinancial layout (dry run unless --apply)"

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Save the recomputed blocks')

    def handle(self, *args, **opts):
        from apps.accounts.services.ledger_balance import update_org_balances
        from apps.orgs.models import OrgBase

        apply = opts['apply']
        removed_total = changed_total = orgs_changed = 0
        with transaction.atomic():
            for org in OrgBase.objects.order_by('id'):
                before = _leaves(org.financial or {})
                after = _leaves(update_org_balances(org, save=apply))
                removed = sorted(set(before) - set(after))
                changed = sorted(p for p in set(before) & set(after) if before[p] != after[p])
                added = sorted(p for p in set(after) - set(before) if after[p] not in (0, 0.0, '', None, False, [], 'USD', 'green', 'stable', 'salary', 30))
                if removed or changed or added:
                    orgs_changed += 1
                    removed_total += len(removed)
                    changed_total += len(changed)
                    self.stdout.write(f'org {org.id} {org.company!r}:')
                    for p in removed:
                        self.stdout.write(f'  - {p} = {before[p]!r}')
                    for p in changed:
                        self.stdout.write(f'  ~ {p}: {before[p]!r} → {after[p]!r}')
                    for p in added:
                        self.stdout.write(f'  + {p} = {after[p]!r}')
        verb = 'Applied' if apply else 'Dry run'
        self.stdout.write(self.style.SUCCESS(
            f'{verb}: {orgs_changed} orgs, {removed_total} undeclared keys removed, '
            f'{changed_total} values recomputed'))
