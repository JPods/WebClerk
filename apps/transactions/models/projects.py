# filepath: /Users/williamjames/Documents/CommerceExpert/webClerk3/transactions/models/projects.py
import uuid
from django.db import models
from common.models import BaseModel

# DDL for the Project table. Execute this with your DB connection (e.g., psycopg2 or SQLAlchemy).
class Project(BaseModel):
    # populated by actions
    task = models.JSONField()
    burndown = models.IntegerField()
    objective = models.JSONField()
    category = models.CharField(max_length=255)
    intent = models.CharField(max_length=255)
    logistics = models.JSONField()
    priority = models.IntegerField()
    profit = models.FloatField()
    profit_velocity = models.IntegerField()
    security_level = models.IntegerField()
    situation = models.TextField()
    status = models.CharField(max_length=255)
    results = models.TextField()
    data = models.JSONField()
# with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
#     cur.execute(PROJECT_TABLE_DDL)

