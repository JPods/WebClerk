"""Values a tree's parent rows take from their children — calculated on the server, so the screen
shows what the server calculates (Bill, 2026-11-01: "sum.cost by sub.components in a BOM").

Rows come depth-first with their level (each parent followed by its children), as every tree list
reads them. A child's own value may itself be rolled up from its children, so the walk runs from
the bottom: in reverse, the rows one level deeper seen since the last row at a parent's level are
exactly that parent's children.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Callable, Sequence, TypeVar

R = TypeVar('R')


def roll_up(rows: Sequence[R], level: Callable[[R], int], own: Callable[[R], Decimal],
            weight: Callable[[R], Decimal] = lambda _r: Decimal('1')) -> list[Decimal]:
    """Each row's rolled value: a row with children takes Σ weight(child) × rolled(child) over its
    direct children; a row without takes own(row). Weight is how many of the child one parent
    holds (a BOM line's quantity); 1 sums plainly."""
    rolled: list[Decimal] = [Decimal('0')] * len(rows)
    pending: dict[int, Decimal] = {}          # level → Σ of its rows seen since their parent
    for i in range(len(rows) - 1, -1, -1):
        lv = level(rows[i])
        below = pending.pop(lv + 1, None)
        rolled[i] = below if below is not None else own(rows[i])
        pending[lv] = pending.get(lv, Decimal('0')) + weight(rows[i]) * rolled[i]
    return rolled
