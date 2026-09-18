from __future__ import annotations

import json
from importlib import import_module
from pathlib import Path
from functools import cached_property
from typing import Any, Dict, List, Optional, Sequence, Tuple, Type, Protocol, cast

from django.conf import settings
from django.db.models import Q, QuerySet, Model
from rest_framework.request import Request

from .registry import get as get_cfg


class _HasRegistryConfig(Protocol):
    def get_registry_config(self) -> Any: ...


class RegistryQuerysetMixin:
    model_key: str

    def get_registry_config(self):
        cfg = get_cfg(self.model_key)
        if not cfg:
            raise RuntimeError(f"wcapi registry missing config for '{self.model_key}'")
        return cfg

    def get_queryset(self) -> QuerySet:
        cfg = self.get_registry_config()
        if cfg.queryset is not None:
            return cfg.queryset.all()
        return cfg.model._default_manager.all()  # type: ignore[attr-defined]


class QSearchMixin:
    def apply_q_search(self, qs: QuerySet, request: Request, extra_fields: Optional[Sequence[str]] = None) -> QuerySet:
        raw_q = (request.GET.get("q") or "").strip()
        if not raw_q:
            return qs
        cfg = cast(_HasRegistryConfig, self).get_registry_config()
        fields = list(cfg.search_fields or [])
        if extra_fields:
            fields.extend(extra_fields)
        if not fields:
            return qs
        terms = [t for t in raw_q.split() if t]
        for term in terms:
            or_q = Q()
            for f in fields:
                or_q |= Q(**{f"{f}__icontains": term})
            qs = qs.filter(or_q)
        return qs


class DevFallbackMetaMixin:
    def add_dev_fallback_meta(self, meta: dict) -> dict:
        cfg = cast(_HasRegistryConfig, self).get_registry_config()
        if cfg.dev_fallback:
            meta.setdefault("policy_missing", True)
            meta.setdefault("policy_source", "dev_fallback")
        return meta