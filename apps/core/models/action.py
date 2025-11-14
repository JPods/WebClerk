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
    # Parent-child relationship
    parent = models.ForeignKey('self', to_field='uuid', related_name='children', null=True, blank=True, on_delete=models.CASCADE)
    
    # Multilingual titles and descriptions
    action = models.JSONField(default=dict, blank=True, null=True)
    description = models.JSONField(default=dict, blank=True, null=True)
    
    # Supported languages for this task
    languages = models.JSONField(default=list, blank=True, null=True)

    # Project information
    project_name = models.CharField(max_length=255, blank=True, null=True)
    project_id = models.CharField(max_length=255, blank=True, null=True)

    # Kanban board and workflow management
    kanban_column = models.CharField(max_length=50, choices=KANBAN_COLUMNS, default='Backlog')
    priority = models.PositiveIntegerField(default=1)
    difficulty = models.PositiveIntegerField(choices=DIFFICULTY_LEVELS, default=10)
    status = models.CharField(max_length=100, blank=True, null=True)

    # Date fields with detailed meta info
    dt_created = models.BigIntegerField(default=0, db_index=True)
    dt_updated = models.BigIntegerField(default=0, db_index=True)
    dt_expected = models.BigIntegerField(blank=True, null=True)
    dt_due = models.BigIntegerField(blank=True, null=True)
    dt_completed = models.BigIntegerField(blank=True, null=True)
    dt_start = models.BigIntegerField(blank=True, null=True)
    dt_end = models.BigIntegerField(blank=True, null=True)
    #days
    duration = models.IntegerField(blank=True, null=True)

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

    # Additional project data (can store child names, meta, or history)
    project_metadata = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = 'actions'
        verbose_name = "Action"
        verbose_name_plural = "Actions"

    def __str__(self):
        action_dict = self.action or {}
        action_text = action_dict.get('en') or action_dict.get('bn') or action_dict.get('ar') or 'Untitled'
        return f"{action_text} ({self.kanban_column})"

    def update_keywords(self):
        """Update keywords for this action record."""
        from apps.core.services.keywords import build_keywords_for_record
        keywords = build_keywords_for_record('action', self.id)
        # Store keywords in refs.keywords
        refs = getattr(self, 'refs', {}) or {}
        if not isinstance(refs, dict):
            refs = {}
        refs['keywords'] = keywords
        self.refs = refs