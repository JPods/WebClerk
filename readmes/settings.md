# Settings

> Configuration records with scope hierarchy. One model drives all
> layouts, defaults, field access, and behavior rules.

---

## Model: `Setting`

**File:** `apps/core/models/setting.py`
**Table:** `settings`
**Inherits:** `BaseModel`

### Fields

| Field          | Type          | Description |
|----------------|---------------|-------------|
| `name`         | CharField     | Identifier within a purpose (e.g. `"transaction_defaults"`) |
| `purpose`      | CharField     | Category — constrained by `SETTING_PURPOSE_CHOICES` |
| `scope`        | CharField     | Hierarchy level: `system`, `org`, `role`, `user` |
| `role`         | CharField     | Role name (when scope=role) |
| `org_id`       | BigIntegerField | Organization ID (when scope=org or role). 0 = all orgs |
| `contact_id`   | BigIntegerField | User contact ID (when scope=user). 0 = all users |
| `parent_model` | CharField     | Canonical model key (validated against MODEL_REGISTRY) |
| `config`       | JSONField     | The configuration payload — structure depends on purpose |

### Scope Hierarchy

Settings resolve from most specific to least specific.
First match wins:

```
user (contact_id=8)     ← Bill's personal layout
  ↓ not found
role (role="admin")     ← all admins see this
  ↓ not found
org (org_id=1)          ← this business's default
  ↓ not found
system                  ← global default for all
```

### Resolver

```python
from apps.core.services.setting_resolver import resolve_setting

# Get the effective detail layout for action, for this user
config = resolve_setting(
    purpose="detail_layout",
    parent_model="action",
    contact_id=8,        # Bill
    org_id=1,            # JPods
    role="admin",
)

# Returns config from the most specific match, or None
```

**API endpoint:**
```
GET /wcapi/setting/resolve/?purpose=detail_layout&parent_model=action
```
Returns `{config, scope}` — the effective config and which scope matched.

---

## Purpose Categories

### Layout & Display
| Purpose | What it stores |
|---------|---------------|
| `detail_layout` | DynamicDetail form layout — row order, fields per row, column count |
| `compact_layout` | Compact/floating window layout |
| `list_column_config` | databrowser list column order, widths, visibility |
| `field_registry` | Field types, labels, options, widgets per model |
| `view_edit` | Per-table field visibility/edit matrix by role |
| `field_access` | Field-level access control |
| `detail_field_access` | Detail page field access rules |
| `workbench_fields` | Workbench column config |

### Defaults
| Purpose | What it stores |
|---------|---------------|
| `db_defaults` | Global database/platform defaults |
| `constants` | Global user-defined constants |
| `sales_defaults` | Sales module defaults |
| `purchase_defaults` | Purchasing module defaults |
| `accounting_defaults` | Accounting/GL/tax defaults |
| `accounting_interface` | GL account mapping rules |
| `print_defaults` | Print/PDF defaults |

### Search & Keywords
| Purpose | What it stores |
|---------|---------------|
| `keywords` | Per-table keyword/denorm field config |
| `search` | Saved search presets |

### QA
| Purpose | What it stores |
|---------|---------------|
| `qa_counters` | QA counter configuration |
| `qa_questions` | QA question sets |

### Alice & AI
| Purpose | What it stores |
|---------|---------------|
| `alice_pending` | Alice's pending observation queue |
| `alice_log` | Alice's observation log |
| `alice_coaching` | Alice coaching rules and thresholds |
| `ai_prompt_history` | AI prompt/response history |

### Admin & System
| Purpose | What it stores |
|---------|---------------|
| `admin` | Admin-level settings |
| `admin_selectlist` | Admin select list overrides |
| `React_settings` | Settings consumed by the React frontend |
| `seed` | Seed data records |
| `system` | System-level configuration |
| `feature` | Feature flags |
| `schema_map` | Pydantic schema mappings |
| `calculated_function` | Custom calculated field definitions |

### Commerce & Collaboration
| Purpose | What it stores |
|---------|---------------|
| `campaign` | Campaign/marketing config |
| `company_profile` | Company/organization profile |
| `collaborate_webclerk` | WC_HQ collaboration settings |
| `wchq_connection` | WC_HQ connection config |

### Sync & Storage
| Purpose | What it stores |
|---------|---------------|
| `sync_config` | Sync connection defaults |
| `file_storage` | Image sizes, upload limits, storage paths |

### Gantt & Sprint
| Purpose | What it stores |
|---------|---------------|
| `gantt_defaults` | Default Gantt view settings per model |
| `burndown_config` | Burndown chart configuration |

---

## How DynamicDetail Uses Settings

When a DynamicDetail form opens for model "action":

1. Frontend calls `/wcapi/setting/resolve/?purpose=detail_layout&parent_model=action`
2. Resolver checks: user → role → org → system
3. Returns the layout config:
   ```json
   {
     "rows": [
       { "fields": ["action"], "cols": 1 },
       { "fields": ["assigned_to", "status"], "cols": 2 },
       { "fields": ["priority", "difficulty", "percent_complete"], "cols": 3 },
       { "fields": ["dt_start", "dt_deadline", "dt_completed"], "cols": 3 }
     ]
   }
   ```
4. DynamicDetail renders the form from this layout
5. In arrange mode, user reorders → saves back as a user-scoped Setting

---

## Creating Settings

### System default (everyone sees this)
```python
Setting.objects.create(
    name="action_detail_layout",
    purpose="detail_layout",
    scope="system",
    parent_model="action",
    config={"rows": [...]},
)
```

### User override (only Bill sees this)
```python
Setting.objects.create(
    name="action_detail_layout",
    purpose="detail_layout",
    scope="user",
    contact_id=8,
    parent_model="action",
    config={"rows": [...]},  # Bill's custom layout
)
```

### Org default (all users in org 1)
```python
Setting.objects.create(
    name="action_detail_layout",
    purpose="detail_layout",
    scope="org",
    org_id=1,
    parent_model="action",
    config={"rows": [...]},
)
```
