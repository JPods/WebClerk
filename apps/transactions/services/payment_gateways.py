import logging
import stripe
from paypalrestsdk import Payment as PayPalPayment
import paypalrestsdk
from django.conf import settings
from django.utils import timezone
from apps.transactions.models import Payment

logger = logging.getLogger(__name__)


class StripeService:
    """Service for handling Stripe payment processing"""

    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    def create_payment_intent(self, payment_obj):
        """Create a Stripe payment intent for the payment"""
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(payment_obj.amount * 100),  # Convert to cents
                currency=settings.PAYMENT_CURRENCY.lower(),
                metadata={
                    'payment_id': payment_obj.id,
                    'invoice_id': payment_obj.invoice_id,
                    'contact_id': payment_obj.contact_id,
                },
                description=f"Payment for Invoice #{payment_obj.invoice_id}",
                receipt_email=payment_obj.contact.email if hasattr(payment_obj.contact, 'email') else None,
            )

            payment_obj.gateway_payment_intent_id = intent.id
            payment_obj.gateway_transaction_id = intent.id
            payment_obj.status = 'processing'
            payment_obj.gateway_response = intent
            payment_obj.save()

            logger.info(f"Created Stripe payment intent {intent.id} for payment {payment_obj.id}")
            return intent

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {e}")
            payment_obj.mark_as_failed(str(e))
            raise

    def confirm_payment_intent(self, payment_intent_id):
        """Confirm a payment intent"""
        try:
            intent = stripe.PaymentIntent.confirm(payment_intent_id)
            return intent
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error confirming payment intent: {e}")
            raise

    def handle_webhook(self, payload, sig_header):
        """Handle Stripe webhook events"""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
        except ValueError as e:
            logger.error(f"Invalid Stripe webhook payload: {e}")
            raise ValueError("Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid Stripe webhook signature: {e}")
            raise ValueError("Invalid signature")

        # Handle the event
        if event.type == 'payment_intent.succeeded':
            payment_intent = event.data.object
            self._handle_payment_succeeded(payment_intent)
        elif event.type == 'payment_intent.payment_failed':
            payment_intent = event.data.object
            self._handle_payment_failed(payment_intent)
        elif event.type == 'payment_intent.canceled':
            payment_intent = event.data.object
            self._handle_payment_cancelled(payment_intent)

        return event

    def _handle_payment_succeeded(self, payment_intent):
        """Handle successful payment"""
        try:
            payment = Payment.objects.get(gateway_payment_intent_id=payment_intent.id)
            payment.status = 'completed'
            payment.processed_at = timezone.now()
            payment.gateway_response = payment_intent
            payment.fee_amount = (payment_intent.amount - payment_intent.amount_received) / 100  # Convert from cents
            payment.save()

            logger.info(f"Payment {payment.id} marked as completed via Stripe webhook")
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for Stripe payment intent {payment_intent.id}")

    def _handle_payment_failed(self, payment_intent):
        """Handle failed payment"""
        try:
            payment = Payment.objects.get(gateway_payment_intent_id=payment_intent.id)
            payment.mark_as_failed(payment_intent.last_payment_error.message if payment_intent.last_payment_error else "Payment failed")
            payment.gateway_response = payment_intent
            payment.save()

            logger.info(f"Payment {payment.id} marked as failed via Stripe webhook")
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for Stripe payment intent {payment_intent.id}")

    def _handle_payment_cancelled(self, payment_intent):
        """Handle cancelled payment"""
        try:
            payment = Payment.objects.get(gateway_payment_intent_id=payment_intent.id)
            payment.status = 'cancelled'
            payment.gateway_response = payment_intent
            payment.save()

            logger.info(f"Payment {payment.id} marked as cancelled via Stripe webhook")
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for Stripe payment intent {payment_intent.id}")


class PayPalService:
    """Service for handling PayPal payment processing"""

    def __init__(self):
        paypalrestsdk.configure({
            "mode": settings.PAYPAL_ENVIRONMENT,
            "client_id": settings.PAYPAL_CLIENT_ID,
            "client_secret": settings.PAYPAL_CLIENT_SECRET
        })

    def create_payment(self, payment_obj, return_url=None, cancel_url=None):
        """Create a PayPal payment"""
        try:
            paypal_payment = PayPalPayment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "redirect_urls": {
                    "return_url": return_url or settings.PAYMENT_SUCCESS_URL,
                    "cancel_url": cancel_url or settings.PAYMENT_CANCEL_URL
                },
                "transactions": [{
                    "amount": {
                        "total": str(payment_obj.amount),
                        "currency": settings.PAYMENT_CURRENCY
                    },
                    "description": f"Payment for Invoice #{payment_obj.invoice_id}",
                    "invoice_number": str(payment_obj.invoice_id)
                }]
            })

            if paypal_payment.create():
                payment_obj.gateway_transaction_id = paypal_payment.id
                payment_obj.status = 'processing'
                payment_obj.gateway_response = paypal_payment.to_dict()
                payment_obj.save()

                logger.info(f"Created PayPal payment {paypal_payment.id} for payment {payment_obj.id}")
                return paypal_payment
            else:
                error_msg = paypal_payment.error
                logger.error(f"PayPal payment creation failed: {error_msg}")
                payment_obj.mark_as_failed(str(error_msg))
                raise Exception(f"PayPal payment creation failed: {error_msg}")

        except Exception as e:
            logger.error(f"PayPal error creating payment: {e}")
            payment_obj.mark_as_failed(str(e))
            raise

    def execute_payment(self, payment_id, payer_id):
        """Execute a PayPal payment"""
        try:
            paypal_payment = PayPalPayment.find(payment_id)
            if paypal_payment.execute({"payer_id": payer_id}):
                # Update payment record
                payment = Payment.objects.get(gateway_transaction_id=payment_id)
                payment.status = 'completed'
                payment.processed_at = timezone.now()
                payment.gateway_response = paypal_payment.to_dict()

                # Calculate fee (PayPal typically takes 2.9% + $0.30)
                fee_rate = 0.029
                fixed_fee = 0.30
                payment.fee_amount = (payment.amount * fee_rate) + fixed_fee
                payment.save()

                logger.info(f"Executed PayPal payment {payment_id} for payment {payment.id}")
                return paypal_payment
            else:
                error_msg = paypal_payment.error
                logger.error(f"PayPal payment execution failed: {error_msg}")
                payment = Payment.objects.get(gateway_transaction_id=payment_id)
                payment.mark_as_failed(str(error_msg))
                raise Exception(f"PayPal payment execution failed: {error_msg}")

        except Exception as e:
            logger.error(f"PayPal error executing payment: {e}")
            raise

    def handle_webhook(self, webhook_data):
        """Handle PayPal webhook events"""
        try:
            event_type = webhook_data.get('event_type')
            resource = webhook_data.get('resource', {})

            if event_type == 'PAYMENT.SALE.COMPLETED':
                self._handle_paypal_payment_completed(resource)
            elif event_type == 'PAYMENT.SALE.DENIED':
                self._handle_paypal_payment_failed(resource)
            elif event_type == 'PAYMENT.SALE.REFUNDED':
                self._handle_paypal_payment_refunded(resource)

            logger.info(f"Processed PayPal webhook event: {event_type}")
            return True

        except Exception as e:
            logger.error(f"Error handling PayPal webhook: {e}")
            raise

    def _handle_paypal_payment_completed(self, resource):
        """Handle PayPal payment completed"""
        try:
            paypal_payment_id = resource.get('parent_payment')
            payment = Payment.objects.get(gateway_transaction_id=paypal_payment_id)
            payment.status = 'completed'
            payment.processed_at = timezone.now()
            payment.gateway_response = resource
            payment.save()

            logger.info(f"Payment {payment.id} marked as completed via PayPal webhook")
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for PayPal payment {paypal_payment_id}")

    def _handle_paypal_payment_failed(self, resource):
        """Handle PayPal payment failed"""
        try:
            paypal_payment_id = resource.get('parent_payment')
            payment = Payment.objects.get(gateway_transaction_id=paypal_payment_id)
            payment.mark_as_failed("PayPal payment denied")
            payment.gateway_response = resource
            payment.save()

            logger.info(f"Payment {payment.id} marked as failed via PayPal webhook")
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for PayPal payment {paypal_payment_id}")

    def _handle_paypal_payment_refunded(self, resource):
        """Handle PayPal payment refunded"""
        try:
            paypal_payment_id = resource.get('parent_payment')
            payment = Payment.objects.get(gateway_transaction_id=paypal_payment_id)
            payment.status = 'refunded'
            payment.gateway_response = resource
            payment.save()

            logger.info(f"Payment {payment.id} marked as refunded via PayPal webhook")
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for PayPal payment {paypal_payment_id}")


class PaymentReconciliationService:
    """Service for reconciling payments with gateway statements"""

    def reconcile_payments(self, start_date=None, end_date=None):
        """Reconcile payments within date range"""
        from django.db.models import Q

        query = Q(status='completed', reconciled=False)
        if start_date:
            query &= Q(processed_at__gte=start_date)
        if end_date:
            query &= Q(processed_at__lte=end_date)

        payments = Payment.objects.filter(query)

        reconciled_count = 0
        for payment in payments:
            try:
                if self._verify_payment_with_gateway(payment):
                    payment.reconcile()
                    reconciled_count += 1
                    logger.info(f"Reconciled payment {payment.id}")
                else:
                    logger.warning(f"Payment {payment.id} could not be verified with gateway")
            except Exception as e:
                logger.error(f"Error reconciling payment {payment.id}: {e}")

        return reconciled_count

    def _verify_payment_with_gateway(self, payment):
        """Verify payment exists and matches gateway records"""
        if payment.gateway == 'stripe':
            return self._verify_stripe_payment(payment)
        elif payment.gateway == 'paypal':
            return self._verify_paypal_payment(payment)
        else:
            # Manual payments are assumed reconciled
            return True

    def _verify_stripe_payment(self, payment):
        """Verify payment with Stripe"""
        try:
            intent = stripe.PaymentIntent.retrieve(payment.gateway_payment_intent_id)
            return intent.status == 'succeeded' and intent.amount == int(payment.amount * 100)
        except stripe.error.StripeError:
            return False

    def _verify_paypal_payment(self, payment):
        """Verify payment with PayPal"""
        try:
            paypal_payment = PayPalPayment.find(payment.gateway_transaction_id)
            return paypal_payment.state == 'approved'
        except Exception:
            return False