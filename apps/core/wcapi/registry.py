from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Type

from django.db import models
from rest_framework.serializers import BaseSerializer

@dataclass
class ModelConfig:
    # URL prefix (can include slashes, e.g., "actions/std")
    key: str
    model: Type[models.Model]
    list_serializer: Optional[Type[BaseSerializer]] = None
    detail_serializer: Optional[Type[BaseSerializer]] = None
    queryset: Optional[models.QuerySet] = None
    search_fields: Sequence[str] = ()
    ordering: Sequence[str] = ("-id",)
    permission_classes: Sequence[Any] = ()
    pagination_class: Optional[Any] = None
    # Router basename (reverse names use this; must not contain '/')
    basename: Optional[str] = None
    # Dev-fallback policy flag (controls envelope shape for lists)
    dev_fallback: bool = False

_REGISTRY: Dict[str, ModelConfig] = {}

def register(cfg: ModelConfig) -> ModelConfig:
    _REGISTRY[cfg.key] = cfg
    return cfg

def get(key: str) -> Optional[ModelConfig]:
    return _REGISTRY.get(key)

def all_configs() -> List[ModelConfig]:
    return list(_REGISTRY.values())