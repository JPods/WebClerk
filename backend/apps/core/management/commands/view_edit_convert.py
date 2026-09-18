"""Write every role's positive leaf lists into the wc:model Settings.

One-time conversion (Bill, 2026-09-18). Reads the old rules — ModelRoleConfig
rows, falling back to role_defaults.ROLE_DEFAULTS exactly as the old
role_filter did — and writes, for every model Setting:

    config.access.roles.<role> = {view, edit, scope, edit_scope, create, delete}

Every "*" becomes the model's full leaf list and every parent path the leaves
under it. Old role names map to the short ones. New roles:
  employee — starts from sales
  agent    — admin's view lists; no edit on accounting models; may act as others
  buyer    — starts from customer
config.access.query_scope (never enforced) is dropped; publish is kept.

    python manage.py view_edit_convert --out report.json            # report
    python manage.py view_edit_convert --out report.json --apply    # write
"""
from __future__ import annotations

import json
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.constants.model_registry import MODEL_REGISTRY
from apps.core.models.setting import Setting
from apps.core.services import access
from apps.core.services import field_leaves as fl

OLD_TO_SHORT = {
    'superuser': 'superuser', 'admin': 'admin',
    'user_accounting': 'accounting', 'user_customer': 'customer',
    'user_manufacturer': 'manufacturer', 'user_production': 'production',
    'user_rep': 'rep', 'user_sales': 'sales', 'user_vendor': 'vendor',
    'user_warehouse': 'warehouse',
}
DERIVED = {'employee': 'sales', 'buyer': 'customer'}
ACCOUNTING_MODELS = access.ACCOUNTING_MODELS
OLD_MODEL_NAME = {'bill_of_material': 'bom', 'gl_account': 'glaccount'}


def old_rule(old_model: str, old_role: str):
    """The rule to carry forward.

    A code default with a view_deny is Bill's refined policy (2026-09-17: a
    customer sees their own price tier and no cost; a vendor sees last cost and
    inventory, no price). The old runtime let an older DB row override it, which
    showed customers every price tier. The refined default wins. Otherwise: the
    DB row if the role was active, else the code default — what actually ran.
    """
    from apps.core.models import ModelRoleConfig, RoleConfig
    from apps.core.services.role_defaults import get_effective_config
    code = get_effective_config(old_role, old_model) or None
    if code and code.get('view_deny'):
        return code
    if RoleConfig.objects.filter(role=old_role, is_active=True).exists():
        row = ModelRoleConfig.objects.filter(role=old_role, model_name=old_model).first()
        if row:
            return {'query_filters': row.query_filters or {}, 'view_fields': row.view_fields or [],
                    'edit_fields': row.edit_fields or [], 'allow_create': row.allow_create,
                    'allow_delete': row.allow_delete}
    return get_effective_config(old_role, old_model) or None


def expand(paths, leaves: frozenset, report: dict, where: str) -> list:
    if paths == '*' or paths == ['*']:
        report['wildcards'].append(where)
        return sorted(leaves)
    out: set[str] = set()
    for p in paths or []:
        if p == '*':
            report['wildcards'].append(where)
            out |= leaves
        elif '$user.' in p:
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


def to_block(cfg: dict, leaves: frozenset, report: dict, where: str) -> dict:
    view = expand(cfg.get('view_fields'), leaves, report, f'{where}/view')
    deny = set(cfg.get('view_deny') or [])
    if deny:
        view = [v for v in view if v not in deny and not any(v.startswith(d + '.') for d in deny)]
    edit = [e for e in expand(cfg.get('edit_fields'), leaves, report, f'{where}/edit') if e in view]
    scope = dict(cfg.get('query_filters') or {})
    edit_scope = scope.pop('_edit_filters', None) or cfg.get('edit_filters') or {}
    return {'view': view, 'edit': edit, 'scope': scope, 'edit_scope': edit_scope,
            'create': bool(cfg.get('allow_create')), 'delete': bool(cfg.get('allow_delete'))}


class Command(BaseCommand):
    help = 'Write positive leaf lists per role into every wc:model Setting'

    @staticmethod
    def pack(roles: dict, leaves: frozenset) -> dict:
        """Store each distinct long list once as a set; roles reference it by @name."""
        full = sorted(leaves)
        sets: dict = {'all': full}
        by_value = {tuple(full): 'all'}
        packed = {}
        for role in sorted(roles, key=access.ROLES.index):
            block = dict(roles[role])
            for kind in ('view', 'edit'):
                lst = sorted(block.get(kind, []))
                if len(lst) < 20:
                    block[kind] = lst
                    continue
                name = by_value.get(tuple(lst))
                if name is None:
                    name = f'{role}_{kind}'
                    sets[name] = lst
                    by_value[tuple(lst)] = name
                block[kind] = [f'@{name}']
            packed[role] = block
        return {'sets': sets, 'roles': packed}

    def add_arguments(self, parser):
        parser.add_argument('--out', required=True)
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **opts):
        report = defaultdict(list)
        proposed = {}
        settings = {s.parent_model: s for s in Setting.objects.filter(purpose='wc:model', is_deleted=False)}
        for key in sorted(settings):
            if key not in MODEL_REGISTRY:
                report['orphan_settings'].append(key)
                continue
            try:
                info = fl.model_leaves(key)
                leaves = info['leaves']
            except Exception as e:
                report['orphan_settings'].append(f'{key}: {e}')
                continue
            old_model = OLD_MODEL_NAME.get(key, key)
            roles = {}
            for old_role, short in OLD_TO_SHORT.items():
                cfg = old_rule(old_model, old_role)
                if cfg:
                    roles[short] = to_block(cfg, leaves, report, f'{key}/{short}')
            # Opaque (untyped) leaves never go to people outside the company.
            for role, block in roles.items():
                if role in access.PORTAL_ROLES:
                    dropped = [p for p in block['view'] if p in info['opaque']]
                    if dropped:
                        report['opaque_dropped_portal'].append(f'{key}/{role}: {len(dropped)}')
                    block['view'] = [p for p in block['view'] if p not in info['opaque']]
                    block['edit'] = [p for p in block['edit'] if p in block['view']]
            for new, base in DERIVED.items():
                if base in roles:
                    roles[new] = json.loads(json.dumps(roles[base]))
            if 'admin' in roles:
                agent = json.loads(json.dumps(roles['admin']))
                if key in ACCOUNTING_MODELS:
                    agent.update(edit=[], create=False, delete=False)
                agent['delete'] = False
                roles['agent'] = agent
            acc = self.pack(roles, leaves)
            problems = access.validate_access(key, acc)
            if problems:
                report['invalid'].extend(problems)
                continue
            proposed[key] = acc

        if opts['apply'] and not report.get('invalid'):
            with transaction.atomic():
                for key, roles in proposed.items():
                    s = settings[key]
                    cfg = dict(s.config or {})
                    acc = dict(cfg.get('access') or {})
                    acc.pop('query_scope', None)
                    acc.update(roles)          # {sets, roles}
                    cfg['access'] = acc
                    s.config = cfg
                    s._setting_update_authorized = True   # admin conversion, run by hand
                    s.save(update_fields=['config'])
            access.clear_cache()

        summary = {
            'models': len(proposed),
            'role_blocks': sum(len(a['roles']) for a in proposed.values()),
            'set_leaves_stored': sum(len(m) for a in proposed.values() for m in a['sets'].values()),
            'applied': bool(opts['apply'] and not report.get('invalid')),
            **{k: len(v) for k, v in report.items()},
        }
        with open(opts['out'], 'w') as fh:
            json.dump({'summary': summary, 'report': report, 'proposed': proposed},
                      fh, indent=1, sort_keys=True)
        self.stdout.write(json.dumps(summary, indent=1))
