"""Reusable service functions for creating sample Project data.

These functions allow tests, shell sessions, or management commands to compose
project creation logic without duplicating randomization rules.
"""
from __future__ import annotations

import random
from typing import Iterable, Sequence
from django.db import transaction
from apps.transactions.models.projects import Project, default_objective, default_tasks

CATEGORIES: Sequence[str] = ("ops", "sales", "finance", "support", "engineering", "compliance")
INTENTS: Sequence[str] = (
    "Improve inventory accuracy",
    "Accelerate order fulfillment",
    "Reduce support backlog",
    "Launch new product line",
    "Optimize procurement cycle",
    "Enhance partner onboarding",
)

STATUS_POOL: Sequence[str] = ("draft", "active", "onhold")
ATTENTION_POOL: Sequence[str] = ("normal", "high", "critical")


def build_project_payload(intent: str | None = None, category: str | None = None, priority: int | None = None,
                          status: str | None = None, attention: str | None = None) -> dict:
    """Return a dict of base Project field values (excluding tasks) with defaults.

    Callers may override any field. The objective summary mirrors intent.
    """
    if intent is None:
        intent = random.choice(INTENTS)
    if category is None:
        category = random.choice(CATEGORIES)
    if priority is None:
        priority = random.randint(1, 5)
    if status is None:
        status = random.choice(STATUS_POOL)
    if attention is None:
        attention = random.choice(ATTENTION_POOL)
    objective = default_objective()
    objective['summary'] = intent
    objective['success']['definition'] = "Outcome TBD"
    return {
        'intent': intent,
        'situation': f"Situation narrative for: {intent}",
        'category': category,
        'priority': priority,
        'status': status,
        'attention': attention,
        'objective': objective,
    }


def build_tasks(count: int, done_fraction: float = 0.3) -> dict:
    """Return a tasks JSON structure with `count` items and approximate done fraction."""
    count = max(0, count)
    done_fraction = min(1.0, max(0.0, done_fraction))
    t = default_tasks()
    items = t['items']
    for i in range(count):
        items.append({
            'id': i + 1,
            'title': f"Task {i+1}",
            'done': random.random() < done_fraction,
            'weight': random.randint(1, 3),
        })
    return t


def create_sample_projects(number: int = 3, tasks_min: int = 0, tasks_max: int = 5,
                           done_fraction: float = 0.3, force: bool = False) -> list[Project]:
    """Create sample projects and return them.

    Args:
        number: how many projects.
        tasks_min / tasks_max: inclusive range for per-project task count.
        done_fraction: probability each task is pre-marked done.
        force: if False, skip creation when an identical intent exists (case-insensitive).
    """
    number = max(1, number)
    tasks_min = max(0, tasks_min)
    tasks_max = max(tasks_min, tasks_max)
    done_fraction = min(1.0, max(0.0, done_fraction))

    created: list[Project] = []
    with transaction.atomic():
        for _ in range(number):
            payload = build_project_payload()
            if not force and Project.objects.filter(intent__iexact=payload['intent']).exists():
                continue
            proj = Project(**payload)
            task_count = random.randint(tasks_min, tasks_max)
            if task_count:
                proj.tasks = build_tasks(task_count, done_fraction)
            proj.save()
            created.append(proj)
    return created

__all__ = [
    'create_sample_projects', 'build_project_payload', 'build_tasks',
    'CATEGORIES', 'INTENTS'
]
