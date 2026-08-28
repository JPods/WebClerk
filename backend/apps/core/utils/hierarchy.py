"""
Hierarchy utility functions for parent-child relationships in Django models.

This module provides utilities to work with parent-child relationships in Django models,
particularly for hierarchical data structures like tags, categories, etc.
"""

from typing import Type, Optional, List
from django.db.models import Model, QuerySet


def _find_parent_field(model: Type[Model]) -> Optional[str]:
    """
    Find the foreign key field that represents the parent relationship.
    Looks for common naming patterns for parent fields.
    """
    for field in model._meta.get_fields():
        if field.one_to_one or field.many_to_one:
            field_name = field.name
            # Common parent field naming patterns
            if field_name in ('parent', 'parent_id', 'parent_field', 'category', 'parent_tag'):
                return field_name
            # Also check related_name if available
            if hasattr(field, 'related_name') and field.related_name:
                if field.related_name in ('parent', 'parent_id', 'parent_field'):
                    return field_name
    return None


def parent_field_name(model: Type[Model]) -> Optional[str]:
    """
    Get the name of the parent field for a model.
    
    Args:
        model: The Django model class
        
    Returns:
        The field name if found, None otherwise
    """
    return _find_parent_field(model)


def children_qs(model: Type[Model], parent_obj: Model, parent_field: str) -> QuerySet:
    """
    Get a queryset of child objects for a given parent.
    
    Args:
        model: The Django model class
        parent_obj: The parent model instance
        parent_field: The name of the parent field
        
    Returns:
        QuerySet of child objects
    """
    if not parent_field or not hasattr(parent_obj, 'pk'):
        return model.objects.none()
    
    return model.objects.filter(**{parent_field: parent_obj.pk})


def parent_chain(model: Type[Model], obj: Model, pf: Optional[str] = None) -> List[Model]:
    """
    Get the chain of parent objects from the given object up to the root.
    
    Args:
        model: The Django model class  
        obj: The starting model instance
        pf: Optional parent field name (if not provided, will be discovered)
        
    Returns:
        List of parent objects from immediate parent to root
    """
    if not hasattr(obj, 'pk'):
        return []
    
    if pf is None:
        pf = parent_field_name(model)
        if pf is None:
            return []
    
    parents = []
    current = obj
    
    # Limit chain length to prevent infinite loops
    max_depth = 100
    depth = 0
    
    while depth < max_depth:
        parent_val = getattr(current, pf, None)
        if parent_val is None:
            break
            
        try:
            if isinstance(parent_val, Model):
                parent = parent_val
            else:
                parent = model.objects.get(pk=parent_val)
                
            if parent.pk == current.pk:  # Prevent infinite loops
                break
                
            parents.append(parent)
            current = parent
            depth += 1
        except model.DoesNotExist:
            break
    
    return parents


def is_descendant(model: Type[Model], potential_descendant: Model, potential_ancestor: Model, parent_field: Optional[str] = None) -> bool:
    """
    Check if potential_descendant is a descendant of potential_ancestor.
    
    Args:
        model: The Django model class
        potential_descendant: The model instance to check
        potential_ancestor: The model instance to check against
        parent_field: Optional parent field name
        
    Returns:
        True if potential_descendant is a descendant of potential_ancestor
    """
    if parent_field is None:
        parent_field = parent_field_name(model)
        if parent_field is None:
            return False
    
    chain = parent_chain(model, potential_descendant, parent_field)
    return potential_ancestor in chain


def move_node(model: Type[Model], node: Model, new_parent: Optional[Model], parent_field: Optional[str] = None) -> bool:
    """
    Move a node to a new parent.
    
    Args:
        model: The Django model class
        node: The node to move
        new_parent: The new parent (None to make root)
        parent_field: Optional parent field name
        
    Returns:
        True if successful
    """
    if parent_field is None:
        parent_field = parent_field_name(model)
        if parent_field is None:
            return False
    
    # Prevent moving a node to itself or its descendants
    if new_parent and (new_parent.pk == node.pk or is_descendant(model, new_parent, node, parent_field)):
        return False
    
    try:
        if new_parent:
            setattr(node, parent_field, new_parent)
        else:
            setattr(node, parent_field, None)
        node.save(update_fields=[parent_field])
        return True
    except Exception:
        return False