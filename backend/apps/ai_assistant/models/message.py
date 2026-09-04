"""
AiMessage — unified model for all user-AI and AI-AI interactions.

Every interaction between any two actors (user, Alice, Allie, Noelle,
Natalie, Nora, Sally, WCHQ, Athena) is a message. Messages can be:

  feedback    — user tip, correction, change request
  help_lookup — shift-for-help query (logged for frequency analysis)
  chat        — conversational exchange
  question    — explicit question expecting an answer
  answer      — response to a question
  observation — Alice/agent pattern observation
  directive   — instruction from one agent to another
  forward     — message forwarded to another actor (e.g., to WCHQ)

Messages are the atoms of interaction. They can be:
  - Threaded (parent FK for conversations)
  - Batched (batch_id groups related messages)
  - Bundled (flows through Connection/Bundle sync infrastructure)
  - Forwarded (forward_of FK tracks provenance)

Actors are identified by name, not FK. Agents aren't contacts.
Users are identified by name + contact_id when available.

    User types feedback about bill_to
        → AiMessage(sender='bill', receiver='alice', kind='feedback')

    Alice forwards to WCHQ
        → AiMessage(sender='alice', receiver='wchq', kind='forward',
                     forward_of=original_message)

    Allie sends pattern to Alice
        → AiMessage(sender='allie', receiver='alice', kind='observation')
"""
from django.db import models
from common.models import BaseModel


class AiMessage(BaseModel):
    """A single interaction between any two actors in the system."""

    KIND_CHOICES = [
        ('feedback', 'User feedback — tip, correction, change request'),
        ('help_lookup', 'Help lookup — shift-for-help query'),
        ('chat', 'Conversational exchange'),
        ('question', 'Question expecting an answer'),
        ('answer', 'Answer to a question'),
        ('observation', 'Agent pattern observation'),
        ('directive', 'Instruction between agents'),
        ('forward', 'Forwarded message'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending — not yet processed'),
        ('read', 'Read — seen by receiver'),
        ('reviewed', 'Reviewed — classified by Alice/admin'),
        ('actioned', 'Actioned — created task, updated help, etc.'),
        ('forwarded', 'Forwarded to another actor'),
        ('resolved', 'Resolved — no further action needed'),
        ('rejected', 'Rejected — not actionable'),
    ]

    # What kind of message
    kind = models.CharField(
        max_length=20, choices=KIND_CHOICES, db_index=True,
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True,
    )

    # Who → Who
    sender = models.CharField(
        max_length=100, db_index=True,
        help_text='Actor name: user login, agent name (alice, allie, noelle, etc.), or wchq.',
    )
    sender_contact_id = models.IntegerField(
        null=True, blank=True,
        help_text='Contact FK when sender is a user. Null for agents.',
    )
    receiver = models.CharField(
        max_length=100, db_index=True,
        help_text='Actor name: alice, allie, wchq, bill, etc.',
    )
    receiver_contact_id = models.IntegerField(
        null=True, blank=True,
        help_text='Contact FK when receiver is a user. Null for agents.',
    )

    # Content
    subject = models.CharField(
        max_length=200, blank=True,
        help_text='Short subject line — auto-generated from context if blank.',
    )
    body = models.TextField(
        help_text='The message content.',
    )

    # Context — what was the user looking at when they sent this
    context = models.JSONField(
        default=dict, blank=True,
        help_text='Structured context: model, field, page, component, source_path.',
    )

    # Threading — self-FK for conversations
    parent = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='replies',
        help_text='Parent message in a thread.',
    )

    # Forwarding — track provenance
    forward_of = models.ForeignKey(
        'self', null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='forwards',
        help_text='Original message this was forwarded from.',
    )

    # Batching — group related messages
    batch_id = models.CharField(
        max_length=50, blank=True, db_index=True,
        help_text='Groups related messages. E.g., all feedback from one help session.',
    )

    # Sync — for Connection/Bundle infrastructure
    source_instance = models.UUIDField(
        null=True, blank=True, db_index=True,
        help_text='UUID of the WC3 instance that created this message.',
    )

    class Meta:
        db_table = 'ai_message'
        ordering = ['-dt_created']
        indexes = [
            models.Index(fields=['kind', 'status'], name='aimsg_kind_status_idx'),
            models.Index(fields=['sender', '-dt_created'], name='aimsg_sender_dt_idx'),
            models.Index(fields=['receiver', '-dt_created'], name='aimsg_receiver_dt_idx'),
            models.Index(fields=['batch_id'], name='aimsg_batch_idx'),
        ]

    def __str__(self):
        return f'{self.sender}→{self.receiver} [{self.kind}]: {self.subject or self.body[:60]}'
