"""Central registry for scheduler maintenance runners and Celery schedule metadata.

This module is the single source of truth for:
- Maintenance function routing (Python callables)
- ScheduledTask bootstrap definitions
"""

from __future__ import annotations

from typing import Any, Callable

from common.tasks import (
    refresh_keywords_task,
    recompute_relationship_counts,
    recompute_basic_stats,
    refresh_model_registry_docs,
)

TASK_MODULE_PATH = "apps.support.scheduler.tasks"

# Task names map to concrete maintenance callables.
MAINTENANCE_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "refresh_keywords": refresh_keywords_task,
    "recompute_relationship_counts": recompute_relationship_counts,
    "recompute_basic_stats": recompute_basic_stats,
    "refresh_model_registry_docs": refresh_model_registry_docs,
}

# Canonical metadata used by scheduler services/admin bootstrap.
SCHEDULED_TASK_DEFINITIONS: dict[str, dict[str, Any]] = {
    "refresh_keywords": {
        "task_path": f"{TASK_MODULE_PATH}.task_refresh_keywords",
        "description": "Refresh search keywords for records with pending updates",
        "frequency": "15min",
        "run_at_minute": 0,
    },
    "recompute_relationship_counts": {
        "task_path": f"{TASK_MODULE_PATH}.task_recompute_relationship_counts",
        "description": "Update denormalized relationship counts (parents, children, linked)",
        "frequency": "hourly",
        "run_at_minute": 0,
    },
    "recompute_basic_stats": {
        "task_path": f"{TASK_MODULE_PATH}.task_recompute_basic_stats",
        "description": "Normalize stats containers on StatsMixin models",
        "frequency": "weekly",
        "run_at_hour": 4,
        "run_on_day": 6,
    },
    "ensure_model_defaults": {
        "task_path": f"{TASK_MODULE_PATH}.task_ensure_model_defaults",
        "description": "Ensure all JSONB envelope fields have proper default structures",
        "frequency": "daily",
        "run_at_hour": 2,
    },
    "export_data": {
        "task_path": f"{TASK_MODULE_PATH}.task_export_data",
        "description": "Export all model data to JSON backup files",
        "frequency": "daily",
        "run_at_hour": 3,
    },
    "refresh_model_registry_docs": {
        "task_path": f"{TASK_MODULE_PATH}.task_refresh_model_registry_docs",
        "description": "Regenerate model registry README, JSON, and CSV files",
        "frequency": "daily",
        "run_at_hour": 5,
    },
    "aggregate_user_daily_logs": {
        "task_path": f"{TASK_MODULE_PATH}.task_aggregate_user_daily_logs",
        "description": "Aggregate APILog entries into UserDailyLog summaries",
        "frequency": "daily",
        "run_at_hour": 1,
        "run_at_minute": 30,
    },
    "reconcile_aging": {
        "task_path": f"{TASK_MODULE_PATH}.task_reconcile_aging",
        "description": "Recalculate AR aging buckets for all active orgs",
        "frequency": "daily",
        "run_at_hour": 2,
        "run_at_minute": 40,
    },
}


def run_maintenance_function(task_name: str, **kwargs: Any) -> Any:
    """Execute a registered maintenance function by task name."""
    func = MAINTENANCE_FUNCTIONS.get(task_name)
    if func is None:
        raise KeyError(f"No registered maintenance function for task '{task_name}'")
    return func(**kwargs)
