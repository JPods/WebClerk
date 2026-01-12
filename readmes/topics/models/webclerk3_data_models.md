# WebClerk3 Data Models

## Model Inheritance Hierarchy

```mermaid
classDiagram
    class CoreModel {
        +id: BigAutoField
        +uuid: UUIDField
        +ida: CharField
        +dt_created: BigIntegerField
        +dt_modified: BigIntegerField
        +version: PositiveIntegerField
        +is_active: BooleanField
        +security_level: IntegerField
        +feature_flags: ["core"]
        +save()*
        +assert_version()*
        +optimistic_save()*
    }

    class BaseModel {
        +metadata: JSONField
        +refs: JSONField
        +prefs: JSONField
        +comments: JSONField
        +actions: JSONField
        +health_rating: IntegerField
        +is_deleted: BooleanField
        +is_archived: BooleanField
        +feature_flags: ["core", "metadata", "refs", "prefs", "comments", "actions", "health", "keywords", "lifecycle", "universal_dict", "atomic_json"]
        +FullManager objects
        +FullQuerySet
        +save()*
        +touch()*
        +record_submission_snapshot()*
        +_compute_changed_fields()*
        +is_effectively_active()*
    }

    CoreModel <|-- BaseModel : inherits
    BaseModel *-- MetadataMixin
    BaseModel *-- RefsMixin
    BaseModel *-- PrefsMixin
    BaseModel *-- CommentsMixin
    BaseModel *-- ActionsMixin
    BaseModel *-- HealthMixin
    BaseModel *-- KeywordsMixin
    BaseModel *-- LifecycleMixin
    BaseModel *-- UniversalDictMixin
    BaseModel *-- AtomicJSONMixin

    class MetadataMixin {
        +metadata: JSONField
        +feature_flags: ["metadata"]
        +_init_metadata_if_needed()*
        +get_history()*
        +get_metadata_value()*
        +set_metadata_value()*
        +get_flow()*
        +set_flow()*
        +get_source()*
        +set_source()*
        +get_created_timestamp()*
        +get_modified_timestamp()*
        +get_verified_timestamp()*
    }

    class RefsMixin {
        +refs: JSONField
        +feature_flags: ["refs"]
        +add_keyword()*
        +add_tag()*
    }

    class PrefsMixin {
        +prefs: JSONField
        +feature_flags: ["prefs"]
    }

    class CommentsMixin {
        +comments: JSONField
        +feature_flags: ["comments"]
        +add_comment()*
        +add_note()*
        +aggregated_comments()*
    }

    class ActionsMixin {
        +actions: JSONField
        +feature_flags: ["actions"]
        +get_action()*
        +set_action()*
    }

    class HealthMixin {
        +health_rating: IntegerField
        +feature_flags: ["health"]
    }

    class KeywordsMixin {
        +feature_flags: ["keywords"]
        +mark_keywords_dirty()*
        +update_keywords()*
        +keywords_pending*
    }

    class LifecycleMixin {
        +is_deleted: BooleanField
        +is_archived: BooleanField
        +feature_flags: ["lifecycle"]
        +soft_delete()*
        +restore()*
        +archive()*
        +unarchive()*
    }

    class UniversalDictMixin {
        +feature_flags: ["universal_dict"]
        +to_universal_dict()*
        +as_pydantic()*
        +pydantic_dump()*
        +pre_save_hook()*
        +api_validate_payload()*
        +post_save_hook()*
    }

    class AtomicJSONMixin {
        +feature_flags: ["atomic_json"]
        +atomic_json_set()*
        +atomic_list_append()*
        +atomic_set()*
        +atomic_append()*
    }
```

## Core Business Models

```mermaid
classDiagram
    class Contact {
        +name_first: CharField
        +name_last: CharField
        +email: CharField
        +company: CharField
        +phone: CharField
        +address: TextField
        +status: CharField
        +role: CharField
        +BaseModel+
    }

    class Action {
        +kind: CharField
        +status: CharField
        +priority: CharField
        +description: TextField
        +due_date: DateTimeField
        +assigned_to_id: IntegerField
        +BaseModel+
    }

    class Email {
        +contact_id: IntegerField
        +email: CharField
        +kind: CharField
        +status: CharField
        +verified_at: DateTimeField
        +BaseModel+
    }

    class Phone {
        +contact_id: IntegerField
        +phone: CharField
        +kind: CharField
        +status: CharField
        +verified_at: DateTimeField
        +BaseModel+
    }

    class Location {
        +contact_id: IntegerField
        +address: TextField
        +city: CharField
        +state: CharField
        +zip_code: CharField
        +country: CharField
        +kind: CharField
        +verified_at: DateTimeField
        +BaseModel+
    }

    class Document {
        +name: CharField
        +slug: SlugField
        +status: CharField
        +description: CharField
        +body: TextField
        +comment: TextField
        +data: JSONField
        +confidential: CharField
        +copyright: JSONField
        +count_accessed: IntegerField
        +model_name: CharField
        +retention_period: IntegerField
        +sequence: IntegerField
        +size_bytes: IntegerField
        +mime_type: CharField
        +path: JSONField
        +checksum: CharField
        +search_vector: SearchVectorField
        +BaseModel+
        +increment_access()*
        +rebuild_search_vector()*
    }

    Contact ||--o{ Action : performs
    Contact ||--o{ Email : has
    Contact ||--o{ Phone : has
    Contact ||--o{ Location : has
    Contact ||--o{ Document : owns
```

## Transaction Models

```mermaid
classDiagram
    class TransactionBaseModel {
        +contact_id: IntegerField
        +status: CharField
        +priority: CharField
        +description: TextField
        +notes: TextField
        +terms: TextField
        +currency: CharField
        +exchange_rate: DecimalField
        +tax_rate: DecimalField
        +discount_rate: DecimalField
        +subtotal: DecimalField
        +tax_amount: DecimalField
        +discount_amount: DecimalField
        +total: DecimalField
        +sell: JSONField
        +cost: JSONField
        +totals: JSONField
        +due_date: DateTimeField
        +ship_date: DateTimeField
        +BaseModel+
    }

    class Proposal {
        +TransactionBaseModel+
        +approved_at: DateTimeField
        +approved_by_id: IntegerField
    }

    class SalesOrder {
        +TransactionBaseModel+
        +approved_at: DateTimeField
        +approved_by_id: IntegerField
        +shipped_at: DateTimeField
        +shipped_by_id: IntegerField
    }

    class PurchaseOrder {
        +TransactionBaseModel+
        +approved_at: DateTimeField
        +approved_by_id: IntegerField
        +received_at: DateTimeField
        +received_by_id: IntegerField
    }

    class Invoice {
        +TransactionBaseModel+
        +paid_at: DateTimeField
        +paid_by_id: IntegerField
        +payment_terms: CharField
        +update_sell_cost_totals()*
    }

    class WorkOrder {
        +TransactionBaseModel+
        +started_at: DateTimeField
        +completed_at: DateTimeField
        +assigned_to_id: IntegerField
    }

    class Requisition {
        +TransactionBaseModel+
        +approved_at: DateTimeField
        +approved_by_id: IntegerField
    }

    TransactionBaseModel <|-- Proposal
    TransactionBaseModel <|-- SalesOrder
    TransactionBaseModel <|-- PurchaseOrder
    TransactionBaseModel <|-- Invoice
    TransactionBaseModel <|-- WorkOrder
    TransactionBaseModel <|-- Requisition
```

## Transaction Line Models

```mermaid
classDiagram
    class TransactionLineBaseModel {
        +parent_id: IntegerField
        +line_number: IntegerField
        +item_id: IntegerField
        +description: CharField
        +quantity: DecimalField
        +quantity_uom: CharField
        +price_unit: DecimalField
        +price_extended: DecimalField
        +cost_unit: DecimalField
        +cost_extended: DecimalField
        +discount_rate: DecimalField
        +discount_amount: DecimalField
        +tax_rate: DecimalField
        +tax_amount: DecimalField
        +status: CharField
        +due_date: DateTimeField
        +ship_date: DateTimeField
        +BaseModel+
    }

    class ProposalLine {
        +TransactionLineBaseModel+
        +probability: DecimalField
    }

    class SalesOrderLine {
        +TransactionLineBaseModel+
        +shipped_quantity: DecimalField
        +backorder_quantity: DecimalField
    }

    class PurchaseOrderLine {
        +TransactionLineBaseModel+
        +received_quantity: DecimalField
        +rejected_quantity: DecimalField
    }

    class InvoiceLine {
        +TransactionLineBaseModel+
        +paid_quantity: DecimalField
    }

    class WorkOrderLine {
        +TransactionLineBaseModel+
        +started_at: DateTimeField
        +completed_at: DateTimeField
        +assigned_to_id: IntegerField
    }

    class RequisitionLine {
        +TransactionLineBaseModel+
        +approved_quantity: DecimalField
    }

    TransactionLineBaseModel <|-- ProposalLine
    TransactionLineBaseModel <|-- SalesOrderLine
    TransactionLineBaseModel <|-- PurchaseOrderLine
    TransactionLineBaseModel <|-- InvoiceLine
    TransactionLineBaseModel <|-- WorkOrderLine
    TransactionLineBaseModel <|-- RequisitionLine

    TransactionBaseModel ||--o{ TransactionLineBaseModel : contains
```

## Product & Inventory Models

```mermaid
classDiagram
    class Catalog {
        +name: CharField
        +description: TextField
        +kind: CharField
        +status: CharField
        +price: JSONField
        +cost: JSONField
        +flags: JSONField
        +is_print_not: BooleanField
        +default_price: DecimalField
        +default_cost: DecimalField
        +BaseModel+
    }

    class InventoryLayer {
        +item_id: IntegerField
        +location_id: IntegerField
        +quantity: DecimalField
        +quantity_uom: CharField
        +cost_avg: DecimalField
        +cost_last: DecimalField
        +cost_standard: DecimalField
        +received_at: DateTimeField
        +expires_at: DateTimeField
        +lot_number: CharField
        +serial_numbers: JSONField
        +reservations: JSONField
        +CoreModel+
    }

    class InventoryReservation {
        +inventory_layer_id: IntegerField
        +contact_id: IntegerField
        +quantity: DecimalField
        +purpose: CharField
        +expires_at: DateTimeField
        +fulfilled_at: DateTimeField
        +CoreModel+
    }

    class BOMLine {
        +parent_id: IntegerField
        +component_id: IntegerField
        +revision: CharField
        +effective_from: DateField
        +effective_to: DateField
        +quantity: DecimalField
        +scrap_factor: DecimalField
        +yield_pct: DecimalField
        +sequence: IntegerField
        +is_alternate: BooleanField
        +alternate_group: CharField
        +is_optional: BooleanField
        +cost_snapshot: JSONField
        +op_data: JSONField
        +change_reason: CharField
        +dt_last_recalc: BigIntegerField
        +CoreModel+
    }

    class InventoryAdjustmentProcessorRun {
        +started_at: DateTimeField
        +completed_at: DateTimeField
        +records_processed: IntegerField
        +errors_encountered: IntegerField
        +CoreModel+
    }

    class InventoryMetricsSnapshot {
        +snapshot_date: DateField
        +total_value: DecimalField
        +total_quantity: DecimalField
        +metrics: JSONField
        +CoreModel+
    }

    Catalog ||--o{ InventoryLayer : tracked
    Catalog ||--o{ BOMLine : component_of
    InventoryLayer ||--o{ InventoryReservation : reserved_by
```

## Supporting Models

```mermaid
classDiagram
    class Setting {
        +purpose: CharField
        +model_name: CharField
        +key: CharField
        +data: JSONField
        +is_active: BooleanField
        +BaseModel+
    }

    class Connection {
        +name: CharField
        +type: CharField
        +config: JSONField
        +comment: TextField
        +status: CharField
        +scripts: JSONField
        +relationships: JSONField
        +action: CharField
        +purpose: CharField
        +maps: JSONField
        +encryption: JSONField
        +rules: JSONField
        +conflicts: JSONField
        +changes: JSONField
        +BaseModel+
    }

    class Pending {
        +model_name: CharField
        +record_id: CharField
        +purpose: CharField
        +name: CharField
        +data: JSONField
        +dt_processed: BigIntegerField
        +CoreModel+
        +mark_processed()*
        +is_processed()*
    }

    class Linkage {
        +kind: CharField
        +status: CharField
        +data: JSONField
        +BaseModel+
    }

    class SoftDeleteLedger {
        +model_name: CharField
        +record_id: IntegerField
        +deleted_at: DateTimeField
        +deleted_by_id: IntegerField
        +reason: TextField
        +CoreModel+
    }
```

## JSON Field Structures

### Metadata Envelope
```json
{
  "security": "",
  "publish": "",
  "priority": "",
  "version": "1.0",
  "access": {
    "view": [],
    "edit": []
  },
  "resources": {
    "required": {},
    "allocated": {}
  },
  "flow": {},
  "source": {},
  "history": {
    "created": {"dt": 1730937600000, "contact_id": 0},
    "modified": {"dt": 1730937600000, "contact_id": 0},
    "accessed": {"dt": 1730937600000, "contact_id": 0},
    "verified": {"dt": 0, "contact_id": 0},
    "synced": {"dt": 0, "contact_id": 0}
  },
  "health": {
    "rating": 0,
    "completeness": 0,
    "accuracy": 0,
    "freshness": 0,
    "consistency": 0
  },
  "flags": {},
  "versioning": {},
  "undefined": {}
}
```

### Refs Envelope
```json
{
  "keywords": [],
  "tags": [],
  "links": {
    "contacts": [],
    "items": []
  },
  "depends_on": {},
  "categories": [],
  "related_ids": []
}
```

### Prefs Envelope
```json
{
  "userdefined": {},
  "submission": {
    "as_submitted": {
      "data": {},
      "dt": 1730937600000,
      "by": 123
    }
  }
}
```

### Comments Envelope
```json
{
  "general": {
    "public": [],
    "process": [],
    "partner": []
  },
  "records": {}
}
```

### Actions Envelope
```json
{
  "required": true,
  "status": "pending",
  "who": 123,
  "when": 1730937600000,
  "what": "call vendor",
  "kind": "followup",
  "extra": {}
}
```

## Database Indexes

- **GIN Indexes**: `refs`, `prefs`, `actions`, `search_vector`
- **Key Text Transforms**: `actions.status`, `actions.required`, `actions.who`, `actions.when`
- **Composite Indexes**: Various field combinations for query optimization
- **Partial Indexes**: Active records, status filters

## Model Capabilities Matrix

| Model | Inherits | Key Capabilities |
|-------|----------|------------------|
| Contact | BaseModel | Full envelope, keywords, lifecycle |
| Action | BaseModel | Full envelope, dependencies, status tracking |
| Email/Phone/Location | BaseModel | Verification flows, contact linking |
| Document | BaseModel | Search vectors, access tracking, linkage |
| Transaction Headers | BaseModel | Totals aggregation, flow tracking |
| Transaction Lines | BaseModel | Lineage, serial tracking, parent linking |
| Catalog | BaseModel | Pricing/costing structures, flags |
| InventoryLayer | CoreModel | Lightweight tracking, reservations |
| Connection | BaseModel | External integrations, encryption |
| Setting | BaseModel | Configuration management |
| Pending | CoreModel | Queue processing, minimal overhead |
| Linkage | BaseModel | Cross-entity relationships |

This data model documentation provides a comprehensive view of WebClerk3's domain structure, inheritance patterns, and JSON envelope usage.