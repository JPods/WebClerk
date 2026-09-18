"""
Episode Model — episodic memory for every WC3 instance.

Episodes record what happened, what was tried, what was learned, and the
principle that emerged. They are the team's experiential memory — the
structured form of TFTS (try-fail-try-succeed) arcs, scars, wins,
faults, and commerce events.

Every WC3 instance creates episodes locally. Episodes flow like
telemetry pings — published and generally available. Connected nodes
pick up the ones they find useful.

WCHQ harvests all episodes from connected instances. Athena and Allie
review them (some will be foolish). Reviewed episodes become available
in the feed. Other instances poll the feed and ingest what's relevant.

    Any instance creates episode
            ↓
    WCHQ harvests (pulls from all connected instances)
            ↓
    Athena + Allie review (grade, filter)
            ↓
    Approved episodes available in feed
            ↓
    Other instances pick up what's useful

Episode types:
  tfts      — complete try-fail-try-succeed arc (most valuable)
  fault     — system-detected problem (Noelle, Alice, Athena)
  scar      — something that cost time, money, or trust
  commerce  — commerce event worth remembering (pricing anomaly, etc.)
  session   — session-level summary
  pattern   — recurring pattern detected by Alice

Sync rules:
  - Episodes are published like telemetry — generally available
  - Actors are PII-scrubbed before leaving the source instance
  - episode_id (EP-{hash}) is the natural key for dedup across instances
  - WCHQ reviews before episodes enter the general feed
"""
from django.db import models
from common.models import BaseModel


class Episode(BaseModel):
    """An experiential memory record — what happened, what was learned.

    Aligns with Allie's episodes table (allie database) for sync.
    Every WC3 instance can create, store, and exchange episodes
    through the Connection/Bundle infrastructure.
    """
    EPISODE_TYPE_CHOICES = [
        ('tfts', 'Try-Fail-Try-Succeed'),
        ('fault', 'System Fault'),
        ('scar', 'Scar (cost something)'),
        ('commerce', 'Commerce Event'),
        ('session', 'Session Summary'),
        ('pattern', 'Detected Pattern'),
    ]
    DOMAIN_CHOICES = [
        ('SU', 'SketchUp'),
        ('PH', 'Physical'),
        ('RT', 'Route-Time'),
        ('WC3', 'WebClerk'),
        ('SYS', 'System'),
        ('ALLIE', 'Allie'),
        ('CROSS', 'Cross-domain'),
    ]
    OUTCOME_CHOICES = [
        ('resolved', 'Resolved'),
        ('unresolved', 'Unresolved'),
        ('ongoing', 'Ongoing'),
    ]
    SEVERITY_CHOICES = [
        ('lesson', 'Lesson'),
        ('scar', 'Scar'),
        ('win', 'Win'),
    ]

    # Natural key for dedup across instances — EP-{hash}
    episode_id = models.CharField(
        max_length=20, unique=True, db_index=True,
        help_text='Natural key: EP-{hash}. Used for dedup across instances.',
    )

    # Classification
    episode_type = models.CharField(
        max_length=30, choices=EPISODE_TYPE_CHOICES, db_index=True,
    )
    domain = models.CharField(
        max_length=20, choices=DOMAIN_CHOICES, default='CROSS', db_index=True,
    )
    severity = models.CharField(
        max_length=20, choices=SEVERITY_CHOICES, default='lesson', db_index=True,
    )
    outcome = models.CharField(
        max_length=20, choices=OUTCOME_CHOICES, default='unresolved', db_index=True,
    )

    # Content
    title = models.CharField(max_length=200, db_index=True)
    narrative = models.TextField(
        blank=True,
        help_text='Full story: problem, what was tried, result, what was revealed.',
    )
    principle = models.TextField(
        blank=True,
        help_text='The lesson learned — the rule that made the final attempt obvious.',
    )

    # Context
    actors = models.JSONField(
        default=list, blank=True,
        help_text='Who was involved (scrubbed before upstream push).',
    )
    related_episodes = models.JSONField(
        default=list, blank=True,
        help_text='episode_id list of related episodes.',
    )
    tags = models.JSONField(
        default=list, blank=True,
        help_text='Searchable tags.',
    )
    source_ref = models.CharField(
        max_length=200, blank=True,
        help_text='Origin reference: tfts:filename, retro:id, sync:connection_ida.',
    )

    # Recall tracking — how often this episode is retrieved
    recall_count = models.IntegerField(
        default=0,
        help_text='Times recalled via similarity search.',
    )
    dt_last_recalled = models.BigIntegerField(
        default=0,
        help_text='Last recall timestamp (epoch ms).',
    )

    # Episode timing (when the event occurred, not when the record was created)
    dt_start = models.BigIntegerField(
        default=0,
        help_text='When the episode began (epoch ms).',
    )
    dt_end = models.BigIntegerField(
        default=0,
        help_text='When the episode ended (epoch ms).',
    )

    # Sync provenance — uuid is the cross-database identity
    source_instance = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text='UUID of the WC3 instance that created this episode.',
    )

    # Review gate — Athena + Allie review before episodes enter the feed
    REVIEW_STATUS_CHOICES = [
        ('raw', 'Raw — not yet reviewed'),
        ('pending', 'Pending review'),
        ('approved', 'Approved for feed'),
        ('rejected', 'Rejected (foolish or harmful)'),
        ('archived', 'Archived (superseded or stale)'),
    ]
    review_status = models.CharField(
        max_length=20, choices=REVIEW_STATUS_CHOICES,
        default='raw', db_index=True,
        help_text='Athena + Allie review gate. Only approved episodes enter the feed.',
    )
    reviewed_by = models.CharField(
        max_length=50, blank=True,
        help_text='Who reviewed: athena, allie, or admin username.',
    )
    dt_reviewed = models.BigIntegerField(
        default=0,
        help_text='When the review happened (epoch ms).',
    )
    review_note = models.TextField(
        blank=True,
        help_text='Reviewer comment — why rejected, what was improved, etc.',
    )
    quality_score = models.FloatField(
        default=0.0,
        help_text='Quality rating: -1.0 (harmful) to 1.0 (excellent). Set by reviewer.',
    )

    class Meta:
        db_table = 'ai_episode'
        indexes = [
            models.Index(fields=['episode_type', 'domain'], name='ep_type_domain_idx'),
            models.Index(fields=['severity', 'outcome'], name='ep_severity_outcome_idx'),
            models.Index(fields=['-dt_created'], name='ep_dt_created_idx'),
            models.Index(fields=['-recall_count'], name='ep_recall_count_idx'),
            models.Index(fields=['review_status'], name='ep_review_status_idx'),
            models.Index(fields=['source_instance'], name='ep_source_instance_idx'),
        ]
        ordering = ['-dt_created']

    def __str__(self):
        return f'[{self.domain}] {self.title[:80]}'
