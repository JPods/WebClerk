"""
Scheduler models for tracking and configuring background tasks.

Models:
    - ScheduledTask: Defines a task that can be scheduled
    - TaskRun: Execution history for each task run
    - TaskConfig: User-configurable parameters for tasks
"""

from django.db import models
from django.utils import timezone
from common.models import BaseModel


class ScheduledTask(BaseModel):
    """
    Represents a schedulable background task.
    
    Each task corresponds to a Celery task function that can be
    configured and monitored through the admin interface.
    """
    
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        PAUSED = 'paused', 'Paused'
        DISABLED = 'disabled', 'Disabled'
    
    class Frequency(models.TextChoices):
        MINUTES_15 = '15min', 'Every 15 minutes'
        HOURLY = 'hourly', 'Hourly'
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'
        CUSTOM = 'custom', 'Custom crontab'
    
    # Identity
    name = models.CharField(max_length=100, unique=True, help_text="Unique task identifier")
    task_path = models.CharField(max_length=255, help_text="Celery task path (e.g., apps.scheduler.tasks.task_name)")
    description = models.TextField(blank=True)
    
    # Schedule
    frequency = models.CharField(max_length=20, choices=Frequency.choices, default=Frequency.DAILY)
    crontab = models.CharField(max_length=100, blank=True, help_text="Custom crontab: 'minute hour day_of_week day_of_month month'")
    run_at_hour = models.PositiveSmallIntegerField(default=2, help_text="Hour to run (0-23) for daily/weekly tasks")
    run_at_minute = models.PositiveSmallIntegerField(default=0, help_text="Minute to run (0-59)")
    run_on_day = models.PositiveSmallIntegerField(default=0, help_text="Day of week (0=Mon) for weekly, day of month for monthly")
    
    # Status
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    
    # Execution tracking
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_run_status = models.CharField(max_length=20, blank=True)
    last_run_duration = models.FloatField(null=True, blank=True, help_text="Seconds")
    next_run_at = models.DateTimeField(null=True, blank=True)
    run_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    
    # Configuration
    default_kwargs = models.JSONField(default=dict, blank=True, help_text="Default kwargs passed to task")
    max_retries = models.PositiveSmallIntegerField(default=3)
    timeout_seconds = models.PositiveIntegerField(default=1800, help_text="Max execution time")
    
    class Meta:
        db_table = 'scheduler_task'
        verbose_name = 'Scheduled Task'
        verbose_name_plural = 'Scheduled Tasks'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"
    
    def record_run(self, success: bool, duration: float, error: str = None):
        """Update task after a run completes."""
        self.last_run_at = timezone.now()
        self.last_run_status = 'success' if success else 'error'
        self.last_run_duration = duration
        self.run_count += 1
        if not success:
            self.error_count += 1
        self.save(update_fields=[
            'last_run_at', 'last_run_status', 'last_run_duration',
            'run_count', 'error_count', 'dt_modified', 'version'
        ])


class TaskRun(BaseModel):
    """
    Records each execution of a scheduled task.
    
    Provides audit trail and debugging information for task runs.
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        SUCCESS = 'success', 'Success'
        ERROR = 'error', 'Error'
        TIMEOUT = 'timeout', 'Timeout'
        RETRY = 'retry', 'Retrying'
    
    task = models.ForeignKey(
        ScheduledTask,
        on_delete=models.CASCADE,
        related_name='runs'
    )
    
    # Execution details
    celery_task_id = models.CharField(max_length=255, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True, help_text="Seconds")
    
    # Input/Output
    kwargs = models.JSONField(default=dict, blank=True, help_text="Arguments passed to task")
    result = models.JSONField(null=True, blank=True, help_text="Task return value")
    error_message = models.TextField(blank=True)
    error_traceback = models.TextField(blank=True)
    
    # Metrics from task
    records_processed = models.PositiveIntegerField(null=True, blank=True)
    records_updated = models.PositiveIntegerField(null=True, blank=True)
    
    # Retry tracking
    attempt = models.PositiveSmallIntegerField(default=1)
    
    class Meta:
        db_table = 'scheduler_task_run'
        verbose_name = 'Task Run'
        verbose_name_plural = 'Task Runs'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['task', '-started_at']),
            models.Index(fields=['status', '-started_at']),
        ]
    
    def __str__(self):
        return f"{self.task.name} @ {self.started_at} ({self.status})"
    
    def start(self):
        """Mark task as running."""
        self.status = self.Status.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at', 'dt_modified', 'version'])
    
    def complete(self, result: dict = None):
        """Mark task as successfully completed."""
        self.status = self.Status.SUCCESS
        self.finished_at = timezone.now()
        if self.started_at:
            self.duration = (self.finished_at - self.started_at).total_seconds()
        if result:
            self.result = result
            self.records_processed = result.get('processed')
            self.records_updated = result.get('updated')
        self.save(update_fields=[
            'status', 'finished_at', 'duration', 'result',
            'records_processed', 'records_updated', 'dt_modified', 'version'
        ])
        # Update parent task
        self.task.record_run(success=True, duration=self.duration or 0)
    
    def fail(self, error: str, traceback: str = ''):
        """Mark task as failed."""
        self.status = self.Status.ERROR
        self.finished_at = timezone.now()
        if self.started_at:
            self.duration = (self.finished_at - self.started_at).total_seconds()
        self.error_message = error
        self.error_traceback = traceback
        self.save(update_fields=[
            'status', 'finished_at', 'duration',
            'error_message', 'error_traceback', 'dt_modified', 'version'
        ])
        # Update parent task
        self.task.record_run(success=False, duration=self.duration or 0, error=error)


class TaskConfig(BaseModel):
    """
    User-configurable parameters for task execution.
    
    Allows adjusting task behavior without code changes.
    Admins can tune limits, batch sizes, and other parameters.
    """
    
    task = models.OneToOneField(
        ScheduledTask,
        on_delete=models.CASCADE,
        related_name='config'
    )
    
    # Common parameters
    limit = models.PositiveIntegerField(
        default=5000,
        help_text="Maximum records to process per run"
    )
    batch_size = models.PositiveIntegerField(
        default=500,
        help_text="Records per database batch"
    )
    
    # Scope filters
    app_filter = models.CharField(
        max_length=100, blank=True,
        help_text="Limit to specific Django app (e.g., 'orgs')"
    )
    model_filter = models.CharField(
        max_length=100, blank=True,
        help_text="Limit to specific model (e.g., 'orgs.OrgBase')"
    )
    
    # Feature flags
    dry_run = models.BooleanField(
        default=False,
        help_text="Preview changes without saving"
    )
    verbose = models.BooleanField(
        default=False,
        help_text="Include detailed logging"
    )
    
    # Custom parameters (task-specific)
    extra_params = models.JSONField(
        default=dict, blank=True,
        help_text="Additional task-specific parameters"
    )
    
    class Meta:
        db_table = 'scheduler_task_config'
        verbose_name = 'Task Configuration'
        verbose_name_plural = 'Task Configurations'
    
    def __str__(self):
        return f"Config for {self.task.name}"
    
    def as_kwargs(self) -> dict:
        """Convert config to task kwargs."""
        kwargs = {
            'limit': self.limit,
            'batch_size': self.batch_size,
        }
        if self.app_filter:
            kwargs['app'] = self.app_filter
        if self.model_filter:
            kwargs['model'] = self.model_filter
        if self.dry_run:
            kwargs['dry_run'] = True
        if self.extra_params:
            kwargs.update(self.extra_params)
        return kwargs
