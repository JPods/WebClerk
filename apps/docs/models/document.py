# filepath: /webClerk3/docs/models/documents.py
from django.db import models
from common.models import BaseModel
from django.utils import timezone
# this table provides a path to documents
# example use is to link line items in orders, proposals, etc.
# with one document that passes on specs, paths, comments, and other details

# If you need a model for the "paths" table, define it as a Django model below.
# Remove raw SQL statements from Python files; use Django ORM and migrations instead.

# Example: Add additional fields to the Document model if needed
class Document(BaseModel):
    name = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=255, blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    publish = models.IntegerField(default=0)  # 0 = private, 1 = public
    body = models.TextField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    confidential = models.CharField(max_length=255, blank=True, null=True)
    copy_right_level = models.CharField(max_length=255, blank=True, null=True)
    copy_right_path = models.CharField(max_length=255, blank=True, null=True)
    count_accessed = models.IntegerField(default=0)
    table_name = models.CharField(max_length=255, blank=True, null=True)
    version = models.CharField(max_length=255, blank=True, null=True)
    retention_period = models.IntegerField(blank=True, null=True)
    security_level = models.IntegerField(blank=True, null=True)
    sequence = models.IntegerField(blank=True, null=True)
    size_bytes = models.IntegerField(blank=True, null=True)
    mime_type = models.CharField(max_length=255, blank=True, null=True)
    path = models.JSONField(blank=True, null=True)  # For JSONB field
#     checksum = models.CharField(max_length=255, blank=True, null=True)
