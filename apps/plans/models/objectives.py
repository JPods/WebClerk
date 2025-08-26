from django.db import models
from common.models import BaseModel
from django.utils import timezone
import uuid

# Explanation: Records for tracking fidelity to mission.

class Objective(BaseModel):
    alignment = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=255, null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    culture = models.TextField(null=True, blank=True)
    intent = models.CharField(max_length=255, null=True, blank=True)
    logistics = models.TextField(null=True, blank=True)
    objective = models.CharField(max_length=255, null=True, blank=True)
    percent = models.IntegerField(null=True, blank=True)
    priority = models.IntegerField(null=True, blank=True)
    profit = models.FloatField(null=True, blank=True)
    profit_velocity = models.IntegerField(null=True, blank=True)
    publish = models.IntegerField(null=True, blank=True)
    situation = models.TextField(null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=255, null=True, blank=True)
    what = models.CharField(max_length=255, null=True, blank=True)
    where = models.CharField(max_length=255, null=True, blank=True)
    who = models.CharField(max_length=255, null=True, blank=True)
    why = models.TextField(null=True, blank=True)
