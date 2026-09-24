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

from django.db.models import Q

logger = logging.getLogger(__name__)

# The role vocabulary (Bill, 2026-09-18). Portal roles are people outside the
# company; their writes are rewritten server-side where the model requires it.
STAFF_ROLES = ('superuser', 'admin', 'accounting', 'sales', 'production',
               'warehouse', 'employee', 'agent', 'rep')
#: People outside the company. A rep is not one of them (Bill, 2026-09-20: "Reps need to
#: behave like staff"): a rep sells on the company's behalf, and being counted as portal
#: meant the order-creation path rewrote their payload against org_ids.customer — which a
#: rep's org does not have, so a rep could not raise an order at all.
PORTAL_ROLES = ('customer', 'buyer', 'vendor', 'manufacturer')
ROLES = STAFF_ROLES + PORTAL_ROLES
# Values contact.role may hold. 'user' means a contact with no login access.
LOGIN_ROLES = tuple(r for r in ROLES if r != 'superuser') + ('user',)

ACT_AS_HEADER = 'HTTP_X_WC_ACT_AS'
#: Where the authentication class leaves a validated act-as role for Actor.from_request.
ACT_AS_REQUEST_ATTR = 'wc_act_as'

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




def is_portal(actor) -> bool:
    from apps.core.services.door import as_actor
    return as_actor(actor).role in PORTAL_ROLES


#: Roles a Connection may hold (Bill, 2026-09-23): the portal roles, rep, and the
#: employee-level roles. Never admin or superuser — a Connection holding either would make
#: sync privileged again by the side door. 'agent' is a login role, not applicable here.
CONNECTION_ROLES = PORTAL_ROLES + ('rep', 'employee', 'accounting', 'sales', 'production',
                                   'warehouse')


def connection_role(connection) -> Optional[str]:
    """The role a Connection holds, or None. An inactive Connection holds none — disabling
    it revokes it, with no second field for anyone to remember to clear."""
    if connection is None:
        return None
    if not getattr(connection, 'is_active', False) or getattr(connection, 'status', '') != 'active':
        return None
    role = (getattr(connection, 'role', '') or '').strip().lower()
    return role if role in CONNECTION_ROLES else None


def act_as_role(user, meta: dict) -> Optional[str]:
    """Validate X-WC-Act-As for an agent login. Returns the role to act as, or None.

    Raises PermissionDenied when a non-agent asks, or the role is unknown or
    superuser — a refused act-as fails the request, it never falls back. The role is
    carried by the request's Actor (Actor.acting_as), never written onto the user
    object (Bill, 2026-09-23: the identity is per call, the login is a record).
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


# ── Security level: the first of three read gates ───────────────────────
# Bill, 2026-09-23. Every read passes three gates, each answering one question:
#   1. security_level  — how sensitive is this record        (per record, here)
#   2. role blocks     — what may this role do with the model (view/edit, below)
#   3. id injection    — whose record is it                  (scope: customer_id, vendor_id, rep_id)
# 0 is unpublished and is the column default: staff only. Everyone else sees a record
# when 0 < security_level <= their ceiling. Roles live in code (Bill: they rarely change).
STAFF_LEVEL = 9
PUBLIC_LEVEL = 1          # the anonymous visitor's ceiling
STAFF_FLAG_LEVEL = 4      # a login flagged is_staff (Bill, 2026-09-23)
LEVEL_CEILING = {
    'superuser': STAFF_LEVEL, 'admin': STAFF_LEVEL,
    'employee': 4, 'accounting': 4, 'sales': 4, 'production': 4, 'warehouse': 4, 'agent': 4,
    'rep': 3, 'vendor': 3, 'manufacturer': 3,
    'customer': 2, 'buyer': 2,
}

#: Models whose new records start unpublished (0): publishing is a deliberate act, and
#: Alice counts what is waiting. Every other new record is stamped NEW_RECORD_LEVEL so
#: its creator sees it (Bill, 2026-09-23).
PUBLISHED_MODELS = frozenset({'item'})
NEW_RECORD_LEVEL = 1


def level_ceiling(actor) -> Optional[int]:
    """The highest security_level this actor may see; None = no role, sees nothing."""
    from apps.core.services.door import as_actor
    actor = as_actor(actor)
    if actor.kind == 'public':
        return PUBLIC_LEVEL
    if not actor.is_guarded:
        return STAFF_LEVEL
    role = actor.role
    ceiling = LEVEL_CEILING.get(role) if role else None
    # One level per contact, the higher (Bill, 2026-09-23): is_staff sets 4, a role with a
    # higher ceiling takes over. is_staff grants no model access — that is the role's.
    user = actor.user if actor.kind in ('user', 'staff') else None
    if user is not None and getattr(user, 'is_staff', False):
        ceiling = max(STAFF_FLAG_LEVEL, ceiling or 0)
    return ceiling


def level_q(actor) -> Q:
    """Gate 1 as a filter: staff see 0..9, everyone else 0 < level <= ceiling."""
    ceiling = level_ceiling(actor)
    if ceiling is None:
        return Q(pk__isnull=True)
    if ceiling >= STAFF_LEVEL:
        return Q(security_level__lte=ceiling)
    return Q(security_level__gt=0, security_level__lte=ceiling)


def new_record_level(name: str) -> int:
    return 0 if model_key(name) in PUBLISHED_MODELS else NEW_RECORD_LEVEL


# ── Public: the anonymous visitor ───────────────────────────────────────
# A record is public only when its model is listed here AND it passes gate 1 at the
# anonymous ceiling (level 1). Anything more requires a login. Items only (Bill).
PUBLIC_READ = {
    'item': ('id', 'ida', 'sku', 'name', 'description', 'kind', 'uom',
             'price.retail', 'price.currency',
             'refs.categories', 'refs.tags', 'refs.keywords', 'refs.variants'),
}


#: What a person may write on their own contact, role or none (Bill, 2026-09-23: a person
#: always reaches their own record). Authority fields are never here — the contact guard
#: refuses them regardless.
SELF_CONTACT_EDIT = ('email', 'name_first', 'name_last', 'name_middle', 'name_prefix',
                     'name_suffix', 'title')


def public_fields(name: str) -> tuple:
    """The leaves an anonymous visitor may see on a published record; () = not public."""
    return PUBLIC_READ.get(model_key(name) or '', ())


def is_admin(actor) -> bool:
    """Admin authority: a login that is superuser or whose OWN role is admin — never an
    act-as role, never a Connection, and not is_staff (Bill, 2026-09-23: is_staff sets a
    security level, it is not admin). One definition; it replaced three copies."""
    from apps.core.services.door import as_actor
    actor = as_actor(actor)
    user = actor.user if actor.kind in ('user', 'staff') else None
    if not user or not getattr(user, 'is_authenticated', False):
        return False
    return bool(getattr(user, 'is_superuser', False) or own_role(user) == 'admin')


def open_read_can_write(user) -> bool:
    """Writes to an open-read model: the login's own superuser role (never act-as)."""
    return own_role(user) == 'superuser'


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
        s = (Setting.objects.filter(purpose='wc:model', parent_model=key)
             .only('config').first())
        _cache[key] = resolve_roles((s.config or {}).get('access') or {}) if s else {}
    return _cache[key]


def block_for(actor, name: str) -> Optional[dict]:
    """The access block for this actor's role on this model, or None (no access)."""
    from apps.core.services.door import as_actor
    role = as_actor(actor).role
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

#: Documents a portal customer may raise for themselves, and the fields they may fill.
#: Not every portal role: 'rep' carries a broader grant of its own, and vendor and
#: manufacturer do not raise customer orders.
PORTAL_ORDER_ROLES = ('customer', 'buyer')
PORTAL_ORDER_MODELS = frozenset({'order', 'quote'})
#: 'notes' and 'comments' were in the tuple this replaced. Neither belongs: notes is not
#: a field of any model (Bill, 2026-09-20: "There should be no notes field or object.
#: Only comments"), and comments is a parent path whose leaves are comments.general.*,
#: which a positive list may not name.
PORTAL_ORDER_FIELDS = ('attention', 'dt_needed', 'ship_via', 'purpose',
                       'lines.item.item_id', 'lines.quantity.active')


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
    roles = {'superuser': full, 'admin': dict(full), 'agent': agent}
    if key in PORTAL_ORDER_MODELS:
        # What a portal customer may put on their own order. This lived as a tuple in
        # apps/transactions/views/wcapi.py, which meant the one place that says what a
        # role may write did not say it (Bill, 2026-09-20: the list is an enumeration in
        # a Setting record). Everything else on the document is set by the server.
        # Not '@all': that expands to every leaf including the opaque (untyped) ones,
        # which never go outside the company — validate_access refuses it, so a new
        # install would not seed. A portal role starts able to see exactly what it may
        # fill; anything more is an admin's deliberate grant.
        portal_fields = [p for p in PORTAL_ORDER_FIELDS if p in leaves]
        portal = {'view': list(portal_fields), 'edit': list(portal_fields),
                  'scope': {'customer_id__in': '$user.org_ids.customer'},
                  'create': True, 'delete': False}
        for role in PORTAL_ORDER_ROLES:
            roles[role] = dict(portal)
    return {'sets': {'all': leaves}, 'roles': roles}


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
