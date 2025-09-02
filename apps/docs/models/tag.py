from django.db import models
from django.db.models import F
from common.models import BaseModel
from django.utils import timezone
# heavily uses .refs and .metadata .data
# used to tag shipments, equipment, locations, etc.
# isolated from linkages because primarily used for tracking   
# the metadata is more detailed and specific to each tag
# tags can be nested such as units in a box as one tag and 
# boxes on a pallet for the same or another tag 
class Tag(BaseModel):
    """Tracking / classification tag.

    Distinct from Linkage: optimized for per-item tracking (shipments, equipment, locations).
    Heavy use of refs / metadata for dynamic attributes.
    Supports hierarchical (nested) relationships via refs.tags.children / parent.
    """

    name = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    purpose = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    status = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    security_level = models.IntegerField(blank=True, null=True, db_index=True)
    table_name = models.CharField(max_length=255, blank=True, null=True, db_index=True, help_text="Source table this tag decorates")
    record_id = models.IntegerField(blank=True, null=True, db_index=True, help_text="ID in source table")
    data = models.JSONField(blank=True, null=True, help_text="Arbitrary structured tag payload")
    count_accessed = models.IntegerField(default=0)
    sequence = models.IntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = 'tags'
        indexes = [
            models.Index(fields=['purpose'], name='tag_purpose_idx'),
            models.Index(fields=['status'], name='tag_status_idx'),
            models.Index(fields=['security_level'], name='tag_sec_level_idx'),
            models.Index(fields=['table_name', 'record_id'], name='tag_table_record_idx'),
        ]




    def __str__(self):
        return f"{self.name or 'Tag'} ({self.id})"

    # --- hierarchy helpers -------------------------------------------------
    def _ensure_tag_refs(self):
        if not isinstance(self.refs, dict):
            self.refs = {}
        raw = self.refs.get('tags')
        # If legacy structure is a list, replace with dict container
        if not isinstance(raw, dict):
            raw = {}
            self.refs['tags'] = raw
        raw.setdefault('children', [])
        raw.setdefault('parent_id', None)
        # Guarantee list type for children
        if not isinstance(raw['children'], list):
            raw['children'] = []
        return raw

    def add_child(self, tag_id: int) -> bool:
        r = self._ensure_tag_refs()
        children = r['children']
        if tag_id not in children:
            children.append(tag_id)
            self.mark_keywords_dirty()
            return True
        return False

    def remove_child(self, tag_id: int) -> bool:
        r = self._ensure_tag_refs()
        children = r['children']
        if tag_id in children:
            children.remove(tag_id)
            self.mark_keywords_dirty()
            return True
        return False

    def set_parent(self, parent_id: int | None):
        r = self._ensure_tag_refs()
        r['parent_id'] = parent_id
        self.mark_keywords_dirty()

    def children_ids(self):
        r = self._ensure_tag_refs()
        return list(r.get('children', []))

    def parent_id(self):  # property-style method name chosen to avoid clash
        r = self._ensure_tag_refs()
        return r.get('parent_id')

    # --- access counter ----------------------------------------------------
    def increment_access(self, by: int = 1, update_history: bool = True):
        if not self.pk:
            return
        type(self).objects.filter(pk=self.pk).update(count_accessed=F('count_accessed') + by)
        self.count_accessed += by
        if update_history:
            now_ms = int(timezone.now().timestamp() * 1000)
            meta = self.metadata or {}
            hist = meta.setdefault('history', {})
            hist['accessed'] = {'dt': now_ms, 'contact_id': 0}
            type(self).objects.filter(pk=self.pk).update(metadata=meta)
    




#     Key changes:

# Expanded Tag model: added name/purpose/status/security_level indexes, table_name+record_id composite index, count_accessed, sequence, is_active, hierarchy helpers (add_child, remove_child, set_parent, children_ids, parent_id), and access counter method.
# Added robust _ensure_tag_refs handling legacy list refs.
# Created serializers (TagSerializer, TagDetailSerializer).
# Added views: list/create (TagListCreateView with 
# pagination, ordering, filters), detail/update 
# (increments access), and hierarchy operations 
# (TagHierarchyView for add/remove child and set parent).
# Wired routes in urls.py.
# Added tests (test_tag_endpoints.py) covering pagination, 
# filtering, hierarchy ops, access increment path.
# Fixed hierarchy bug (list vs dict in refs.tags) and 
# re-ran tests: all tag tests now pass.
# Status:

# Tag tests: pass.
# Existing QA, Document, Linkage tests previously green 
# (unchanged by fix).
# No migration generated (fields already compatible 
# or prior migration may be needed later if DB schema 
# differs; generate manually if deploying to fresh DB).

# NOTE uniqueness is managed by id.



# CREATE TABLE IF NOT EXISTS "load_tags" (
#     "id" BIGSERIAL PRIMARY KEY,
#     "uuid" UUID UNIQUE NOT NULL,
#     "call_tag" VARCHAR(255),
#     "comment" TEXT,
#     "container_type" VARCHAR(255),
#     "cost_customs" DOUBLE PRECISION,
#     "cost_declared_value" DOUBLE PRECISION,
#     "cost_estimate" DOUBLE PRECISION,
#     "cost_fuel_charge" DOUBLE PRECISION,
#     "cost_hazard" DOUBLE PRECISION,
#     "cost_insurance" DOUBLE PRECISION,
#     "cost_other" DOUBLE PRECISION,
#     "cost_ship" DOUBLE PRECISION,
#     "cost_size_charge" DOUBLE PRECISION,
#     "cost_total" DOUBLE PRECISION,
#     "customer_po" VARCHAR(255),
#     "hazard_class" VARCHAR(255),
#     "height" DOUBLE PRECISION,
#     "instructions" TEXT,
#     "insurance_name" VARCHAR(255),
#     "is_complete" INTEGER,
#     "is_insured_ship" BOOLEAN DEFAULT FALSE,
#     "length" DOUBLE PRECISION,
#     "lines" JSONB,
#     "lines_index" INTEGER,
#     "list_invoices" TEXT,
#     "list_pos" TEXT,
 
#     "references" JSONB,
#     "status" VARCHAR(255),
#     "table_name" INTEGER,
#     "tag_options" TEXT,
#     "transaction_type" VARCHAR(255),
#     "value" DOUBLE PRECISION,
#     "vendor_invoice" VARCHAR(255),
#     "weight_extended" DOUBLE PRECISION,
#     "weight_pallet_container" DOUBLE PRECISION,
#     "weight_product" DOUBLE PRECISION,
#     "weight_tare" DOUBLE PRECISION,
#     "width" DOUBLE PRECISION
# );
