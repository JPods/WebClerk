"""Dual pricing / cash discount service.

Computes two payment options for any transaction:
  - Cash total: the base price (what's already in totals.total)
  - Card total: base price + card surcharge

The surcharge is computed from the installation-level DualPricingConfig
Setting. No invoice lines are added or removed — this is a presentation
and payment-processing concern, not a line-level concern.

Legal basis: cash discount programs are legal in all 50 US states under
the Durbin Amendment (Dodd-Frank 2010). Frame as "save X% with cash/ACH",
not "card fee of X%". Debit cards cannot be surcharged (card brand rule).

See: common/schemas/payment.py — DualPricingConfig, DualPricingProjection
"""
import logging
from decimal import Decimal
from typing import Optional

from common.decimals import safe_decimal as _d

logger = logging.getLogger(__name__)


def _load_config() -> Optional[dict]:
    """Load the dual pricing config from Setting."""
    from apps.core.models import Setting
    try:
        setting = Setting.objects.get(
            purpose='wc:dual_pricing',
            is_active=True,
        )
        return setting.config or {}
    except Setting.DoesNotExist:
        return None


def get_dual_pricing_config() -> dict:
    """Return the validated dual pricing config, or disabled defaults."""
    raw = _load_config()
    if not raw:
        return {'enabled': False}
    from apps.transactions.models.payment_pydantic import DualPricingConfig
    validated = DualPricingConfig(**raw)
    return validated.model_dump()


def compute_dual_pricing(transaction_totals: dict) -> dict:
    """Compute cash and card totals for a transaction.

    Args:
        transaction_totals: the header.totals dict (TransactionTotals schema)

    Returns:
        DualPricingProjection as dict:
          enabled, cash_total, card_total, card_rate,
          adjustment_amount, disclosure_text
    """
    config = get_dual_pricing_config()
    if not config.get('enabled'):
        total = float(transaction_totals.get('total', 0))
        return {
            'enabled': False,
            'cash_total': total,
            'card_total': total,
            'card_rate': 0.0,
            'adjustment_amount': 0.0,
            'disclosure_text': '',
        }

    card_rate = _d(config.get('card_rate', 3.5))
    apply_before_tax = config.get('apply_before_tax', True)

    if apply_before_tax:
        base_amount = _d(transaction_totals.get('subtotal', 0))
    else:
        base_amount = _d(transaction_totals.get('total', 0))

    adjustment = _d(base_amount * card_rate / 100)
    cash_total = _d(transaction_totals.get('total', 0))
    card_total = _d(cash_total + adjustment)

    disclosure = config.get('disclosure_text', '')
    disclosure = disclosure.replace('{rate}', f'{float(card_rate):.1f}')

    return {
        'enabled': True,
        'cash_total': float(cash_total),
        'card_total': float(card_total),
        'card_rate': float(card_rate),
        'adjustment_amount': float(adjustment),
        'disclosure_text': disclosure,
    }


def compute_for_transaction(transaction_id: int, model_name: str) -> dict:
    """Compute dual pricing for a specific transaction by ID.

    Loads the transaction, reads its totals, and computes the projection.
    """
    from apps.core.constants.model_registry import get_model_meta

    meta = get_model_meta(model_name)
    if not meta:
        raise ValueError(f"Unknown model: {model_name}")

    Model = meta.import_model()
    try:
        header = Model.objects.get(pk=transaction_id)
    except Model.DoesNotExist:
        raise ValueError(f"{model_name} #{transaction_id} not found")

    totals = getattr(header, 'totals', None) or {}
    return compute_dual_pricing(totals)


def is_exempt_method(method: str) -> bool:
    """Check if a payment method is exempt from surcharging (gets cash price).

    Exempt methods: cash, check, ACH, wire, debit.
    Matching is case-insensitive and checks if the method string
    contains any of the exempt keywords.
    """
    config = get_dual_pricing_config()
    if not config.get('enabled'):
        return False

    exempt = config.get('exempt_methods', [])
    method_lower = (method or '').lower()
    return any(ex.lower() in method_lower for ex in exempt)


def compute_payment_amount(
    transaction_totals: dict,
    payment_method: str,
) -> dict:
    """Determine the actual payment amount based on method.

    Returns:
        {
            'amount': float,         # what to charge
            'is_cash_price': bool,   # True if exempt method
            'surcharge': float,      # 0.0 if exempt
            'card_rate': float,
        }
    """
    projection = compute_dual_pricing(transaction_totals)
    if not projection['enabled']:
        return {
            'amount': projection['cash_total'],
            'is_cash_price': True,
            'surcharge': 0.0,
            'card_rate': 0.0,
        }

    if is_exempt_method(payment_method):
        return {
            'amount': projection['cash_total'],
            'is_cash_price': True,
            'surcharge': 0.0,
            'card_rate': projection['card_rate'],
        }

    return {
        'amount': projection['card_total'],
        'is_cash_price': False,
        'surcharge': projection['adjustment_amount'],
        'card_rate': projection['card_rate'],
    }
