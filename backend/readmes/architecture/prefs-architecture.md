# Prefs Architecture — Where Defaults Come From

## The Three Tiers

```mermaid
flowchart TD
    subgraph SYSTEM["Setting(parent_model='wc', purpose='system')"]
        S1[".prefs.company_name"]
        S2[".prefs.default_org_id"]
        S3[".prefs.currency"]
        S4[".prefs.timezone"]
        S5[".prefs.locale"]
        S6[".prefs.tax_id"]
    end

    subgraph MODEL_PAYMENT["Setting(parent_model='payment', purpose='field_access')"]
        P1[".prefs.defaults.type = 'expense'"]
        P2[".prefs.defaults.method = 'visa_3425'"]
        P3[".prefs.defaults.category = 'Office Supplies'"]
        P4[".config.select_lists.category"]
        P5[".config.select_lists.method"]
        P6[".config.field_behaviors"]
        P7[".config.select_lists.category.gl_map"]
    end

    subgraph MODEL_ORDER["Setting(parent_model='order', purpose='field_access')"]
        O1[".prefs.defaults.status = 'draft'"]
        O2[".prefs.defaults.priority = 'medium'"]
        O3[".prefs.defaults.terms"]
    end

    subgraph MODEL_INVOICE["Setting(parent_model='invoice', purpose='field_access')"]
        I1[".prefs.defaults.status = 'draft'"]
        I2[".prefs.defaults.terms = 'Net 30'"]
    end

    subgraph MODEL_CONTACT["Setting(parent_model='contact', purpose='field_access')"]
        C1[".prefs.defaults.salutation"]
        C2[".prefs.defaults.country = 'US'"]
    end

    subgraph FEATURE_GANTT["Setting(parent_model='gantt', purpose='feature')"]
        G1[".prefs.default_view = 'week'"]
        G2[".prefs.colors"]
        G3[".prefs.dependency_display"]
    end

    subgraph FEATURE_DB["Setting(parent_model='databrowser', purpose='feature')"]
        D1[".prefs.detail_width = 420"]
        D2[".prefs.font_size = 12"]
        D3[".prefs.theme = 'dark'"]
        D4[".prefs.density = 'comfortable'"]
    end

    subgraph DISPLAY["Setting(parent_model=X, purpose='workbench_fields')"]
        W1[".config.list = [field specs]"]
        W2[".config.detail = [field specs]"]
        W3[".config.views = [named layouts]"]
    end

    NEW_RECORD["+New Record"] --> |"1. system defaults"| SYSTEM
    NEW_RECORD --> |"2. model defaults"| MODEL_PAYMENT
    NEW_RECORD --> |"3. display prefs"| FEATURE_DB
    NEW_RECORD --> |"4. layout"| DISPLAY
```

## Flow: Creating a New Payment

```mermaid
sequenceDiagram
    participant U as User
    participant UI as databrowser
    participant WC as Setting(wc, system)
    participant FA as Setting(payment, field_access)
    participant WB as Setting(payment, workbench_fields)
    participant DB as Setting(databrowser, feature)
    participant API as wcapi/save

    U->>UI: Clicks +New
    UI->>FA: Read .prefs.defaults
    FA-->>UI: {type: expense, method: visa_3425, category: Office Supplies}
    UI->>WB: Read .config.detail
    WB-->>UI: [field order for form]
    UI->>DB: Read .prefs (or localStorage)
    DB-->>UI: {detail_width: 420, font_size: 12}
    UI->>UI: createBlankRecord() + apply defaults
    UI->>API: save(payment, {type: expense, method: visa_3425, ...})
    API-->>UI: {id: 42, ...}
    UI->>U: Form opens with defaults pre-filled
```

## The Rule

| Question | Answer |
|----------|--------|
| Is it about the company? | `Setting(wc, system).prefs` |
| Is it about how a model behaves? | `Setting(model, field_access).prefs` |
| Is it about how a model displays? | `Setting(model, workbench_fields).config` |
| Is it about a feature that isn't a model? | `Setting(feature_name, feature).prefs` |
| Is it about a specific record? | `record.prefs` (rare — userdefined fields) |
| Is it system/audit data? | `record.metadata` (GL postings, sync state, audit trail) |

## What Does NOT Go in Prefs

- **Record data** — amount, contact, date. That's model fields.
- **Audit trail** — GL postings, sync state. That's `.metadata`.
- **Computed values** — totals, balances. That's server-calculated.
- **User identity** — login, role, permissions. That's the User/UserProfile model.

## Where Record-Level `.prefs` Is Used

The `.prefs` JSONField on individual records is reserved for:

- **`prefs.userdefined`** — custom fields the user added to this record
- **`prefs.pinned`** — user pinned this record for quick access
- **`prefs.tags`** — user-applied tags (not categories — tags are personal)

These are record-level, user-initiated. Not defaults, not system config.

## Alice's Role

Alice observes usage patterns and recommends changes to Setting.prefs.defaults:

- 80% of expenses use "visa_3425" → confirm as default
- New category typed repeatedly → suggest adding to select list
- Users override a default consistently → suggest changing the default
- New user joins → Alice explains the current defaults and shows entry points

Alice never changes defaults without admin approval. She recommends.
The admin promotes. The pattern: `observe → log → pattern → recommend → promote`.
