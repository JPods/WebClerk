"""
Field Projection Service.

Filters record data based on role field permissions.
- filter_data_by_fields(): View projection - remove disallowed fields from response
- validate_edit_fields(): Edit validation - ensure only allowed fields are being modified

See readmes/topics/architecture/role-based-access-plan.md for full documentation.
"""
from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

from apps.core.services.role_filter import get_allowed_fields
from common.json_path import get_nested_value, set_nested_value


# =============================================================================
# Field Path Utilities
# =============================================================================

def is_field_allowed(field_path: str, allowed_fields: list) -> bool:
    """
    Check if a field path is allowed by the allowed_fields list.
    
    Args:
        field_path: Dotted path like "totals.total" or "refs.links.customer"
        allowed_fields: List of allowed paths, or ["*"] for all
    
    Returns:
        True if field is allowed
    
    Rules:
    - "*" allows all fields
    - Exact match allows field
    - Parent path allows children (e.g., "totals" allows "totals.total")
    """
    if not allowed_fields:
        return False
    
    if "*" in allowed_fields:
        return True
    
    # Exact match
    if field_path in allowed_fields:
        return True
    
    # Parent path allows children
    parts = field_path.split(".")
    for i in range(len(parts)):
        parent = ".".join(parts[:i + 1])
        if parent in allowed_fields:
            return True
    
    return False


# =============================================================================
# View Field Projection
# =============================================================================

def filter_data_by_fields(
    data: dict,
    allowed_fields: list,
    mode: str = "view"
) -> dict:
    """
    Filter record data to only allowed fields.
    
    Args:
        data: Record data dictionary
        allowed_fields: List of allowed field paths, or ["*"] for all
        mode: "view" or "edit" (affects logging)
    
    Returns:
        New dict with only allowed fields
    
    Examples:
        allowed = ["id", "ida", "totals.total", "refs.tags"]
        filter_data_by_fields(data, allowed)
        → {"id": 1, "ida": "ORD-001", "totals": {"total": 100.0}, "refs": {"tags": [...]}}
    """
    if not data:
        return {}
    
    if not allowed_fields:
        return {}
    
    # "*" means all fields allowed
    if "*" in allowed_fields:
        return copy.deepcopy(data)
    
    result = {}
    
    # Build allowed top-level fields and their subpath allowances
    top_level_allowed = set()
    nested_allowed = {}  # field -> list of subpaths
    
    for field in allowed_fields:
        parts = field.split(".")
        top = parts[0]
        top_level_allowed.add(top)
        
        if len(parts) > 1:
            subpath = ".".join(parts[1:])
            if top not in nested_allowed:
                nested_allowed[top] = []
            nested_allowed[top].append(subpath)
    
    # Process each allowed top-level field
    for top in top_level_allowed:
        if top not in data:
            continue
        
        value = data[top]
        
        # If entire field is allowed (no subpath restrictions), copy it fully
        if top in allowed_fields:
            result[top] = copy.deepcopy(value)
        elif top in nested_allowed:
            # Only specific subpaths allowed
            if isinstance(value, dict):
                result[top] = _filter_nested(value, nested_allowed[top])
            elif isinstance(value, list):
                # For lists (like lines), filter each item
                result[top] = [
                    _filter_nested(item, nested_allowed[top])
                    if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                # Primitive with subpath spec - just include it
                result[top] = copy.deepcopy(value)
    
    return result


def _filter_nested(data: dict, allowed_subpaths: list) -> dict:
    """
    Filter nested dict to only allowed subpaths.
    
    Args:
        data: Nested dictionary
        allowed_subpaths: List of allowed paths within this dict
    
    Returns:
        Filtered dict
    """
    if not isinstance(data, dict):
        return data
    
    result = {}
    
    # Group by first component
    top_allowed = set()
    deeper = {}
    
    for subpath in allowed_subpaths:
        parts = subpath.split(".")
        top = parts[0]
        top_allowed.add(top)
        
        if len(parts) > 1:
            rest = ".".join(parts[1:])
            if top not in deeper:
                deeper[top] = []
            deeper[top].append(rest)
    
    for key in top_allowed:
        if key not in data:
            continue
        
        value = data[key]
        
        if key in [sp for sp in allowed_subpaths if "." not in sp]:
            # Entire key allowed
            result[key] = copy.deepcopy(value)
        elif key in deeper:
            # Recurse
            if isinstance(value, dict):
                result[key] = _filter_nested(value, deeper[key])
            else:
                result[key] = copy.deepcopy(value)
    
    return result


def filter_response_data(
    user: AbstractUser,
    model_name: str,
    data: dict
) -> dict:
    """
    Filter response data based on user's view permissions.
    
    High-level API for use in views/serializers.
    
    Args:
        user: Django User instance
        model_name: Model name for permission lookup
        data: Record data to filter
    
    Returns:
        Filtered data based on user's view_fields
    """
    allowed = get_allowed_fields(user, model_name, mode="view")
    return filter_data_by_fields(data, allowed, mode="view")


# =============================================================================
# Edit Field Validation
# =============================================================================

def get_modified_fields(original: dict, modified: dict) -> set:
    """
    Get set of field paths that differ between original and modified.
    
    Args:
        original: Original record data
        modified: Modified record data
    
    Returns:
        Set of dotted paths that were changed
    """
    changes = set()
    _compare_dicts(original or {}, modified or {}, "", changes)
    return changes


def _compare_dicts(
    orig: dict,
    mod: dict,
    prefix: str,
    changes: set
) -> None:
    """Recursively compare dicts and collect changed paths."""
    all_keys = set(orig.keys()) | set(mod.keys())
    
    for key in all_keys:
        path = f"{prefix}.{key}" if prefix else key
        
        orig_val = orig.get(key)
        mod_val = mod.get(key)
        
        if orig_val == mod_val:
            continue
        
        # Different - record the path
        if isinstance(orig_val, dict) and isinstance(mod_val, dict):
            # Recurse for nested dicts
            _compare_dicts(orig_val, mod_val, path, changes)
        else:
            changes.add(path)


def validate_edit_fields(
    original: Optional[dict],
    modified: dict,
    allowed_fields: list
) -> tuple[bool, list]:
    """
    Validate that only allowed fields are being modified.
    
    Args:
        original: Original record data (None for new records)
        modified: Modified/new record data
        allowed_fields: List of allowed edit paths, or ["*"] for all
    
    Returns:
        Tuple of (is_valid, list of disallowed fields)
    
    Example:
        allowed = ["status", "notes", "refs.tags"]
        validate_edit_fields(orig, mod, allowed)
        → (True, []) if only status/notes/refs.tags changed
        → (False, ["totals.total"]) if totals.total was modified
    """
    if "*" in allowed_fields:
        return True, []
    
    if not allowed_fields:
        # No fields allowed - any change is invalid
        if original is None:
            # New record - all fields in modified are changes
            return False, list(modified.keys())
        changes = get_modified_fields(original, modified)
        return len(changes) == 0, list(changes)
    
    # Get changed fields
    if original is None:
        # New record - all provided fields are "changes"
        changed = set(modified.keys())
    else:
        changed = get_modified_fields(original, modified)
    
    # Check each change against allowed
    disallowed = []
    for field_path in changed:
        if not is_field_allowed(field_path, allowed_fields):
            disallowed.append(field_path)
    
    return len(disallowed) == 0, disallowed


def validate_user_edit(
    user: AbstractUser,
    model_name: str,
    original: Optional[dict],
    modified: dict
) -> tuple[bool, list]:
    """
    Validate user's edit based on their role permissions.
    
    High-level API for use in save views.
    
    Args:
        user: Django User instance
        model_name: Model name for permission lookup
        original: Original record (None for creates)
        modified: Modified/new record data
    
    Returns:
        Tuple of (is_valid, list of disallowed fields)
    """
    allowed = get_allowed_fields(user, model_name, mode="edit")
    return validate_edit_fields(original, modified, allowed)


# =============================================================================
# Lines Field Filtering
# =============================================================================

def filter_lines_data(
    lines: list,
    allowed_line_fields: list
) -> list:
    """
    Filter line items to only allowed fields.
    
    Args:
        lines: List of line item dicts
        allowed_line_fields: Allowed fields for each line
    
    Returns:
        Filtered lines list
    """
    if not lines:
        return []
    
    if "*" in allowed_line_fields:
        return copy.deepcopy(lines)
    
    return [
        filter_data_by_fields(line, allowed_line_fields)
        for line in lines
        if isinstance(line, dict)
    ]
