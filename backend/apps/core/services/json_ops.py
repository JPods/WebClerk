"""
JSON Field Operations — surgical updates to nested JSON fields.

One function: apply_json_op(). Walks a dot-path into any JSON structure,
handles both dicts and arrays, and only touches the leaf. Everything
else stays untouched.

Operations:
  update  — set the value at path (creates intermediate dicts/arrays)
  merge   — deep-merge a dict into the dict at path (dicts only)
  upsert  — find-or-append in an array by key field, replace the match
  append  — append value to array at path
  remove  — remove from array by key match, or delete dict key
  delete  — alias for remove

Path syntax:
  "config.views"           — nested dict keys
  "config.views[name=Bill]" — array element where name="Bill"
  "refs.keywords"        — any JSON field, any depth

Examples:
  # Set a nested value — only touches the leaf
  apply_json_op(obj, "metadata.flags.reviewed", "update", True)

  # Upsert a view into data.views by name
  apply_json_op(obj, "config.views", "upsert", {"name": "Bill", "list": [...]}, key="name")

  # Append a keyword without replacing the array
  apply_json_op(obj, "refs.keywords", "append", "urgent")

  # Remove a view by name
  apply_json_op(obj, "config.views", "remove", "Bill", key="name")

  # Deep-merge into metadata without touching other keys
  apply_json_op(obj, "metadata.flags", "merge", {"reviewed": True, "priority": 1})

  # Set a value inside an array element
  apply_json_op(obj, "data.views[name=Bill].list", "update", [{"field": "ida"}, {"field": "email"}])
"""
import copy
import json
import logging
import re

logger = logging.getLogger('console')

MAX_PATH_DEPTH = 8                # max dot-path segments allowed
MAX_MERGE_DEPTH = 8               # max recursion depth for _deep_merge


def apply_json_op(target, path: str, mode: str, value=None, key: str = None) -> bool:
    """Apply a surgical operation to a nested JSON field.

    Args:
        target: Django model instance or dict. If model, reads/writes via getattr/setattr.
        path: Dot-path to the field. Array selectors: "views[name=Bill]".
        mode: "update", "merge", "upsert", "append", "remove", "delete".
        value: The value to set/merge/append/upsert.
        key: For upsert/remove on arrays — the field name to match by.

    Returns:
        True if the operation changed something, False otherwise.
    """
    if not path:
        return False

    parts = _parse_path(path)
    if not parts:
        return False

    if len(parts) > MAX_PATH_DEPTH:
        logger.warning(
            "[JSON_OPS] Path depth %d exceeds max %d: %s",
            len(parts), MAX_PATH_DEPTH, path[:80],
        )
        return False

    # Split into root field (on the model) and remaining path (inside the JSON)
    root_field = parts[0]['key']
    json_path = parts[1:]

    # Get the root JSON value
    if isinstance(target, dict):
        root_val = target.get(root_field)
    elif hasattr(target, root_field):
        root_val = getattr(target, root_field)
    else:
        return False

    # Ensure root is a mutable copy (Django JSONField returns a new dict each time,
    # but we need to set it back after modification)
    if root_val is None:
        root_val = {} if json_path else None
    elif isinstance(root_val, (dict, list)):
        root_val = copy.deepcopy(root_val)

    if not json_path:
        # Operating on the root field itself
        new_val = _apply_at_node(root_val, mode, value, key)
        if isinstance(target, dict):
            target[root_field] = new_val
        else:
            setattr(target, root_field, new_val)
        return True

    # Walk the path to the parent of the leaf
    node = root_val
    for i, part in enumerate(json_path[:-1]):
        node = _descend(node, part)
        if node is None:
            # Path doesn't exist — create intermediate structure
            node = _create_intermediate(root_val, json_path[:i + 1])
            if node is None:
                return False

    # Apply the operation at the leaf
    leaf_part = json_path[-1]

    if leaf_part.get('selector'):
        # Path ends with array selector: e.g., "views[name=Bill]"
        arr = _get_child(node, leaf_part['key'])
        if not isinstance(arr, list):
            return False
        sel_key, sel_val = leaf_part['selector']
        idx = next((i for i, el in enumerate(arr) if isinstance(el, dict) and str(el.get(sel_key)) == sel_val), None)
        if mode in ('update', 'merge') and idx is not None:
            if mode == 'merge' and isinstance(arr[idx], dict) and isinstance(value, dict):
                _deep_merge(arr[idx], value)
            else:
                arr[idx] = value
        elif mode in ('remove', 'delete') and idx is not None:
            arr.pop(idx)
        elif mode == 'upsert':
            if idx is not None:
                arr[idx] = value
            else:
                arr.append(value)
        else:
            return False
    else:
        # Regular key
        child_key = leaf_part['key']
        if isinstance(node, dict):
            node[child_key] = _apply_at_node(node.get(child_key), mode, value, key)
        elif isinstance(node, list) and child_key.isdigit():
            idx = int(child_key)
            if 0 <= idx < len(node):
                node[idx] = _apply_at_node(node[idx], mode, value, key)
            else:
                return False
        else:
            return False

    # Write back the root value
    if isinstance(target, dict):
        target[root_field] = root_val
    else:
        setattr(target, root_field, root_val)
    return True


def _apply_at_node(current, mode, value, key):
    """Apply an operation at a single node."""
    if mode == 'update':
        return value

    elif mode == 'merge':
        if isinstance(current, dict) and isinstance(value, dict):
            _deep_merge(current, value)
            return current
        return value  # fallback to replace

    elif mode == 'upsert':
        if not isinstance(current, list):
            current = []
        if key and isinstance(value, dict):
            match_val = value.get(key)
            idx = next((i for i, el in enumerate(current)
                       if isinstance(el, dict) and el.get(key) == match_val), None)
            if idx is not None:
                current[idx] = value
            else:
                current.append(value)
        else:
            current.append(value)
        return current

    elif mode == 'append':
        if not isinstance(current, list):
            current = []
        if isinstance(value, list):
            current.extend(value)
        else:
            current.append(value)
        return current

    elif mode in ('remove', 'delete'):
        if isinstance(current, list) and key:
            return [el for el in current
                    if not (isinstance(el, dict) and el.get(key) == value)]
        elif isinstance(current, dict) and isinstance(value, str):
            current.pop(value, None)
            return current
        return current

    return current


def _parse_path(path: str) -> list:
    """Parse a dot-path with optional array selectors.

    "data.views[name=Bill].list" ->
    [
        {"key": "data"},
        {"key": "views", "selector": ("name", "Bill")},
        {"key": "list"},
    ]
    """
    parts = []
    for segment in path.split('.'):
        m = re.match(r'^(\w+)\[(\w+)=(.+)\]$', segment)
        if m:
            parts.append({'key': m.group(1), 'selector': (m.group(2), m.group(3))})
        else:
            parts.append({'key': segment})
    return parts


def _get_child(node, key):
    """Get a child value from dict or list."""
    if isinstance(node, dict):
        return node.get(key)
    elif isinstance(node, list) and key.isdigit():
        idx = int(key)
        return node[idx] if 0 <= idx < len(node) else None
    return None


def _descend(node, part):
    """Walk one step into the structure."""
    key = part['key']
    child = _get_child(node, key)
    if part.get('selector') and isinstance(child, list):
        sel_key, sel_val = part['selector']
        match = next((el for el in child
                      if isinstance(el, dict) and str(el.get(sel_key)) == sel_val), None)
        return match
    return child


def _create_intermediate(root, parts):
    """Create intermediate dicts/lists along the path."""
    node = root
    for part in parts:
        key = part['key']
        if isinstance(node, dict):
            if key not in node:
                node[key] = [] if part.get('selector') else {}
            node = node[key]
            if part.get('selector') and isinstance(node, list):
                sel_key, sel_val = part['selector']
                match = next((el for el in node
                             if isinstance(el, dict) and str(el.get(sel_key)) == sel_val), None)
                if match is None:
                    new_el = {sel_key: sel_val}
                    node.append(new_el)
                    node = new_el
                else:
                    node = match
    return node


def _check_json_depth(obj, depth: int = 0) -> int:
    """Return max nesting depth of a dict/list structure."""
    if depth >= MAX_MERGE_DEPTH:
        return depth
    if isinstance(obj, dict):
        if not obj:
            return depth
        return max(_check_json_depth(v, depth + 1) for v in obj.values())
    if isinstance(obj, list):
        if not obj:
            return depth
        return max(_check_json_depth(v, depth + 1) for v in obj)
    return depth


def _deep_merge(a: dict, b: dict, _depth: int = 0) -> dict:
    """Recursively merge dict b into dict a. Only replaces leaf values.

    Raises ValueError if merge depth exceeds MAX_MERGE_DEPTH.
    """
    if _depth >= MAX_MERGE_DEPTH:
        raise ValueError(
            f"JSON merge depth exceeds {MAX_MERGE_DEPTH} levels"
        )
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            _deep_merge(a[k], v, _depth + 1)
        else:
            if isinstance(v, (dict, list)):
                incoming = _check_json_depth(v)
                if _depth + incoming >= MAX_MERGE_DEPTH:
                    raise ValueError(
                        f"JSON nesting depth exceeds {MAX_MERGE_DEPTH} levels"
                    )
            a[k] = v
    return a
