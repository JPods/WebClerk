# JSON Default Factories Pattern

## Overview

All models inheriting from `BaseModel` automatically populate JSON envelope fields on save. This ensures data consistency and eliminates the need for manual initialization of complex JSON structures.

## How It Works

### The Pattern

Each model layer can define a `JSON_DEFAULT_FACTORIES` dictionary that maps field names to factory functions:

```python
class MyModel(BaseModel):
    JSON_DEFAULT_FACTORIES = {
        "field_name": default_field_factory,
    }
```

On `save()`, `BaseModel` collects all factories from the entire class hierarchy (via MRO) and populates any empty or partial JSON fields with defaults.

### Inheritance Chain

The system walks the Method Resolution Order (MRO) to collect factories from all parent classes:

| Layer | Fields Auto-Populated |
|-------|----------------------|
| **Mixins** (MetadataMixin, RefsMixin, etc.) | `metadata`, `refs`, `prefs`, `comments` |
| **TransactionBaseModel** | `totals`, `cost`, `sell`, `finance`, `flow`, `source`, `action` |
| **Concrete Models** | Any model-specific fields |

### Example: Order

When an `Order` is saved, these factories are collected and applied:

```python
# From mixins (via BaseModel):
metadata → default_metadata()
refs     → default_refs()
prefs    → default_prefs()
comments → default_comments()

# From TransactionBaseModel:
totals   → default_totals()
cost     → default_cost()
sell     → default_sell()
finance  → default_finance()
flow     → default_transaction_flow()
source   → default_source()
action   → default_action()
```

## Implementation Details

### BaseModel.save()

```python
def save(self, *args, **kwargs):
    self.ensure_json_defaults()  # Auto-populate JSON fields
    # ... rest of save logic
    return super().save(*args, **kwargs)
```

### Key Methods

- `_collect_json_default_factories()` - Walks MRO to gather all factories
- `_merge_json_defaults(current, defaults)` - Merges existing values with defaults
- `ensure_json_defaults()` - Applies all factories to populate fields

### Merge Behavior

When a field already has partial data, defaults are merged (not replaced):

```python
# Existing value:
{"total": 100, "balance": 50}

# Default structure:
{"total": None, "balance": None, "subtotal": None, "tax": None}

# Result after merge:
{"total": 100, "balance": 50, "subtotal": None, "tax": None}
```

Existing values are preserved; only missing keys get defaults.

## Adding New JSON Fields

### 1. Define the Factory Function

```python
def default_my_field() -> Dict[str, Any]:
    return {
        "key1": None,
        "key2": 0,
        "key3": "",
    }
```

### 2. Add to JSON_DEFAULT_FACTORIES

```python
class MyModel(BaseModel):
    my_field = models.JSONField(default=dict, blank=True, null=True)
    
    JSON_DEFAULT_FACTORIES = {
        "my_field": default_my_field,
    }
```

### 3. For Subclasses

Subclasses automatically inherit parent factories. To add more:

```python
class ChildModel(ParentModel):
    extra_field = models.JSONField(default=dict, blank=True, null=True)
    
    JSON_DEFAULT_FACTORIES = {
        "extra_field": default_extra_field,
    }
```

The parent's factories are collected via MRO and merged with the child's.

## Backfilling Existing Records

To apply defaults to existing records that were created before this pattern:

```bash
# Dry run (show what would be updated)
python manage.py populate_json_defaults --dry-run

# Apply to specific model
python manage.py populate_json_defaults --model Order

# Apply to all models
python manage.py populate_json_defaults

# With batch size control
python manage.py populate_json_defaults --batch-size 100
```

See: `apps/core/management/commands/populate_json_defaults.py`

## Files

- **Pattern Implementation**: `common/models.py` (BaseModel, mixins)
- **Transaction Defaults**: `apps/transactions/models/base_transaction_model.py`
- **Backfill Command**: `apps/core/management/commands/populate_json_defaults.py`

## Related

- [01-architecture-overview.md](../../01-architecture-overview.md) - Base Model System
- [save-hooks.md](../api/save-hooks.md) - Pre/post save hooks
