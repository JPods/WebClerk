"""Payment gateway integration via Spreedly.

Spreedly is a universal payment aggregator. One integration, 100+ gateways.
Users configure their own gateway (Stripe, PayPal, Braintree, etc.) in Settings.
WC3 talks to Spreedly; Spreedly talks to the gateway.

TOKEN RULE (established 2026-08-05):
  WC3 stores ONLY: gateway reference ID (pm_xxx), last4, brand, exp.
  NEVER: card number, CVV, full token, or anything replayable.
  The gateway's client-side SDK (iframe) collects card data.
  Our HTML/JS never touches card data. Token in a token.
"""

import logging
import requests
from decimal import Decimal
from django.utils import timezone

logger = logging.getLogger(__name__)


class SpreedlyService:
    """Universal payment gateway via Spreedly."""

    BASE = "https://core.spreedly.com/v1"

    def __init__(self, env_key: str, access_secret: str, gateway_token: str):
        self.env_key = env_key
        self.access_secret = access_secret
        self.gateway_token = gateway_token

    @classmethod
    def from_settings(cls):
        """Build from the payment_gateway Setting record."""
        from apps.core.models.setting import Setting
        try:
            setting = Setting.objects.get(purpose='wc:payment_gateway')
        except Setting.DoesNotExist:
            raise RuntimeError("No payment_gateway Setting found. Run: manage.py seed_payment_gateway")
        cfg = setting.config or {}
        spreedly = cfg.get('spreedly', {})
        env_key = spreedly.get('environment_key', '')
        access_secret = spreedly.get('access_secret', '')
        gateway_token = cfg.get('active_gateway_token', '')
        if not env_key or not access_secret:
            raise RuntimeError("Spreedly credentials not configured in payment_gateway Setting")
        if not gateway_token:
            raise RuntimeError("No active_gateway_token configured in payment_gateway Setting")
        return cls(env_key, access_secret, gateway_token)

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        """Make authenticated request to Spreedly API."""
        resp = requests.request(
            method,
            f"{self.BASE}{path}",
            auth=(self.env_key, self.access_secret),
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        data = resp.json()
        if resp.status_code >= 400:
            errors = data.get('errors', [])
            msg = errors[0].get('message', resp.text) if errors else resp.text
            logger.error(f"Spreedly {method} {path} → {resp.status_code}: {msg}")
            raise SpreedlyError(msg, status_code=resp.status_code, response=data)
        return data

    # ── Transactions ─────────────────────────────────────────────────

    def purchase(self, payment_method_token: str, amount_cents: int,
                 currency: str = "USD", order_id: str = "",
                 retain: bool = True) -> dict:
        """Authorize + capture in one step."""
        body = {
            "transaction": {
                "payment_method_token": payment_method_token,
                "amount": amount_cents,
                "currency_code": currency,
                "order_id": order_id,
                "retain_on_success": retain,
            }
        }
        return self._request("POST", f"/gateways/{self.gateway_token}/purchase.json", body)

    def authorize(self, payment_method_token: str, amount_cents: int,
                  currency: str = "USD", order_id: str = "",
                  retain: bool = True) -> dict:
        """Authorize only — capture later."""
        body = {
            "transaction": {
                "payment_method_token": payment_method_token,
                "amount": amount_cents,
                "currency_code": currency,
                "order_id": order_id,
                "retain_on_success": retain,
            }
        }
        return self._request("POST", f"/gateways/{self.gateway_token}/authorize.json", body)

    def capture(self, transaction_token: str, amount_cents: int | None = None) -> dict:
        """Capture a prior authorization. Omit amount for full capture."""
        body = {"transaction": {}}
        if amount_cents is not None:
            body["transaction"]["amount"] = amount_cents
        return self._request("POST", f"/transactions/{transaction_token}/capture.json", body)

    def void(self, transaction_token: str) -> dict:
        """Void a transaction before settlement."""
        return self._request("POST", f"/transactions/{transaction_token}/void.json")

    def credit(self, transaction_token: str, amount_cents: int | None = None) -> dict:
        """Refund after settlement. Omit amount for full refund."""
        body = {"transaction": {}}
        if amount_cents is not None:
            body["transaction"]["amount"] = amount_cents
        return self._request("POST", f"/transactions/{transaction_token}/credit.json", body)

    def refund(self, transaction_token: str, amount_cents: int | None = None) -> dict:
        """Try void first, fall back to credit."""
        try:
            return self.void(transaction_token)
        except SpreedlyError:
            return self.credit(transaction_token, amount_cents)

    # ── Gateway management ───────────────────────────────────────────

    def add_gateway(self, gateway_type: str, credentials: dict) -> dict:
        """Add a payment gateway (Stripe, PayPal, etc.)."""
        body = {"gateway": {"gateway_type": gateway_type, **credentials}}
        return self._request("POST", "/gateways.json", body)

    def list_gateways(self) -> dict:
        """List all configured gateways."""
        return self._request("GET", "/gateways.json")

    # ── Payment method info ──────────────────────────────────────────

    def get_payment_method(self, pm_token: str) -> dict:
        """Retrieve payment method details (never returns full card number)."""
        return self._request("GET", f"/payment_methods/{pm_token}.json")

    def retain_payment_method(self, pm_token: str) -> dict:
        """Retain (vault) a payment method for future use."""
        return self._request("PUT", f"/payment_methods/{pm_token}/retain.json")

    def redact_payment_method(self, pm_token: str) -> dict:
        """Permanently remove a payment method from the vault."""
        return self._request("PUT", f"/payment_methods/{pm_token}/redact.json")


class SpreedlyError(Exception):
    def __init__(self, message: str, status_code: int = 0, response: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response or {}


# ── Helper: process a WC3 Payment record ─────────────────────────────

def process_payment(payment_id: int, payment_method_token: str) -> dict:
    """Process a Payment record through Spreedly.

    Called from the payment UI after the client-side SDK returns a token.
    The token is a reference to a card vaulted in Spreedly — WC3 never saw
    the card number.

    Returns the Spreedly transaction result.
    """
    from apps.transactions.models import Payment

    payment = Payment.objects.get(pk=payment_id)
    svc = SpreedlyService.from_settings()

    amount_cents = int(payment.amount * 100)
    order_id = f"wc3-{payment.id}"

    payment.gateway = 'spreedly'
    payment.status = 'processing'
    payment.save(update_fields=['gateway', 'status'])

    try:
        result = svc.purchase(payment_method_token, amount_cents, order_id=order_id)
        txn = result.get('transaction', {})
        pm = txn.get('payment_method', {})

        payment.id_gateway_transaction = txn.get('token', '')
        payment.id_gateway_payment_intent = txn.get('gateway_transaction_id', '')
        payment.dt_processed = timezone.now()

        # Token-in-a-token: store only the reference, last4, brand
        payment.refs = payment.refs or {}
        payment.refs['card'] = {
            'pm_token': pm.get('token', ''),
            'last4': pm.get('last_four_digits', ''),
            'brand': pm.get('card_type', ''),
            'exp_month': pm.get('month', ''),
            'exp_year': pm.get('year', ''),
            'fingerprint': pm.get('fingerprint', ''),
        }

        if txn.get('succeeded'):
            payment.status = 'completed'
            payment.gateway_response = {
                'spreedly_token': txn.get('token', ''),
                'gateway_transaction_id': txn.get('gateway_transaction_id', ''),
                'message': txn.get('message', ''),
                'succeeded': True,
            }
            payment.add_audit_entry('gateway_payment_completed', {
                'gateway': 'spreedly',
                'transaction_token': txn.get('token', ''),
                'amount_cents': amount_cents,
            })
        else:
            payment.status = 'failed'
            payment.gateway_response = {
                'succeeded': False,
                'message': txn.get('message', 'Transaction failed'),
            }

        payment.save()
        logger.info(f"Payment {payment.id} processed via Spreedly: {payment.status}")
        return result

    except SpreedlyError as e:
        payment.status = 'failed'
        payment.gateway_response = {'succeeded': False, 'message': str(e)}
        payment.save(update_fields=['status', 'gateway_response'])
        logger.error(f"Payment {payment.id} failed via Spreedly: {e}")
        raise


def refund_payment(payment_id: int, amount_cents: int | None = None) -> dict:
    """Refund a completed Payment through Spreedly.

    Tries void first (pre-settlement), falls back to credit (post-settlement).
    """
    from apps.transactions.models import Payment

    payment = Payment.objects.get(pk=payment_id)
    if not payment.id_gateway_transaction:
        raise ValueError("Payment has no gateway transaction to refund")

    svc = SpreedlyService.from_settings()
    result = svc.refund(payment.id_gateway_transaction, amount_cents)

    txn = result.get('transaction', {})
    if txn.get('succeeded'):
        if amount_cents and amount_cents < int(payment.amount * 100):
            payment.status = 'partially_refunded'
        else:
            payment.status = 'refunded'
        payment.add_audit_entry('gateway_refund', {
            'refund_token': txn.get('token', ''),
            'amount_cents': amount_cents or int(payment.amount * 100),
        })
    else:
        payment.add_audit_entry('gateway_refund_failed', {
            'message': txn.get('message', ''),
        })

    payment.save()
    logger.info(f"Payment {payment.id} refund: {payment.status}")
    return result
