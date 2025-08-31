"""Seed Project records with optional randomized tasks, profit simulation, and order linkage.

Usage examples:
    python manage.py seed_projects --projects 5 --tasks-min 2 --tasks-max 6
    python manage.py seed_projects --projects 4 --simulate-profit --link-orders 3
    python manage.py seed_projects --projects 3 --force --done-fraction 0.5

Options:
    --simulate-profit    Randomize profit & profit_velocity values.
    --link-orders N      Attach up to N random Order ids into project.refs['related_ids'] (if Orders exist).

Behavior:
    - Delegates core creation to services.project_seeding.create_sample_projects
    - Optionally enriches each new project with simulated profit metrics
    - Optionally links existing Order primary keys (lightweight association)
    - All operations wrapped in a single atomic transaction
"""

from django.core.management.base import BaseCommand
from django.db import transaction
import random
from decimal import Decimal

from apps.transactions.models.projects import Project
from apps.transactions.models.line_variants import Order
from apps.transactions.services.project_seeding import create_sample_projects


class Command(BaseCommand):
    help = "Seed Project records with optional task backlogs."

    def add_arguments(self, parser):  # pragma: no cover - simple CLI wiring
        parser.add_argument('--projects', type=int, default=3, help='Number of projects to create (default 3).')
        parser.add_argument('--tasks-min', type=int, default=0, help='Minimum tasks per project (default 0).')
        parser.add_argument('--tasks-max', type=int, default=5, help='Maximum tasks per project (default 5).')
        parser.add_argument('--done-fraction', type=float, default=0.3, help='Approx fraction of tasks pre-marked done (0-1).')
        parser.add_argument('--force', action='store_true', help='Create even if a similar intent exists.')
        parser.add_argument('--simulate-profit', action='store_true', help='Populate random profit & velocity.')
        parser.add_argument('--link-orders', type=int, default=0, help='Link up to N random existing orders via refs.related_ids.')

    def handle(self, *args, **opts):
        count = max(1, opts['projects'])
        tasks_min = max(0, opts['tasks_min'])
        tasks_max = max(tasks_min, opts['tasks_max'])
        done_fraction = min(1.0, max(0.0, opts['done_fraction']))
        force = opts['force']

        with transaction.atomic():
            new_projects = create_sample_projects(
                number=count,
                tasks_min=tasks_min,
                tasks_max=tasks_max,
                done_fraction=done_fraction,
                force=force,
            )

            if opts['simulate_profit'] and new_projects:
                for p in new_projects:
                    # profit between 5k and 250k; velocity rough daily delta
                    profit_val = Decimal(random.randint(5_000, 250_000)) / Decimal('1')
                    p.profit = profit_val
                    p.profit_velocity = random.randint(50, 1500)
                    p.save(update_fields=['profit', 'profit_velocity'])

            link_orders_n = max(0, opts.get('link_orders') or 0)
            if link_orders_n and new_projects:
                order_ids = list(Order.objects.order_by('?').values_list('id', flat=True)[:link_orders_n])
                if order_ids:
                    for p in new_projects:
                        refs = getattr(p, 'refs', {}) or {}
                        rel = refs.setdefault('related_ids', [])
                        # merge without duplicates
                        for oid in order_ids:
                            if oid not in rel:
                                rel.append(oid)
                        p.refs = refs
                        p.save(update_fields=['refs'])

        skipped = count - len(new_projects)
        self.stdout.write(self.style.SUCCESS(
            f"Created {len(new_projects)} projects (skipped {skipped} duplicate intents)."
        ))