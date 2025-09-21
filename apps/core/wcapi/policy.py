from __future__ import annotations
from typing import Iterable, Optional
from django.db.models import QuerySet, Model

def inject_constraints(qs: QuerySet, *, request, model_key: str) -> QuerySet:
    # TODO: enforce role/tenant/publish/reserved rules via Settings
    return qs

def field_allowlist(model: type[Model], *, request) -> Optional[Iterable[str]]:
    # Optional: restrict outbound fields by role/settings
    return None