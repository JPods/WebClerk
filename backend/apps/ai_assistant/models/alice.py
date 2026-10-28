"""
Alice Models — Alice's persistent records in the commerce database.

Alice is the bookkeeper, coach, and pattern detector. These models store
what she produces — not her internal state (that's in the allie database).

Record types (AliceInsight became core.Lesson, 2026-10-28):
  - AliceObservation: patterns, anomalies, coaching suggestions
  - AlicePreset: promoted searches, dashboards, workflows (the "paved paths")
  (Drill completions are Log rows, purpose coaching — the one log, 2026-10-28.)

These are commerce_expert records — they ship with the product, sync via
Connection+Bundle, and appear in the DataBrowser.
"""
from django.db import models
from common.models import CoreModel, BaseModel


class AliceObservation(BaseModel):
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
        ('schema', 'Pydantic Schema Question'),
        ('console', 'Console Capture'),
        ('escalation', 'Escalation to Claude'),
        ('pii_correction', 'PII Correction'),
        ('bill_question', 'Question for Bill'),
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
    target_model = models.CharField(max_length=50, blank=True, db_index=True)
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


class AlicePreset(BaseModel):
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

    # The preset data lives in config (inherited from CoreModel)
    # Structure depends on preset_type:
    # search: {model, term, filters}
    # layout: {model, list, detail, widths}
    # dashboard: {panels: [{model, type, filters}]}
    # workflow: {steps: [{action, params}]}
    # report: {report_name, model, filters, format}

    # Context
    target_model = models.CharField(max_length=50, blank=True, db_index=True)

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
            models.Index(fields=['preset_type', 'target_model'], name='alicepreset_type_model_idx'),
        ]

    def __str__(self):
        return f'[{self.preset_type}] {self.name}'
