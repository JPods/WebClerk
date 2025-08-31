"""Seed Project records with optional randomized tasks.

Usage examples:
  python manage.py seed_projects --projects 5
  python manage.py seed_projects --projects 3 --tasks-min 2 --tasks-max 8 --force

Behavior:
  - Creates the requested number of Project rows (default 3)
  - For each project populates situation / intent / category / objective skeleton
  - Optionally seeds a random number of tasks (each with id/title/done/weight)
  - Burndown is auto-derived by the model save() (tasks.completed/total)
  - Skips creation if a plausible duplicate intent already exists unless --force

Fields intentionally minimal; profit / velocity left at defaults so that later
domain enrichment or synchronization processes can fill them in.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
import random
import datetime as dt

from apps.transactions.models.projects import Project, default_objective, default_tasks

CATEGORIES = ["ops", "sales", "finance", "support", "engineering", "compliance"]
INTENTS = [
    "Improve inventory accuracy",
    "Accelerate order fulfillment",
    "Reduce support backlog",
    "Launch new product line",
    "Optimize procurement cycle",
    "Enhance partner onboarding",
]


class Command(BaseCommand):
    help = "Seed Project records with optional task backlogs."

    def add_arguments(self, parser):  # pragma: no cover - simple CLI wiring
        parser.add_argument('--projects', type=int, default=3, help='Number of projects to create (default 3).')
        parser.add_argument('--tasks-min', type=int, default=0, help='Minimum tasks per project (default 0).')
        parser.add_argument('--tasks-max', type=int, default=5, help='Maximum tasks per project (default 5).')
        parser.add_argument('--done-fraction', type=float, default=0.3, help='Approx fraction of tasks pre-marked done (0-1).')
        parser.add_argument('--force', action='store_true', help='Create even if a similar intent exists.')

    def handle(self, *args, **opts):
        count = max(1, opts['projects'])
        tasks_min = max(0, opts['tasks_min'])
        tasks_max = max(tasks_min, opts['tasks_max'])
        done_fraction = min(1.0, max(0.0, opts['done_fraction']))
        force = opts['force']

        created = 0
        duplicates_skipped = 0

        with transaction.atomic():
            for n in range(count):
                intent = random.choice(INTENTS)
                if not force and Project.objects.filter(intent__iexact=intent).exists():
                    duplicates_skipped += 1
                    continue

                objective = default_objective()
                objective['summary'] = intent
                objective['success']['definition'] = "Outcome TBD"

                proj = Project(
                    intent=intent,
                    situation=f"Situation narrative for: {intent}",
                    category=random.choice(CATEGORIES),
                    priority=random.randint(1, 5),
                    status=random.choice(["draft", "active", "onhold"]),
                    attention=random.choice(["normal", "high", "critical"]),
                    objective=objective,
                )

                # tasks
                task_count = random.randint(tasks_min, tasks_max)
                if task_count:
                    t_struct = default_tasks()
                    items = t_struct['items']
                    for i in range(task_count):
                        items.append({
                            'id': i + 1,
                            'title': f"Task {i+1} for {intent[:18]}",
                            'done': random.random() < done_fraction,
                            'weight': random.randint(1, 3),
                        })
                    proj.tasks = t_struct

                proj.save()
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Created {created} projects (skipped {duplicates_skipped} duplicate intents)."
        ))