"""Seed formal Project -> Transaction associations.

Creates association rows linking existing Projects to existing transactional
header models (Order, Proposal, etc.) up to requested counts per project.

Usage examples:
  python manage.py seed_project_links --per-project 3 --models order,proposal
  python manage.py seed_project_links --per-project 5 --randomize --models order,invoice

Behavior:
  - For each project, sample up to N objects from each selected model
  - Creates ProjectAssociation rows (skips existing duplicates)
  - Optional --randomize will shuffle and limit globally across all models
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
import random

from apps.transactions.models.projects import Project
from apps.transactions.models.project_links import ProjectAssociation, LINK_MODEL_CHOICES
from apps.transactions.models.line_variants import (
    Proposal,
    SalesOrder as Order,          # alias to maintain legacy model_code 'order'
    Invoice,
    PurchaseOrder as Purchase,    # alias to maintain legacy model_code 'purchase'
    Workorder,
    Requisition,
)

MODEL_MAP = {
    'proposal': Proposal,
    'order': Order,
    'invoice': Invoice,
    'purchase': Purchase,
    'workorder': Workorder,
    'requisition': Requisition,
}

class Command(BaseCommand):
    help = "Seed ProjectAssociation links between projects and transactional headers."

    def add_arguments(self, parser):  # pragma: no cover
        parser.add_argument('--per-project', type=int, default=2, help='Max links per model per project (default 2).')
        parser.add_argument('--models', type=str, default='order,proposal', help='Comma list of model codes to link.')
        parser.add_argument('--randomize', action='store_true', help='Randomize selection order per model.')

    def handle(self, *args, **opts):
        per = max(1, opts['per_project'])
        model_codes = [m.strip() for m in opts['models'].split(',') if m.strip()]
        invalid = [m for m in model_codes if m not in MODEL_MAP]
        if invalid:
            self.stdout.write(self.style.ERROR(f"Invalid model codes: {', '.join(invalid)}"))
            return
        randomize = opts['randomize']

        projects = list(Project.objects.all())
        if not projects:
            self.stdout.write(self.style.WARNING('No projects found. Run seed_projects first.'))
            return

        created = 0
        skipped = 0
        now_ms = int(timezone.now().timestamp() * 1000)

        with transaction.atomic():
            for proj in projects:
                for code in model_codes:
                    model = MODEL_MAP[code]
                    qs = model.objects.all().order_by('-id')
                    ids = list(qs.values_list('id', flat=True)[: per * 3])  # extra to allow shuffle/sample
                    if randomize:
                        random.shuffle(ids)
                    ids = ids[:per]
                    for oid in ids:
                        # idempotent create
                        obj, created_flag = ProjectAssociation.objects.get_or_create(
                            project=proj, model_code=code, object_id=oid,
                            defaults={'created_dt': now_ms}
                        )
                        if created_flag:
                            created += 1
                        else:
                            skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"Created {created} project association(s); skipped {skipped} existing."
        ))
