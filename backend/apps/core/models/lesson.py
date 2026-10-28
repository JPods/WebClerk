"""
Lesson — what was learned (core). See the class docstring.
"""
from django.db import models
from common.models import BaseModel


class Lesson(BaseModel):
    """What was learned — one per agent per contact per subject (Bill, 2026-10-28: "not an
    ai.log as much as an ai.lessons"). The third kind of record: a Log is what happened (written
    once), an Action is what to do, a Lesson is what was learned — confirmed, counted, promoted
    or retired, so it changes. refs.links.log names the Log rows it was drawn from. It was
    ai_assistant.AliceInsight (no rows); it lives in core because every agent and person
    teaches and reads it.

    Agents and people build lessons at multiple granularities.
    The same schema serves Alice.everywhere (every installation),
    Alice.wchq (headquarters aggregation), and Athena (security).

    agent   | subject_type | subject_key        | What the agent learns
    ------- | ------------ | ------------------ | ------------------------------------
    alice   | user         | (empty)            | How this person works overall
    alice   | model        | "contact"          | How this person uses contacts
    alice   | model        | "invoice"          | How this person handles invoices
    alice   | flow         | "order_to_invoice" | Order→invoice→cash patterns
    alice   | flow         | "dedup"            | How this person handles dedup
    alice   | sync         | "wchq"             | Sync patterns with WC_HQ
    alice   | sync         | "peer_store_42"    | Sync with a specific peer
    alice   | coaching     | "gl_basics"        | Progress on a coaching track
    athena  | security     | "login"            | Login patterns, anomalies
    athena  | risk         | "bulk_delete"       | Risk behavior: mass record deletion
    athena  | user         | (empty)            | Overall security posture for user

    Common frame of reference:
    - Alice.everywhere and Alice.wchq share this schema
    - WC_HQ aggregates anonymized lessons across installations
    - Athena writes security/risk lessons using the same structure
    - subject_type + subject_key is the common vocabulary

    This is NOT the user's preferences (that's contact.metadata.wcui).
    Agents and people write them; everyone can read them. config.details
    by subject_type:

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
    # Custom agents register themselves by writing lessons.

    agent = models.CharField(
        max_length=50, default='alice', db_index=True,
        help_text='Who learned it: alice, athena, allie, or a person (user-defined allowed)',
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
    contact_id = models.BigIntegerField(
        default=0, db_index=True,
        help_text="Contact id the lesson is about (value, not FK — it survives the contact); "
                  "0 = about no one person. Never null: the unique key treats nulls as distinct",
    )
    subject_type = models.CharField(
        max_length=20, choices=SUBJECT_CHOICES, db_index=True,
        help_text='What kind of subject the lesson is about',
    )
    subject_key = models.CharField(
        max_length=100, blank=True, default='',
        help_text='Specific subject within the type (model name, flow name, etc.)',
    )

    # Summary — Alice's one-line assessment, updated periodically
    summary = models.TextField(
        blank=True,
        help_text='The lesson in one line',
    )

    # config.details (LessonConfig): the structured understanding; its shape varies by
    # subject_type (see the table above).

    # Engagement metrics
    observation_count = models.IntegerField(
        default=0,
        help_text='Times this lesson was observed',
    )
    dt_last_interaction = models.BigIntegerField(
        default=0,
        help_text='Last time the subject was observed (UTC epoch ms)',
    )
    dt_last_updated = models.BigIntegerField(
        default=0,
        help_text='Last time the lesson changed (UTC epoch ms)',
    )

    class Meta:
        db_table = 'lessons'
        unique_together = [('agent', 'contact_id', 'subject_type', 'subject_key')]
        indexes = [
            models.Index(fields=['agent', 'contact_id', 'subject_type'], name='lesson_agent_ct_type_idx'),
            models.Index(fields=['agent', 'subject_type', 'subject_key'], name='lesson_agent_type_key_idx'),
            models.Index(fields=['dt_last_updated'], name='lesson_last_updated_idx'),
        ]

    def __str__(self):
        key = f':{self.subject_key}' if self.subject_key else ''
        return f'Lesson {self.agent} {self.subject_type}{key} — contact {self.contact_id}'


__all__ = ['Lesson']
