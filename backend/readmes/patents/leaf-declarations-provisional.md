# PROVISIONAL PATENT APPLICATION

## SYSTEM AND METHOD FOR DECLARATIVE JSON FIELD CLASSIFICATION IN DATABASE-DRIVEN USER INTERFACES

---

**Inventor:** William B. James
**Date:** August 20, 2026
**Status:** DRAFT — Provisional Patent Application

---

### FIELD OF THE INVENTION

The present invention relates to database-driven user interface rendering, and more particularly to a system and method for classifying schemaless JSON database fields by semantic purpose so that user interface components render them correctly without runtime value inspection.

### CROSS-REFERENCE TO RELATED APPLICATIONS

This application is related to the WebClerk commerce platform and its data-driven UI architecture (datadrivenui.com).

---

### BACKGROUND OF THE INVENTION

Modern web applications frequently store structured data in JSON (JavaScript Object Notation) columns within relational databases. Database systems such as PostgreSQL, MySQL, and SQLite provide native JSON column types that allow developers to store arbitrarily structured data alongside traditional typed columns (integers, strings, dates, booleans).

A fundamental problem arises when a user interface must render these JSON columns. Traditional typed columns carry their rendering intent in their type: a `BooleanField` renders as a checkbox, a `DateField` renders as a date picker, a `CharField` renders as a text input. JSON columns carry no such intent. The database type system says only "this is JSON" — it does not distinguish between:

1. **Display values** — simple key-value objects storing human-readable text in one or more languages (e.g., `{"en": "Draft term sheet", "es": "Borrador de hoja de terminos"}`). These should render as editable text fields.

2. **Structural envelopes** — nested data trees storing configuration, metadata, relationships, or system state (e.g., `{"history": {"created": {"dt": 1234567890}}, "flags": {"archived": false}}`). These should render as expandable tree viewers or specialized editors.

3. **Generic data** — JSON of indeterminate structure that requires a general-purpose editor.

#### Prior Art Limitations

Existing approaches to this problem include:

**A. Separate columns per language (django-modeltranslation, django-parler, wagtail):** The application creates individual database columns for each language variant (e.g., `title_en`, `title_es`, `title_fr`). This preserves type information but requires schema migrations when adding languages, scales poorly across many fields and languages, and does not generalize to the broader JSON classification problem.

**B. Runtime value inspection:** The user interface examines the actual value stored in the JSON column at render time and guesses the appropriate widget. If the value is a simple object with string values, render as text. If it is deeply nested, render as a tree. This approach is fragile: it fails when values are null, empty, or structurally ambiguous; it cannot distinguish between a language object `{"en": "text"}` and a configuration object `{"mode": "dark"}` when both have the same shape; and it creates inconsistent rendering when the same field contains different value shapes across records.

**C. Schema definition databases (Directus, Strapi, Payload CMS):** The headless CMS platforms store field metadata in a configuration database alongside the data itself. This introduces a stability risk: a corrupted or incorrectly edited metadata record can break rendering for an entire model. It also creates a dual source-of-truth problem between the code and the database.

**D. Widget type assertions in behavior configuration:** The application stores a `type` property (e.g., `"json"`, `"text"`, `"select"`) in a behavior configuration record. This type acts as an assertion that short-circuits all auto-detection logic. When the stored assertion is wrong or stale (as occurs after schema changes, migrations, or seed operations), the UI renders incorrectly and the error is invisible — the system appears to work but displays the wrong widget.

None of these approaches provide a reliable, code-defined, schema-aware mechanism for classifying JSON fields by semantic purpose that survives schema evolution, requires no runtime guessing, and maintains a single source of truth in version-controlled code.

### SUMMARY OF THE INVENTION

The present invention provides a system and method for declarative JSON field classification comprising:

1. **A leaf declaration registry** maintained in application source code that explicitly classifies every JSON database field by its semantic purpose: internationalization display value (`i18n`), structural envelope (`envelope`), or generic JSON (`json`).

2. **A classification service** that reads the leaf declaration registry and the application's data schema definitions (e.g., Pydantic, TypeORM, Zod, or equivalent schema validators) to produce a complete field classification map for each data model.

3. **An API response extension** that includes the leaf classification map alongside existing field behavior metadata, delivering the classification to the user interface layer in a single request.

4. **A rendering pipeline** in the user interface that reads the declared classification — not the runtime value — to select the appropriate widget, extraction method, and change handler for each field.

5. **An internationalization extraction protocol** wherein fields classified as `i18n` have their display value extracted by user language preference with fallback to the first value (`[0]`), and edits are wrapped back into the language-keyed object structure transparently.

The system eliminates runtime value guessing, survives schema evolution through code-level declarations, and maintains a single source of truth that is version-controlled, code-reviewed, and testable.

### DETAILED DESCRIPTION OF THE INVENTION

#### System Architecture

The invention operates across three layers of a web application stack:

```
LAYER 1: SCHEMA DEFINITION (Source of Truth)
    Schema validation classes (Pydantic, TypeORM, Zod, etc.)
    Leaf declaration registry (_I18N_FIELDS, _ENVELOPE_FIELDS sets)
        |
        v
LAYER 2: CLASSIFICATION SERVICE (Computation)
    get_leaf_declarations(model_key) function
    Reads schema + registry, produces classification map
    Included in API response alongside field behaviors
        |
        v
LAYER 3: USER INTERFACE (Rendering)
    Receives classification map on model load
    renderField() reads leaf.type to select widget
    No runtime value inspection for classified fields
```

#### Layer 1: Schema Definition and Leaf Declaration Registry

The leaf declaration registry consists of two explicitly maintained sets in application source code:

```python
_ENVELOPE_FIELDS = {'metadata', 'refs', 'prefs', 'config', 'comments', 'actions'}

_I18N_FIELDS = {
    'action', 'description', 'assigned_to', 'languages',
    'created_by', 'start_by', 'deadline_by', 'expected_by',
    'completed_by', 'updated_by', 'end_by',
}
```

Adding a new internationalized display field requires adding one entry to the `_I18N_FIELDS` set. The remainder of the pipeline handles it automatically.

The schema validation layer (in the preferred embodiment, Pydantic classes inheriting from base envelope schemas) provides structural definitions for envelope fields. The leaf declaration registry bridges the gap between the schema layer (which defines internal structure) and the UI layer (which needs rendering intent).

#### Layer 2: Classification Service

A classification function examines every JSON-typed field in a data model and produces a classification map:

```python
def get_leaf_declarations(model_key, field_map=None):
    leaves = {}
    for name, field in field_map.items():
        if field.type != 'JSONField':
            continue
        if name in _ENVELOPE_FIELDS:
            leaves[name] = {'type': 'envelope'}
        elif name in _I18N_FIELDS:
            leaves[name] = {'type': 'i18n', 'extract': '[0]'}
        else:
            leaves[name] = {'type': 'json'}
    return leaves
```

This function is called at request time (not at build time or deployment time) so that it always reflects the current state of the code. The classification map is included in the API response that delivers field behavior metadata to the user interface:

```json
{
  "behaviors": { ... },
  "field_groups": [ ... ],
  "leaves": {
    "action": {"type": "i18n", "extract": "[0]"},
    "description": {"type": "i18n", "extract": "[0]"},
    "config": {"type": "envelope"},
    "metadata": {"type": "envelope"},
    "refs": {"type": "envelope"}
  }
}
```

#### Layer 3: User Interface Rendering

The user interface stores the leaf classification map in application state on model load. When rendering a field, the rendering function reads the declared type rather than inspecting the value:

```typescript
function renderField(name, value, behavior, onChange, opts) {
    const isI18n = behavior.type === 'i18n'
        || opts?.leaf?.type === 'i18n';

    if (isI18n && typeof value === 'object') {
        // Extract display value: user language preference, then [0]
        const key = Object.keys(value)[0];
        const displayValue = value[key];
        // Render as text widget with transparent write-back
        const wrappedOnChange = (v) => onChange({...value, [key]: v});
        return <TextWidget value={displayValue} onChange={wrappedOnChange} />;
    }

    if (behavior.type === 'envelope' || opts?.leaf?.type === 'envelope') {
        return <JsonTreeWidget value={value} />;
    }

    // ... standard type detection for non-JSON fields
}
```

#### Internationalization Extraction Protocol

For fields classified as `i18n`, the system implements a transparent extraction and write-back protocol:

1. **Read path:** The stored value `{"en": "Draft term sheet"}` is extracted to the display string `"Draft term sheet"` before the widget receives it. The extraction key is determined by user language preference with fallback to the first key in the object.

2. **Write path:** When the user edits the display string to `"Final term sheet"`, the change handler wraps it back: `{"en": "Final term sheet"}`. The language key is preserved; only the value changes.

3. **Multi-value path:** When a field supports multiple selections (e.g., assigned team members), values are stored as comma-separated within the language key: `{"en": "Bill James, Claude Code"}`.

4. **List column path:** List/grid views use a `[0]` notation in column specifications (e.g., `assigned_to[0]`). The grid resolver interprets `[0]` on an object as "first value" (not numeric array index), extracting the display string for tabular presentation.

#### Advantages Over Prior Art

1. **No schema migration for new languages.** Unlike per-column approaches, adding a language requires no database changes.

2. **No runtime guessing.** Unlike value-inspection approaches, the classification is declared in code and never ambiguous.

3. **No database stability risk.** Unlike schema-definition-database approaches, the classification lives in version-controlled source code, is code-reviewed, and cannot be corrupted by a bad database write.

4. **Single source of truth.** The leaf declaration registry is the one place that determines rendering intent. It is not duplicated in configuration databases, behavior override records, or widget selection logic.

5. **One-line extensibility.** Adding a new internationalized field requires adding one entry to the `_I18N_FIELDS` set. The classification service, API response, and rendering pipeline handle it automatically.

6. **Survives schema evolution.** When fields are added, renamed, or removed, the registry is updated in the same code change. No separate migration, seed operation, or configuration update is required.

### CLAIMS

**1.** A computer-implemented method for rendering database fields stored as schemaless JSON in a user interface, comprising:
   - (a) maintaining a leaf declaration registry in application source code that classifies each JSON database field by semantic purpose, wherein the classifications include at least an internationalization display type and a structural envelope type;
   - (b) computing a classification map for a data model by reading the leaf declaration registry and the model's field definitions;
   - (c) transmitting the classification map to a user interface client as part of a field metadata response;
   - (d) selecting a user interface widget for each JSON field based on the declared classification rather than by inspecting the runtime value stored in the field.

**2.** The method of claim 1, wherein the internationalization display type classification causes the user interface to:
   - (a) extract a display value from a language-keyed JSON object by user language preference with fallback to the first value;
   - (b) render the extracted value in a text editing widget;
   - (c) wrap edited values back into the language-keyed object structure transparently.

**3.** The method of claim 1, wherein the structural envelope type classification causes the user interface to render the field as an expandable tree viewer using schema definitions from a validation framework.

**4.** The method of claim 1, wherein the classification map is computed at request time from source code declarations, ensuring the classification reflects the current state of the application without requiring a separate build, deployment, or configuration step.

**5.** The method of claim 1, wherein adding a new internationalized display field requires adding a single entry to the leaf declaration registry, with all downstream behavior — extraction, rendering, and write-back — handled automatically by the existing pipeline.

**6.** A system for declarative JSON field classification in a database-driven user interface, comprising:
   - (a) a leaf declaration registry stored in version-controlled application source code, comprising at least a first set of field names classified as internationalization display fields and a second set of field names classified as structural envelope fields;
   - (b) a classification service that reads the leaf declaration registry and produces a classification map for each data model;
   - (c) an application programming interface that includes the classification map in field metadata responses;
   - (d) a user interface rendering component that reads the classification map and selects widgets based on declared type rather than runtime value inspection.

**7.** The system of claim 6, wherein the leaf declaration registry is maintained alongside schema validation definitions such that both the data structure and the rendering intent for each field are defined in the same codebase.

**8.** The system of claim 6, further comprising an extraction protocol for internationalization display fields that:
   - (a) extracts a single display value from a multi-language JSON object;
   - (b) determines the extraction key by user language preference;
   - (c) falls back to the first value in the object when the preferred language is not present;
   - (d) preserves the language key structure when writing edited values back to the database.

**9.** The system of claim 6, wherein a list/grid view component interprets a bracket-zero notation (e.g., `field[0]`) on a JSON object field as "first value of the object" rather than as a numeric array index, enabling tabular display of internationalized values.

**10.** A computer-readable medium storing instructions that, when executed by a processor, cause the processor to:
   - (a) read a leaf declaration registry from application source code;
   - (b) classify each JSON-typed database field as one of: internationalization display, structural envelope, or generic JSON;
   - (c) transmit the classification to a user interface client;
   - (d) render each classified field using a widget selected by the declared classification rather than by runtime value inspection;
   - (e) for internationalization display fields, extract a display value by language preference and wrap edited values back into the language-keyed structure.

### ABSTRACT

A system and method for classifying schemaless JSON database fields by semantic purpose — internationalization display value, structural envelope, or generic JSON — using explicit declarations maintained in version-controlled application source code. A classification service reads the declarations and transmits a classification map to the user interface, which selects rendering widgets based on the declared type rather than inspecting runtime values. For internationalization display fields, the system extracts a single display value from a language-keyed JSON object by user language preference, renders it as editable text, and wraps edits back into the language-keyed structure transparently. The approach eliminates runtime guessing, survives schema evolution, requires no database migrations for new languages, and maintains a single source of truth in code.

### DRAWINGS

Reference is made to the accompanying flowchart diagram:
- `readmes/flowcharts/leaf-declarations.dot` (source)
- `readmes/flowcharts/leaf-declarations.svg` (rendered)

---

**NOTES FOR PATENT COUNSEL:**

1. This is a provisional application draft. Review and refine claims before filing.
2. The flowchart SVG should be formatted as a formal patent drawing (Figure 1).
3. Consider adding dependent claims for: the multi-select protocol (Cmd+click comma-separated values within a language key), the [0] notation resolver for grid columns, and the behavior type override mechanism (declared i18n overrides stored 'json' assertions).
4. Prior art search should cover: Directus field configuration, Strapi content-type builder, Payload CMS field types, django-modeltranslation, django-parler, and wagtail StreamField.
5. The provisional filing date establishes priority. A non-provisional application must be filed within 12 months.
