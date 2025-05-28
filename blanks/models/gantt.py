


#  // Method: GanttParse
#     GanttParse.4dm

from django.db import models
from django.contrib.postgres.fields import JSONField

class Gantt(models.Model):
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('delayed', 'Delayed'),
    ]

    id = models.CharField(
        max_length=100,
        primary_key=True,
        help_text="Unique identifier for the Gantt action"
    )
    name = models.CharField(
        max_length=255,
        help_text="Title of the Gantt action"
    )
    progress = models.FloatField(
        default=0.0,
        help_text="Progress percentage (0.0 to 100.0)"
    )
    progress_by_worklog = models.BooleanField(
        default=False,
        help_text="Whether progress is calculated by worklog"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the Gantt action"
    )
    code = models.CharField(
        max_length=100,
        blank=True,
        help_text="Code identifier for the Gantt action"
    )
    level = models.IntegerField(
        default=0,
        help_text="Hierarchical level of the Gantt action"
    )
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='planned',
        help_text="Status of the Gantt action"
    )
    depends = models.CharField(
        max_length=255,
        blank=True,
        help_text="Dependency identifiers (e.g., comma-separated IDs)"
    )
    start = models.BigIntegerField(
        help_text="Planned start datetime as Unix timestamp (milliseconds)"
    )
    duration = models.FloatField(
        help_text="Planned duration (e.g., in days or hours)"
    )
    end = models.BigIntegerField(
        help_text="Planned end datetime as Unix timestamp (milliseconds)"
    )
    start_is_milestone = models.BooleanField(
        default=False,
        help_text="Whether the start date is a milestone"
    )
    end_is_milestone = models.BooleanField(
        default=False,
        help_text="Whether the end date is a milestone"
    )
    collapsed = models.BooleanField(
        default=False,
        help_text="Whether the Gantt item is collapsed in the UI"
    )
    can_write = models.BooleanField(
        default=True,
        help_text="Whether the user can edit the Gantt item"
    )
    can_add = models.BooleanField(
        default=True,
        help_text="Whether the user can add new Gantt items"
    )
    can_delete = models.BooleanField(
        default=True,
        help_text="Whether the user can delete the Gantt item"
    )
    can_add_issue = models.BooleanField(
        default=True,
        help_text="Whether the user can add issues to the Gantt item"
    )
    has_child = models.BooleanField(
        default=False,
        help_text="Whether the Gantt item has child tasks"
    )
    assigs = JSONField(
        default=list,
        help_text="Assignments: [{id: string, resourceId: string, roleId: string, effort: long}]"
    )

    class Meta:
        db_table = 'gantt'
        verbose_name = 'Gantt Item'
        verbose_name_plural = 'Gantt Items'

    def __str__(self):
        return f"Gantt #{self.id} ({self.name})"