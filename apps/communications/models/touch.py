# path: apps/communications/models/touch.py
from django.db import models
from common.models import BaseModel


class Touch(BaseModel):
    """Contact event log — calls, emails, visits, texts.

    A Touch records that a communication happened. It is NOT an Action
    (work to be done). An Action may trigger a Touch, and a Touch may
    spawn an Action, but they are different models with different lifecycles.

    tel:/mailto:/sms: URI launchers initiate the communication;
    the Touch record captures what happened afterward.
    """

    CHANNEL_CHOICES = [
        ('call', 'Phone Call'),
        ('email', 'Email'),
        ('visit', 'Visit'),
        ('text', 'Text/SMS'),
        ('meeting', 'Meeting'),
    ]

    DIRECTION_CHOICES = [
        ('out', 'Outbound'),
        ('in', 'Inbound'),
    ]

    contact = models.ForeignKey(
        'core.Contact',
        on_delete=models.CASCADE,
        related_name='touches',
        null=True,
        blank=True,
        help_text="Contact who was touched"
    )

    channel = models.CharField(
        max_length=10,
        choices=CHANNEL_CHOICES,
        db_index=True,
        help_text="Communication channel: call, email, visit, text, meeting"
    )

    direction = models.CharField(
        max_length=3,
        choices=DIRECTION_CHOICES,
        default='out',
        db_index=True,
        help_text="Inbound or outbound"
    )

    subject = models.CharField(
        max_length=255,
        blank=True,
        help_text="Brief description — e.g. 'Discussed pricing'"
    )

    summary = models.TextField(
        blank=True,
        help_text="What happened, what was said, next steps"
    )

    duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duration in minutes (mainly for calls)"
    )

    email_message_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Email Message-ID header — paste from email program for cross-reference"
    )

    action = models.ForeignKey(
        'core.Action',
        on_delete=models.SET_NULL,
        related_name='touches',
        null=True,
        blank=True,
        help_text="Action that triggered this touch (optional)"
    )

    org_id = models.BigIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Organization ID — paired with org_model to link to any org type"
    )

    org_model = models.CharField(
        max_length=30,
        blank=True,
        db_index=True,
        help_text="Model registry key: customer, vendor, manufacturer, rep, employee"
    )

    project_id = models.BigIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Project this touch relates to"
    )

    linkage_id = models.BigIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Linkage group — ties touch to the transaction graph (proposal→order→invoice)"
    )

    logged_by = models.BigIntegerField(
        default=0,
        db_index=True,
        help_text="Contact ID of who recorded this touch"
    )

    OUTCOME_CHOICES = [
        ('connected', 'Connected'),
        ('voicemail', 'Voicemail'),
        ('no_answer', 'No Answer'),
        ('bounced', 'Bounced'),
        ('rescheduled', 'Rescheduled'),
    ]

    outcome = models.CharField(
        max_length=12,
        choices=OUTCOME_CHOICES,
        blank=True,
        db_index=True,
        help_text="What happened: connected, voicemail, no_answer, bounced, rescheduled"
    )

    impact = models.PositiveSmallIntegerField(
        default=0,
        db_index=True,
        help_text="Rep judgment of touch importance, 1-5 (0 = not rated)"
    )

    plan = models.PositiveSmallIntegerField(
        default=0,
        db_index=True,
        help_text="Follow-up in N days from dt_created. 0 = no follow-up. Due when dt_created + (plan * 86400000) <= now."
    )

    class Meta:
        db_table = 'touches'
        verbose_name = 'Touch'
        verbose_name_plural = 'Touches'
        ordering = ['-dt_created']
        indexes = [
            models.Index(fields=['contact']),
            models.Index(fields=['channel']),
            models.Index(fields=['direction']),
            models.Index(fields=['-dt_created']),
            models.Index(fields=['action']),
            models.Index(fields=['org_model', 'org_id']),
        ]

    def __str__(self):
        direction = 'to' if self.direction == 'out' else 'from'
        contact_str = str(self.contact) if self.contact else 'unknown'
        return f"{self.get_channel_display()} {direction} {contact_str}"

    def pre_save_hook(self, data):
        if 'channel' in data and data['channel'] not in dict(self.CHANNEL_CHOICES):
            return f'channel: must be one of {", ".join(dict(self.CHANNEL_CHOICES).keys())}'
        return None

    def _resolve_org_from_contact(self):
        """When contact is set, populate org_id and org_model from contact's org FKs."""
        if not self.contact_id:
            return
        # Don't overwrite if both are already explicitly set
        if self.org_id and self.org_model:
            return
        try:
            contact = self.contact
            if not contact:
                return
            # Check org FKs on contact — first match wins
            for field, model_key in [
                ('customer_id', 'customer'),
                ('vendor_id', 'vendor'),
                ('manufacturer_id', 'manufacturer'),
            ]:
                org_pk = getattr(contact, field, None)
                if org_pk:
                    self.org_id = org_pk
                    self.org_model = model_key
                    return
        except Exception:
            pass

    def save(self, *args, **kwargs):
        self._resolve_org_from_contact()
        super().save(*args, **kwargs)

    def post_save_hook(self, data, is_update=False, context=None):
        base_msg = super().post_save_hook(data, is_update=is_update, context=context)
        return '; '.join(filter(None, [base_msg, 'touch saved']))
