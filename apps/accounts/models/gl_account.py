from django.db import models

from common.models import BaseModel
from apps.accounts.choices import (
    GL_ACCOUNT_CATEGORY_CHOICES,
    GL_ACCOUNT_TYPE_CHOICES,
    GL_ACCOUNT_USAGE_CHOICES,
)

class GlAccount(BaseModel):
    account_credit = models.CharField(max_length=255, blank=True, null=True)
    account_debit = models.CharField(max_length=255, blank=True, null=True)
    category = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        choices=GL_ACCOUNT_CATEGORY_CHOICES,
    )
    
    name = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        choices=GL_ACCOUNT_TYPE_CHOICES,
    )
    used_for = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        choices=GL_ACCOUNT_USAGE_CHOICES,
    )

    class Meta:
        db_table = 'gl_accounts'

    def __str__(self):
        return f"{self.name or 'GlAccount'} ({self.id})"
    