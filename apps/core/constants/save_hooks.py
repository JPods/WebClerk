"""
Save hooks management for pre/post save scripts.

This module provides functionality to load and execute custom save hooks
defined in Setting records with purpose='save_pre_post'.

Setting record structure:
- purpose: 'save_pre_post'
- parent_model: The model name this hook applies to (e.g., 'contact', 'proposal')
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
    logger.debug("[HOOK DEBUG] get_save_hooks called for model '%s'", model_name)

    cache_key = cache_service.make_key('save_hooks', model_name)
    cached_data = cache_service.get(cache_key)

    logger.debug("[HOOK DEBUG] Cache key: %s", cache_key)
    logger.debug("[HOOK DEBUG] Cached data found: %s", cached_data is not None)

    if cached_data is None:
        # Load from database
        logger.debug("[HOOK DEBUG] Loading hooks from database for model '%s'", model_name)

        hooks: Dict[str, Dict[str, Any]] = {}
        settings_qs = Setting.objects.filter(
            purpose='save_pre_post',
            parent_model=model_name,
            is_active=True
        ).only('name', 'data')

        logger.debug("[HOOK DEBUG] Found %d setting records", settings_qs.count())

        for setting in settings_qs:
            hook_name = setting.name
                logger.debug(
                    "[HOOK DEBUG] Processing setting: name='%s', data keys=%s",
                    hook_name,
                    list(setting.data.keys()) if setting.data else 'None',
                )
            if hook_name and setting.data:
                hooks[hook_name] = setting.data

        logger.debug("[HOOK DEBUG] Loaded %d hooks: %s", len(hooks), list(hooks.keys()))

        # Cache the result
        cache_service.set(cache_key, hooks, ttl=3600)  # 1 hour cache
        cached_data = hooks

    logger.debug("[HOOK DEBUG] Returning %d hooks", len(cached_data))
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

    logger.debug("[HOOK DEBUG] Looking for hooks for model '%s' and type '%s'", model_name, hook_type)

    hooks = get_save_hooks(model_name)
    logger.debug("[HOOK DEBUG] Found %d hooks for %s", len(hooks), model_name)

    for hook_name, hook_data in hooks.items():
        script = hook_data.get(hook_type)
        if not script:
            logger.debug("[HOOK DEBUG] No %s script for hook '%s'", hook_type, hook_name)
            continue

        logger.debug("[HOOK DEBUG] Processing hook '%s' with %s script", hook_name, hook_type)

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
            logger.debug("[HOOK DEBUG] Executing %s hook '%s' for %s", hook_type, hook_name, model_name)
            logger.debug("[HOOK DEBUG] Script: %s", script)
            logger.debug("[HOOK DEBUG] Instance metadata before execution: %s", getattr(instance, 'metadata', {}))

            exec(script, {'__builtins__': {}}, context)

            logger.debug("[HOOK DEBUG] Successfully executed %s hook '%s'", hook_type, hook_name)
            logger.debug("[HOOK DEBUG] Instance metadata after execution: %s", getattr(instance, 'metadata', {}))

            # Check if the script modified the instance
            if hasattr(instance, '_meta'):
                logger.debug("[HOOK DEBUG] Instance fields that may have changed: %s", [f.name for f in instance._meta.fields if f.name in ['metadata', 'refs', 'prefs', 'comments', 'actions']])

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
    ).only('name', 'parent_model', 'data')

    for setting in settings_qs:
        model_name = setting.parent_model
        hook_name = setting.name

        if model_name not in all_hooks:
            all_hooks[model_name] = {}

        if hook_name and setting.data:
            all_hooks[model_name][hook_name] = setting.data

    return all_hooks