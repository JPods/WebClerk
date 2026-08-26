"""Consolidated Decimal coercion — single source of truth.

Replaces 6 local copies of the same function across:
  - apps/transactions/services/totals.py (_d)
  - apps/transactions/services/transaction_save.py (_d)
  - apps/transactions/models/base_line_model.py (_to_decimal)
  - apps/accounts/services/tax_calculation.py (_d)
  - apps/ai_assistant/services/aggregate_tracker.py (_d)
  - apps/transactions/services/transfer_utils.py (_to_decimal_safe)
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any


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
