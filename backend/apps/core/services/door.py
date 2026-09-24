"""What every door shares: who is asking, how it refuses, and what it resolves.

Bill, 2026-09-22: *"Having every save, get, delete flow through their own individual
channel creates a maintainable system. There are few places to audit."*

One channel per verb — ``save.py``, ``delete.py`` — and these are the pieces all of them
hold in common, defined once so the three cannot drift apart.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, cast

from django.db import models

from apps.core.constants.model_registry import (get_model, normalize_table_key,
                                                to_model_name)

console_logger = logging.getLogger('console')


# ── what the caller is ────────────────────────────────────────────────

#: Every kind an actor may be. Anything else is a construction error, not a quietly
#: guarded or quietly privileged actor (Axiom 6).
KINDS = ('user', 'staff', 'public', 'system', 'sync')
#: The kinds that skip the guards written for callers. Named, so the default is guarded:
#: a kind added later is checked until someone decides otherwise. Only our own code —
#: commands and tasks — is privileged; a sync bundle is guarded by its Connection's role
#: (Bill, 2026-09-23).
PRIVILEGED_KINDS = ('system',)


@dataclass
class Actor:
    """Who is asking, and in what capacity — the one principal every door and every
    access check takes.

    ``kind`` decides policy, not the door: a ``system`` actor is still audited, still
    validated, still versioned — it is simply permitted more. "No backdoor" and "a
    command may write what a user may not" are only compatible if the second is written
    down rather than assumed from an absence.

    user    a signed-in person (Contact login) at the API or the admin
    staff   a person at the Django admin — guarded exactly like user
    public  an anonymous visitor: no login, the public role only
    sync    another system over a Connection — the Connection's role and scope
    system  our own commands and tasks — the only privileged kind
    """
    user: Any = None
    kind: str = 'user'
    source: str = 'wcapi'       # wcapi | admin | command | task | sync
    connection: Any = None
    acting_as: Optional[str] = None   # an agent's validated X-WC-Act-As role, this call only

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f'unknown actor kind {self.kind!r}; one of {KINDS}')
        if self.kind in ('user', 'staff') and self.user is None:
            raise ValueError(f'a {self.kind} actor is a signed-in person; use Actor.anonymous() '
                             'for a visitor or Actor.system() for our own code')
        if self.kind in ('public', 'system', 'sync') and self.user is not None:
            raise ValueError(f'a {self.kind} actor carries no user')
        if self.kind == 'sync' and self.connection is None:
            raise ValueError('a sync actor needs the Connection it arrived on')
        if self.acting_as and self.kind != 'user':
            raise ValueError('only a signed-in agent may act as another role')

    @property
    def is_guarded(self) -> bool:
        """Every guard written for callers applies: create/edit/delete rights, edit
        filters, the staff-only models, the write policy, the contact account guard."""
        return self.kind not in PRIVILEGED_KINDS

    # ── constructors ──
    @classmethod
    def from_request(cls, request, source: str = 'wcapi') -> 'Actor':
        from apps.core.services.access import ACT_AS_REQUEST_ATTR
        # A read made by a service (services/get.py) carries its actor with it.
        carried = getattr(request, 'wc_actor', None)
        if carried is not None:
            return carried
        user = getattr(request, 'user', None)
        if user is None or not getattr(user, 'is_authenticated', False):
            return cls.anonymous(source)
        django_request = getattr(request, '_request', request)
        return cls(user=user, kind='user', source=source,
                   acting_as=getattr(django_request, ACT_AS_REQUEST_ATTR, None))

    @classmethod
    def anonymous(cls, source: str = 'wcapi') -> 'Actor':
        return cls(kind='public', source=source)

    @classmethod
    def system(cls, source: str = 'command') -> 'Actor':
        return cls(kind='system', source=source)

    @classmethod
    def for_connection(cls, connection, source: str = 'sync') -> 'Actor':
        """The Connection comes from the authenticated credential, never from a payload."""
        return cls(kind='sync', source=source, connection=connection)

    # ── what the access checks read ──
    @property
    def user_id(self):
        """The login behind this actor; None for sync, public and system — a sync write
        must never be linked to whichever contact shares a connection's id."""
        return getattr(self.user, 'id', None) if self.kind in ('user', 'staff') else None

    @property
    def role(self) -> Optional[str]:
        """The role the three gates read. None = no role: sees and writes nothing."""
        from apps.core.services import access
        if self.kind in ('user', 'staff'):
            return self.acting_as or access.own_role(self.user)
        if self.kind == 'sync':
            return access.connection_role(self.connection)
        return None

    def context(self) -> Dict[str, Any]:
        """The ids a role's scope resolves against ($user.org_ids.customer, …)."""
        from apps.core.services import role_filter
        if self.kind in ('user', 'staff'):
            context = role_filter.build_user_context(self.user)
            context["roles"] = [self.role] if self.role else []
            return context
        if self.kind == 'sync':
            return role_filter.build_connection_context(self.connection, self.role)
        return role_filter.empty_context()

    @property
    def price_level(self) -> str:
        from apps.core.services import role_filter
        return role_filter.user_price_level(self.user) if self.user_id else ''

    @property
    def may_write_open_read(self) -> bool:
        """Writes to an open-read model (Settings): a login's own superuser role, never an
        act-as and never a Connection."""
        from apps.core.services import access
        return (self.kind in ('user', 'staff') and not self.acting_as
                and access.open_read_can_write(self.user))

    def describe(self) -> str:
        """For log lines and history: the institution behind a sync write is traceable."""
        if self.kind == 'sync':
            return f"sync connection #{getattr(self.connection, 'pk', '?')}"
        return f"{self.kind} actor" + (f" #{self.user_id}" if self.user_id else '')


def as_actor(actor) -> 'Actor':
    """Access checks take an Actor. A bare user is a caller not yet converted: fail
    loudly rather than guess what kind of principal it is."""
    if not isinstance(actor, Actor):
        raise TypeError(f'access checks take an Actor, not {type(actor).__name__}')
    return actor


# ── what the door refuses with ────────────────────────────────────────

class Refused(Exception):
    """A save the door will not make, with the answer the caller should be given.

    One exception, carrying the status and code the response needs, because the codes are
    the contract: tests and the front end both read ``error.code``.
    """

    def __init__(self, status: int, code: str, message: str, details: Any = None,
                 extra: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details if details is not None else message
        self.extra = extra or {}

    def as_error(self) -> Dict[str, Any]:
        return {'code': self.code, 'details': self.details, **self.extra}


@dataclass
class SaveResult:
    """What the door did, in the shape the response is built from."""
    obj: Any
    obj_id: Optional[int]
    model_key: str
    created: bool
    record: Dict[str, Any] = field(default_factory=dict)
    version: Optional[int] = None
    linked: bool = False
    messages: List[str] = field(default_factory=list)
    warning: Optional[str] = None
    sync: Optional[Dict[str, Any]] = None

    def payload(self) -> Dict[str, Any]:
        data = {
            'id': self.obj_id,
            'record': self.record,
            'model_name': self.model_key,
            'version': self.version,
            'linked': self.linked,
        }
        if self.messages:
            data['messages'] = list(self.messages)
        if self.sync:
            data.update(self.sync)
        return data


# ── phase 1: resolve ──────────────────────────────────────────────────

def resolve_model(raw_model_name: str):
    """(model_cls, model_key, norm_key) for a payload's model_name."""
    if not raw_model_name:
        raise Refused(400, 'missing_model_name', 'Missing required field: model_name',
                      'Provide model_name (singular)')
    norm_key = normalize_table_key(raw_model_name)
    model = get_model(norm_key) if norm_key else None
    if not model:
        raise Refused(400, 'unknown_model', f'Unknown model: {raw_model_name}',
                      f'Unknown model: {raw_model_name}')
    model_cls = cast(Type[models.Model], model)
    return model_cls, (to_model_name(model_cls) or raw_model_name), norm_key


