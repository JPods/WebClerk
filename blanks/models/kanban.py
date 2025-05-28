from django.db import models
from django.contrib.postgres.fields import JSONField

class Kanban(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('InProgress', 'In Progress'),
        ('Done', 'Done'),
        ('Blocked', 'Blocked'),
    ]
    
    TYPE_CHOICES = [
        ('Story', 'Story'),
        ('Task', 'Task'),
        ('Bug', 'Bug'),
        ('Epic', 'Epic'),
    ]
    
    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Critical', 'Critical'),
    ]
    
    id = models.BigIntegerField(
        primary_key=True,
        help_text="Unique identifier for the kanban item"
    )
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='Open',
        help_text="Current status of the kanban item"
    )
    summary = models.TextField(
        help_text="Summary of the kanban item"
    )
    type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        default='Story',
        help_text="Type of kanban item"
    )
    priority = models.CharField(
        max_length=50,
        choices=PRIORITY_CHOICES,
        default='Low',
        help_text="Priority level of the kanban item"
    )
    tags = models.CharField(
        max_length=255,
        blank=True,
        help_text="Comma-separated tags (e.g., Analyze,Customer)"
    )
    estimate = models.FloatField(
        help_text="Estimated effort in hours"
    )
    per_cent = models.IntegerField(
        help_text="Percentage completion (0-100)"
    )
    assignee = models.CharField(
        max_length=100,
        blank=True,
        help_text="Assigned person's name"
    )
    rank_id = models.IntegerField(
        help_text="Rank or order of the kanban item"
    )
    link = JSONField(
        default=dict,
        blank=True,
        help_text="Link data: {tableName: string, id: long, denormalized: string, comment: string}"
    )

    class Meta:
        db_table = 'kanban'
        verbose_name = 'Kanban Item'
        verbose_name_plural = 'Kanban Items'

    def __str__(self):
        return f"Kanban #{self.id} ({self.summary[:50]}...)"