"""What a figure counts (Bill's standing rule): a record whose ida starts zz or qq is training
or disposable and is left out of every report, GL, dashboard and decision. One helper, so no
report carries its own copy of the rule.
"""
from __future__ import annotations

TRAINING_PREFIXES = ('zz', 'qq')


def tallied(qs):
    """`qs` without the training rows; a model with no ida has none."""
    if not any(f.name == 'ida' for f in qs.model._meta.concrete_fields):
        return qs
    for prefix in TRAINING_PREFIXES:
        qs = qs.exclude(ida__istartswith=prefix)
    return qs
