# refs Setting Records Management

This document describes how to manage Setting records for model configurations, particularly for keyword requirements and refs setup.

## Key Functions

- **`build_keywords_for_record(model_name, record_id)`** - `apps/core/services/keywords.py`
  - Main function that processes refs_setup configurations to build keyword collections
  - Extracts keywords from self fields and related model fields
  - Stores results in `refs.keywords`

- **`get_keyword_requirements()`** - `apps/core/constants/keyword_requirements.py`
  - Loads cached Setting records with `purpose="refs_setup"`
  - Returns configuration dictionary keyed by model name

- **`refs_setting_manage`** - `apps/core/management/commands/refs_setting_manage.py`
  - Django management command for administrative management of Setting records
  - Supports listing, viewing, and updating settings from baseline files

## Overview

Setting records store configuration data for various model behaviors. The `refs_setting_manage` management command provides administrative tools to create, view, and update these settings.

## Management Command

The `refs_setting_manage` command is located at `apps/core/management/commands/refs_setting_manage.py`.

### Usage

```bash
python manage.py refs_setting_manage [options]
```

### Options

- `--list`: List all settings
- `--model MODEL`: Filter by model name
- `--purpose PURPOSE`: Filter by purpose
- `--view`: View setting data for specified model/purpose
- `--update-baseline`: Update setting from baseline file
- `--baseline-dir DIR`: Directory containing baseline files (default: `readmes/baseline_setting`)
- `--all-models`: Process all models found in baseline directory

### Examples

#### List all settings

```bash
python manage.py refs_setting_manage --list
```

#### List settings for a specific model

```bash
python manage.py refs_setting_manage --list --model contact
```

#### List settings for a specific purpose

```bash
python manage.py refs_setting_manage --list --purpose refs_setup
```

#### View a specific setting

```bash
python manage.py refs_setting_manage --view --model contact --purpose refs_setup
```

#### Update a setting from baseline

```bash
python manage.py refs_setting_manage --update-baseline --model contact --purpose refs_setup
```

#### Update all settings from baselines

```bash
python manage.py refs_setting_manage --update-baseline --all-models
```

This command searches for baseline files in both:

- `readmes/baseline_setting/` (purpose-specific files)
- `readmes/baseline_setting/models/` (model-specific files)

## Baseline Files

Settings are managed through baseline files stored in `readmes/baseline_setting/`. The directory structure supports scalability:

### Directory Structure

```g
readmes/baseline_setting/
├── models/                          # Model-specific configurations
│   ├── contact_refs_setup.txt
│   ├── action_refs_setup.txt
│   └── ... (other model configs)
└── ... (purpose-specific files if needed)
```

### File Format

Each baseline file contains a single setting configuration with this format:

```g
setting model_name="contact" purpose="refs_setup"
{
    "self_fields": [
        "email",
        "name_first",
        "name_last",
        "company",
        "department"
    ],
    "related_keywords": {
        "email": ["email", "attention"],
        "location": ["address1", "city", "state", "zip", "country"],
        "phone": ["number", "country_code", "attention"],
        "customer": ["refs.keywords"],
        "vendor": ["refs.keywords"]
    },
    "related_models": ["email", "location", "phone", "customer", "vendor"]
}
```

### Naming Convention

- **Model-specific files**: `{model_name}_{purpose}.txt` (e.g., `contact_refs_setup.txt`)
- **Purpose-specific files**: `{purpose}.txt` (for multiple models in one file)
- **Location**: `readmes/baseline_setting/models/` for model-specific files

## Refs Setup Configuration

The `refs_setup` purpose is used for configuring both keyword generation and relationship denormalization. It defines:

1. Which fields to use for keyword generation
2. Which related models to include in `refs.links` for relationship tracking
3. How to extract keywords from related records

### Configuration Structure

```json
{
    "self_fields": ["field1", "field2", ...],
    "related_keywords": {
        "related_model_name": ["field1", "field2", ...],
        ...
    },
    "related_models": ["model1", "model2", ...]
}
```

- `self_fields`: Array of field names from the model's own table for keyword generation
- `related_keywords`: Object mapping related model names to arrays of their fields for keyword extraction
- `related_models`: Array of related model names to include in `refs.links` (may include models not used for keywords)

### Special Field References

- `refs.keywords`: References the keywords field from a related record's refs object
- Standard field names reference direct model fields

### Relationship Denormalization

In addition to keywords, the system denormalizes record IDs into `refs.links`. For example:

```json
{
  "links": {
    "vendor": [1, 2, 3],
    "customer": [4, 5],
    "contact": [6]
  }
}
```

Models listed in `related_models` will have their IDs collected into `refs.links` even if they're not used for keyword generation.

## Current Configurations

### Contact Model (refs_setup)

```json
{
    "self_fields": [
        "email",
        "name_first",
        "name_last",
        "company",
        "department"
    ],
    "related_keywords": {
        "email": ["email", "attention"],
        "location": ["address1", "city", "state", "zip", "country"],
        "phone": ["number", "country_code", "attention"],
        "customer": ["refs.keywords"],
        "vendor": ["refs.keywords"]
    },
    "related_models": ["email", "location", "phone", "customer", "vendor"]
}
```

This configuration tells the system to:

**Generate keywords from:**

- Contact's own email, names, company, and department
- Related email addresses and their attention lines
- Related location addresses
- Related phone numbers and country codes
- Keywords from associated customer and vendor records

**Include in refs.links:**

- All related email, location, phone, customer, and vendor record IDs

### Action Model (refs_setup) - Example

```json
{
    "self_fields": [
        "action.en",
        "action.bn",
        "action.ar",
        "description.en",
        "description.bn",
        "description.ar",
        "project_name",
        "assigned_to"
    ],
    "related_keywords": {
        "vendor": ["name", "email"],
        "contact": ["email", "name_first", "name_last", "company"],
        "customer": ["name", "email"]
    },
    "related_models": ["domain", "customer", "contact", "vendor"]
}
```

This action model configuration:

- Extracts keywords from action/description fields and project info
- Gets keywords from related vendor, contact, and customer names/emails
- Links to domain, customer, contact, and vendor records in refs.links (domain doesn't contribute keywords but is still linked)

## Workflow

1. Edit baseline files in `readmes/baseline_setting/models/` (model-specific) or `readmes/baseline_setting/` (purpose-specific)
2. Run the management command to update database settings:

   ```bash
   python manage.py refs_setting_manage --update-baseline --all-models
   ```

3. The settings are automatically used by the keyword generation system via `build_keywords_for_record()`

## Database Storage

Settings are stored in the `core_setting` table with:

- `model_name`: The model this configuration applies to
- `purpose`: The purpose of this configuration (e.g., "refs_setup")
- `data`: JSON blob containing the configuration
- `is_active`: Whether this setting is currently active
