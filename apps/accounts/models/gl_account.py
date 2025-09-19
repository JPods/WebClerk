from django.db import models
from common.models import BaseModel

class GlAccount(BaseModel):
    account_credit = models.CharField(max_length=255, blank=True, null=True)
    account_debit = models.CharField(max_length=255, blank=True, null=True)
    category = models.CharField(max_length=255, blank=True, null=True)
    
    name = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)
    used_for = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'gl_accounts'

    def __str__(self):
        return f"{self.name or 'GlAccount'} ({self.id})"
    