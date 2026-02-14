"""
RefsMismatchLog — daily audit log for FK ↔ refs.links discrepancies.

When the React front-end loads a detail page it fetches related records both
by foreign-key (e.g. Contact.customer_id == 82) and by the JSON refs blob
(customer.refs.links.contact == [3, 5]).  Any divergence is POSTed here so
we can track how often and which functions produce mismatches.

The log is designed for periodic review:
  • Which models have the most mismatches?
  • Are specific functions (save, import, migration) the root cause?
  • Trend over time — are mismatches decreasing as we consolidate on FKs?
"""

from django.db import models
from common.models import BaseModel


class RefsMismatchLog(BaseModel):
    """One row per detected mismatch between FK-based and refs-based record sets."""

    class Meta:
        db_table = "refs_mismatch_log"
        indexes = [
            models.Index(fields=["parent_model", "dt_created"]),
            models.Index(fields=["related_model", "dt_created"]),
            models.Index(fields=["mismatch_type", "dt_created"]),
        ]
        ordering = ["-dt_created"]

    # Which parent record was compared (e.g. model=customer, id=82)
    parent_model = models.CharField(max_length=50, help_text="Parent model name (e.g. customer)")
    parent_id = models.BigIntegerField(help_text="Parent record ID")

    # Which related model we checked (e.g. contact)
    related_model = models.CharField(max_length=50, help_text="Related model name (e.g. contact)")

    # FK field used for the FK-based query (e.g. customer_id)
    fk_field = models.CharField(max_length=50, help_text="FK field name on the related model")

    # Mismatch classification
    MISMATCH_TYPES = [
        ("fk_only", "Record found by FK but missing from refs.links"),
        ("refs_only", "Record in refs.links but FK does not match"),
        ("both_differ", "Both exist but sets differ"),
    ]
    mismatch_type = models.CharField(max_length=20, choices=MISMATCH_TYPES, help_text="Type of mismatch detected")

    # The actual discrepant IDs
    fk_ids = models.JSONField(default=list, help_text="IDs found via FK query")
    refs_ids = models.JSONField(default=list, help_text="IDs found in refs.links")
    only_in_fk = models.JSONField(default=list, help_text="IDs present in FK but missing from refs")
    only_in_refs = models.JSONField(default=list, help_text="IDs present in refs but missing from FK")

    # Context: which function / caller triggered the comparison
    caller = models.CharField(max_length=200, blank=True, help_text="Function or endpoint that triggered the comparison")
    user_id = models.BigIntegerField(null=True, blank=True, help_text="User who triggered the check (if known)")

    # Optional notes / details
    details = models.JSONField(default=dict, blank=True, help_text="Additional context")

    def __str__(self):
        return (
            f"RefsMismatch: {self.parent_model}#{self.parent_id} ↔ "
            f"{self.related_model} ({self.mismatch_type}) "
            f"FK={self.fk_ids} refs={self.refs_ids}"
        )

    # ------------------------------------------------------------------
    # Convenience class method
    # ------------------------------------------------------------------
    @classmethod
    def log_mismatch(
        cls,
        *,
        parent_model: str,
        parent_id: int,
        related_model: str,
        fk_field: str,
        fk_ids: list,
        refs_ids: list,
        caller: str = "",
        user_id: int | None = None,
        details: dict | None = None,
    ) -> "RefsMismatchLog | None":
        """Compare FK-based vs refs-based ID sets and log if they differ.

        Returns the created log entry, or None when the sets match.
        """
        fk_set = set(fk_ids)
        refs_set = set(refs_ids)

        if fk_set == refs_set:
            return None  # No mismatch

        only_fk = sorted(fk_set - refs_set)
        only_refs = sorted(refs_set - fk_set)

        if only_fk and not only_refs:
            mismatch_type = "fk_only"
        elif only_refs and not only_fk:
            mismatch_type = "refs_only"
        else:
            mismatch_type = "both_differ"

        return cls.objects.create(
            parent_model=parent_model,
            parent_id=parent_id,
            related_model=related_model,
            fk_field=fk_field,
            mismatch_type=mismatch_type,
            fk_ids=sorted(fk_set),
            refs_ids=sorted(refs_set),
            only_in_fk=only_fk,
            only_in_refs=only_refs,
            caller=caller,
            user_id=user_id,
            details=details or {},
        )


__all__ = ["RefsMismatchLog"]
