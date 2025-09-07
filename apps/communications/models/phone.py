# path: apps/communications/models/phone.py
from django.db import models
from common.models import BaseModel
from django.utils import timezone  # Add this import
import uuid

class Phone(BaseModel):
    number = models.CharField(max_length=20, blank=True, help_text="Phone number")
    country_code = models.CharField(max_length=5, blank=True, help_text="Country code (e.g., +1)")
    format = models.CharField(max_length=50, blank=True, help_text="Formatted phone number")
    name = models.CharField(max_length=100, blank=True, help_text="Display name for this phone")
    attention = models.CharField(max_length=100, blank=True, help_text="Person or department attention line")
    opt_out = models.BooleanField(default=False, help_text="Opted out of communications")
    
    # Remove this database field - now using metadata
    # dt_verified = models.DateTimeField(null=True, blank=True, help_text="When phone was verified")

    class Meta:
        db_table = 'phones'
        verbose_name = 'Phone Number'
        verbose_name_plural = 'Phone Numbers'
        
    def __str__(self):
        if self.name:
            return f"{self.name} ({self.number})"
        return self.number

    # --- Hooks (example overrides) ------------------------------------
    def pre_save_hook(self, data):  # type: ignore[override]
        # Reject obviously bad phone numbers when provided
        if 'number' in data and data['number'] and len(str(data['number'])) < 4:
            return 'number: too short'
        return None

    def api_validate_payload(self, data, is_update):  # type: ignore[override]
        errors: list[str] = []
        if 'country_code' in data and data['country_code'] and not str(data['country_code']).startswith('+'):
            errors.append('country_code: must start with +')
        return (not errors, errors)

    def post_save_hook(self, data):  # type: ignore[override]
        # Return informational message (useful for tests / client log)
        return 'phone saved'

    # --- Verification queue (stub) ---------------------------------------
    def queue_verification(self, connection_name: str | None = None) -> None:
        try:
            from apps.communications.tasks import validate_phone_basic
            validate_phone_basic.delay(self.pk)
        except Exception:
            pass
