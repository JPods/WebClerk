from django.db import models
from common.models import BaseModel
import uuid

class Email(BaseModel):
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    email = models.EmailField(max_length=254, blank=False, help_text="Email address")
    name = models.CharField(max_length=100, blank=True, help_text="Display name for this email")
    attention = models.CharField(max_length=100, blank=True, help_text="Person or department attention line")
    
    # Use choices for better data integrity
    OPT_OUT_CHOICES = [
        ('', 'Active'),
        ('opted_out', 'Opted Out'),
        ('bounced', 'Bounced'),
        ('invalid', 'Invalid'),
        ('spam_complaint', 'Spam Complaint'),
    ]
    opt_out = models.CharField(max_length=20, choices=OPT_OUT_CHOICES, blank=True, default='')
    
    # Better field for comments
    comment = models.TextField(blank=True, null=True, help_text="Additional notes about this email")
    
    # Add useful tracking fields
    is_primary = models.BooleanField(default=False, help_text="Mark as primary email address")
    is_verified = models.BooleanField(default=False, help_text="Email address has been verified")
    dt_verified = models.DateTimeField(null=True, blank=True, help_text="When email was verified")
    dt_bounced = models.DateTimeField(null=True, blank=True, help_text="Last bounce date")

    class Meta:
        db_table = 'emails'
        verbose_name = 'Email Address'
        verbose_name_plural = 'Email Addresses'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_primary']),
            models.Index(fields=['opt_out']),
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
        
        # Ensure only one primary email per user (you'd need to add user relationship)
        # This is a placeholder - you'd implement based on your user model relationship

    @property
    def status_display(self):
        """Human-readable status display."""
        return dict(self.OPT_OUT_CHOICES).get(self.opt_out, 'Active')

    @property
    def is_active(self):
        """Check if email is active (not opted out, bounced, etc.)."""
        return not self.opt_out