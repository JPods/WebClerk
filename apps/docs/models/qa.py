# filepath: /webClerk3/docs/models/qas.py
from django.db import models
from common.models import BaseModel
from django.utils import timezone
# bulk of this table is in the .refs to relate other tables
# example use is to link line items in orders, proposals, etc. 
# with one document that passes on specs, paths, comments, and other details
class Qa(BaseModel):
    answered_by = models.CharField(max_length=255, blank=True, null=True)
    contact_id = models.ForeignKey('contacts.Contact', on_delete=models.SET_NULL, blank=True, null=True)
    answer = models.TextField(blank=True, null=True)
    # from settings
    question = models.CharField(max_length=255, blank=True, null=True)
    question_id = models.ForeignKey('settings.id', on_delete=models.SET_NULL, blank=True, null=True)
    sequence = models.IntegerField(default=0)
    table_name = models.CharField(max_length=255, blank=True, null=True)
    #image, videos, and other documents many be attached and will be 
    #stored by the system, with the id, name, and path saved in .refs


    # create settings records to store questions and
    # the default answers. Answers also need ids so their
    # use can be tracked and managed effectively.

    class Meta:
        db_table = 'qas'

    def __str__(self):
        return f"Qa {self.id}"