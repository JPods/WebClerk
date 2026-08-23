"""
AI Assistant models — conversation history, feedback tracking, and inventory events.
"""
import uuid
from django.conf import settings

# Import Alice-specific models so Django discovers them
from apps.ai_assistant.models_alice import AliceObservation, AlicePreset, AliceCoachingLog, AliceInsight  # noqa: F401
from django.contrib.postgres.fields import ArrayField
from django.db import models


# =============================================================================
# INVENTORY EVENT — LLM Observational Learning
# =============================================================================

class InventoryEvent(models.Model):
    """
    Structured event log for LLM observational learning.
    Captures both data changes and semantic context for inventory operations.
    
    Used by the LLM to:
    - Learn user patterns
    - Generate natural language summaries
    - Detect anomalies and suggest actions
    """
    
    # Identity
    event_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    # Event Classification
    CATEGORY_CHOICES = [
        ('transaction', 'Transaction Activity'),
        ('adjustment', 'Manual Adjustment'),
        ('transfer', 'Inter-Location Transfer'),
        ('receipt', 'Goods Receipt'),
        ('count', 'Physical Count'),
        ('reorder', 'Reorder Action'),
        ('alert', 'System Alert'),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    
    EVENT_TYPE_CHOICES = [
        # Transaction events
        ('order_line_add', 'Line added to order'),
        ('order_line_update', 'Line quantity changed'),
        ('order_line_delete', 'Line removed from order'),
        ('order_convert_invoice', 'Order converted to invoice'),
        ('invoice_line_add', 'Line added to invoice'),
        ('invoice_line_update', 'Invoice line changed'),
        ('invoice_line_delete', 'Invoice line removed'),
        ('invoice_pack', 'Invoice lines packed/shipped'),
        # Purchase events
        ('po_create', 'Purchase order created'),
        ('po_line_add', 'PO line added'),
        ('po_line_update', 'PO line changed'),
        ('po_line_delete', 'PO line removed'),
        ('po_receive', 'PO goods received'),
        # Proposal events
        ('proposal_line_add', 'Line added to proposal'),
        ('proposal_line_update', 'Proposal line changed'),
        ('proposal_line_delete', 'Proposal line removed'),
        # Adjustment events
        ('qty_adjust_up', 'Quantity increased'),
        ('qty_adjust_down', 'Quantity decreased'),
        ('cost_adjust', 'Unit cost changed'),
        # Alert events
        ('below_reorder', 'Fell below reorder point'),
        ('below_safety', 'Fell below safety stock'),
        ('overstock', 'Exceeded max stock level'),
        # Pending processed
        ('pending_processed', 'Pending record processed'),
    ]
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES, db_index=True)
    
    # Actor
    user_id = models.IntegerField(null=True, blank=True, db_index=True)
    user_name = models.CharField(max_length=100, blank=True, default='')
    is_system = models.BooleanField(default=False)
    
    # Subject (what was affected)
    item_id = models.IntegerField(null=True, blank=True, db_index=True)
    item_code = models.CharField(max_length=50, blank=True, default='')
    item_description = models.CharField(max_length=255, blank=True, default='')
    
    # Context (related entities)
    transaction_type = models.CharField(max_length=20, blank=True, default='')
    transaction_id = models.IntegerField(null=True, blank=True, db_index=True)
    transaction_ida = models.CharField(max_length=50, blank=True, default='')
    line_id = models.IntegerField(null=True, blank=True)
    customer_id = models.IntegerField(null=True, blank=True)
    customer_name = models.CharField(max_length=100, blank=True, default='')
    vendor_id = models.IntegerField(null=True, blank=True)
    vendor_name = models.CharField(max_length=100, blank=True, default='')
    
    # Quantitative Data
    quantity_before = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    quantity_after = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    quantity_delta = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    
    # Inventory Buckets (snapshot after event)
    on_hand = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    on_order = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    on_purchase = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    available = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    reorder_point = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    
    # Semantic Context (for LLM consumption)
    reason = models.TextField(blank=True, default='')
    tags = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
    )
    
    # Raw payload for detailed analysis
    payload = models.JSONField(default=dict, blank=True)
    
    # LLM Processing
    llm_summary = models.TextField(blank=True, default='')
    llm_processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'ai_inventory_event'
        indexes = [
            models.Index(fields=['created_at', 'category']),
            models.Index(fields=['item_id', 'created_at']),
            models.Index(fields=['transaction_id', 'transaction_type']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.event_type}: {self.item_code or self.item_id} ({self.created_at:%Y-%m-%d %H:%M})"


# =============================================================================
# CONVERSATION & MESSAGE — Chat History
# =============================================================================

class Conversation(models.Model):
    """A conversation session between a user and the AI assistant."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_conversations",
        null=True, blank=True,
    )
    session_key = models.CharField(max_length=64, blank=True, default="")
    context_page = models.CharField(
        max_length=255, blank=True, default="",
        help_text="The page/view the user was on when starting the conversation",
    )
    dt_created = models.DateTimeField(auto_now_add=True)
    dt_modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-dt_created"]

    def __str__(self):
        return f"Conversation {self.pk} — {self.user or 'anonymous'}"


class Message(models.Model):
    """A single message in a conversation (user question or AI response)."""
    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
        ("system", "System"),
    ]
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField()
    sources = models.JSONField(
        default=list, blank=True,
        help_text="List of source documents used for RAG context",
    )
    feedback = models.SmallIntegerField(
        null=True, blank=True,
        help_text="User feedback: 1=helpful, -1=not helpful",
    )
    dt_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["dt_created"]

    def __str__(self):
        return f"{self.role}: {self.content[:60]}"


# =============================================================================
# CODING SESSION — Developer Activity Learning
# =============================================================================

class CodingSession(models.Model):
    """
    Captures a development session for LLM observational learning.
    
    Records what was worked on, problems encountered, solutions applied,
    and learnings extracted. Used to build institutional knowledge over time.
    """
    
    # Identity
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    
    # Timing
    started_at = models.DateTimeField(db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Classification
    SESSION_TYPE_CHOICES = [
        ('feature', 'New Feature'),
        ('bugfix', 'Bug Fix'),
        ('refactor', 'Refactoring'),
        ('test', 'Testing'),
        ('docs', 'Documentation'),
        ('devops', 'DevOps / Infrastructure'),
        ('debug', 'Debugging Session'),
        ('exploration', 'Code Exploration'),
        ('review', 'Code Review'),
    ]
    session_type = models.CharField(max_length=20, choices=SESSION_TYPE_CHOICES, db_index=True)
    
    # Scope
    apps = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
        help_text="Django apps touched (e.g., ['transactions', 'products'])"
    )
    models_touched = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
        help_text="Model names touched (e.g., ['Order', 'OrderLine'])"
    )
    files_changed = ArrayField(
        models.CharField(max_length=255),
        default=list,
        blank=True,
        help_text="File paths changed during session"
    )
    
    # Problem → Solution
    problem = models.TextField(
        blank=True,
        default='',
        help_text="What problem was being solved?"
    )
    solution = models.TextField(
        blank=True,
        default='',
        help_text="How was it solved?"
    )
    
    # Learnings
    learnings = models.TextField(
        blank=True,
        default='',
        help_text="Key takeaways, patterns discovered, gotchas to remember"
    )
    
    # Error tracking
    errors_encountered = ArrayField(
        models.TextField(),
        default=list,
        blank=True,
        help_text="Error messages encountered during session"
    )
    error_fixes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Map of error → fix applied"
    )
    
    # Context
    tags = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
        help_text="Semantic tags for categorization"
    )
    related_sessions = ArrayField(
        models.UUIDField(),
        default=list,
        blank=True,
        help_text="UUIDs of related sessions"
    )
    
    # AI processing
    llm_summary = models.TextField(
        blank=True,
        default='',
        help_text="LLM-generated summary of the session"
    )
    llm_processed_at = models.DateTimeField(null=True, blank=True)
    
    # Raw data
    conversation_log = models.TextField(
        blank=True,
        default='',
        help_text="Raw conversation with AI assistant"
    )
    git_commits = ArrayField(
        models.CharField(max_length=40),
        default=list,
        blank=True,
        help_text="Git commit hashes from this session"
    )
    
    class Meta:
        db_table = 'coding_session'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['started_at', 'session_type']),
            models.Index(fields=['session_type']),
        ]
    
    def __str__(self):
        return f"{self.session_type}: {self.problem[:50] if self.problem else 'Untitled'}"


class ErrorPattern(models.Model):
    """
    Captures recurring error patterns and their fixes.
    Built from CodingSession.error_fixes over time.
    """
    
    # Identity
    pattern_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    
    # Pattern matching
    error_text = models.TextField(help_text="The error message or pattern to match")
    error_regex = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text="Optional regex for flexible matching"
    )
    
    # Classification
    CATEGORY_CHOICES = [
        ('import', 'Import Error'),
        ('type', 'Type Error'),
        ('runtime', 'Runtime Error'),
        ('test', 'Test Failure'),
        ('lint', 'Lint / Style'),
        ('build', 'Build / Compile'),
        ('db', 'Database'),
        ('api', 'API / HTTP'),
        ('config', 'Configuration'),
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    
    # Diagnosis
    cause = models.TextField(help_text="Root cause explanation")
    fix = models.TextField(help_text="How to fix it")
    prevention = models.TextField(
        blank=True,
        default='',
        help_text="How to prevent it in the future"
    )
    
    # Stats
    occurrences = models.IntegerField(default=1)
    last_seen = models.DateTimeField(auto_now=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    
    # Context
    related_files = ArrayField(
        models.CharField(max_length=255),
        default=list,
        blank=True,
        help_text="Files commonly involved when this error occurs"
    )
    tags = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
    )
    
    class Meta:
        db_table = 'error_pattern'
        ordering = ['-occurrences', '-last_seen']
    
    def __str__(self):
        return f"{self.category}: {self.error_text[:60]}"


# =============================================================================
# GIT EVENT — Code Change Observational Learning
# =============================================================================

class GitEvent(models.Model):
    """
    Captures git commits and file changes for LLM learning.
    
    Used to:
    - Track what files change together (co-change patterns)
    - Learn from commit messages and diffs
    - Detect schema drift when outdated code is pushed
    """
    
    # Identity
    event_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    commit_hash = models.CharField(max_length=40, unique=True, db_index=True)
    
    # Timing
    committed_at = models.DateTimeField(db_index=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    # Author
    author_name = models.CharField(max_length=100)
    author_email = models.CharField(max_length=255)
    
    # Commit info
    message = models.TextField()
    branch = models.CharField(max_length=100, blank=True, default='')
    
    # Files changed
    files_added = ArrayField(
        models.CharField(max_length=255),
        default=list,
        blank=True,
    )
    files_modified = ArrayField(
        models.CharField(max_length=255),
        default=list,
        blank=True,
    )
    files_deleted = ArrayField(
        models.CharField(max_length=255),
        default=list,
        blank=True,
    )
    
    # Stats
    lines_added = models.IntegerField(default=0)
    lines_deleted = models.IntegerField(default=0)
    
    # Classification
    COMMIT_TYPE_CHOICES = [
        ('feature', 'New Feature'),
        ('bugfix', 'Bug Fix'),
        ('refactor', 'Refactoring'),
        ('docs', 'Documentation'),
        ('test', 'Test'),
        ('chore', 'Maintenance'),
        ('style', 'Code Style'),
        ('perf', 'Performance'),
        ('ci', 'CI/CD'),
        ('unknown', 'Unknown'),
    ]
    commit_type = models.CharField(
        max_length=20,
        choices=COMMIT_TYPE_CHOICES,
        default='unknown',
        db_index=True,
    )
    
    # Apps/models touched (inferred from file paths)
    apps_touched = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
    )
    models_touched = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
    )
    
    # LLM processing
    llm_summary = models.TextField(blank=True, default='')
    llm_processed_at = models.DateTimeField(null=True, blank=True)
    
    # Drift detection
    has_drift_issues = models.BooleanField(default=False)
    drift_issues = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = 'git_event'
        ordering = ['-committed_at']
        indexes = [
            models.Index(fields=['committed_at', 'author_email']),
            models.Index(fields=['commit_type']),
        ]
    
    def __str__(self):
        return f"{self.commit_hash[:8]}: {self.message[:50]}"


class SchemaDrift(models.Model):
    """
    Tracks schema/API drift issues detected in commits.
    
    Flags when:
    - Code references deprecated field names
    - API shapes don't match current models
    - Old patterns are reintroduced
    """
    
    # Identity
    drift_id = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    
    # Source
    git_event = models.ForeignKey(
        GitEvent,
        on_delete=models.CASCADE,
        related_name='drift_records',
        null=True,
        blank=True,
    )
    file_path = models.CharField(max_length=255, db_index=True)
    line_number = models.IntegerField(null=True, blank=True)
    
    # Drift type
    DRIFT_TYPE_CHOICES = [
        ('deprecated_field', 'Uses deprecated field name'),
        ('old_api_shape', 'Uses outdated API response shape'),
        ('banned_pattern', 'Uses banned code pattern'),
        ('missing_migration', 'Schema change without migration'),
        ('stale_import', 'Imports from moved/deleted module'),
        ('type_mismatch', 'Type doesn\'t match current schema'),
    ]
    drift_type = models.CharField(max_length=30, choices=DRIFT_TYPE_CHOICES, db_index=True)
    
    # Severity
    SEVERITY_CHOICES = [
        ('error', 'Error - Must fix'),
        ('warning', 'Warning - Should fix'),
        ('info', 'Info - Consider updating'),
    ]
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='warning')
    
    # Details
    description = models.TextField()
    current_value = models.CharField(max_length=255, blank=True, default='')
    expected_value = models.CharField(max_length=255, blank=True, default='')
    fix_suggestion = models.TextField(blank=True, default='')
    
    # Status
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.CharField(max_length=100, blank=True, default='')
    resolved_in_commit = models.CharField(max_length=40, blank=True, default='')
    
    # Timing
    detected_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'schema_drift'
        ordering = ['-detected_at']
        indexes = [
            models.Index(fields=['drift_type', 'is_resolved']),
            models.Index(fields=['file_path']),
        ]
    
    def __str__(self):
        return f"{self.drift_type}: {self.file_path}"
