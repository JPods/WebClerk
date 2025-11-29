from django.utils import timezone

def append_contact_link(instance, user_id):
    """
    Append a contact link to the action's refs.contact_links list.

    Args:
        instance: The Action instance
        user_id: The ID of the current user
    """
    now_ms = int(timezone.now().timestamp() * 1000)
    contact_links = instance.refs.get('contact_links', [])
    contact_links.append({"id_contact": user_id, "dt": now_ms})
    instance.refs['contact_links'] = contact_links
from django.utils import timezone


def append_contact_link(instance, user_id):
    """
    Append a contact link to the action's refs.contact_links list.

    Args:
        instance: The Action instance
        user_id: The ID of the current user
    """
    now_ms = int(timezone.now().timestamp() * 1000)
    contact_links = instance.refs.get('contact_links', [])
    contact_links.append({"id_contact": user_id, "dt": now_ms})
    instance.refs['contact_links'] = contact_links


def add_child_dependency(action, child_id, sequence=1):
    """
    Add a child dependency to an action for Gantt chart relationships.

    Args:
        action: The Action instance (parent)
        child_id: The ID of the child action
        sequence: Order/priority of this dependency (default: 1)
    """
    links = action.refs.setdefault('links', {})
    children = links.setdefault('children', [])

    # Avoid duplicates
    for child in children:
        if child.get('id') == child_id:
            child['sequence'] = sequence  # Update sequence if already exists
            return

    children.append({'id': child_id, 'sequence': sequence})
    action.refs['links'] = links


def add_parent_dependency(action, parent_id, sequence=1):
    """
    Add a parent dependency to an action for Gantt chart relationships.

    Args:
        action: The Action instance (child)
        parent_id: The ID of the parent action
        sequence: Order/priority of this dependency (default: 1)
    """
    links = action.refs.setdefault('links', {})
    parents = links.setdefault('parents', [])

    # Avoid duplicates
    for parent in parents:
        if parent.get('id') == parent_id:
            parent['sequence'] = sequence  # Update sequence if already exists
            return

    parents.append({'id': parent_id, 'sequence': sequence})
    action.refs['links'] = links


def remove_child_dependency(action, child_id):
    """
    Remove a child dependency from an action.

    Args:
        action: The Action instance
        child_id: The ID of the child action to remove

    Returns:
        bool: True if dependency was removed, False if not found
    """
    links = action.refs.get('links', {})
    children = links.get('children', [])

    for i, child in enumerate(children):
        if child.get('id') == child_id:
            children.pop(i)
            action.refs['links'] = links
            return True

    return False


def remove_parent_dependency(action, parent_id):
    """
    Remove a parent dependency from an action.

    Args:
        action: The Action instance
        parent_id: The ID of the parent action to remove

    Returns:
        bool: True if dependency was removed, False if not found
    """
    links = action.refs.get('links', {})
    parents = links.get('parents', [])

    for i, parent in enumerate(parents):
        if parent.get('id') == parent_id:
            parents.pop(i)
            action.refs['links'] = links
            return True

    return False


def get_child_dependencies(action):
    """
    Get all child dependencies for an action.

    Args:
        action: The Action instance

    Returns:
        list: List of child dependency dicts [{'id': int, 'sequence': int}, ...]
    """
    links = action.refs.get('links', {})
    return links.get('children', [])


def get_parent_dependencies(action):
    """
    Get all parent dependencies for an action.

    Args:
        action: The Action instance

    Returns:
        list: List of parent dependency dicts [{'id': int, 'sequence': int}, ...]
    """
    links = action.refs.get('links', {})
    return links.get('parents', [])


def get_dependencies_sorted(action, dependency_type='children'):
    """
    Get dependencies sorted by sequence.

    Args:
        action: The Action instance
        dependency_type: 'children' or 'parents'

    Returns:
        list: Sorted list of dependency dicts
    """
    deps = get_child_dependencies(action) if dependency_type == 'children' else get_parent_dependencies(action)
    return sorted(deps, key=lambda x: x.get('sequence', 999))