"""
LinkageEntry - Unified linkage model for relating records across tables.

Design: Each row represents ONE link entry. Entries are grouped by `group_id`.
A record (model_name, record_id) can only belong to ONE group (DB-enforced uniqueness).

Usage:
    # Create a new group with entries
    group_id = LinkageEntry.next_group_id()
    LinkageEntry.objects.create(group_id=group_id, model_name='order', record_id=123)
    LinkageEntry.objects.create(group_id=group_id, model_name='item', record_id=456)
    
    # Find all entries in a group
    entries = LinkageEntry.objects.filter(group_id=group_id)
    
    # Find which group a record belongs to
    entry = LinkageEntry.objects.filter(model_name='order', record_id=123).first()
    if entry:
        group_id = entry.group_id
"""
from __future__ import annotations

from django.db import models, transaction
from django.db.models import Max
from common.models import BaseModel


class LinkageEntry(BaseModel):
    """Single linkage entry - relates a record to a linkage group.
    
    Each row is one link; group_id clusters related links.
    
    Uniqueness: A (model_name, record_id) pair can only appear ONCE,
    enforced at DB level. This means a record can only belong to one group.
    
    Inherits from BaseModel: refs, prefs, metadata, actions, comments, etc.
    Group-level metadata can be stored on any entry, or use a "header" entry.
    """

    # Group identity - entries sharing the same group_id are related
    group_id = models.BigIntegerField(db_index=True, help_text="Links with same group_id form a relationship cluster")
    
    # What this entry links to
    model_name = models.CharField(max_length=255, db_index=True, help_text="Target model (e.g., 'order', 'item', 'contact')")
    record_id = models.BigIntegerField(db_index=True, help_text="ID in target model")
    
    # Classification / description
    purpose = models.CharField(max_length=255, blank=True, null=True, db_index=True, help_text="Linkage purpose/type")
    name = models.CharField(max_length=255, blank=True, null=True, db_index=True, help_text="Human-readable name")
    note = models.TextField(blank=True, default="", help_text="Notes about this specific link")
    
    # Optional: role within the group (e.g., 'source', 'target', 'parent', 'child')
    role = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="Role in the linkage (e.g., 'source', 'target')")
    
    # Sequence for ordering within group
    sequence = models.IntegerField(default=0, db_index=True, help_text="Order within group")

    class Meta:
        db_table = 'linkage_entries'
        constraints = [
            # A record can only be in ONE linkage group
            models.UniqueConstraint(
                fields=['model_name', 'record_id'], 
                name='uniq_linkage_entry_record'
            )
        ]
        indexes = [
            models.Index(fields=['group_id'], name='linkent_group_idx'),
            models.Index(fields=['model_name', 'group_id'], name='linkent_model_group_idx'),
            models.Index(fields=['purpose'], name='linkent_purpose_idx'),
            models.Index(fields=['role'], name='linkent_role_idx'),
        ]
        ordering = ['group_id', 'sequence', 'id']

    def __str__(self) -> str:
        return f"LinkageEntry {self.id}: {self.model_name}:{self.record_id} (group={self.group_id})"

    # -------------------------------------------------------------------------
    # Class methods for group management
    # -------------------------------------------------------------------------
    
    @classmethod
    def next_group_id(cls) -> int:
        """Generate the next available group_id."""
        max_id = cls.objects.aggregate(max_group=Max('group_id'))['max_group']
        return (max_id or 0) + 1

    @classmethod
    def create_group(cls, entries: list[dict], purpose: str = None, name: str = None) -> int:
        """Create a new linkage group with multiple entries atomically.
        
        Args:
            entries: List of dicts with keys: model_name, record_id, optional: role, note, sequence
            purpose: Optional purpose for all entries
            name: Optional name for all entries
            
        Returns:
            The new group_id
            
        Raises:
            ValueError: If any record is already linked elsewhere
        """
        with transaction.atomic():
            group_id = cls.next_group_id()
            
            for i, entry_data in enumerate(entries):
                model_name = entry_data.get('model_name')
                record_id = entry_data.get('record_id')
                
                if not model_name or record_id is None:
                    raise ValueError(f"Entry {i} missing model_name or record_id")
                
                # Check for existing
                existing = cls.objects.filter(model_name=model_name, record_id=record_id).first()
                if existing:
                    raise ValueError(
                        f"Record {model_name}:{record_id} already linked to group {existing.group_id}"
                    )
                
                cls.objects.create(
                    group_id=group_id,
                    model_name=model_name,
                    record_id=record_id,
                    purpose=entry_data.get('purpose', purpose),
                    name=entry_data.get('name', name),
                    note=entry_data.get('note', ''),
                    role=entry_data.get('role'),
                    sequence=entry_data.get('sequence', i),
                )
            
            return group_id

    @classmethod  
    def get_group_entries(cls, group_id: int):
        """Get all entries in a group."""
        return cls.objects.filter(group_id=group_id).order_by('sequence', 'id')

    @classmethod
    def get_record_group(cls, model_name: str, record_id: int) -> int | None:
        """Find which group a record belongs to, if any."""
        entry = cls.objects.filter(model_name=model_name, record_id=record_id).first()
        return entry.group_id if entry else None

    @classmethod
    def group_summary(cls, group_id: int) -> dict:
        """Return a summary of a group: {model_name: [record_ids], ...}"""
        entries = cls.objects.filter(group_id=group_id).values('model_name', 'record_id')
        summary: dict[str, list[int]] = {}
        for e in entries:
            summary.setdefault(e['model_name'], []).append(e['record_id'])
        return summary

    # -------------------------------------------------------------------------
    # Instance methods
    # -------------------------------------------------------------------------

    def add_to_group(self, model_name: str, record_id: int, role: str = None, note: str = '') -> 'LinkageEntry':
        """Add another record to this entry's group.
        
        Raises:
            ValueError: If record already linked elsewhere
        """
        existing = LinkageEntry.objects.filter(model_name=model_name, record_id=record_id).first()
        if existing:
            if existing.group_id == self.group_id:
                return existing  # Already in this group
            raise ValueError(f"Record {model_name}:{record_id} already linked to group {existing.group_id}")
        
        max_seq = LinkageEntry.objects.filter(group_id=self.group_id).aggregate(m=Max('sequence'))['m'] or 0
        return LinkageEntry.objects.create(
            group_id=self.group_id,
            model_name=model_name,
            record_id=record_id,
            purpose=self.purpose,
            name=self.name,
            role=role,
            note=note,
            sequence=max_seq + 1,
        )

    def remove_from_group(self) -> bool:
        """Remove this entry from its group (delete self)."""
        if self.pk:
            self.delete()
            return True
        return False

    def group_entries(self):
        """Get all other entries in the same group."""
        return LinkageEntry.objects.filter(group_id=self.group_id).exclude(pk=self.pk)

    def group_record_ids(self, model_name: str = None) -> list[int]:
        """Get record_ids from the group, optionally filtered by model_name."""
        qs = LinkageEntry.objects.filter(group_id=self.group_id)
        if model_name:
            qs = qs.filter(model_name=model_name)
        return list(qs.values_list('record_id', flat=True))


# Convenience alias for backward compatibility during migration
LinkageHub = LinkageEntry  # Can query LinkageHub.get_group_entries(group_id)
