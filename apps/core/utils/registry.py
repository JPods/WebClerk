from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Type

from django.db import models
from rest_framework.serializers import BaseSerializer
from django.apps import apps as django_apps

@dataclass
class ModelConfig:
    # URL prefix (can include slashes; e.g., "actions/std")
    key: str
    model: Type[models.Model]
    list_serializer: Optional[Type[BaseSerializer]] = None
    detail_serializer: Optional[Type[BaseSerializer]] = None
    queryset: Optional[models.QuerySet] = None
    search_fields: Sequence[str] = ()
    ordering: Sequence[str] = ("-id",)
    permission_classes: Sequence[Any] = ()
    pagination_class: Optional[Any] = None
    # Router basename for reverse() names. Must not contain '/'
    basename: Optional[str] = None
    # If True, middleware will set envelope.data to list for list endpoints
    dev_fallback: bool = False

_REGISTRY: Dict[str, ModelConfig] = {}

def register(cfg: ModelConfig) -> ModelConfig:
    _REGISTRY[cfg.key] = cfg
    return cfg

def get(key: str) -> Optional[ModelConfig]:
    return _REGISTRY.get(key)

def all_configs() -> List[ModelConfig]:
    return list(_REGISTRY.values())

def resolve(key: str):
    """
    Resolve a registry key or model path to a Django model class.
    Order:
      1) Registered key -> cfg.model
      2) app_label.ModelName or app_label.modelname
      3) Any installed model whose _meta.model_name == key
    """
    if not key:
        return None
    skey = str(key).strip().strip('/')

    # 1) registry
    cfg = get(skey)
    if cfg:
        return cfg.model

    # 2) dotted path
    if '.' in skey:
        app_label, _, model_part = skey.partition('.')
        try:
            cls = django_apps.get_model(app_label, model_part, require_ready=False)
            if cls:
                return cls
        except Exception:
            try:
                for m in django_apps.get_app_config(app_label).get_models():
                    if getattr(m._meta, 'model_name', '').lower() == model_part.lower():
                        return m
            except Exception:
                pass

    # 3) by model_name
    target = skey.lower()
    for m in django_apps.get_models():
        try:
            if getattr(m._meta, 'model_name', '').lower() == target:
                return m
        except Exception:
            continue
    return None


def refresh_from_settings():
    """
    Refresh the registry from Django settings.
    
    This method populates the registry with ModelConfig objects based on:
    - WCAPI_BLESSED_MODELS: maps model keys to Django model paths
    - WCAPI_MODEL_POLICIES: per-model field access policies
    - WCAPI_WHITELIST_APPS: whitelist of apps for WCAPI access
    
    The registry will be cleared and repopulated with fresh configurations.
    """
    from django.conf import settings
    
    # Clear existing registry
    _REGISTRY.clear()
    
    # Get blessed models from settings
    blessed_models = getattr(settings, 'WCAPI_BLESSED_MODELS', {})
    model_policies = getattr(settings, 'WCAPI_MODEL_POLICIES', {})
    whitelist_apps = getattr(settings, 'WCAPI_WHITELIST_APPS', None)
    
    # Process each blessed model
    for key, model_path in blessed_models.items():
        try:
            # Parse model path (e.g., "core.Contact" -> app_label="core", model_name="Contact")
            if '.' not in model_path:
                continue
                
            app_label, model_name = model_path.rsplit('.', 1)
            
            # Check whitelist if configured
            if whitelist_apps and app_label not in whitelist_apps:
                continue
            
            # Get the actual model class
            try:
                model_class = django_apps.get_model(app_label, model_name, require_ready=False)
            except Exception:
                continue
            
            # Get policies for this model
            policies = model_policies.get(key, {})
            
            # Create ModelConfig with settings-based configuration
            cfg = ModelConfig(
                key=key,
                model=model_class,
                search_fields=policies.get('search_fields', []),
                permission_classes=policies.get('permission_classes', []),
            )
            
            # Register the configuration
            register(cfg)
            
        except Exception:
            # Continue processing other models if one fails
            continue