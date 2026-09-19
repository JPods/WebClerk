"""
Field Projection Service — positive lists of leaves.

- filter_data_by_fields(): view projection — only named leaves leave the server
- validate_edit_fields(): edit check — every changed leaf must be named

A list is a set of leaf paths (apps/core/services/field_leaves). There is no
wildcard and no parent path: naming "totals" grants nothing; "totals.total"
grants that value. An element of a list of objects shares the list's path
(lines.quantity.ordered is that value on every line). A leaf whose value is a
list of plain values or an outside payload is passed whole.

Rules live in each model's wc:model Setting (apps/core/services/access.py).
"""
from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Iterable, Optional

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

from apps.core.services.role_filter import get_allowed_fields


# =============================================================================
# Paths
# =============================================================================

def is_field_allowed(field_path: str, allowed_fields: Iterable[str]) -> bool:
    """True only when field_path is itself a named leaf."""
    return field_path in set(allowed_fields or ())


def _reachable(path: str, allowed: set) -> bool:
    """True when path is a named leaf or lies on the way to one."""
    if path in allowed:
        return True
    prefix = path + '.'
    return any(a.startswith(prefix) for a in allowed)


def _leaf_paths(value, prefix: str) -> set:
    """Every leaf path a value occupies under prefix."""
    if isinstance(value, dict):
        if not value:
            return {prefix} if prefix else set()
        out = set()
        for k, v in value.items():
            out |= _leaf_paths(v, f'{prefix}.{k}' if prefix else k)
        return out
    if isinstance(value, list) and value and all(isinstance(v, dict) for v in value):
        out = set()
        for v in value:
            out |= _leaf_paths(v, prefix)
        return out
    return {prefix}


# =============================================================================
# View projection
# =============================================================================

def _project(value, prefix: str, allowed: set):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            path = f'{prefix}.{k}' if prefix else k
            if path in allowed:
                out[k] = copy.deepcopy(v)
            elif _reachable(path, allowed) and isinstance(v, (dict, list)):
                out[k] = _project(v, path, allowed)
        return out
    if isinstance(value, list):
        return [_project(v, prefix, allowed) for v in value if isinstance(v, dict)]
    return None


def filter_data_by_fields(data: dict, allowed_fields: Iterable[str], mode: str = "view") -> dict:
    """Keep only the named leaves of a record. Nothing named → nothing returned."""
    if not data or not allowed_fields:
        return {}
    return _project(data, '', set(allowed_fields))


def filter_response_data(user: AbstractUser, model_name: str, data: dict) -> dict:
    """Project a record to what this user's role may see."""
    from apps.core.services import access
    if access.is_open_read(model_name):
        return data if access.user_role(user) else {}
    return filter_data_by_fields(data, get_allowed_fields(user, model_name, mode="view"))


def filter_lines_data(lines: list, allowed_line_fields: Iterable[str]) -> list:
    """Project line records to the named leaves."""
    allowed = set(allowed_line_fields or ())
    return [_project(line, '', allowed) for line in (lines or []) if isinstance(line, dict)]


def filter_setting_layout(user, setting_data: dict) -> dict:
    """Drop layout columns for fields this user's role may not see.

    Applies to wc:model / wc:workbench_fields Settings describing parent_model.
    A role that may see nothing on the model gets no columns.
    """
    if setting_data.get('purpose', '') not in ('wc:model', 'wc:workbench_fields'):
        return setting_data
    target_model = setting_data.get('parent_model', '')
    config = setting_data.get('config')
    if not target_model or not isinstance(config, dict) or not isinstance(config.get('layout'), dict):
        return setting_data

    allowed = set(get_allowed_fields(user, target_model, mode="view"))

    def column_allowed(col) -> bool:
        field = col if isinstance(col, str) else (col.get('field', '') if isinstance(col, dict) else '')
        return bool(field) and _reachable(field, allowed)

    def filter_tree(node):
        if isinstance(node, list):
            return [item for item in node
                    if not isinstance(item, (str, dict)) or
                    (isinstance(item, dict) and 'field' not in item) or column_allowed(item)]
        if isinstance(node, dict):
            return {k: ([c for c in v if column_allowed(c)] if k == 'columns' and isinstance(v, list)
                        else filter_tree(v))
                    for k, v in node.items()}
        return node

    result = dict(setting_data)
    result['config'] = dict(config)
    result['config']['layout'] = filter_tree(config['layout'])
    return result


# =============================================================================
# Edit validation
# =============================================================================

def get_modified_fields(original: dict, modified: dict) -> set:
    """Leaf paths whose value differs between original and modified."""
    changes: set = set()
    _compare(original or {}, modified or {}, '', changes)
    return changes


def _compare(orig, mod, prefix: str, changes: set) -> None:
    if orig == mod:
        return
    if isinstance(orig, dict) and isinstance(mod, dict):
        for key in set(orig) | set(mod):
            _compare(orig.get(key), mod.get(key), f'{prefix}.{key}' if prefix else key, changes)
        return
    # A replaced value: every leaf it had or now has has changed.
    before = _leaf_paths(orig, prefix) if orig not in (None, {}, []) else set()
    after = _leaf_paths(mod, prefix) if mod not in (None, {}, []) else set()
    changes |= (before | after) or {prefix}


def validate_edit_fields(original: Optional[dict], modified: dict,
                         allowed_fields: Iterable[str]) -> tuple[bool, list]:
    """(ok, disallowed leaf paths). Every changed leaf must be named in allowed_fields."""
    allowed = set(allowed_fields or ())
    changed = _leaf_paths(modified or {}, '') if original is None else get_modified_fields(original, modified)
    disallowed = sorted(p for p in changed if p not in allowed)
    return not disallowed, disallowed


def validate_user_edit(user: AbstractUser, model_name: str,
                       original: Optional[dict], modified: dict) -> tuple[bool, list]:
    """Validate an edit against the user's role edit list."""
    from apps.core.services import access
    if access.is_open_read(model_name):
        return (True, []) if access.open_read_can_write(user) else (False, [f'{model_name}: superuser only'])
    return validate_edit_fields(original, modified, get_allowed_fields(user, model_name, mode="edit"))
