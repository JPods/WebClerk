# filepath: /webClerk3/accounts/models/gl_journal.py
from django.db import models
from common.models import BaseModel

# build up predefined metadata and refs and prefs

class Gl_journal(BaseModel):
    account = models.CharField(max_length=255, blank=True, null=True)
    
    credit = models.FloatField(blank=True, null=True)
    debit = models.FloatField(blank=True, null=True)
    source = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=255, blank=True, null=True)


    class Meta:
        db_table = 'gl_accounts'

    def __str__(self):
        return f"{self.account or 'Gl_account'} ({self.id})"
    