"""Service / domain helpers for BillOfMaterial operations.

These functions encapsulate non-trivial logic (validation orchestration, roll-ups, filtering) so views remain thin.
"""
from __future__ import annotations

from datetime import date
from typing import Iterable
from django.db import transaction
from django.db.models import Q
from apps.products.models.bill_of_material import BillOfMaterial


def list_bom_lines(parent_id: int, *, as_of: date | None = None, revision: str | None = None) -> Iterable[BillOfMaterial]:
    """Return BOM lines for a parent filtered by optional effective window and revision."""
    qs = BillOfMaterial.objects.filter(parent_id=parent_id)
    if revision is not None:
        qs = qs.filter(revision=revision)
    if as_of:
        qs = qs.filter(
            (Q(effective_from__isnull=True) | Q(effective_from__lte=as_of)) &
            (Q(effective_to__isnull=True) | Q(effective_to__gte=as_of))
        )
    return qs.order_by('sequence', 'id')


@transaction.atomic
def create_bom_line(**data) -> BillOfMaterial:
    line = BillOfMaterial(**data)
    line.full_clean()
    line.save()
    return line


@transaction.atomic
def update_bom_line(line: BillOfMaterial, **data) -> BillOfMaterial:
    for k, v in data.items():
        setattr(line, k, v)
    line.full_clean()
    line.save()
    return line


@transaction.atomic
def delete_bom_line(line: BillOfMaterial) -> None:
    line.delete()


def recalc_parent_cost(parent_id: int) -> None:
    BillOfMaterial.recalc_parent_cost(parent_id)

__all__ = [
    'list_bom_lines', 'create_bom_line', 'update_bom_line', 'delete_bom_line', 'recalc_parent_cost'
]
