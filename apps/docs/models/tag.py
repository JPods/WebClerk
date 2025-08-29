# filepath: /webClerk3/docs/models/linkages.py
from django.db import models
from common.models import BaseModel
from django.utils import timezone
# bulk of this table is in the .refs to relate other tables
# example use is to link line items in orders, proposals, etc. 
# with one document that passes on specs, paths, comments, and other details
class Tag(BaseModel):
    comment = models.TextField(blank=True, null=True)
    purpose = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    # heavily uses .refs and .metadata 
    # isolated from linkages because primarily used for tracking
    # shipments and equipment locators
    # the metadata is more detailed and specific to each tag
    # tags can be nested such as units in a box as one tag and 
    # boxes on a pallet for the same or another tag


    class Meta:
        db_table = 'tags'

    def __str__(self):
        return f"{self.name or 'Tag'} ({self.id})"
    