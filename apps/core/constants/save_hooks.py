"""
Save hooks management for pre/post save scripts.

This module provides functionality to load and execute custom save hooks
defined in Setting records with purpose='save_pre_post'.

Setting record structure:
- purpose: 'save_pre_post'
- model_target: The model name this hook applies to (e.g., 'contact', 'proposal')
- name: Descriptive name (e.g., 'contact_validation', 'audit_trail')
- data: {
    'save_pre': 'Python script to execute before save (synchronous)',
    'save_post': 'Python script to execute after save (synchronous)',
    'save_async': 'Python script to execute asynchronously after save'
  }
- is_active: true/false

Usage:
    from apps.core.constants.save_hooks import get_save_hooks, execute_save_hook

    # Get hooks for a model
    hooks = get_save_hooks('contact')

    # Execute a pre-save hook
    result = execute_save_hook('contact', 'save_pre', instance, data)
"""
import logging
from typing import Dict, Any, Optional

from apps.core.services.cache_service import cache_service
from apps.core.models.setting import Setting

logger = logging.getLogger(__name__)


def get_save_hooks(model_name: str) -> Dict[str, Dict[str, Any]]:
    """
    Get all active save hooks for a specific model.

    Args:
        model_name: The model name to get hooks for

    Returns:
        Dictionary with hook names as keys, containing hook data as values.
        Example: {
            'contact_validation': {
                'save_pre': 'script content',
                'save_post': 'script content'
            }
        }
    """
    print(f"[HOOK DEBUG] get_save_hooks called for model '{model_name}'")

    cache_key = cache_service.make_key('save_hooks', model_name)
    cached_data = cache_service.get(cache_key)

    print(f"[HOOK DEBUG] Cache key: {cache_key}")
    print(f"[HOOK DEBUG] Cached data found: {cached_data is not None}")

    if cached_data is None:
        # Load from database
        print(f"[HOOK DEBUG] Loading hooks from database for model '{model_name}'")

        hooks: Dict[str, Dict[str, Any]] = {}
        settings_qs = Setting.objects.filter(
            purpose='save_pre_post',
            model_target=model_name,
            is_active=True
        ).only('name', 'data')

        print(f"[HOOK DEBUG] Found {settings_qs.count()} setting records")

        for setting in settings_qs:
            hook_name = setting.name
            print(
                f"[HOOK DEBUG] Processing setting: name='{hook_name}', data keys="
                f"{list(setting.data.keys()) if setting.data else 'None'}"
            )
            if hook_name and setting.data:
                hooks[hook_name] = setting.data

        print(f"[HOOK DEBUG] Loaded {len(hooks)} hooks: {list(hooks.keys())}")

        # Cache the result
        cache_service.set(cache_key, hooks, ttl=3600)  # 1 hour cache
        cached_data = hooks

    print(f"[HOOK DEBUG] Returning {len(cached_data)} hooks")
    return cached_data


def execute_save_hook(model_name: str, hook_type: str, instance, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Execute all save hooks of a specific type for a model.

    Args:
        model_name: The model name
        hook_type: 'save_pre', 'save_post', or 'save_async'
        instance: The model instance being saved
        data: Additional context data

    Returns:
        Dictionary with execution results
    """
    if hook_type not in ['save_pre', 'save_post', 'save_async']:
        return {'success': False, 'error': f'Invalid hook type: {hook_type}'}

    hooks = get_save_hooks(model_name)
    results = {
        'success': True,
        'executed': [],
        'errors': [],
        'warnings': [],
        'scripts_executed': []  # Track actual scripts for debugging
    }

    print(f"[HOOK DEBUG] Looking for hooks for model '{model_name}' and type '{hook_type}'")

    hooks = get_save_hooks(model_name)
    print(f"[HOOK DEBUG] Found {len(hooks)} hooks for {model_name}")

    for hook_name, hook_data in hooks.items():
        script = hook_data.get(hook_type)
        if not script:
            print(f"[HOOK DEBUG] No {hook_type} script for hook '{hook_name}'")
            continue

        print(f"[HOOK DEBUG] Processing hook '{hook_name}' with {hook_type} script")

        try:
            # Create execution context with access to instance
            context = {
                'instance': instance,
                'data': data or {},
                'model_name': model_name,
                'hook_name': hook_name,
                'hook_type': hook_type,
            }

            # Execute the script
            # Note: In production, you might want to use a safer execution method
            # like restricted Python execution or a scripting engine
            print(f"[HOOK DEBUG] Executing {hook_type} hook '{hook_name}' for {model_name}")
            print(f"[HOOK DEBUG] Script: {script}")
            print(f"[HOOK DEBUG] Instance metadata before execution: {getattr(instance, 'metadata', {})}")

            exec(script, {'__builtins__': {}}, context)

            print(f"[HOOK DEBUG] Successfully executed {hook_type} hook '{hook_name}'")
            print(f"[HOOK DEBUG] Instance metadata after execution: {getattr(instance, 'metadata', {})}")

            # Check if the script modified the instance
            if hasattr(instance, '_meta'):
                print(f"[HOOK DEBUG] Instance fields that may have changed: {[f.name for f in instance._meta.fields if f.name in ['metadata', 'refs', 'prefs', 'comments', 'actions']]}")

            results['executed'].append(hook_name)
            results['scripts_executed'].append(script)

        except Exception as e:
            error_msg = f"Hook '{hook_name}' failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results['errors'].append(error_msg)
            results['success'] = False

    return results


def invalidate_save_hooks_cache(model_name: Optional[str] = None):
    """
    Invalidate save hooks cache.

    Args:
        model_name: Specific model to invalidate, or None for all
    """
    if model_name:
        cache_key = cache_service.make_key('save_hooks', model_name)
        cache_service.delete(cache_key)
    else:
        # Invalidate all save hooks cache
        cache_service.invalidate_namespace('save_hooks')


def validate_save_hook_script(script: str) -> Dict[str, Any]:
    """
    Validate a save hook script for syntax and safety.

    Args:
        script: The Python script to validate

    Returns:
        Validation result with any issues found
    """
    result = {
        'valid': True,
        'issues': [],
        'warnings': []
    }

    try:
        # Basic syntax check
        compile(script, '<string>', 'exec')
    except SyntaxError as e:
        result['valid'] = False
        result['issues'].append(f"Syntax error: {e}")

    # Check for potentially dangerous operations
    dangerous_patterns = [
        'import os', 'import sys', 'import subprocess',
        'exec(', 'eval(', '__import__(',
        'open(', 'file(', 'input('
    ]

    for pattern in dangerous_patterns:
        if pattern in script:
            result['warnings'].append(f"Potentially dangerous pattern found: {pattern}")

    return result


def get_all_save_hooks() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Get all save hooks grouped by model.

    Returns:
        Dictionary with model names as keys, containing hook dictionaries as values.
    """
    all_hooks = {}

    settings_qs = Setting.objects.filter(
        purpose='save_pre_post',
        is_active=True
    ).only('name', 'model_target', 'data')

    for setting in settings_qs:
        model_name = setting.model_target
        hook_name = setting.name

        if model_name not in all_hooks:
            all_hooks[model_name] = {}

        if hook_name and setting.data:
            all_hooks[model_name][hook_name] = setting.data

    return all_hooks