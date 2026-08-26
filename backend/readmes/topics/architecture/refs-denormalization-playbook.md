# Refs Denormalization Playbook

Action: Define and operate FK-first denormalization rules for refs.links and refs.keywords.
Function: `maintain_contact_communications()` and `audit_refs_templates` maintain FK-first denormalized display/search payloads.
Frequency: Every model design/update touching relationships, plus during maintenance and audits.
Process: Define source-of-truth FK -> define refs templates/fields -> run maintenance -> run audit -> document examples.

## Purpose

This playbook defines how FK relationships and refs denormalization must work together.

- FK columns are always the source of truth for ownership and joins.
- refs.links is a denormalized display/search cache.
- refs.keywords is a denormalized search token list.

## Action Header Semantics

- `Action:` The operational outcome or task the readme supports.
- `Function:` The actual function, command, service, management command, or entry point associated with the process when one exists.
- `Frequency:` When the function/process should be run or reviewed.
- `Process:` The execution sequence.

If no single callable exists, `Function:` may name the owning subsystem or service responsibility instead.

## Core Rule

For any pair of related models:

1. Query/filter/constraints use FK.
2. Display/search acceleration uses refs.links + refs.keywords.
3. Rebuild jobs reconcile refs from FK when drift appears.

## Contact <-> Communications Pattern

### Source of Truth

- Email.contact_id, Phone.contact_id, Domain.contact_id, Address.contact_id
- Contact.email_id, Contact.phone_id, Contact.domain_id, Contact.address_id (primary pointers)

### Denormalize into Contact.refs.links

Contact refs should include communication snapshots:

- contact.refs.links.email[]
- contact.refs.links.phone[]
- contact.refs.links.domain[]
- contact.refs.links.address[]

Empty communication buckets should be omitted entirely. Do not store:

- `refs.links.email: []`
- `refs.links.phone: []`
- `refs.links.domain: []`
- `refs.links.address: []`

Example:

```json
{
  "refs": {
    "links": {
      "phone": [
        {
          "id": 3,
          "number": "3435551212",
          "name": "home",
          "country_code": "+1",
          "format": "(343) 555-1212",
          "opt_out": true
        }
      ]
    }
  }
}
```

### Reverse Denormalize into Communication.refs

Each communication row must carry a contact snapshot and keywords.

- communication.refs.links.contact[] contains key contact fields.
- communication.refs.keywords contains lowercased search terms including:
  - contact name_first
  - contact name_last
  - contact display name
  - contact email/phone/company
  - communication-specific values (email address, phone number, etc.)

Example (phone row):

```json
{
  "refs": {
    "links": {
      "contact": [
        {
          "id": 18,
          "name_first": "Bill",
          "name_last": "James",
          "email": "bill@example.com",
          "company": "Commerce Expert"
        }
      ]
    },
    "keywords": [
      "bill",
      "james",
      "bill james",
      "bill@example.com",
      "3435551212",
      "commerce expert",
      "home"
    ]
  }
}
```

## Field Templates

### Registry (refs.links payload fields)

- file: common/denorm_registry.py
- owner: backend architecture
- use: standardized denormalized fields per model key

### Link + keyword templates

- file: apps/core/services/link_defaults.py
- owner: API/service layer
- use: runtime template for refs.links entry shape and keyword extraction intent

## Operational Commands

### Reconcile contact communications FK <-> refs

```bash
python manage.py contact_communications_maintenance
```

Useful options:

```bash
python manage.py contact_communications_maintenance --dry-run
python manage.py contact_communications_maintenance --contact-id 18
python manage.py contact_communications_maintenance --limit 500
python manage.py contact_communications_maintenance --no-alice
```

### Audit refs template coverage (Alice-aware)

```bash
python manage.py audit_refs_templates
python manage.py audit_refs_templates --no-alice
```

## Alice Integration

The process emits Alice notes for visibility:

- alice_pending/data_quality for duplicate communication values.
- alice_pending/action_required when maintenance errors occur.
- alice_log/system run summary after maintenance.
- refs template audit logs via alice_log/system and config gap notes when detected.

## Adding a New Model to Denormalization

1. Add fields in common/denorm_registry.py.
2. Add/adjust template in apps/core/services/link_defaults.py.
3. Add examples to this playbook.
4. Run:

```bash
python manage.py audit_refs_templates
```

5. Run model-specific backfill/maintenance command.

## Guardrails

- Never treat refs.links as the write authority over FK.
- Do not store conflicting IDs in refs.links and FK for the same relationship.
- Keep refs.keywords lowercase and deduplicated.
- Prefer stable keys (`id`, canonical field names) in refs.links snapshots.
- Omit empty refs.links buckets instead of storing empty arrays.

## Best-Guess Coverage by App (Current Direction)

This is the current recommended scope for denormalization.

| App | Strategy |
|---|---|
| contacts (core.Contact) | FK-first + two-way refs denormalization with communications |
| actions (core.Action) | FK/explicit IDs for authority + refs for dependency graph and denormalized parties |
| communications | FK owner (`contact_id`) authoritative; refs holds contact snapshot + search keywords |
| docs | FK or explicit ids authoritative; refs links for display context (contact/org/tag/linkage) |
| orgs | FK/role FKs authoritative; refs links for related transaction/contact display acceleration |
| transactions | Header/line FK fields + parent/source authoritative; refs links for customer/vendor/manufacturer/contact and UI display |
| all other apps for now | FK-only (no new refs denormalization until explicitly approved) |

## Best-Guess Model Guidance by App

### 1) Contacts App (core)

Primary model: `contact`

- Source of truth:
  - Contact scalar fields and primary communication pointer ids (`email_id`, `phone_id`, `domain_id`, `address_id`)
  - Communication ownership FKs (`communication.contact_id`)
- Denormalize on contact:
  - `contact.refs.links.email[]`
  - `contact.refs.links.phone[]`
  - `contact.refs.links.domain[]`
  - `contact.refs.links.address[]`
- Reverse denormalize on communication rows:
  - `communication.refs.links.contact[]`
  - `communication.refs.keywords[]` including `name_first`, `name_last`, display name, and comm values

### 2) Actions App (core)

Primary model: `action`

- Source of truth:
  - Explicit relation fields / target ids used by action services
  - Action dependency truth remains in action dependency payloads (parents/depends_on semantics)
- Denormalize on action:
  - `action.refs.links.contact[]` for assigned/requested contacts
  - `action.refs.links.org[]` (or role buckets when available) for display context
  - `action.refs.parents[]`, `action.refs.depends_on{}` for graph traversal (not FK replacement)
  - `action.refs.keywords[]` with action name/description + party names

### 3) Communications App

Primary models: `email`, `phone`, `domain`, `address`

- Source of truth:
  - `contact_id` FK ownership
  - model scalar values (`email`, `number`, `path`, `address*`)
- Denormalize on comm rows:
  - `refs.links.contact[]` (one or more denormalized contact entries)
  - `refs.keywords[]` contact + communication tokens
- Denormalize on contact:
  - reflected snapshots under `contact.refs.links.<comm_model>[]`

### 4) Docs App

Primary models: `document`, `tag`, `linkage`, `question_answer`

- Source of truth:
  - FK and direct ids in model fields
- Denormalize:
  - `document.refs.links.contact[]` when document belongs to/created for a contact
  - `document.refs.links.org[]` or role-based org buckets for customer/vendor/manufacturer context
  - `document.refs.links.tag[]` for quick display chips
  - `document.refs.links.linkage[]` for cross-transaction/doc chains
  - `document.refs.keywords[]` from title, file name, tag names, linked party names

### 5) Orgs App

Primary models: `org` and role facades (`customer`, `vendor`, `manufacturer`, `employee`, `rep`)

- Source of truth:
  - Org model fields + role identity
  - FK links in downstream records (contacts/transactions)
- Denormalize:
  - On transaction-like consumers: `refs.links.customer[]`, `refs.links.vendor[]`, `refs.links.manufacturer[]`
  - On org itself (optional and limited):
    - `org.refs.links.contact[]` for key contacts
    - `org.refs.links.transaction[]` only for lightweight recent context (avoid large fan-out)
  - `org.refs.keywords[]` from company, ida, email, phone, attention

### 6) Transactions App

Primary models: `proposal`, `order`, `invoice`, `purchase`, `workorder`, `requisition` and line models

- Source of truth:
  - Header FKs: customer/vendor/manufacturer/contact/rep/employee where present
  - Parent/source flow fields on header/line models
  - Line foreign keys and ids
- Denormalize on headers:
  - `refs.links.customer[]`, `vendor[]`, `manufacturer[]`, `contact[]`
  - `refs.keywords[]` from doc identity + linked party snapshots
- Denormalize on lines (selective):
  - `refs.links.item[]` for SKU/name display
  - `refs.links.linkage[]` for transfer chains
  - avoid large payload snapshots on every line unless needed by UI

## FK-Only Policy for Other Apps (For Now)

For apps outside the scope above (for example: accounts/support/sync/products internals not explicitly listed in this document), default to:

1. Use FK/model fields only for relationships.
2. Do not add new `refs.links.*` buckets unless there is a demonstrated UI/search need.
3. If denormalization is proposed, add:
   - a template in `apps/core/services/link_defaults.py`
   - a field registry entry in `common/denorm_registry.py`
   - a maintenance/backfill path
   - an example update in this playbook.
