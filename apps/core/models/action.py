# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/core/models/action.py
import uuid
from django.db import models
from django.utils import timezone
from common.models import BaseModel

class Action(BaseModel):
    action = models.CharField(max_length=255, blank=True, null=True)
    action_by = models.CharField(max_length=255, blank=True, null=True)
    priority = models.CharField(max_length=255, blank=True, null=True)
    difficulty = models.CharField(max_length=255, blank=True, null=True)
    hours = models.FloatField(blank=True, null=True)
    percent = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    quality = models.CharField(max_length=255, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    dt_action = models.DateTimeField(null=True, blank=True)
    dt_completed = models.DateTimeField(null=True, blank=True)
    dt_due = models.DateTimeField(null=True, blank=True)
    dt_updated = models.DateTimeField(null=True, blank=True)
    comment = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'actions'

    def __str__(self):
        return f"{self.action or 'Action'} ({self.id})"
    



#     Take care of this in Actions
# CREATE TABLE IF NOT EXISTS "services" (
#     "action" VARCHAR(255),
#     "action_by" VARCHAR(255),
#     "attention" VARCHAR(255),
#     "attribute" VARCHAR(255),
#     "cause" VARCHAR(255),
#     "comment" TEXT,
#     "comment_public" TEXT,
#     "company" VARCHAR(255),
#     "cost_to_customer" INTEGER,
#     "cost_to_rep" INTEGER,
#     "cost_to_us" INTEGER,
#     "created_by" VARCHAR(255),
#     "description" VARCHAR(255),
#     "display" TEXT,
#     "duration_planned" INTEGER,
#     "expense_explain" TEXT,
#     "expenses" DOUBLE PRECISION,
#     "field_56" VARCHAR(255),
#     "is_tracked_sales" BOOLEAN DEFAULT FALSE,
#     "miles" INTEGER,
#     "price_service" DOUBLE PRECISION,
#     "price_travel" DOUBLE PRECISION,
#     "process" VARCHAR(255),
#     "publish" INTEGER,
#     "purpose" VARCHAR(255),
#     "references" JSONB,
#     "timer" INTEGER,
#     "travel_time" INTEGER
# );
