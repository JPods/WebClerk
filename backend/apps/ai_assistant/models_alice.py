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


class AliceCoachingLog(BaseModel):
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


class AliceInsight(BaseModel):
    """Agent insight record — one per agent per contact per subject.

    Multiple agents build insight records at multiple granularities.
    The same schema serves Alice.everywhere (every installation),
    Alice.wchq (headquarters aggregation), and Athena (security).

    agent   | subject_type | subject_key        | What the agent learns
    ------- | ------------ | ------------------ | ------------------------------------
    alice   | user         | (empty)            | How this person works overall
    alice   | model        | "contact"          | How this person uses contacts
    alice   | model        | "invoice"          | How this person handles invoices
    alice   | flow         | "order_to_invoice" | Order→invoice→payment patterns
    alice   | flow         | "dedup"            | How this person handles dedup
    alice   | sync         | "wchq"             | Sync patterns with WC_HQ
    alice   | sync         | "peer_store_42"    | Sync with a specific peer
    alice   | coaching     | "gl_basics"        | Progress on a coaching track
    athena  | security     | "login"            | Login patterns, anomalies
    athena  | risk         | "bulk_delete"       | Risk behavior: mass record deletion
    athena  | user         | (empty)            | Overall security posture for user

    Common frame of reference:
    - Alice.everywhere and Alice.wchq share this schema
    - WC_HQ aggregates anonymized insight patterns across installations
    - Athena writes security/risk insights using the same structure
    - subject_type + subject_key is the common vocabulary

    This is NOT the user's preferences (that's contact.metadata.wcui).
    These are agent-written records. Agents observe, agents write.
    Users can read them. The config JSONField schema varies by
    subject_type — each agent/subject combination evolves its own
    structure as the agent learns what matters.

    config JSONField by subject_type:

    user:     skill_levels, navigation_patterns, communication_style,
              pain_points, strengths, coaching_notes[]
    model:    fields_used, fields_ignored, common_filters, avg_time_on_page,
              error_patterns, preferred_layout
    flow:     steps_completed, steps_skipped, avg_duration, common_errors,
              last_successful_dt
    sync:     frequency, last_result, conflict_count, resolution_patterns
    coaching: drills_completed, scores, time_spent, next_recommended
    security: last_review_dt, flags[], cleared_flags[], risk_score
    risk:     occurrences, severity, last_occurrence_dt, action_taken
    """
    # No choices constraint — users may add their own agents.
    # Built-in: alice (bookkeeper/coach), athena (security/risk).
    # Custom agents register themselves by writing insight records.

    agent = models.CharField(
        max_length=50, default='alice', db_index=True,
        help_text='Agent that wrote this insight (alice, athena, or user-defined)',
    )
    SUBJECT_CHOICES = [
        ('user', 'User Profile'),
        ('model', 'Model Usage'),
        ('flow', 'Transaction Flow'),
        ('sync', 'Sync Pattern'),
        ('coaching', 'Coaching Track'),
        ('security', 'Security Review'),
        ('risk', 'Risk Assessment'),
        ('system', 'System Health'),
    ]
    contact = models.ForeignKey(
        'core.Contact', on_delete=models.CASCADE,
        related_name='alice_insights',
        help_text='The user Alice is learning about',
    )
    subject_type = models.CharField(
        max_length=20, choices=SUBJECT_CHOICES, db_index=True,
        help_text='Category of insight',
    )
    subject_key = models.CharField(
        max_length=100, blank=True, default='',
        help_text='Specific subject within the type (model name, flow name, etc.)',
    )

    # Summary — Alice's one-line assessment, updated periodically
    summary = models.TextField(
        blank=True,
        help_text='Alice one-line summary for this subject',
    )

    # config is inherited from BaseModel (ConfigMixin).
    # Agent writes structured understanding here; schema varies by subject_type.

    # Engagement metrics
    observation_count = models.IntegerField(
        default=0,
        help_text='Observations Alice has made on this subject',
    )
    dt_last_interaction = models.BigIntegerField(
        default=0,
        help_text='Last time Alice observed activity on this subject (epoch ms)',
    )
    dt_last_updated = models.BigIntegerField(
        default=0,
        help_text='Last time Alice updated this insight (epoch ms)',
    )

    class Meta:
        db_table = 'alice_insights'
        unique_together = [('agent', 'contact', 'subject_type', 'subject_key')]
        indexes = [
            models.Index(fields=['agent', 'contact', 'subject_type'], name='aliceins_agent_ct_type_idx'),
            models.Index(fields=['agent', 'subject_type', 'subject_key'], name='aliceins_agent_type_key_idx'),
            models.Index(fields=['dt_last_updated'], name='aliceins_last_updated_idx'),
        ]

    def __str__(self):
        name = getattr(self.contact, 'attention', None) or f'Contact {self.contact_id}'
        key = f':{self.subject_key}' if self.subject_key else ''
        return f'{self.agent} {self.subject_type}{key} — {name}'
