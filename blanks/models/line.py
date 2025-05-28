from django.db import models
from django.contrib.postgres.fields import JSONBField
import uuid

class Line(models.Model):
    id = models.BigAutoField(primary_key=True)
    uuid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4)
    table = JSONBField(null=True, blank=True, default=dict)
    index_line = models.IntegerField()
    probability = models.IntegerField(null=True, blank=True)
    type_sale = models.CharField(max_length=255, null=True, blank=True)
    sequence = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=255, null=True, blank=True)
    metadata = JSONBField(null=True, blank=True, default=dict)
    references = JSONBField(null=True, blank=True, default=dict)
    comment = models.TextField(null=True, blank=True)
    item = JSONBField(null=True, blank=True, default=lambda: {
        "id_num": 0,
        "ida_item": "",
        "description": "",
        "description_text": "",
        "time_lead": 0,
        "location": "",
        "unit_measure": ""
    })
    quantities = JSONBField(null=True, blank=True, default=lambda: {
        "ordered": 0.00,
        "backlog": 0.00,
        "remaining": 0.00,
        "is_fixed": False
    })
    costs = JSONBField(null=True, blank=True, default=lambda: {
        "freight": 0.00,
        "unit": 0.00,
        "extended": 0.00,
        "is_fixed": False
    })
    prices = JSONBField(null=True, blank=True, default=lambda: {
        "unit": 0.00,
        "discount_percent": 0.00,
        "discount_amount": 0.00,
        "extended": 0.00,
        "is_fixed": False,
        "//qqq_manufacturer_suggested_retail": 0.00
    })
    tax = JSONBField(null=True, blank=True, default=lambda: {
        "sales_rate": 0.00,
        "sales": 0.00,
        "cost_rate": 0.00,
        "cost": 0.00
    })
    dates = JSONBField(null=True, blank=True, default=lambda: {
        "completed": "2024-12-28T17:00:00Z",
        "created": "2024-12-28T17:00:00Z",
        "expected": "2024-12-28T17:00:00Z",
        "updated": "2024-12-28T17:00:00Z"
    })
    people = JSONBField(null=True, blank=True, default=lambda: {
        "action_by": "",
        "created_by": "",
        "requested_by": "",
        "updated_by": ""
    })
    weights = JSONBField(null=True, blank=True, default=lambda: {
        "unit": 0.00,
        "extended": 0.00
    })
    flow = JSONBField(null=True, blank=True, default=lambda: {
        "source_type": "Proposal-SO SO-Invoice SO-PO Request-PO",
        "id_num": 0,
        "destination_type": "",
        "id_destination": ""
    })
    sources = JSONBField(null=True, blank=True, default=lambda: {
        "only": "Requests-POs",
        "id_num": 0,
        "name": "",
        "offered_price": 0.00,
        "vendor": "",
        "manufacturer": ""
    })

    class Meta:
        db_table = 'lines'

    def __str__(self):
        return f"Line {self.id}"