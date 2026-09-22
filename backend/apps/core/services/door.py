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

@dataclass
class Actor:
    """Who is writing, and in what capacity.

    ``kind`` decides policy, not the door: a ``system`` actor is still audited, still
    validated, still versioned — it is simply permitted more. "No backdoor" and "a
    command may write what a user may not" are only compatible if the second is written
    down rather than assumed from an absence.
    """
    user: Any = None
    kind: str = 'user'          # user | system | sync
    source: str = 'wcapi'       # wcapi | admin | command | task | sync

    @classmethod
    def from_request(cls, request, source: str = 'wcapi') -> 'Actor':
        return cls(user=getattr(request, 'user', None), kind='user', source=source)

    @classmethod
    def system(cls, source: str = 'command') -> 'Actor':
        return cls(user=None, kind='system', source=source)

    @property
    def user_id(self):
        return getattr(self.user, 'id', None)


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


