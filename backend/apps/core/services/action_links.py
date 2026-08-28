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


def auto_schedule_from_parents(action, save=True):
    """
    Auto-schedule an action based on its parent dependencies.
    
    When an action has parents in refs.parents[], its start date (dt_start)
    should be set to the latest end date (dt_end or dt_deadline) of all parents.
    This implements Finish-to-Start (FS) dependency scheduling.
    
    Args:
        action: The Action instance with refs.parents to process
        save: Whether to save the action after updating (default: True)
    
    Returns:
        dict: {
            'updated': bool - whether dt_start was updated,
            'dt_start': int or None - the new start date (milliseconds),
            'parent_count': int - number of parent dependencies found,
            'latest_parent_id': str or None - ID of the parent with latest end date
        }
    """
    from apps.core.models import Action
    import logging
    
    logger = logging.getLogger('console')
    result = {
        'updated': False,
        'dt_start': None,
        'parent_count': 0,
        'latest_parent_id': None
    }
    
    # Get refs.parents (list of parent action IDs as strings)
    refs = getattr(action, 'refs', {}) or {}
    if not isinstance(refs, dict):
        refs = {}
    
    parents = refs.get('parents', [])
    if not parents or not isinstance(parents, list):
        return result
    
    result['parent_count'] = len(parents)
    
    # Find the latest end date among all parents
    # "Latest" means the parent that finishes last (largest timestamp = furthest in future)
    latest_end = None
    latest_parent_id = None
    
    for parent_id in parents:
        try:
            parent_id_str = str(parent_id)
            # Try to get parent as integer ID
            try:
                parent_id_int = int(parent_id_str)
                parent_action = Action.objects.filter(id=parent_id_int).first()
            except (ValueError, TypeError):
                continue
            
            if not parent_action:
                logger.debug(f"[AutoSchedule] Parent {parent_id} not found for action {action.id}")
                continue
            
            # Calculate parent's effective end date for scheduling:
            # 1. Use dt_start + duration (the scheduled/planned end)
            # 2. Fall back to dt_deadline if no duration
            # 3. Last resort: dt_completed (when it was actually finished)
            parent_end = None
            ms_per_day = 24 * 60 * 60 * 1000
            
            if parent_action.dt_start and parent_action.duration:
                # Use calculated end: dt_start + duration (days -> ms)
                parent_end = parent_action.dt_start + (parent_action.duration * ms_per_day)
                logger.debug(f"[AutoSchedule] Parent {parent_id} using dt_start + duration: {parent_end}")
            elif parent_action.dt_deadline:
                parent_end = parent_action.dt_deadline
                logger.debug(f"[AutoSchedule] Parent {parent_id} using dt_deadline: {parent_end}")
            elif parent_action.dt_completed:
                parent_end = parent_action.dt_completed
                logger.debug(f"[AutoSchedule] Parent {parent_id} using dt_completed: {parent_end}")
            else:
                logger.debug(f"[AutoSchedule] Parent {parent_id} has no end date info")
                continue
            
            # Ensure we're comparing integers
            if parent_end is not None:
                parent_end = int(parent_end)
            
            # Track the LARGEST end date (furthest in future = finishes last)
            if parent_end and (latest_end is None or parent_end > latest_end):
                latest_end = parent_end
                latest_parent_id = parent_id_str
                logger.debug(f"[AutoSchedule] New latest_end from parent {parent_id}: {latest_end}")
                
        except Exception as e:
            logger.warning(f"[AutoSchedule] Error processing parent {parent_id}: {e}")
            continue
    
    if latest_end is not None and latest_parent_id:
        # Update the action's start date (keep the same duration)
        current_start = action.dt_start
        current_duration = action.duration
        ms_per_day = 24 * 60 * 60 * 1000
        
        update_fields = []
        
        if current_start != latest_end:
            action.dt_start = latest_end
            result['updated'] = True
            result['dt_start'] = latest_end
            result['latest_parent_id'] = latest_parent_id
            update_fields.append('dt_start')
            
            logger.info(
                f"[AutoSchedule] Action {action.id} dt_start updated: {current_start} -> {latest_end} "
                f"(based on parent {latest_parent_id})"
            )
        
        # If duration is null or zero, default to 7 days
        if not current_duration or current_duration == 0:
            action.duration = 7
            update_fields.append('duration')
            logger.info(f"[AutoSchedule] Action {action.id} duration defaulted to 7 days")
        
        if save and update_fields:
            action.save(update_fields=update_fields)
    
    return result


def check_and_reschedule_children(action, save=True):
    """
    When a parent action's end date changes, reschedule all dependent children.
    
    This is the inverse of auto_schedule_from_parents - when a parent's dt_end
    or dt_deadline changes, all actions that depend on it should be rescheduled.
    
    Args:
        action: The parent Action instance whose end date changed
        save: Whether to save the children after updating (default: True)
    
    Returns:
        list: List of child action IDs that were rescheduled
    """
    from apps.core.models import Action
    import logging
    
    logger = logging.getLogger('console')
    rescheduled = []
    
    action_id_str = str(action.id)
    
    # Find all actions that have this action in their refs.parents
    # We need to search for actions where refs.parents contains this action's ID
    try:
        # Query actions where refs->parents array contains this action's ID
        from django.db.models import Q
        from django.db.models.functions import Cast
        from django.db.models import TextField
        
        # PostgreSQL JSON containment - refs->'parents' @> '["action_id"]'
        children = Action.objects.filter(
            refs__parents__contains=[action_id_str]
        ) | Action.objects.filter(
            refs__parents__contains=[action.id]
        )
        
        for child in children:
            result = auto_schedule_from_parents(child, save=save)
            if result['updated']:
                rescheduled.append(child.id)
                logger.info(f"[AutoSchedule] Rescheduled child action {child.id}")
                
    except Exception as e:
        logger.warning(f"[AutoSchedule] Error rescheduling children of action {action.id}: {e}")
    
    return rescheduled


def would_create_circular_dependency(source_id, target_id):
    """
    Check if creating a dependency from source → target would create a circular dependency.
    
    A circular dependency would occur if target is already an ancestor of source
    (i.e., source depends on target directly or transitively).
    
    Args:
        source_id: The parent action ID (the action that must finish first)
        target_id: The child action ID (the action that depends on the parent)
    
    Returns:
        dict: {
            'would_create_cycle': bool,
            'cycle_path': list of IDs if cycle found, empty otherwise
        }
    """
    from apps.core.models import Action
    import logging
    
    logger = logging.getLogger('console')
    result = {
        'would_create_cycle': False,
        'cycle_path': []
    }
    
    source_id_str = str(source_id)
    target_id_str = str(target_id)
    
    # Self-reference check
    if source_id_str == target_id_str:
        result['would_create_cycle'] = True
        result['cycle_path'] = [source_id_str]
        return result
    
    # Check if source already has target as an ancestor (traverse up from source)
    visited = set()
    path = [source_id_str]
    
    def has_ancestor(action_id, looking_for):
        """Recursively check if looking_for is an ancestor of action_id"""
        if action_id in visited:
            return False
        visited.add(action_id)
        
        try:
            action = Action.objects.filter(id=int(action_id)).first()
            if not action:
                return False
            
            refs = getattr(action, 'refs', {}) or {}
            parents = refs.get('parents', [])
            
            for parent_id in parents:
                parent_id_str = str(parent_id)
                
                if parent_id_str == looking_for:
                    path.append(parent_id_str)
                    return True
                
                # Deeper search
                path.append(parent_id_str)
                if has_ancestor(parent_id_str, looking_for):
                    return True
                path.pop()
                
        except Exception as e:
            logger.warning(f"[CircularCheck] Error checking ancestors of {action_id}: {e}")
        
        return False
    
    # If target is an ancestor of source, adding source as a parent of target would create a cycle
    if has_ancestor(source_id_str, target_id_str):
        result['would_create_cycle'] = True
        result['cycle_path'] = path
        logger.warning(f"[CircularCheck] Would create cycle: {' → '.join(path)}")
    
    return result