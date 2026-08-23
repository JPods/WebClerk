# path: apps/communications/models/email.py
from django.db import models
from django.utils import timezone

from common.models import BaseModel
from apps.communications.choices import EMAIL_OPT_OUT_CHOICES, EMAIL_TYPE_CHOICES

class Email(BaseModel):
    # Direct FK to contact - explicit ownership relationship
    contact = models.ForeignKey(
        'core.Contact',
        on_delete=models.CASCADE,
        related_name='emails',
        null=True,
        blank=True,
        help_text="Contact this email belongs to"
    )
    
    email = models.EmailField(max_length=254, blank=False, help_text="Email address")
    name = models.CharField(max_length=100, blank=True, help_text="Display name for this email")
    attention = models.CharField(max_length=100, blank=True, help_text="Person or department attention line")
    type = models.CharField(
        max_length=50,
        blank=True,
        choices=EMAIL_TYPE_CHOICES,
        default="",
        help_text="Type of email (e.g., work, personal)",
    )

    opt_out = models.CharField(max_length=20, choices=EMAIL_OPT_OUT_CHOICES, blank=True, default='')
    
    
    # Add useful tracking fields
    is_primary = models.BooleanField(default=False, help_text="Mark as primary email address")
    is_verified = models.BooleanField(default=False, help_text="Email has been verified")  # Add this field
    
    # put these in metadata.history
    #dt_verified = models.DateTimeField(null=True, blank=True, help_text="When email was verified")
    #dt_bounced = models.DateTimeField(null=True, blank=True, help_text="Last bounce date")

    class Meta:
        db_table = 'emails'
        verbose_name = 'Email Address'
        verbose_name_plural = 'Email Addresses'
        indexes = [
            models.Index(fields=['contact']),
            models.Index(fields=['email']),
            models.Index(fields=['is_primary']),
            models.Index(fields=['opt_out'])
        ]

    def __str__(self):
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email

    def clean(self):
        """Validate the email field and ensure data consistency."""
        from django.core.exceptions import ValidationError
        from django.core.validators import validate_email
        
        if self.email:
            try:
                validate_email(self.email)
            except ValidationError:
                raise ValidationError({'email': 'Enter a valid email address.'})



    @property
    def status_display(self):
        """Human-readable status derived from opt_out state."""
        return dict(EMAIL_OPT_OUT_CHOICES).get(self.opt_out, 'Active')

    # --- Verification helpers (async + decision gate) -------------------
    def queue_verification(self, connection_name: str | None = None) -> None:
        try:
            from apps.communications.tasks import validate_email_format
            validate_email_format(self.pk)
        except Exception:
            pass

    def mark_verification_review(self, status: str, exchange_id: int | None = None, by: int | None = None):
        meta = self.metadata if isinstance(self.metadata, dict) else {}
        ver_parent = meta.setdefault('versioning', {})
        if not isinstance(ver_parent, dict):
            ver_parent = {}
            meta['versioning'] = ver_parent
        ver = ver_parent.setdefault('validation', {})
        if not isinstance(ver, dict):
            ver = {}
            ver_parent['validation'] = ver
        ver['review'] = {"status": status, "exchange_id": exchange_id, "by": by or 0, "dt": int(timezone.now().timestamp()*1000)}
        self.metadata = meta  # type: ignore[assignment]
        self.save(update_fields=['metadata', 'dt_modified'])