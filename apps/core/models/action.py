import uuid
from django.db import models
from django.utils import timezone
from common.models import BaseModel

KANBAN_COLUMNS = [
    ('Backlog', 'Backlog'),
    ('Planning', 'Planning'),
    ('InProcess', 'In Process'),
    ('Review', 'Review'),
    ('Complete', 'Complete'),
]

DIFFICULTY_LEVELS = [
    (100, 'Extreme'),
    (50, 'Hard'),
    (15, 'Moderate'),
    (10, 'Normal'),
    (4, 'Easy'),
    (1, 'Trivial'),
]

class Action(BaseModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Parent-child relationship
    parent = models.ForeignKey('self', related_name='children', null=True, blank=True, on_delete=models.CASCADE)
    
    # Multilingual titles
    action_en = models.CharField(max_length=255, blank=True, null=True)
    action_ar = models.CharField(max_length=255, blank=True, null=True)
    action_bn = models.CharField(max_length=255, blank=True, null=True)
    action_es = models.CharField(max_length=255, blank=True, null=True)

    # Multilingual descriptions
    description_en = models.TextField(blank=True, null=True)
    description_ar = models.TextField(blank=True, null=True)
    description_bn = models.TextField(blank=True, null=True)
    description_es = models.TextField(blank=True, null=True)
    
    # Supported languages for this task
    languages = models.JSONField(default=list, blank=True, null=True)

    # Kanban board and workflow management
    kanban_column = models.CharField(max_length=50, choices=KANBAN_COLUMNS, default='Backlog')
    priority = models.PositiveIntegerField(default=1)
    difficulty = models.PositiveIntegerField(choices=DIFFICULTY_LEVELS, default=10)
    status = models.CharField(max_length=100, blank=True, null=True)

    # Date fields with detailed meta info
    dt_created = models.DateTimeField(default=timezone.now)
    dt_updated = models.DateTimeField(auto_now=True)
    dt_expected = models.DateTimeField(blank=True, null=True)
    dt_due = models.DateTimeField(blank=True, null=True)
    dt_completed = models.DateTimeField(blank=True, null=True)
    dt_start = models.DateTimeField(blank=True, null=True)
    dt_end = models.DateTimeField(blank=True, null=True)

    # Audit info: who created / updated etc.
    created_by = models.JSONField(blank=True, null=True)
    updated_by = models.JSONField(blank=True, null=True)
    expected_by = models.JSONField(blank=True, null=True)
    due_by = models.JSONField(blank=True, null=True)
    completed_by = models.JSONField(blank=True, null=True)
    start_by = models.JSONField(blank=True, null=True)
    end_by = models.JSONField(blank=True, null=True)

    # Assigned users (many-to-many like, via JSON)
    assigned_to = models.JSONField(blank=True, null=True)

    # Linkage or weighting to other systems/tasks
    linkage = models.PositiveIntegerField(default=0)

    # Additional Kanban data (can store child names, meta, or history)
    kanban_meta = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = 'actions'
        verbose_name = "Action"
        verbose_name_plural = "Actions"

    def __str__(self):
        return f"{self.action_en or self.action_bn or self.action_ar or 'Untitled'} ({self.kanban_column})"