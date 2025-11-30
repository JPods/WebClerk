from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from typing import Optional, Dict, Any
from apps.core.models import Contact
from apps.transactions.models import Proposal, SalesOrder, Invoice, Payment


class TransactionEmailService:
    """Service for sending email notifications for transaction events."""

    @staticmethod
    def get_contact_email(contact_id: int) -> Optional[str]:
        """Get the primary email address for a contact."""
        try:
            contact = Contact.objects.get(id=contact_id)
            return contact.email
        except Contact.DoesNotExist:
            return None

    @staticmethod
    def get_recipient_emails(contact_id: int) -> list[str]:
        """Get all valid email addresses for a contact (primary + additional verified emails)."""
        emails = []
        try:
            contact = Contact.objects.get(id=contact_id)
            # Primary email
            if contact.email:
                emails.append(contact.email)

            # Additional emails that are verified and not opted out
            for email_obj in contact.emails.filter(is_verified=True, opt_out=''):
                emails.append(email_obj.email)

        except Contact.DoesNotExist:
            pass

        # Add additional recipients from settings
        additional_recipients = getattr(settings, 'EMAIL_ADDITIONAL_RECIPIENTS', '')
        if additional_recipients:
            for email in additional_recipients.split(','):
                email = email.strip()
                if email and email not in emails:
                    emails.append(email)

        return emails

    @staticmethod
    def send_transaction_email(
        template_name: str,
        subject: str,
        recipient_emails: list[str],
        context: Dict[str, Any],
        from_email: Optional[str] = None
    ) -> bool:
        """Send an HTML email using a template."""
        if not recipient_emails:
            return False

        if from_email is None:
            from_email = settings.DEFAULT_FROM_EMAIL

        try:
            # Render HTML content
            html_content = render_to_string(f'transactions/emails/{template_name}.html', context)

            # Create plain text version by stripping HTML
            text_content = strip_tags(html_content)

            # Prepare recipients
            to_emails = recipient_emails
            bcc_emails = []

            # Add BCC admin if configured
            if getattr(settings, 'EMAIL_BCC_ADMIN', False):
                admin_email = getattr(settings, 'EMAIL_ADMIN_RECIPIENT', '')
                if admin_email and admin_email not in to_emails:
                    bcc_emails.append(admin_email)

            # Send email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=to_emails,
                bcc=bcc_emails
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            return True
        except Exception as e:
            # Log the error in a real implementation
            print(f"Failed to send email: {e}")
            return False

    @classmethod
    def send_proposal_submitted_notification(cls, proposal: Proposal) -> bool:
        """Send notification when a proposal is submitted."""
        if not getattr(settings, 'EMAIL_NOTIFICATIONS_ENABLED', True):
            return False
        if not getattr(settings, 'EMAIL_PROPOSAL_SUBMITTED_ENABLED', True):
            return False

        recipient_emails = cls.get_recipient_emails(proposal.customer_id)
        if not recipient_emails:
            return False

        context = {
            'proposal': proposal,
            'contact': Contact.objects.get(id=proposal.customer_id),
            'company_name': getattr(settings, 'COMPANY_NAME', 'WebClerk3'),
        }

        subject = f"Proposal Submitted - {proposal.name}"

        return cls.send_transaction_email(
            'proposal_submitted',
            subject,
            recipient_emails,
            context
        )

    @classmethod
    def send_order_created_notification(cls, order: SalesOrder) -> bool:
        """Send notification when an order is created."""
        if not getattr(settings, 'EMAIL_NOTIFICATIONS_ENABLED', True):
            return False
        if not getattr(settings, 'EMAIL_ORDER_CREATED_ENABLED', True):
            return False

        recipient_emails = cls.get_recipient_emails(order.customer_id)
        if not recipient_emails:
            return False

        context = {
            'order': order,
            'contact': Contact.objects.get(id=order.customer_id),
            'company_name': getattr(settings, 'COMPANY_NAME', 'WebClerk3'),
        }

        subject = f"Order Created - {order.name}"

        return cls.send_transaction_email(
            'order_created',
            subject,
            recipient_emails,
            context
        )

    @classmethod
    def send_invoice_sent_notification(cls, invoice: Invoice) -> bool:
        """Send notification when an invoice is sent."""
        if not getattr(settings, 'EMAIL_NOTIFICATIONS_ENABLED', True):
            return False
        if not getattr(settings, 'EMAIL_INVOICE_SENT_ENABLED', True):
            return False

        recipient_emails = cls.get_recipient_emails(invoice.customer_id)
        if not recipient_emails:
            return False

        # Get payment terms if available
        payment_terms = "Net 30"  # Default
        if hasattr(invoice, 'payment_term') and invoice.payment_term:
            payment_terms = invoice.payment_term.name

        context = {
            'invoice': invoice,
            'contact': Contact.objects.get(id=invoice.customer_id),
            'company_name': getattr(settings, 'COMPANY_NAME', 'WebClerk3'),
            'payment_terms': payment_terms,
        }

        subject = f"Invoice Sent - {invoice.name}"

        return cls.send_transaction_email(
            'invoice_sent',
            subject,
            recipient_emails,
            context
        )

    @classmethod
    def send_payment_received_notification(cls, payment: Payment) -> bool:
        """Send notification when a payment is received."""
        if not getattr(settings, 'EMAIL_NOTIFICATIONS_ENABLED', True):
            return False
        if not getattr(settings, 'EMAIL_PAYMENT_RECEIVED_ENABLED', True):
            return False

        recipient_emails = cls.get_recipient_emails(payment.contact_id)
        if not recipient_emails:
            return False

        context = {
            'payment': payment,
            'contact': Contact.objects.get(id=payment.contact_id),
            'company_name': getattr(settings, 'COMPANY_NAME', 'WebClerk3'),
        }

        subject = "Payment Received - Thank You"

        return cls.send_transaction_email(
            'payment_received',
            subject,
            recipient_emails,
            context
        )