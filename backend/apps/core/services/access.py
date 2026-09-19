"""Access — who may see and change what. One source: the wc:model Setting.

Each model's Setting(purpose='wc:model').config.access.roles holds, per role:

    {
      "view":   ["id", "status", "totals.total", …],   # leaves only
      "edit":   ["status", …],                          # leaves only, ⊆ view
      "scope":  {"customer_id__in": "$user.org_ids.customer"},   # rows
      "edit_scope": {"assigned_to__contains": …},       # rows this role may change
      "create": false,
      "delete": false
    }

Long lists are stored once as named sets and referenced as "@name":

    "sets":  {"all": ["id", "ida", …every leaf, listed…]},
    "roles": {"admin": {"view": ["@all"], "edit": ["@all"], …}}

A set is a stored enumeration, not a wildcard: a leaf added to the schema
later is in no set until someone adds it.

A positive list (Bill, 2026-09-18): nothing leaves the server unless it is
named here. No wildcard, no parent path — every path is a leaf from
apps/core/services/field_leaves. A role with no block for a model, or a model
with no Setting, gets nothing. Superuser is a role with its own full lists,
not a bypass. An empty scope ({}) means every row; that is a row rule, not a
field wildcard.

The role is the login's role. The login is the Contact (AUTH_USER_MODEL =
core.Contact), so there is one field: contact.role. 'user' is not a role: a
contact whose role is 'user' has no access until given one. An agent may act as another role for a
request (header X-WC-Act-As) so agents can test what that role sees; it may
never act as superuser, and every act-as is logged.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# The role vocabulary (Bill, 2026-09-18). Portal roles are people outside the
# company; their writes are rewritten server-side where the model requires it.
STAFF_ROLES = ('superuser', 'admin', 'accounting', 'sales', 'production',
               'warehouse', 'employee', 'agent')
PORTAL_ROLES = ('rep', 'customer', 'buyer', 'vendor', 'manufacturer')
ROLES = STAFF_ROLES + PORTAL_ROLES
# Values contact.role may hold. 'user' means a contact with no login access.
LOGIN_ROLES = tuple(r for r in ROLES if r != 'superuser') + ('user',)

ACT_AS_HEADER = 'HTTP_X_WC_ACT_AS'
ACT_AS_ATTR = '_wc_act_as'

BLOCK_KEYS = {'view', 'edit', 'scope', 'edit_scope', 'create', 'delete'}

_cache: dict[str, dict] = {}


# ── Role ────────────────────────────────────────────────────────────────

def own_role(user) -> Optional[str]:
    """The user's own role: superuser, or contact.role when it is a known role."""
    if user is None or not getattr(user, 'is_authenticated', False):
        return None
    if user.is_superuser:
        return 'superuser'
    role = (getattr(user, 'role', '') or '').strip().lower()
    return role if role in ROLES else None


def user_role(user) -> Optional[str]:
    """The role this request runs as: an agent's act-as role, else the user's own."""
    acting = getattr(user, ACT_AS_ATTR, None)
    return acting or own_role(user)


def is_portal(user) -> bool:
    return user_role(user) in PORTAL_ROLES


def apply_act_as_user(user, meta: dict) -> Optional[str]:
    """Honour X-WC-Act-As for agents. Returns the role acted as, or None.

    Raises PermissionDenied when a non-agent asks, or the role is unknown or
    superuser — a refused act-as fails the request, it never falls back.
    """
    from rest_framework.exceptions import PermissionDenied
    wanted = (meta.get(ACT_AS_HEADER) or '').strip().lower()
    if not wanted:
        return None
    mine = own_role(user)
    if mine != 'agent':
        raise PermissionDenied(f'act-as is for agents; this login is {mine!r}')
    if wanted not in ROLES or wanted == 'superuser':
        raise PermissionDenied(f'cannot act as {wanted!r}')
    setattr(user, ACT_AS_ATTR, wanted)
    logger.info('[ACCESS] agent user=%s acting as %s: %s %s', user.id, wanted,
                meta.get('REQUEST_METHOD', ''), meta.get('PATH_INFO', ''))
    return wanted


# ── Open-read models ────────────────────────────────────────────────────
# Settings are the React app's interface: any signed-in role reads the whole
# record, only a superuser writes (Bill, 2026-09-18). Treat a Setting as seen by
# every login — nothing private goes in one; credentials live on Connection
# records. Not per-leaf: Setting config varies by purpose and is untyped.
OPEN_READ_MODELS = frozenset({'setting'})


def is_open_read(name: str) -> bool:
    return model_key(name) in OPEN_READ_MODELS


def open_read_can_write(user) -> bool:
    """Writes to an open-read model: the login's own superuser role (never act-as)."""
    return own_role(user) == 'superuser' and getattr(user, ACT_AS_ATTR, None) is None


# ── Blocks ──────────────────────────────────────────────────────────────

def model_key(name: str) -> Optional[str]:
    """The key a model's wc:model Setting uses (ModelMeta.key), or None.

    Accepts any name the API accepts ('bundle' → 'sync_bundle',
    'workorderline' → 'workorder_line').
    """
    from apps.core.services.field_leaves import canonical_key
    return canonical_key(name)


def expand_sets(paths: list, sets: dict) -> list:
    """Replace "@name" with the named set's leaves. An unknown set expands to nothing."""
    out: list = []
    for p in paths or []:
        if isinstance(p, str) and p.startswith('@'):
            out.extend(sets.get(p[1:], []))
        else:
            out.append(p)
    return out


def resolve_roles(acc: dict) -> dict:
    """access dict → {role: block} with sets expanded."""
    sets = acc.get('sets') or {}
    roles = {}
    for role, block in (acc.get('roles') or {}).items():
        b = dict(block)
        b['view'] = expand_sets(block.get('view', []), sets)
        b['edit'] = expand_sets(block.get('edit', []), sets)
        roles[role] = b
    return roles


def model_access(name: str) -> dict:
    """{role: block} for a model, sets expanded. Empty when the model has no Setting."""
    key = model_key(name)
    if key is None:
        return {}
    if key not in _cache:
        from apps.core.models.setting import Setting
        s = (Setting.objects.filter(purpose='wc:model', parent_model=key, is_deleted=False)
             .only('config').first())
        _cache[key] = resolve_roles((s.config or {}).get('access') or {}) if s else {}
    return _cache[key]


def block_for(user, name: str) -> Optional[dict]:
    """The access block for this user on this model, or None (no access)."""
    role = user_role(user)
    if role is None:
        return None
    return model_access(name).get(role)


def clear_cache(name: Optional[str] = None) -> None:
    if name is None:
        _cache.clear()
    else:
        _cache.pop(model_key(name) or name, None)


# ── Defaults ────────────────────────────────────────────────────────────

ACCOUNTING_MODELS = frozenset({'cash', 'ledger', 'gl_account', 'gl_journal', 'journal_batch',
                               'currency', 'term', 'tax_jurisdiction'})


def default_access(key: str) -> dict:
    """The access a new install starts with for one model.

    superuser and admin see and edit every leaf; agent sees every leaf and edits
    every leaf except on accounting models, never deletes. 'all' is the model's
    leaves enumerated now — a leaf added later is in no list until someone adds
    it. Every other role starts with nothing and is granted by an admin.
    """
    from apps.core.services import field_leaves as fl
    leaves = sorted(fl.model_leaves(key)['leaves'])
    full = {'view': ['@all'], 'edit': ['@all'], 'scope': {}, 'create': True, 'delete': True}
    agent = dict(full, delete=False)
    if key in ACCOUNTING_MODELS:
        agent.update(edit=[], create=False)
    return {'sets': {'all': leaves},
            'roles': {'superuser': full, 'admin': dict(full), 'agent': agent}}


# ── Validation ──────────────────────────────────────────────────────────

def validate_access(key: str, acc: dict) -> list[str]:
    """Problems with a model's access dict ({sets, roles}). Empty list = valid."""
    from apps.core.services import field_leaves as fl
    problems: list[str] = []
    sets = (acc or {}).get('sets') or {}
    for name, members in sets.items():
        if not isinstance(members, list):
            problems.append(f'{key}/sets/{name}: must be a list of leaves')
        elif any(isinstance(m, str) and m.startswith('@') for m in members):
            problems.append(f'{key}/sets/{name}: sets may not reference sets')
    for role, block in ((acc or {}).get('roles') or {}).items():
        for kind in ('view', 'edit'):
            for p in (block or {}).get(kind, []) if isinstance(block, dict) else []:
                if isinstance(p, str) and p.startswith('@') and p[1:] not in sets:
                    problems.append(f'{key}/{role}/{kind}: unknown set {p!r}')
    roles = resolve_roles(acc or {})
    try:
        info = fl.model_leaves(key)
    except LookupError as e:
        return [str(e)]
    leaves, opaque = info['leaves'], info['opaque']
    for role, block in (roles or {}).items():
        where = f'{key}/{role}'
        if role not in ROLES:
            problems.append(f'{where}: unknown role')
            continue
        if not isinstance(block, dict):
            problems.append(f'{where}: block must be an object')
            continue
        extra = set(block) - BLOCK_KEYS
        if extra:
            problems.append(f'{where}: unknown keys {sorted(extra)}')
        for kind in ('view', 'edit'):
            paths = block.get(kind, [])
            if not isinstance(paths, list):
                problems.append(f'{where}/{kind}: must be a list of leaves')
                continue
            for p in paths:
                if not isinstance(p, str) or '*' in p:
                    problems.append(f'{where}/{kind}: {p!r} — no wildcards')
                elif '$user.' in p:
                    head = p.split('$user.')[0]
                    if not any(leaf.startswith(head) for leaf in leaves):
                        problems.append(f'{where}/{kind}: {p!r} — no leaf under {head!r}')
                elif p not in leaves:
                    problems.append(f'{where}/{kind}: {p!r} is not a leaf')
                elif role in PORTAL_ROLES and p in opaque:
                    problems.append(f'{where}/{kind}: {p!r} is opaque (untyped) — '
                                    'not shown outside the company until it has a schema')
        stray = set(block.get('edit', [])) - set(block.get('view', []))
        if stray:
            problems.append(f'{where}: edit not viewable {sorted(stray)[:5]}')
    return problems
