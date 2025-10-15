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
    

    class Meta:
        db_table = 'actions'

    def __str__(self):
        return f"{self.action or 'Action'} ({self.id})"
    
# insert into metadata
# {
#   "parent": {
#   "zzz":"id of the parent action",
#     "id": "YOUR_DATABASE_ID"
#   },
#   "properties": {
#     "lang":["en","ab","bn"],
    
#     "Name": {
#       "title": {"en":{
#           "text": {
#             "content": "My New Page Title"
#           }
#         },
#         "ab":{
#           "text": {
#             "content": "My New Page Title"
#           }
#         },
#         "bn":{
#           "text": {
#             "content": "My New Page Title"
#           }
#         }
#       }
#     },
#     "zzzCollumn":"only one of Backlog, Planning, InProcess, Review, Complete",
#     "Collumn": "InProgress",
#     "zzzImportance":"only one of Immediate, High, Medium, Low",
#     "Importance":"Immediate",
#     "zzzPriority":"do  we need this",
#     "Priority": 1,
#     "zzzDifficulty":"only one of 100, 50, 15, 10, 4, 1",
#     "Difficulty": 50,
#     "Date": {
#       "zzzdatetime":"these are datetimes",
#       "start": "456343453453452345",
#        "end": null
#       }
#     },
#     "Assigned To": {
#       "people": [
#         {
#           "id": "USER_ID_1",
#           "name": "name"
#         }
#       ]
#     },
#     "Linkage":25,
#     "Description": {
#       "rich_text": [
#         {
#           "text": {
#             "content": "This is a detailed description of the new page."
#           }
#         }
#       ]
#     },
# "children": [
#     {"id":19,
#     "name":"some name"},
#     {"id":20,
#     "name":"other name"}
#   ]
# }

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
