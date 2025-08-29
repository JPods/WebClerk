# filepath: /webClerk3/docs/models/linkages.py
from django.db import models
from common.models import BaseModel
from django.utils import timezone
# bulk of this table is in the .refs to relate other tables
# example use is to link line items in orders, proposals, etc. 
# with one document that passes on specs, paths, comments, and other details
class Linkage(BaseModel):
    """Lightweight cross-record linkage hub.

    Stores relationship fan-out centrally in refs.links structure:
      refs = { 'links': { 'table_a': [id,...], 'table_b': [id,...] }}

    Intended to reduce N-N join table sprawl for ad-hoc associations.
    Health & history inherited from BaseModel (metadata.history, metadata.flags etc.).
    """

    comment = models.TextField(blank=True, null=True)
    purpose = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    name = models.CharField(max_length=255, blank=True, null=True, db_index=True)

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
        if record_id not in lst:
            lst.append(record_id)
            self.mark_keywords_dirty()  # treat as structural change for keyword set
            return True
        return False

    def remove_link(self, table: str, record_id):
        links = self._ensure_links()
        lst = links.get(table, [])
        if record_id in lst:
            lst.remove(record_id)
            self.mark_keywords_dirty()
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

