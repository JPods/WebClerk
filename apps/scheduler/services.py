"""
Service functions for the scheduler app.

Provides utilities for managing and executing scheduled tasks
outside of the Celery context (e.g., manual runs, testing).
"""

from typing import Optional
from django.utils import timezone
from django.apps import apps


def get_or_create_scheduled_tasks():
    """
    Ensure all defined tasks have ScheduledTask records.
    
    Call this after migrations or when adding new tasks.
    Returns dict of created/existing task records.
    """
    from .models import ScheduledTask, TaskConfig
    from .tasks import CELERY_BEAT_SCHEDULE
    
    results = {'created': [], 'existing': []}
    
    task_definitions = {
        'refresh_keywords': {
            'task_path': 'apps.scheduler.tasks.task_refresh_keywords',
            'description': 'Refresh search keywords for records with pending updates',
            'frequency': ScheduledTask.Frequency.MINUTES_15,
            'run_at_minute': 0,
        },
        'recompute_relationship_counts': {
            'task_path': 'apps.scheduler.tasks.task_recompute_relationship_counts',
            'description': 'Update denormalized relationship counts (parents, children, linked)',
            'frequency': ScheduledTask.Frequency.HOURLY,
            'run_at_minute': 0,
        },
        'recompute_basic_stats': {
            'task_path': 'apps.scheduler.tasks.task_recompute_basic_stats',
            'description': 'Normalize stats containers on StatsMixin models',
            'frequency': ScheduledTask.Frequency.WEEKLY,
            'run_at_hour': 4,
            'run_on_day': 6,  # Sunday
        },
        'ensure_model_defaults': {
            'task_path': 'apps.scheduler.tasks.task_ensure_model_defaults',
            'description': 'Ensure all JSONB envelope fields have proper default structures',
            'frequency': ScheduledTask.Frequency.DAILY,
            'run_at_hour': 2,
        },
        'export_data': {
            'task_path': 'apps.scheduler.tasks.task_export_data',
            'description': 'Export all model data to JSON backup files',
            'frequency': ScheduledTask.Frequency.DAILY,
            'run_at_hour': 3,
        },
        'refresh_model_registry_docs': {
            'task_path': 'apps.scheduler.tasks.task_refresh_model_registry_docs',
            'description': 'Regenerate model registry README, JSON, and CSV files',
            'frequency': ScheduledTask.Frequency.DAILY,
            'run_at_hour': 5,
        },
    }
    
    for name, definition in task_definitions.items():
        task, created = ScheduledTask.objects.get_or_create(
            name=name,
            defaults={
                'task_path': definition['task_path'],
                'description': definition.get('description', ''),
                'frequency': definition.get('frequency', ScheduledTask.Frequency.DAILY),
                'run_at_hour': definition.get('run_at_hour', 0),
                'run_at_minute': definition.get('run_at_minute', 0),
                'run_on_day': definition.get('run_on_day', 0),
            }
        )
        
        if created:
            results['created'].append(name)
            # Create default config
            TaskConfig.objects.create(task=task)
        else:
            results['existing'].append(name)
    
    return results


def run_task_now(task_name: str, **kwargs) -> dict:
    """
    Execute a scheduled task immediately (synchronously).
    
    Useful for testing or manual runs from Django shell/admin.
    
    Args:
        task_name: Name of the ScheduledTask
        **kwargs: Override parameters
        
    Returns:
        Task result dict
    """
    from .models import ScheduledTask, TaskRun
    from . import tasks as task_module
    
    task = ScheduledTask.objects.filter(name=task_name).first()
    if not task:
        return {'error': f"Task '{task_name}' not found"}
    
    # Get task function
    func_name = f"task_{task_name}"
    task_func = getattr(task_module, func_name, None)
    if not task_func:
        return {'error': f"Task function '{func_name}' not found"}
    
    # Merge config with kwargs
    config_kwargs = {}
    if hasattr(task, 'config'):
        config_kwargs = task.config.as_kwargs()
    final_kwargs = {**config_kwargs, **kwargs}
    
    # Create run record
    run = TaskRun.objects.create(
        task=task,
        kwargs=final_kwargs,
        status=TaskRun.Status.RUNNING,
        started_at=timezone.now(),
    )
    
    try:
        # Execute synchronously (call underlying function, not Celery task)
        # This bypasses Celery's delay() mechanism
        result = task_func.run(**final_kwargs)
        run.complete(result)
        return result
    except Exception as e:
        import traceback
        run.fail(str(e), traceback.format_exc())
        return {'error': str(e)}


def get_task_status(task_name: str) -> dict:
    """
    Get current status and recent history for a task.
    
    Args:
        task_name: Name of the ScheduledTask
        
    Returns:
        Status dict with task info and recent runs
    """
    from .models import ScheduledTask, TaskRun
    
    task = ScheduledTask.objects.filter(name=task_name).first()
    if not task:
        return {'error': f"Task '{task_name}' not found"}
    
    recent_runs = TaskRun.objects.filter(task=task).order_by('-started_at')[:10]
    
    return {
        'name': task.name,
        'status': task.status,
        'frequency': task.get_frequency_display(),
        'last_run': {
            'at': task.last_run_at,
            'status': task.last_run_status,
            'duration': task.last_run_duration,
        } if task.last_run_at else None,
        'next_run_at': task.next_run_at,
        'stats': {
            'run_count': task.run_count,
            'error_count': task.error_count,
            'success_rate': (
                (task.run_count - task.error_count) / task.run_count * 100
                if task.run_count > 0 else 0
            ),
        },
        'recent_runs': [
            {
                'started_at': r.started_at,
                'status': r.status,
                'duration': r.duration,
                'processed': r.records_processed,
                'updated': r.records_updated,
            }
            for r in recent_runs
        ],
    }


def pause_task(task_name: str) -> bool:
    """Pause a scheduled task."""
    from .models import ScheduledTask
    return ScheduledTask.objects.filter(name=task_name).update(
        status=ScheduledTask.Status.PAUSED
    ) > 0


def resume_task(task_name: str) -> bool:
    """Resume a paused task."""
    from .models import ScheduledTask
    return ScheduledTask.objects.filter(name=task_name).update(
        status=ScheduledTask.Status.ACTIVE
    ) > 0


def disable_task(task_name: str) -> bool:
    """Disable a task completely."""
    from .models import ScheduledTask
    return ScheduledTask.objects.filter(name=task_name).update(
        status=ScheduledTask.Status.DISABLED
    ) > 0
