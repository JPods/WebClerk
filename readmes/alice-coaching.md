# Alice Coaching System

**Created:** 2026-06-29
**Purpose:** Alice coaches users in real-time as they work — writing scripts, managing layouts, entering data, navigating the system. Coaching content is stored as records, not hardcoded.

## Architecture

Alice's coaching is **data, not code**. Coaching content lives in Setting records (purpose='alice_coaching') and can be synced from WCHQ, submitted by users for bonus credit, and refined by Alice as she learns what users actually need help with.

### Coaching Record Structure

```json
{
  "purpose": "alice_coaching",
  "parent_model": "invoice",
  "name": "alice_coaching:invoice",
  "data": {
    "context": {
      "page": "detail",
      "trigger": "on_load"
    },
    "tips": [
      {
        "id": "inv-01",
        "title": "Invoice Status Flow",
        "body": "Invoices move: planned → released → complete. Only released invoices can be posted to GL.",
        "type": "concept",
        "level": "beginner"
      },
      {
        "id": "inv-02",
        "title": "Balance Due",
        "body": "Balance = Total - Payments. When balance reaches 0, the invoice is fully paid.",
        "type": "concept",
        "level": "beginner"
      }
    ],
    "field_help": {
      "total": "Calculated from line items. Edit lines to change the total — don't edit directly.",
      "balance": "Total minus payments received. Read-only — updated when payments are applied.",
      "status": "planned = draft, released = sent to customer, complete = paid and closed.",
      "terms": "Payment terms (N30, COD, etc.). Sets the due date on the ledger record.",
      "price_level": "Which price tier to use for this customer (retail, wholesale, distributor)."
    },
    "actions": {
      "create": "To create an invoice: select a customer first, then add line items. Each line needs an item and quantity.",
      "print": "Use the Reports button (🖨) to choose a print format. Standard Invoice is the default.",
      "payment": "To apply a payment: navigate to Payments > Apply Payments, select the invoice, enter amount."
    },
    "warnings": [
      "Don't change status to 'complete' manually — it should happen when balance reaches 0.",
      "GL posting is one-way. Once posted, you can only reverse, not edit."
    ],
    "related_docs": [
      {"title": "GL Journal Export", "url": "/readmes/wcapi-query-scoping.md"},
      {"title": "Print Formats", "url": "/readmes/databrowser-initial-layouts.md"}
    ],
    "code_examples": [
      {
        "title": "Fetch invoice via wcapi",
        "language": "javascript",
        "code": "const res = await getRecord('invoice', invoiceId);\nconst invoice = res.record;\nconsole.log(invoice.total, invoice.balance);"
      },
      {
        "title": "Create invoice via wcapi",
        "language": "javascript",
        "code": "await saveRecord('invoice', {\n  customer_id: customerId,\n  status: 'planned',\n  price_level: 'retail',\n});"
      }
    ],
    "api_reference": {
      "get": "GET /wcapi/get/?model_name=invoice&id={id}",
      "list": "GET /wcapi/get/?model_name=invoice&status=released&ordering=-dt_created",
      "save": "POST /wcapi/save/ {model_name: 'invoice', ...fields}",
      "delete": "POST /wcapi/delete/ {model_name: 'invoice', id: {id}}"
    }
  }
}
```

### Content Types

| Type | What it is | When Alice shows it |
|------|-----------|-------------------|
| **tips** | Short conceptual guidance | On page load, in a coaching panel |
| **field_help** | Per-field explanation | On field focus or hover |
| **actions** | Step-by-step for common tasks | When user clicks a task button or seems stuck |
| **warnings** | Things that can go wrong | Before destructive actions or common mistakes |
| **related_docs** | Links to readmes and guides | In coaching panel sidebar |
| **code_examples** | Copy-pastable code snippets | When user is writing scripts or using the API |
| **api_reference** | Endpoint signatures | When user opens API docs or types in a script |

### Coaching Levels

| Level | Who it's for | What Alice shows |
|-------|-------------|-----------------|
| **beginner** | New users, first week | Everything — tips, field help, step-by-step actions, warnings |
| **intermediate** | Users who know basics | Field help on hover, warnings, code examples |
| **advanced** | Power users, developers | Code examples, API reference, keyboard shortcuts |
| **expert** | Admins, WCHQ staff | Nothing unless asked — Alice stays quiet |

Level stored on Contact.metadata.coaching_level. Default: beginner. Alice can suggest promotion: "You've completed 50 invoices without errors — want me to reduce coaching tips?"

## How Alice Delivers Coaching

### 1. Coaching Panel (side drawer)

A collapsible panel on the right side of any page. Shows:
- Tips relevant to the current page/model
- Field help for the selected field
- Action guides for available operations
- Code examples if the user has developer role

Toggle: keyboard shortcut (Cmd/Ctrl+?) or toolbar button.

### 2. Field-Level Help

When a user focuses on a field, Alice can show a tooltip with the `field_help` text from the coaching record. This is NOT the field_behaviors label — it's the explanation of what the field means and how to use it.

### 3. Contextual Warnings

Before destructive actions (delete, GL post, status change to complete), Alice shows relevant warnings from the coaching record. Not a confirmation dialog — a coaching moment: "Here's what this means and why it matters."

### 4. Smart Suggestions

Alice watches user behavior (via alice_log events) and suggests:
- "You've been searching for items by name — try using the SKU field for exact matches"
- "This customer has 3 overdue invoices — want to see the collections view?"
- "You're editing the same 5 fields on every order — save a layout to speed this up"

### 5. Script Helper

When a user opens a script editor or the API test tool:
- Auto-complete model names from the registry
- Show API signatures from the coaching record
- Suggest code examples based on what model the user is working with
- Link to relevant readmes

## Seeding Coaching Content

```bash
./bin/python manage.py seed_coaching          # seed for all models
./bin/python manage.py seed_coaching --force   # overwrite existing
```

### What gets seeded per model:
- 2-3 beginner tips (what the model is, how it fits in the workflow)
- field_help for the 10 most important fields
- Action guides for create, print, common operations
- 1-2 warnings for dangerous operations
- 1-2 code examples (get, save via wcapi)
- API reference (get, list, save, delete endpoints)

### User-submitted coaching content

Users can submit coaching tips via sync (same as layouts):
1. User writes a helpful tip or code example
2. Submits via Submit for Bonus
3. WCHQ reviews and approves
4. Sync pushes to all deployments
5. Alice serves it to other users
6. Original author gets credit based on adoption

## Integration Points

| System | How Alice uses it |
|--------|------------------|
| **field_access Setting** | Knows which fields the user can see/edit — only coaches on visible fields |
| **field_behaviors Setting** | Knows field types — coaches differently for selects vs. text vs. lookups |
| **alice_log** | Tracks what users do — feeds smart suggestions |
| **alice_pending** | User-reported issues — Alice can offer proactive help for known problems |
| **workbench_fields Setting** | Knows user's layout preferences — suggests optimizations |

## Key Files

| File | Purpose |
|------|---------|
| `readmes/alice-coaching.md` | This document |
| `readmes/daily-development-practice.md` | Development practices Alice coaches on |
| `readmes/databrowser-initial-layouts.md` | Layout design principles |
| `readmes/wcapi-query-scoping.md` | API security model |
| `apps/core/management/commands/seed_coaching.py` | Seeder (to be built) |

## Next Steps

1. Build `seed_coaching.py` management command
2. Build React CoachingPanel component (side drawer)
3. Add coaching_level to Contact.metadata
4. Wire field_help tooltips into BehaviorField
5. Connect alice_log events to smart suggestions
