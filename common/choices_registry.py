from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from functools import lru_cache
from importlib import import_module
from typing import Any, Dict, Iterable, List

from django.apps import apps

_CHOICES_ATTR = "DEFAULT_SELECT_LISTS"
_LAST_ERRORS: List[Dict[str, str]] = []


@lru_cache(maxsize=1)
def collect_default_select_lists() -> Dict[str, Dict[str, Dict[str, tuple]]]:
    """Return a deepcopy of DEFAULT_SELECT_LISTS for all apps exposing a choices module."""
    registry: Dict[str, Dict[str, Dict[str, tuple]]] = {}
    errors: List[Dict[str, str]] = []
    for app_config in apps.get_app_configs():
        module_name = f"{app_config.name}.choices"
        try:
            module = import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name == module_name:
                continue
            errors.append({"module": module_name, "error": str(exc)})
            continue
        except Exception as exc:
            errors.append({"module": module_name, "error": str(exc)})
            continue

        default_lists = getattr(module, _CHOICES_ATTR, None)
        if not default_lists:
            continue
        try:
            registry[app_config.label] = deepcopy(default_lists)
        except Exception as exc:
            errors.append({"module": module_name, "error": str(exc)})
            continue

    global _LAST_ERRORS
    _LAST_ERRORS = errors
    return registry


def build_choices_payload(app_labels: Iterable[str] | None = None) -> Dict[str, Dict[str, Dict[str, list[Dict[str, Any]]]]]:
    """Materialize a JSON-serializable payload of all DEFAULT_SELECT_LISTS."""
    raw = collect_default_select_lists()
    if app_labels is not None:
        selected_labels = set(app_labels)
        filtered = {label: raw[label] for label in raw.keys() & selected_labels}
    else:
        filtered = raw

    payload: Dict[str, Dict[str, Dict[str, list[Dict[str, Any]]]]] = {}
    for app_label, models in filtered.items():
        model_payload: Dict[str, Dict[str, list[Dict[str, Any]]]] = {}
        for model_name, fields in models.items():
            field_payload: Dict[str, list[Dict[str, Any]]] = {}
            for field_name, choices in fields.items():
                field_payload[field_name] = _normalize_choices(choices)
            model_payload[model_name] = field_payload
        if model_payload:
            payload[app_label] = model_payload
    return payload


def _normalize_choices(raw_choices: Any) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    if raw_choices is None:
        return normalized

    try:
        iterator = iter(raw_choices)
    except TypeError:
        return normalized

    for entry in iterator:
        if isinstance(entry, Mapping):
            value = entry.get("value")
            label = entry.get("label", value)
            if value is None and label is None:
                continue
        elif isinstance(entry, Sequence) and not isinstance(entry, (str, bytes, bytearray)):
            if len(entry) >= 2:
                value, label = entry[0], entry[1]
            elif len(entry) == 1:
                value = label = entry[0]
            else:
                continue
        else:
            value = label = entry

        normalized.append({"value": value, "label": label})

    return normalized


def get_registry_errors() -> List[Dict[str, str]]:
    return list(_LAST_ERRORS)
