# Refs Setup System

## Overview

The `.refs` system in WebClerk provides denormalized data storage to simplify user searching and data queries. Each record contains a `.refs` object that stores denormalized values from related records and user-defined search terms.

## Structure

```json
{
  "refs": {
    "tags": [],
    "links": {
      "emails": [1,2],
      "phones": [1,2],
      "locations": [1,2],
      "domains": [1,2]
    },
    "keywords": []
  }
}
```
- ensure_refs_setup.py currently has the related models liste

- **`tags`**: User-defined search words
- **`links`**: Arrays of related record IDs for quick lookups
- **`keywords`**: Denormalized text fields from related records for search indexing

## Configuration

Each model can have a `refs_setup` setting that controls how data is denormalized. Settings are stored in the `Setting` model with:
- `purpose = "refs_setup"`
- `model_name = "<canonical_model_key>"`
- `data` containing the configuration

### Default Configuration Structure

```json
{
  "model_name": "contact",
  "priority_order": [
    {"model_name": "contact", "field_name": "name_first", "priority": 10},
    {"model_name": "contact", "field_name": "name_last", "priority": 9},
    {"model_name": "customer", "field_name": "company", "priority": 8}
  ]
}
```

- **`model_name`**: The canonical model key this configuration applies to
- **`priority_order`**: Ordered list of field priorities for keyword weighting from related models

### Priority Weighting

Fields from related models are prioritized based on common naming patterns:
- `name_first` (10)
- `name_last` (9)
- `company` (8)
- `name` (7)
- `title` (6)
- `description` (5)
- `email` (4)
- `phone` (3)
- `address` (2)

When building keywords, the system loops through `refs.links` to get denormalized data from related records (contacts, customers, vendors, etc.) and applies these priorities.

## Management Command

Use the `ensure_refs_setup` management command to create default refs_setup settings for all models:

```bash
python manage.py ensure_refs_setup
```

This command:
1. Iterates through all models in the model registry
2. Checks if a refs_setup setting exists for each model
3. Creates default settings with model_name and priority ordering for related model fields
4. Reports creation statistics

### Options

- `--quiet`: Suppress verbose output
- `--rebuild`: Delete existing refs_setup settings and recreate them

### Example Output

```
Completed: 1 created, 52 already existed
```

## Usage in Code

### Creating Settings Programmatically

```python
from apps.core.models.setting import Setting

setting = Setting(
    name='contact refs setup',
    purpose='refs_setup',
    model_name='contact',
    data={
        'model_name': 'contact',
        'priority_order': [
            {'model_name': 'contact', 'field_name': 'name_first', 'priority': 10},
            {'model_name': 'contact', 'field_name': 'name_last', 'priority': 9}
        ]
    }
)
setting.save()
```

### Accessing Settings

```python
from apps.core.models.setting import Setting

# Get refs_setup for a specific model
setting = Setting.objects.filter(
    model_name='contact',
    purpose='refs_setup'
).first()

if setting:
    model_name = setting.data.get('model_name')
    priority_order = setting.data.get('priority_order', [])
```

## Integration with Search

The `.refs.keywords` field is used for full-text search indexing. When keywords are built, the system loops through `refs.links` to get denormalized data from related records. The priority ordering ensures that more important fields (like names) from related models are weighted higher in search results.

For example, action records can include phone and email data from contacts, customers, vendors, etc. that are linked via `refs.links`.

## Future Enhancements

- Custom transformation functions for data normalization
- Role-based field filtering
- Automatic refs rebuilding on related record changes
- Integration with Elasticsearch for advanced search capabilities