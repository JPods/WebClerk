"""
Alice Models — Alice's persistent records in the commerce database.

Alice is the bookkeeper, coach, and pattern detector. These models store
what she produces — not her internal state (that's in the allie database).

Three record types:
  - AliceObservation: patterns, anomalies, coaching suggestions
  - AlicePreset: promoted searches, dashboards, workflows (the "paved paths")
  - AliceCoachingLog: training drill completions, user progress

These are commerce_expert records — they ship with the product, sync via
Connection+Bundle, and appear in the DataBrowser.
"""
from django.db import models
from common.models import CoreModel


class AliceObservation(CoreModel):
    """A pattern, anomaly, or coaching suggestion Alice has detected.

    Created by alice-patterns.py (scheduled) or real-time signal handlers.
    Visible to users in the AliceHintBar and Help Dashboard.
    Acknowledged observations are retained for 30 days then pruned.
    """
    CATEGORY_CHOICES = [
        ('pattern', 'Workflow Pattern'),
        ('anomaly', 'Data Anomaly'),
        ('coaching', 'Coaching Suggestion'),
        ('alert', 'Alert'),
        ('search', 'Search Pattern'),
        ('layout', 'Layout Suggestion'),
        ('performance', 'Performance Issue'),
    ]
    SOURCE_CHOICES = [
        ('alice', 'Alice (local)'),
        ('wchq', 'WCHQ (synced)'),
        ('power_user', 'Power User'),
    ]
    PRIORITY_CHOICES = [
        (0, 'Normal'),
        (1, 'Important'),
        (2, 'Urgent'),
    ]

    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='pattern', db_index=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='alice')
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=0)
    message = models.TextField()
    detail = models.TextField(blank=True)  # longer explanation or data

    # Context — what model/record/user this observation is about
    model_name = models.CharField(max_length=50, blank=True, db_index=True)
    record_id = models.BigIntegerField(null=True, blank=True)
    contact = models.ForeignKey(
        'core.Contact', on_delete=models.SET_NULL,
        null=True, blank=True, db_index=True,
        related_name='alice_observations',
    )

    # Lifecycle
    acknowledged = models.BooleanField(default=False, db_index=True)
    dt_acknowledged = models.BigIntegerField(default=0)
    acknowledged_by = models.ForeignKey(
        'core.Contact', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='acknowledged_observations',
    )
    resolved = models.BooleanField(default=False, db_index=True)
    resolution = models.TextField(blank=True)

    # Dedup — prevent duplicate observations for the same issue
    dedup_key = models.CharField(max_length=200, blank=True, db_index=True)

    class Meta:
        db_table = 'alice_observations'
        indexes = [
            models.Index(fields=['category', 'resolved'], name='aliceobs_cat_resolved_idx'),
            models.Index(fields=['contact', 'acknowledged'], name='aliceobs_contact_ack_idx'),
        ]

    def __str__(self):
        return f'[{self.category}] {self.message[:80]}'


class AlicePreset(CoreModel):
    """A promoted search, layout, or workflow — a "paved path."

    Created when Alice or a power user promotes a frequently-used pattern.
    Available to all users. Protected from casual deletion.
    """
    TYPE_CHOICES = [
        ('search', 'Search Preset'),
        ('layout', 'Layout'),
        ('dashboard', 'Dashboard Config'),
        ('workflow', 'Workflow Sequence'),
        ('report', 'Report Preset'),
    ]
    SOURCE_CHOICES = [
        ('alice', 'Alice (pattern detection)'),
        ('wchq', 'WCHQ (synced)'),
        ('power_user', 'Power User'),
    ]

    preset_type = models.CharField(max_length=20, choices=TYPE_CHOICES, db_index=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='alice')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # The preset data — structure depends on preset_type
    # search: {model, term, filters}
    # layout: {model, list, detail, widths}
    # dashboard: {panels: [{model, type, filters}]}
    # workflow: {steps: [{action, params}]}
    # report: {report_name, model, filters, format}
    config = models.JSONField(default=dict)

    # Context
    model_name = models.CharField(max_length=50, blank=True, db_index=True)

    # Usage tracking — Alice watches which presets are actually used
    use_count = models.IntegerField(default=0)
    dt_last_used = models.BigIntegerField(default=0)
    created_by = models.ForeignKey(
        'core.Contact', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_presets',
    )

    class Meta:
        db_table = 'alice_presets'
        indexes = [
            models.Index(fields=['preset_type', 'model_name'], name='alicepreset_type_model_idx'),
        ]

    def __str__(self):
        return f'[{self.preset_type}] {self.name}'


class AliceCoachingLog(CoreModel):
    """Training drill completion and user progress tracking.

    Alice coaches users through training drills. This tracks what
    drills they've completed, how long it took, and whether they
    passed. Feeds into user skill assessment.
    """
    contact = models.ForeignKey(
        'core.Contact', on_delete=models.CASCADE,
        db_index=True,
        related_name='coaching_log',
    )
    drill_id = models.CharField(max_length=50, db_index=True)  # e.g., 'TRAIN-COMM-drill-3'
    document_id = models.BigIntegerField(null=True, blank=True)  # FK to training document
    drill_name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, blank=True)  # 'commission', 'inventory', 'gl', etc.

    # Results
    completed = models.BooleanField(default=False)
    passed = models.BooleanField(default=False)
    score = models.IntegerField(null=True, blank=True)  # 0-100
    duration_seconds = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)  # Alice's coaching notes

    # Timing
    dt_started = models.BigIntegerField(default=0)
    dt_completed = models.BigIntegerField(default=0)

    class Meta:
        db_table = 'alice_coaching_log'
        indexes = [
            models.Index(fields=['contact', 'completed'], name='alicecoach_contact_done_idx'),
            models.Index(fields=['category'], name='alicecoach_category_idx'),
        ]

    def __str__(self):
        status = 'passed' if self.passed else 'completed' if self.completed else 'started'
        return f'{self.drill_name} ({status})'
