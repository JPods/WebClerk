from django.db import models
from common.models import BaseModel

# build up predefined metadata and refs and prefs
# capture incremental value changes
# move tables into .refs values and changes into metadata

class Ledger(BaseModel):
    
    discount_potential = models.FloatField(blank=True, null=True)
    source = models.CharField(max_length=255, blank=True, null=True)
    table_name = models.CharField(max_length=255, blank=True, null=True)
    table_name_parent = models.CharField(max_length=255, blank=True, null=True)
    value_available = models.FloatField(blank=True, null=True)
    value_original = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f"Ledger ({self.id})"

    class Meta:
        db_table = 'ledger'
    