"""Exchange Rate Service — Setting-based currency conversion.

All transactions operate in base currency (like all datetimes are UTC).
Exchange rates live in a single Setting record (purpose='exchange_rates').
When printing or sharing with a trading partner, the rate captured at
transaction time is applied. At settlement, the difference between the
captured rate and the current bank rate creates a balancing payment
record journalized to an FX gain/loss GL account.

Setting config structure:
    {
        "base_currency": "USD",
        "precision_convert": 4,
        "precision_display": 2,
        "rates": {
            "EUR": {"rate": 0.92, "dt_updated": 1723334400000},
            "GBP": {"rate": 0.79, "dt_updated": 1723334400000},
            "CAD": {"rate": 1.36, "dt_updated": 1723334400000}
        },
        "dt_updated": 1723334400000,
        "source": "manual"
    }

Usage:
    from apps.accounts.services.exchange_rates import (
        get_rate, convert, capture_rate, settle_fx_difference,
    )

    rate = get_rate('EUR')                     # current rate
    foreign = convert(100.00, 'EUR')           # USD → EUR
    base = convert(92.00, 'EUR', to_base=True) # EUR → USD
    capture_rate('EUR', invoice)               # stamp rate on transaction
"""
from __future__ import annotations

import logging
import time
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from django.apps import apps

logger = logging.getLogger(__name__)

_SETTING_PURPOSE = 'exchange_rates'
_SETTING_PARENT = 'setting'


def _now_ms() -> int:
    return int(time.time() * 1000)


def _get_config() -> dict:
    """Load the exchange rates Setting config."""
    Setting = apps.get_model('core', 'Setting')
    setting = Setting.objects.filter(
        purpose=_SETTING_PURPOSE, parent_model=_SETTING_PARENT, is_active=True,
    ).first()
    if not setting or not setting.config:
        return {'base_currency': 'USD', 'rates': {}, 'precision_convert': 4, 'precision_display': 2}
    return setting.config


def _save_config(config: dict):
    """Save updated config back to the Setting record."""
    Setting = apps.get_model('core', 'Setting')
    Setting.objects.filter(
        purpose=_SETTING_PURPOSE, parent_model=_SETTING_PARENT,
    ).update(config=config)


def get_base_currency() -> str:
    """Return the base currency code."""
    return _get_config().get('base_currency', 'USD')


def get_rate(currency_code: str) -> Optional[Decimal]:
    """Get the current exchange rate for a currency (base → foreign).

    Returns None if the currency is not configured.
    Returns Decimal('1') if currency matches base.
    """
    config = _get_config()
    if currency_code == config.get('base_currency', 'USD'):
        return Decimal('1')
    entry = config.get('rates', {}).get(currency_code.upper())
    if not entry:
        return None
    return Decimal(str(entry.get('rate', 1)))


def get_precision() -> tuple[int, int]:
    """Return (precision_convert, precision_display)."""
    config = _get_config()
    return config.get('precision_convert', 4), config.get('precision_display', 2)


def convert(
    amount: float,
    currency_code: str,
    to_base: bool = False,
    rate_override: Optional[float] = None,
) -> Decimal:
    """Convert between base currency and foreign currency.

    Args:
        amount: amount to convert
        currency_code: the foreign currency
        to_base: if True, convert foreign → base; if False, base → foreign
        rate_override: use this rate instead of the current Setting rate

    Returns:
        Converted amount as Decimal, rounded to conversion precision.
    """
    if rate_override is not None:
        rate = Decimal(str(rate_override))
    else:
        rate = get_rate(currency_code)
        if rate is None:
            logger.warning('No exchange rate for %s — returning amount unchanged', currency_code)
            return Decimal(str(amount))

    if rate == 0:
        return Decimal(str(amount))

    prec_convert, _ = get_precision()
    quantizer = Decimal(10) ** -prec_convert

    amt = Decimal(str(amount))
    if to_base:
        result = amt / rate
    else:
        result = amt * rate

    return result.quantize(quantizer, rounding=ROUND_HALF_UP)


def format_display(amount: Decimal, currency_code: str = '') -> str:
    """Format an amount for display with the display precision."""
    _, prec_display = get_precision()
    quantizer = Decimal(10) ** -prec_display
    formatted = amount.quantize(quantizer, rounding=ROUND_HALF_UP)
    if currency_code:
        return f'{currency_code} {formatted}'
    return str(formatted)


def set_rate(currency_code: str, rate: float, source: str = 'manual'):
    """Set or update an exchange rate.

    Args:
        currency_code: 3-letter currency code
        rate: rate to convert base → this currency
        source: 'manual', 'api', connection name
    """
    config = _get_config()
    rates = config.get('rates', {})
    rates[currency_code.upper()] = {
        'rate': rate,
        'dt_updated': _now_ms(),
        'source': source,
    }
    config['rates'] = rates
    config['dt_updated'] = _now_ms()
    config['source'] = source
    _save_config(config)
    logger.info('Exchange rate set: %s = %s (source: %s)', currency_code, rate, source)


def capture_rate(currency_code: str, transaction) -> Optional[float]:
    """Stamp the current exchange rate onto a transaction.

    Stores in transaction.sell or transaction.cost envelope as
    'exchange_rate' and 'exchange_currency'. Call this when creating
    an order/invoice for a foreign-currency customer.

    Args:
        currency_code: the customer's currency
        transaction: Order, Invoice, etc.

    Returns:
        The captured rate as float, or None if no rate found.
    """
    rate = get_rate(currency_code)
    if rate is None:
        return None

    rate_float = float(rate)

    # Stamp on sell envelope
    sell = getattr(transaction, 'sell', None) or {}
    if isinstance(sell, dict):
        sell['exchange_rate'] = rate_float
        sell['exchange_currency'] = currency_code
        sell['exchange_dt'] = _now_ms()
        transaction.sell = sell
        transaction.save(update_fields=['sell', 'dt_modified', 'version'])

    return rate_float


def settle_fx_difference(
    invoice_id: int,
    payment_id: int,
) -> dict:
    """Create a balancing payment record for FX gain/loss at settlement.

    When payment is received, the difference between the rate captured
    on the invoice and the current bank rate creates a gain or loss.
    This is journalized to the FX gain/loss GL account.

    Args:
        invoice_id: Invoice PK (has captured rate in sell envelope)
        payment_id: Payment PK (just received)

    Returns:
        {fx_amount, direction, payment_id} or {error}
    """
    Invoice = apps.get_model('transactions', 'Invoice')
    Payment = apps.get_model('transactions', 'Payment')

    try:
        invoice = Invoice.objects.get(pk=invoice_id)
    except Invoice.DoesNotExist:
        return {'error': f'Invoice {invoice_id} not found'}

    try:
        payment = Payment.objects.get(pk=payment_id)
    except Payment.DoesNotExist:
        return {'error': f'Payment {payment_id} not found'}

    sell = invoice.sell or {}
    captured_rate = sell.get('exchange_rate')
    currency = sell.get('exchange_currency')

    if not captured_rate or not currency:
        return {'fx_amount': 0, 'direction': 'none', 'message': 'No exchange rate on invoice'}

    current_rate = get_rate(currency)
    if current_rate is None:
        return {'error': f'No current rate for {currency}'}

    captured = Decimal(str(captured_rate))
    current = Decimal(str(float(current_rate)))

    if captured == current:
        return {'fx_amount': 0, 'direction': 'none', 'message': 'Rates unchanged'}

    # FX difference on the invoice total
    invoice_total = Decimal(str(sell.get('total', 0) or 0))
    if invoice_total <= 0:
        return {'fx_amount': 0, 'direction': 'none'}

    # Amount in base currency at captured rate vs current rate
    base_at_captured = invoice_total / captured if captured else invoice_total
    base_at_current = invoice_total / current if current else invoice_total
    fx_amount = (base_at_current - base_at_captured).quantize(Decimal('0.01'))

    if fx_amount == 0:
        return {'fx_amount': 0, 'direction': 'none'}

    direction = 'gain' if fx_amount > 0 else 'loss'

    # Create balancing payment record
    from apps.accounts.services.terms_ledger import record_payment
    from datetime import datetime, timezone as tz

    fx_payment = record_payment(
        invoice=invoice,
        amount=abs(fx_amount),
        dt_paid=datetime.now(tz.utc),
        payment=None,
        gl_account_id=None,
        source='FX',
    )

    # Mark it as FX adjustment
    if fx_payment:
        meta = fx_payment.refs or {}
        meta['fx'] = {
            'captured_rate': float(captured),
            'current_rate': float(current),
            'currency': currency,
            'direction': direction,
            'invoice_id': invoice_id,
            'payment_id': payment_id,
        }
        fx_payment.refs = meta
        fx_payment.save(update_fields=['refs'])

    logger.info(
        'FX settlement: invoice=%d %s %.2f (%s rate %.4f → %.4f)',
        invoice_id, direction, abs(fx_amount), currency, captured, current,
    )

    return {
        'fx_amount': float(fx_amount),
        'direction': direction,
        'fx_ledger_id': fx_payment.pk if fx_payment else None,
        'captured_rate': float(captured),
        'current_rate': float(current),
        'currency': currency,
    }
