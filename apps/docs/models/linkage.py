from django.db import models, transaction
from common.models import BaseModel
from django.utils import timezone
# bulk of this table is in the .refs to relate other tables
# example use is to link line items in orders, proposals, etc. 
# with one document that passes on specs, paths, comments, and other details

#linkage model primarily uses its 
# .refs.links:{"model_name":[], "model_name":[]}
# purpose of these records is to link records 
# that can be linked to many other models. 
# For instance, a linkage record can be 
# shared by records in items, proposal_lines, 
# order_lines, etc... 

class Linkage(BaseModel):
    """Lightweight cross-record linkage hub.

    Stores relationship fan-out centrally in refs.links structure:
      refs = { 'links': { 'table_a': [id,...], 'table_b': [id,...] }}

    Intended to reduce N-N join table sprawl for ad-hoc associations.
    Health & history inherited from BaseModel (metadata.history, metadata.flags etc.).
    """

    
    purpose = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    name = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    note = models.TextField(blank=True, default="", help_text="General note (Linkage-specific text block)")

    class Meta:
        db_table = 'linkages'
        indexes = [
            models.Index(fields=['purpose'], name='linkage_purpose_idx'),
            models.Index(fields=['name'], name='linkage_name_idx'),
        ]

    # --- refs.links helpers -------------------------------------------------
    def _ensure_links(self):
        if not isinstance(self.refs, dict):
            self.refs = {}
        self.refs.setdefault('links', {})
        return self.refs['links']

    def add_link(self, table: str, record_id):
        links = self._ensure_links()
        lst = links.setdefault(table, [])
        if record_id in lst:
            return False
        # Enforce uniqueness at index level: a record belongs to only one linkage
        from apps.docs.models.linkage_index import LinkageIndex
        with transaction.atomic():
            # Pre-check existing to avoid integrity errors
            existing = LinkageIndex.objects.filter(table_name=table, record_id=record_id).first()
            if existing:
                if (getattr(existing, 'linkage_id', None) == self.id) or (getattr(existing, 'linkage', None) and existing.linkage.pk == self.id):
                    lst.append(record_id)
                    self.mark_keywords_dirty()
                    return True
                existing_target = getattr(existing, 'linkage_id', None) or (existing.linkage.pk if getattr(existing, 'linkage', None) else None)
                raise ValueError(f"Record {table}:{record_id} already linked to linkage {existing_target if existing_target else 'unknown'}")
            # Try to create, catch race
            try:
                LinkageIndex.objects.create(linkage=self, table_name=table, record_id=record_id)
            except Exception:
                existing2 = LinkageIndex.objects.filter(table_name=table, record_id=record_id).first()
                if existing2 and ((getattr(existing2, 'linkage_id', None) == self.id) or (getattr(existing2, 'linkage', None) and existing2.linkage.pk == self.id)):
                    pass
                else:
                    existing_target = getattr(existing2, 'linkage_id', None) or (existing2.linkage.pk if (existing2 and getattr(existing2, 'linkage', None)) else None)
                    raise ValueError(f"Record {table}:{record_id} already linked to linkage {existing_target if existing_target else 'unknown'}")
            lst.append(record_id)
            self.mark_keywords_dirty()  # treat as structural change for keyword set
            return True

    def remove_link(self, table: str, record_id):
        links = self._ensure_links()
        lst = links.get(table, [])
        if record_id in lst:
            lst.remove(record_id)
            self.mark_keywords_dirty()
            # Remove index entry if present
            try:
                from apps.docs.models.linkage_index import LinkageIndex
                LinkageIndex.objects.filter(linkage=self, table_name=table, record_id=record_id).delete()
            except Exception:
                pass
            return True
        return False

    def link_counts(self) -> dict[str, int]:
        links = self._ensure_links()
        return {k: len(v) for k, v in links.items() if isinstance(v, list)}

    def clean(self):
        # Ensure all link lists are lists of scalar ids (basic validation)
        links = self._ensure_links()
        for k, v in list(links.items()):
            if not isinstance(v, list):
                links[k] = []
            else:
                # normalize duplicates while preserving order
                seen = set()
                new_list = []
                for item in v:
                    if item not in seen:
                        seen.add(item)
                        new_list.append(item)
                links[k] = new_list

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    # Idempotent bulk add helper driven by a mapping {table_name: [ids]}
    def add_links(self, mapping: dict[str, list[int]], strict: bool = True) -> dict:
        """Add multiple links ensuring index uniqueness.

        strict=True will raise on any unique conflict; False will skip conflicts.
        Returns a summary dict with counts.
        """
        added = 0
        skipped = 0
        for table, ids in (mapping or {}).items():
            if not isinstance(ids, list):
                continue
            for rid in ids:
                try:
                    if self.add_link(table, rid):
                        added += 1
                except Exception:
                    if strict:
                        raise
                    skipped += 1
        if added:
            try:
                self.save(update_fields=['refs', 'dt_modified', 'version'])  # type: ignore[attr-defined]
            except Exception:
                pass
        return {'added': added, 'skipped': skipped}

    # Delegated comment handling via BaseModel / CommentsMixin; keep thin summary wrapper.
    def aggregated_comment_summary(self) -> dict:  # compatibility wrapper
        return getattr(self, 'comments', {})

