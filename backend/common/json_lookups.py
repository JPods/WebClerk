"""JSON path lookup helpers for PJPV queries.

Replace scalar shadow fields with Cast(KeyTextTransform(...)) expressions.
These work with PostgreSQL functional indexes on JSON paths.

Usage:
    from common.json_lookups import totals_total, totals_balance

    Invoice.objects.annotate(_total=totals_total()).filter(_total__gt=0)
    Invoice.objects.annotate(_bal=totals_balance()).aggregate(s=Sum('_bal'))
"""
from django.db.models import DecimalField
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast


def totals_total():
    """Annotation expression for totals->>'total' as Decimal."""
    return Cast(
        KeyTextTransform('total', 'totals'),
        output_field=DecimalField(max_digits=18, decimal_places=6),
    )


def totals_balance():
    """Annotation expression for totals->>'balance' as Decimal."""
    return Cast(
        KeyTextTransform('balance', 'totals'),
        output_field=DecimalField(max_digits=18, decimal_places=6),
    )


def totals_received():
    """Annotation expression for totals->>'received' as Decimal."""
    return Cast(
        KeyTextTransform('received', 'totals'),
        output_field=DecimalField(max_digits=18, decimal_places=6),
    )
