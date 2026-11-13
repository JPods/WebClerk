"""Consolidated Decimal coercion — single source of truth.

Replaces 5 local copies of the same function across:
  - apps/transactions/services/totals.py (_d)
  - apps/transactions/services/transaction_save.py (_d)
  - apps/transactions/models/base_line_model.py (_to_decimal)
  - apps/accounts/services/tax_calculation.py (_d)
  - apps/transactions/services/transfer_utils.py (_to_decimal_safe)

The rounding rule lives here too (Bill, 2026-11-12, readme 111): "up if half or more, down if
less than half". Python's Decimal defaults to half-even, so a bare ``.quantize(CENT)`` rounded
0.125 to 0.12 where the totals engine stored 0.13. Importing this module (settings.py does)
makes half-up the rule for every Decimal operation in the process: this thread's context and
the default every later thread starts from. ``money()`` is the explicit form for new code.
"""

import decimal
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

decimal.DefaultContext.rounding = ROUND_HALF_UP
decimal.getcontext().rounding = ROUND_HALF_UP

CENT = Decimal("0.01")


def safe_decimal(
    val: Any,
    places: int = 2,
    default: Decimal = Decimal("0"),
    rounding: str = ROUND_HALF_UP,
) -> Decimal:
    """Coerce any value to Decimal with optional quantization.

    Args:
        val:      Value to convert (None, str, int, float, Decimal).
        places:   Decimal places to quantize to.  Pass -1 to skip quantization.
        default:  Returned on None or conversion failure.
        rounding: Rounding mode (default ROUND_HALF_UP).

    Returns:
        Decimal — quantized result, or *default* on any error.
    """
    try:
        if val is None:
            return default
        d = Decimal(str(val))
        if places >= 0:
            return d.quantize(Decimal(10) ** -places, rounding=rounding)
        return d
    except Exception:
        return default


def money(val: Any) -> Decimal:
    """A money amount in cents, half-up. Raises on a value that is not a number."""
    return Decimal(str(val if val is not None else 0)).quantize(CENT, rounding=ROUND_HALF_UP)
