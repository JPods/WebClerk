"""Register a new WC3 installation with WCHQ.

Two endpoints:
    POST /wcapi/register/           — register installation, create Contact + Customer
    POST /wcapi/register/subscribe/ — choose subscription tier + payment

Registration creates:
    On WCHQ: Contact, Customer (OrgBase), Connection (with Athena token)
    Returns: Athena token for all subsequent WCHQ communication

No authentication required for initial registration — the Athena token
IS the authentication for all subsequent WCHQ communication.
"""
import hashlib
import json
import logging
import secrets
import uuid
from datetime import datetime, timezone

from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

# Pricing: $14 per 5 staff users per month. Alice counts is_staff.
# Community (free) = run your own Ollama, no cloud.
# Subscribed = Alice cloud + support channel, priced by staff count.
PRICE_PER_5_USERS = 1400  # cents


def calculate_monthly_price(staff_count: int) -> int:
    """$14 per 5 staff users, rounded up. Minimum 1 block."""
    if staff_count <= 0:
        return 0
    import math
    blocks = math.ceil(staff_count / 5)
    return blocks * PRICE_PER_5_USERS


def get_staff_count() -> int:
    """Count active staff users in the local database."""
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.filter(is_staff=True, is_active=True).count()
    except Exception:
        return 0


def _generate_athena_token(installation_id: str) -> str:
    """Generate a unique Athena token for an installation."""
    raw = f"{installation_id}:{secrets.token_hex(32)}:{datetime.now(timezone.utc).isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()


@method_decorator(csrf_exempt, name='dispatch')
class RegisterInstallationView(View):
    """POST /wcapi/register/ — register a new installation.

    Body: {
        "installation_id": "uuid",
        "contact": {"name_first": "", "name_last": "", "email": ""},
        "company": {"name": "", "industry": "", "website": ""},
        "onboarding": {"goals": [], "pain_points": [], "data_sources": []},
        "tier": "community"
    }

    Creates Contact + Customer + Connection on WCHQ.
    Returns the Athena token.
    """

    def post(self, request):
        try:
            body = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        installation_id = body.get('installation_id', '')
        if not installation_id:
            return JsonResponse({'error': 'installation_id required'}, status=400)

        contact_data = body.get('contact', {})
        company_data = body.get('company', {})
        onboarding = body.get('onboarding', {})
        subscribed = body.get('subscribed', False)  # True = Alice cloud + support
        staff_count = body.get('staff_count', 0)
        price_monthly = calculate_monthly_price(staff_count) if subscribed else 0

        email = contact_data.get('email', '').strip()
        if not email:
            return JsonResponse({'error': 'contact.email required'}, status=400)

        # Generate Athena token
        athena_token = _generate_athena_token(installation_id)
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        now_ms = int(now.timestamp() * 1000)

        result = {
            'installation_id': installation_id,
            'token': athena_token,
            'dt_registered': now_iso,
            'subscribed': subscribed,
            'staff_count': staff_count,
            'price_monthly': price_monthly,
            'status': 'registered',
        }

        try:
            from apps.core.models import Contact
            from apps.orgs.models import OrgBase
            from apps.sync.models import Connection

            # Create Contact
            contact = Contact.objects.create(
                uuid=uuid.uuid4(),
                ida=f'wchq-{installation_id[:8]}',
                name_first=contact_data.get('name_first', ''),
                name_last=contact_data.get('name_last', ''),
                status='active',
                purpose='wchq_registration',
                config={
                    'installation_id': installation_id,
                    'onboarding': onboarding,
                },
                metadata={
                    'history': {
                        'created': {'dt': now_ms, 'source': 'wchq_registration'},
                    },
                    'wchq': {
                        'subscribed': subscribed,
                        'staff_count': staff_count,
                        'price_monthly': price_monthly,
                        'dt_registered': now_iso,
                    },
                },
            )
            result['contact_id'] = contact.id

            # Create email record if model supports it
            try:
                from apps.communications.models import Email
                Email.objects.create(
                    contact=contact,
                    address=email,
                    purpose='primary',
                    is_active=True,
                )
            except Exception:
                # Store email in contact config if comm model not available
                contact.config['email'] = email
                contact.save(update_fields=['config'])

            # Create Customer (OrgBase)
            company_name = company_data.get('name', '') or f"{contact_data.get('name_first', '')} {contact_data.get('name_last', '')}".strip()
            customer = OrgBase.objects.create(
                uuid=uuid.uuid4(),
                ida=f'wchq-cust-{installation_id[:8]}',
                company=company_name,
                role='customer',
                status='active',
                contact=contact,
                config={
                    'installation_id': installation_id,
                    'industry': company_data.get('industry', ''),
                    'website': company_data.get('website', ''),
                    'subscription': {
                        'subscribed': subscribed,
                        'staff_count': staff_count,
                        'dt_started': now_iso,
                        'price_monthly': price_monthly,
                    },
                },
                metadata={
                    'history': {
                        'created': {'dt': now_ms, 'source': 'wchq_registration'},
                    },
                },
            )
            result['customer_id'] = customer.id

            # Create Connection (Athena token link)
            connection = Connection.objects.create(
                uuid=uuid.uuid4(),
                ida=f'wchq-conn-{installation_id[:8]}',
                name=f"WCHQ: {company_name}",
                type='wchq_installation',
                status='active',
                config={
                    'installation_id': installation_id,
                    'athena_token': athena_token,
                    'subscribed': subscribed,
                    'staff_count': staff_count,
                    'price_monthly': price_monthly,
                    'dt_registered': now_iso,
                    'contact_id': contact.id,
                    'customer_id': customer.id,
                },
            )
            result['connection_id'] = connection.id

            logger.info(
                "[WCHQ] Registration complete: %s company=%s subscribed=%s staff=%d price=$%.2f contact=%d customer=%d",
                installation_id[:12], company_name, subscribed, staff_count,
                price_monthly / 100, contact.id, customer.id,
            )

        except Exception as e:
            logger.exception("[WCHQ] Registration record creation failed")
            result['warning'] = f'Token issued but record creation failed: {e}'

        return JsonResponse(result, status=201)


@method_decorator(csrf_exempt, name='dispatch')
class SubscriptionView(View):
    """POST /wcapi/register/subscribe/ — update subscription.

    Body: {
        "athena_token": "...",
        "subscribed": true,
        "donation_amount": 0
    }

    Alice reports staff_count automatically. WCHQ calculates price.
    Authenticated by Athena token. Updates the Connection and Customer.
    """

    def post(self, request):
        try:
            body = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        athena_token = body.get('athena_token', '').strip()
        if not athena_token:
            return JsonResponse({'error': 'athena_token required'}, status=401)

        subscribed = body.get('subscribed', False)
        staff_count = body.get('staff_count', 0)
        donation_amount = body.get('donation_amount', 0)
        price_monthly = calculate_monthly_price(staff_count) if subscribed else 0

        try:
            from apps.sync.models import Connection
            from apps.orgs.models import OrgBase

            conn = Connection.objects.filter(
                type='wchq_installation',
                config__athena_token=athena_token,
                is_active=True,
            ).first()

            if not conn:
                return JsonResponse({'error': 'Invalid Athena token'}, status=401)

            now_iso = datetime.now(timezone.utc).isoformat()

            # Update Connection
            config = conn.config or {}
            old_subscribed = config.get('subscribed', False)
            old_staff = config.get('staff_count', 0)
            config['subscribed'] = subscribed
            config['staff_count'] = staff_count
            config['price_monthly'] = price_monthly
            config['dt_updated'] = now_iso
            config['history'] = config.get('history', [])
            config['history'].append({
                'subscribed': subscribed,
                'staff_count': staff_count,
                'price_monthly': price_monthly,
                'dt': now_iso,
            })
            conn.config = config
            conn.save(update_fields=['config'])

            # Update Customer
            customer_id = config.get('customer_id')
            if customer_id:
                try:
                    customer = OrgBase.objects.get(pk=customer_id)
                    cust_config = customer.config or {}
                    cust_config['subscription'] = {
                        'subscribed': subscribed,
                        'staff_count': staff_count,
                        'dt_updated': now_iso,
                        'price_monthly': price_monthly,
                    }
                    customer.config = cust_config
                    customer.save(update_fields=['config'])
                except OrgBase.DoesNotExist:
                    pass

            # Handle donation
            if donation_amount and donation_amount > 0:
                try:
                    from apps.transactions.models import Payment
                    Payment.objects.create(
                        contact_id=config.get('contact_id', 0),
                        amount=donation_amount,
                        gateway='donation',
                        status='completed',
                        config={
                            'type': 'donation',
                            'installation_id': config.get('installation_id', ''),
                            'dt': now_iso,
                        },
                    )
                except Exception as e:
                    logger.warning("[WCHQ] Donation record failed: %s", e)

            logger.info(
                "[WCHQ] Subscription updated: subscribed=%s staff=%d price=$%.2f (installation=%s)",
                subscribed, staff_count, price_monthly / 100,
                config.get('installation_id', '?')[:12],
            )

            return JsonResponse({
                'status': 'ok',
                'subscribed': subscribed,
                'staff_count': staff_count,
                'price_monthly': price_monthly,
                'price_display': f"${price_monthly / 100:.2f}/mo",
                'dt_changed': now_iso,
            })

        except Exception as e:
            logger.exception("[WCHQ] Subscription change failed")
            return JsonResponse({'error': str(e)}, status=500)
