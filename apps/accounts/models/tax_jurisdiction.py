from django.db import models
from common.models import BaseModel


# build up predefined metadata and refs and prefs
# capture incremental value changes
# move tables into .refs values and changes into metadata

class TaxJurisdiction(BaseModel):
    tax_jurisdiction = models.CharField(max_length=255, blank=True, null=True)
    gl_account_payable = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=False)
    scripts = models.JSONField(default=dict, blank=True, null=True)
    # costs, sales, shipping, import, etc...
    service_id = models.BigIntegerField
    service_provider = models.CharField(max_length=255, blank=True, null=True)
    tax_name = models.CharField(max_length=255, blank=True, null=True)
    tax_rate_cost = models.FloatField(blank=True, null=True)
    tax_rate_on_shipping = models.FloatField(blank=True, null=True)
    tax_rate_sales = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"TaxJurisdiction ({self.id})"

    class Meta:
        db_table = 'tax_jurisdictions'
    