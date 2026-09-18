"""Convert today's role rules into positive leaf lists — dry run.

Reads the rules the API enforces today (ModelRoleConfig rows, falling back to
role_defaults.py exactly as role_filter does) and writes, for every wc:model
Setting, the access block it would carry under the positive-list rule:

    config.access.roles.<role> = {view: [leaves], edit: [leaves],
                                  scope: {...}, create: bool, delete: bool}

Every "*" becomes the model's full leaf list; every parent path becomes the
leaves under it. Nothing is written to the database. The report says what was
expanded, what could not be resolved, and where edit is not a subset of view.

    python manage.py view_edit_convert --out /path/report.json
"""
from __future__ import annotations

import json
from collections import defaultdict

from django.core.management.base import BaseCommand

from apps.core.models.setting import Setting
from apps.core.services import field_leaves as fl

# Enforced role name → short name (Bill, 2026-09-18).
ROLE_SHORT = {
    'superuser': 'superuser',
    'admin': 'admin',
    'user_accounting': 'accounting',
    'user_customer': 'customer',
    'user_manufacturer': 'manufacturer',
    'user_production': 'production',
    'user_rep': 'rep',
    'user_sales': 'sales',
    'user_vendor': 'vendor',
    'user_warehouse': 'warehouse',
}

# RBAC model_name → wc:model key, where they differ.
RBAC_MODEL_KEY = {
    'bom': 'bill_of_material',
    'glaccount': 'gl_account',
}


def expand(paths, leaves: frozenset, report: dict, where: str) -> list:
    """Paths → sorted leaves. Records wildcards, parents, tokens and unknowns."""
    if paths == '*' or paths == ['*']:
        report['wildcards'].append(where)
        return sorted(leaves)
    out: set[str] = set()
    for p in paths or []:
        if p == '*':
            report['wildcards'].append(where)
            out |= leaves
        elif '$user.' in p:
            report['tokens'].append(f'{where}: {p}')
            out.add(p)
        elif p in leaves:
            out.add(p)
        else:
            under = {leaf for leaf in leaves if leaf.startswith(p + '.')}
            if under:
                report['parents'].append(f'{where}: {p} → {len(under)} leaves')
                out |= under
            else:
                report['unknown'].append(f'{where}: {p}')
    return sorted(out)


class Command(BaseCommand):
    help = 'Dry run: convert role rules into positive leaf lists per wc:model Setting'

    def add_arguments(self, parser):
        parser.add_argument('--out', required=True, help='Where to write the JSON report')

    def handle(self, *args, **opts):
        from apps.core.models import ModelRoleConfig, RoleConfig
        from apps.core.services.role_filter import get_role_filter_config

        report = defaultdict(list)
        proposed: dict = {}
        leaf_counts: dict = {}

        rbac_models = set(ModelRoleConfig.objects.values_list('model_name', flat=True))
        wc_keys = set(Setting.objects.filter(purpose='wc:model').values_list('parent_model', flat=True))

        # RBAC model names that match no wc:model key are reported, not guessed.
        for m in sorted(rbac_models):
            if RBAC_MODEL_KEY.get(m, m) not in wc_keys:
                report['rbac_model_without_setting'].append(m)

        active_roles = set(RoleConfig.objects.filter(is_active=True).values_list('role', flat=True))
        for r in sorted(set(ModelRoleConfig.objects.values_list('role', flat=True)) - active_roles):
            report['dead_role_rows'].append(r)

        key_to_rbac = {RBAC_MODEL_KEY.get(m, m): m for m in rbac_models}

        for model_key in sorted(wc_keys):
            try:
                info = fl.model_leaves(model_key)
            except LookupError as e:
                report['orphan_settings'].append(f'{model_key}: {e}')
                continue
            leaves = info['leaves']
            leaf_counts[model_key] = len(leaves)
            rbac_name = key_to_rbac.get(model_key, model_key)
            roles_out = {}
            for long_role, short in ROLE_SHORT.items():
                cfg = get_role_filter_config(rbac_name, long_role)
                if not cfg:
                    continue
                where = f'{model_key}/{short}'
                view = expand(cfg.get('view_fields'), leaves, report, f'{where}/view')
                edit = expand(cfg.get('edit_fields'), leaves, report, f'{where}/edit')
                deny = set(cfg.get('view_deny') or [])
                if deny:
                    view = [v for v in view
                            if v not in deny and not any(v.startswith(d + '.') for d in deny)]
                stray = sorted(set(edit) - set(view))
                if stray:
                    report['edit_not_viewable'].append(f'{where}: {len(stray)} leaves')
                roles_out[short] = {
                    'view': view,
                    'edit': edit,
                    'scope': cfg.get('query_filters') or {},
                    'create': bool(cfg.get('allow_create')),
                    'delete': bool(cfg.get('allow_delete')),
                }
            proposed[model_key] = {
                'missing_schemas': list(info['missing_schemas']),
                'open_maps': list(info['open_maps']),
                'roles': roles_out,
            }

        summary = {
            'models': len(proposed),
            'leaves': sum(leaf_counts.values()),
            'role_blocks': sum(len(p['roles']) for p in proposed.values()),
            **{k: len(v) for k, v in report.items()},
        }
        with open(opts['out'], 'w') as fh:
            json.dump({'summary': summary, 'report': report, 'proposed': proposed},
                      fh, indent=1, sort_keys=True)
        self.stdout.write(json.dumps(summary, indent=1))
