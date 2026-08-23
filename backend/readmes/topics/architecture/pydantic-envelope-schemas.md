# Pydantic Envelope Schemas — Typed JSON at Every Layer

**Date:** 2026-08-04 (established), 2026-08-06 (documented and tightened)
**Location:** `common/schemas/`
**Xref:** Duplicate maintained at `~/Allie/readmes/pydantic-envelope-schemas.md` — update both when either changes.

---

## The Problem

Every BaseModel record carries six JSON fields: `.config`, `.metadata`, `.prefs`, `.refs`, `.comments`, `.actions`. Without schema enforcement, these are untyped dicts — typos fail silently, missing fields go unnoticed, and every developer invents their own structure. The same problem threatened the Data-Driven UI layout JSON: a misspelled field name renders nothing, and nobody knows why.

## The Solution

Pydantic models define the structure of every JSON envelope. Every model inherits from shared base schemas and extends only what's model-specific. 79 model schema files cover every model in the system.

## The Six Envelopes

| Envelope | Owner | Base class | Default extra |
|----------|-------|------------|---------------|
| `.config` | Application | `ConfigBase` | `forbid` — forces deliberate schema decisions |
| `.metadata` | System | `MetadataBase` | strict — all fields typed |
| `.prefs` | User | `RecordPrefsBase` | strict — userdefined is the escape valve |
| `.refs` | System | `RefsBase` | strict — FKs are truth, refs are cache |
| `.comments` | User + System | `CommentsBase` | strict — three channels + append-only notes |
| `.actions` | System | `ActionsBase` | strict — frequently indexed, kept small (32KB) |

## The Base Schemas

Six base classes in `common/schemas/envelopes.py` define what every record gets:

### MetadataBase — The System's Space

Machine-managed. Never user-written.

```python
class MetadataBase(BaseModel):
    flow: dict                    # workflow state
    flags: RecordFlags            # schema_rev, keywords_pending
    access: AccessControl         # edit[], view[] contact IDs
    health: HealthScores          # rating, accuracy, freshness, consistency, completeness
    history: RecordHistory        # synced, created, accessed, modified, verified (each: dt + contact_id)
    version: str                  # "1.0"
    versioning: VersioningInfo    # changed_fields[], size_activity
    audit_trail: list[AuditEntry] # append-only: action, dt, details, user_id
    import_data: ImportProvenance # source, dt_imported, risk, original dict
    small_stings: list            # customer-assessed fines
    # ... plus temp, erosions, priority, security, resources, publish
```

### RecordPrefsBase — The User's Space

User-written. Never system-managed.

```python
class RecordPrefsBase(BaseModel):
    userdefined: dict    # custom fields the user added (project_code, rush, etc.)
    tags: list[str]      # personal tags — not categories
    pinned: bool         # user pinned this record
```

### RefsBase — The Relationship Cache

Denormalized pointers. FKs are truth; refs are fast lookups.

```python
class RefsBase(BaseModel):
    links: dict                  # customer_id, invoice_ids, etc.
    source: Optional[SourceRef]  # originating document {type, id}
```

### CommentsBase — Structured Notes

Three named channels plus an append-only audit trail.

```python
class CommentsBase(BaseModel):
    public: str          # customer-facing
    process: str         # internal workflow
    partner: str         # vendor/supplier communication
    notes: list[CommentNote]  # append-only: ts, by, text, source
```

### ActionsBase — Next-Action Metadata

Frequently indexed for dashboard queries. Kept small (32KB max).

```python
class ActionsBase(BaseModel):
    required: bool       # action is required
    status: str          # pending, done, blocked
    who: Optional[int]   # contact_id
    when: int            # epoch ms — due/next date
    what: str            # action description
    kind: str            # followup, review, ship, approve
    extra: dict          # free-form per domain
```

### ConfigBase — Structural Data

Model-specific structural data. Default: `extra = 'forbid'` — models must declare their config fields explicitly. Models that genuinely need flexibility override with `extra = 'allow'` and a comment explaining why.

```python
class ConfigBase(BaseModel):
    class Config:
        extra = 'forbid'  # forces deliberate schema decisions
```

## The Mixins

Composed into model schemas only where needed — never globally:

| Mixin | What it adds | Which models |
|-------|-------------|-------------|
| **FinancialMetadataMixin** | gl_accounts, ledger, reconciliation, gateway_metadata | Transactions, payments |
| **StaffPrefsMixin** | nav, wcui, databrowser, color_mode, gantt, layout, training | Contacts with is_staff |
| **RepPrefsMixin** | territory, commission_display, default_price_level, account_sort | Contacts with rep FK |
| **EmployeePrefsMixin** | department, schedule, notifications, dashboard | Contacts with employee FK |
| **CartPrefsMixin** | language, currency, shipping_default, payment_method, saved_addresses | Customer-facing contacts |

## How a Model Inherits and Extends

Every model follows the same pattern. Contact is the richest example:

```python
# common/schemas/contact.py

class ContactMetadata(MetadataBase):
    """Inherits all standard fields. Adds contact-specific."""
    zb: Optional[ZeroBounceValidation] = None   # email validation
    images: dict                                 # legacy image paths
    search_log: list[SearchLogEntry]             # what this user searched for
    navigation_log: list[NavigationLogEntry]     # where this user went

class ContactPrefs(RecordPrefsBase):
    """Inherits userdefined, tags, pinned. Adds role-conditional sections."""
    staff: Optional[StaffPrefsMixin] = None      # activated by is_staff
    employee: Optional[EmployeePrefsMixin] = None # activated by employee FK
    rep: Optional[RepPrefsMixin] = None           # activated by rep FK
    cart: Optional[CartPrefsMixin] = None          # customer-facing

class ContactRefs(RefsBase):
    """Inherits links, source. Adds contact-specific relationship cache."""
    links: ContactRefsLinks     # email[], phone[], address[], customer[], vendor[], etc.
    tags: list[str]
    keywords: list[str]
    categories: list[str]
    parents: list
    related_ids: list[int]

class ContactConfig(BaseModel):
    """Structural import data."""
    original_mac: Optional[dict] = None
    phone_original: Optional[str] = None
```

A simple model inherits the bases unchanged:

```python
# common/schemas/warehouse.py (or any simple model)

class WarehouseMetadata(MetadataBase):
    pass

class WarehousePrefs(RecordPrefsBase):
    pass

class WarehouseRefs(RefsBase):
    tags: list[str]
    keywords: list[str]
    source: Optional[SourceRef] = None
```

## The schema_map Setting

Every model has a `schema_map` Setting record that connects the Pydantic schemas to the model at runtime. This tells wcapi which schema to validate against when writing to `.config`, `.prefs`, `.metadata`, or `.refs`.

```
Setting(purpose='schema_map', model_name='contact', ...)
```

`seed_all_schema_maps` creates these for every model in MODEL_REGISTRY. Models with custom schemas (contact, customer, item, serial, payment, transaction) are seeded manually.

## Coverage

| Layer | Count | What |
|-------|-------|------|
| Base schemas | 4 | MetadataBase, RecordPrefsBase, RefsBase, config pattern |
| Shared types | 10 | AuditEntry, HistoryTimestamp, RecordHistory, HealthScores, RecordFlags, AccessControl, VersioningInfo, ImportProvenance, SourceRef, SettingDefaults |
| Mixins | 5 | Financial, Staff, Rep, Employee, Cart |
| Model schemas | 79 | One file per model in `common/schemas/` |
| Template | 1 | `_template.py` — copy to create new model schema |

## The Rules

1. **Inherit, never duplicate.** Every model extends the bases. No model redefines `audit_trail` or `userdefined`.
2. **Mixins compose, not inherit.** `FinancialMetadataMixin` is mixed into transaction metadata, not into MetadataBase.
3. **extra = "allow" on config.** Config is the least standardized envelope — model-specific structural data varies. Other envelopes are strict.
4. **The user owns .prefs. The system owns .metadata.** Never cross the streams.
5. **refs are cache, not truth.** FKs are authoritative. `.refs.links` is denormalized for fast queries.
6. **Schema validation runs at write time.** wcapi validates against the schema_map before persisting. Typos and missing fields fail at save, not at render.

## Connection to Data-Driven UI

The Pydantic schemas are the validation layer that makes Data-Driven UI safe. When a form layout references a field name, BehaviorField reads the field from the record. The Pydantic schema ensures that:

- The field exists and has the right type
- Default values are populated for new records
- Invalid data is rejected at save time, not rendered silently wrong

Without the schemas, the 96% code reduction in Data-Driven UI would trade compile-time safety for runtime fragility. With them, the JSON layouts are validated at the data layer — the UI can trust what it reads.

## Alice and the Wisdom of the Many

Schemas do not evolve in isolation. Every WebClerk installation has an Alice — and every Alice watches how her users actually use the JSON envelopes. What fields do they add to `.prefs.userdefined`? What patterns emerge in `.config`? What structures recur across installations that the base schema doesn't cover?

### The Loop

```
Alice observes → patterns emerge → Alice recommends → user approves → schema improves
    ↑                                                                         |
    └─────────────── published back to the network ───────────────────────────┘
```

1. **Alice observes.** Each Alice monitors her installation's actual JSON field usage — what keys appear in `extra = "allow"` fields, what structures users build in `.prefs.userdefined`, what `.config` patterns repeat across records of the same model.

2. **Alice recommends.** When a pattern is consistent enough (same field name, same type, across enough records), Alice proposes a schema addition: "17 of your contacts have `prefs.userdefined.department` as a string. Promote to a typed field?"

3. **User approves.** Schema changes never happen silently. The user's Setting record carries their consent preference — whether Alice may propose schema changes, and whether proposals require explicit approval or auto-apply. The default is explicit approval.

4. **Alice shares.** With user approval (stored in the contact's Setting record), Alice submits the observed pattern to WC_HQ via sync. Not the data — just the schema proposal: "model=contact, field=prefs.department, type=string, observed_in=17_records."

5. **WC_HQ aggregates.** Across all participating installations, WC_HQ sees which schema proposals recur. If 40 installations independently discover that contacts need a `department` field, that's not one user's preference — that's the Wisdom of the Many.

6. **WC_HQ publishes.** Validated patterns are published as recommended schema updates. Installations that subscribe receive them via sync. Alice presents the recommendation: "The network recommends adding `prefs.department` to Contact. 40 installations use this pattern. Apply?"

7. **User approves again.** The receiving installation's user decides whether to adopt the recommendation. No schema change is forced. The individual is sovereign — including over their data structure.

### Why This Matters

The traditional approach is top-down: a vendor designs the schema, ships it, and every customer adapts. The WebClerk approach is bottom-up: users shape their data, Alice observes the patterns, the network aggregates the wisdom, and recommended structures flow back. The schema evolves from usage, not from a committee.

This is Metcalfe's law applied to data structure. One installation's `userdefined.department` is a hack. Forty installations' `userdefined.department` is a signal. The network's value scales with the square of its connections — but only if the connections carry signal, not just data.

### The Setting Record

Each user's participation level is stored in their contact Setting:

| Setting | Values | Default |
|---------|--------|---------|
| `schema_sharing` | `off`, `propose`, `auto` | `off` |
| `schema_recommendations` | `off`, `review`, `auto` | `review` |

- `schema_sharing = off` — Alice observes locally but never shares upstream
- `schema_sharing = propose` — Alice submits proposals to WC_HQ; user reviews before sending
- `schema_sharing = auto` — Alice submits proposals automatically (still anonymized, still schema-only)
- `schema_recommendations = off` — ignore network recommendations
- `schema_recommendations = review` — Alice presents recommendations; user decides
- `schema_recommendations = auto` — Alice applies recommendations that match observed local patterns

### What Is Never Shared

- Record data. Never. Only schema structure proposals.
- User identity. Proposals are anonymized to installation ID.
- Proprietary field names. If a field name contains a trademark or product name, Alice flags it for review before proposing.

The principle: your data is yours. The structure of your data — the shape, not the content — is knowledge that helps everyone when shared. Usufruct applied to data architecture.

## Open Items

1. **Config schemas are weak.** Most models have `extra = "allow"` on config with no defined fields. As config usage patterns solidify, tighten these — and Alice's observation loop is the mechanism that will drive this.
2. **Layout schema.** The form layout format now has Pydantic models (`NamedFormLayout`, `CardSpec`, `EditRules` etc. in `setting.py`) — established 2026-08-18. Design Mode saves should validate against these.
3. **Alice schema audit.** `schema_audit.py` exists but needs to run on schedule, flagging models where the actual data diverges from the declared schema.
4. **WC_HQ aggregation endpoint.** The sync protocol supports bundle exchange; the schema proposal format and aggregation logic need to be built.
5. **Alice observation queries.** Alice needs queries that scan `extra` fields across records of the same model, group by key name and type, and surface patterns above a threshold.
