from django.db import models

from common.models import BaseModel
from apps.accounts.choices import EROSION_CATEGORY_CHOICES, EROSION_SOURCE_MODEL_CHOICES


class Erosion(BaseModel):
    """
    Erosion Tracker
    ===============
    Captures every event where value is lost between transaction stages,
    currency conversions, late payments, returns, rework, or discounting.

    Two population modes:
      1. Auto-calculated — triggered during invoice/payment saves
         (margin erosion, FX loss, late-payment carrying cost)
      2. Manual — entered via UI or from .metadata annotations
         (rework, shipping errors, disputes)

    Sign convention: `amount` is always POSITIVE — it represents value lost.
    """

    category = models.CharField(
        max_length=50,
        choices=EROSION_CATEGORY_CHOICES,
        db_index=True,
        help_text="Type of value erosion",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Dollar value of erosion (always positive)",
    )
    amount_pct = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        blank=True,
        null=True,
        help_text="Percentage erosion (e.g., 0.11 = 11 margin points lost)",
    )

    # Who is involved
    org = models.ForeignKey(
        'orgs.OrgBase',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='erosion_events',
        help_text="Customer or vendor associated with this erosion",
    )
    contact = models.ForeignKey(
        'core.Contact',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='erosion_events',
        help_text="Rep or salesperson responsible (if applicable)",
    )

    # Source document — the transaction where erosion was detected
    source_model = models.CharField(
        max_length=50,
        choices=EROSION_SOURCE_MODEL_CHOICES,
        help_text="Transaction type where erosion was detected",
    )
    source_id = models.BigIntegerField(
        db_index=True,
        help_text="PK of the source transaction",
    )

    # Parent document — what we're measuring erosion against (ancestor in the chain)
    parent_model = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=EROSION_SOURCE_MODEL_CHOICES,
        help_text="Transaction type being compared (e.g., proposal for margin erosion on invoice)",
    )
    parent_id = models.BigIntegerField(
        blank=True,
        null=True,
        db_index=True,
        help_text="PK of the parent/comparison transaction",
    )

    # Timing
    dt_event = models.DateTimeField(
        blank=True,
        null=True,
        help_text="When the erosion event occurred",
    )

    # Detail
    notes = models.TextField(
        blank=True,
        default='',
        help_text="Free-text explanation of the erosion event",
    )
    is_auto = models.BooleanField(
        default=False,
        help_text="True if auto-calculated during save pipeline, False if manual",
    )

    def __str__(self):
        return f"Erosion #{self.id} {self.category} ${self.amount}"

    class Meta:
        db_table = 'erosion'
        indexes = [
            models.Index(fields=['org', 'category'], name='idx_erosion_org_cat'),
            models.Index(fields=['org', 'dt_event'], name='idx_erosion_org_date'),
            models.Index(fields=['source_model', 'source_id'], name='idx_erosion_source'),
        ]
