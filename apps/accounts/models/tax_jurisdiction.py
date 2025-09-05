from django.db import models
from common.models import BaseModel


# build up predefined metadata and refs and prefs
# capture incremental value changes
# move tables into .refs values and changes into metadata

class TaxJurisdiction(BaseModel):
    # README (tax localization):
    # Jurisdiction definitions are highly localized. Rates, exemptions and product
    # categorization often diverge per state/province/country and can also vary at
    # municipal levels. This model should remain lightweight: store identifiers,
    # human-friendly naming, and soft metadata only. Detailed product-type rules
    # belong either in external tax services or in soft JSON blobs (params/scripts)
    # so schema changes in one region do not force global migrations.
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
    