# Saved Searches — Operations Guide
**Status:** Design complete | **Source:** Bill 2026-07-04

---

## Principle

No new model. Saved searches are Report records with `category='saved_search'`. A saved search is just a report that returns data instead of a formatted document. Fewer tables is good.

---

## Report Model Handles Three Things

| Category | What It Does | Output |
|---|---|---|
| `customer_facing` / `operations` / `accounting` / `sales_analysis` | Print documents, PDFs | Formatted document |
| `email` (delivery_type='email') | Email templates | SMTP send + Action |
| `saved_search` | Reusable queries | DataBrowser filtered view |

Same model, different category. Same pdfme template system for documents, same config JSON for queries.

---

## Saved Search Config

```json
Report (category='saved_search') config = {
  "model": "invoice",
  "filters": [
    {"field": "status", "op": "eq", "value": "planned"},
    {"field": "total", "op": "gte", "value": 1000},
    {"field": "dt_created", "op": "gte", "value": "last_30_days"}
  ],
  "sort": [
    {"field": "total", "direction": "desc"}
  ],
  "fields": ["ida", "customer.company", "total", "status", "dt_created"],
  "description": "Large planned invoices from last 30 days"
}
```

Loading a saved search = opening DataBrowser with these filters pre-applied.

---

## Security — MUST Inject User Context

Every saved search execution MUST inject the user's identity:

```python
def execute_saved_search(report_id, user):
    config = report.config
    qs = build_queryset(config['model'], config['filters'])
    
    # MANDATORY: apply user's query_scope from field_access Setting
    qs = inject_role_filters(qs, user)
    
    # Rep sees only their customers
    # Vendor sees only their products
    # field_access controls which fields are visible/editable
    
    return qs
```

No one can query outside their gated allowance. The saved search defines WHAT to query. The user's role defines WHAT THEY CAN SEE.

---

## Per-User Favorites (Alice)

Alice stores frequently used queries per user — without cluttering the global Report list:

```json
Contact.metadata.saved_searches = [
  {
    "name": "My open orders",
    "model": "order",
    "filters": [{"field": "status", "op": "in", "value": ["planned", "released"]}],
    "sort": [{"field": "dt_created", "direction": "desc"}],
    "dt_last_used": 1720100000000,
    "use_count": 47
  }
]
```

Alice observes: if a user runs the same manual filter 5+ times, suggest saving it. Batch coaching — "You've filtered orders by status=planned 7 times this week. Want me to save this as a quick search?"

---

## Power Users — SQL View

Power users can view the generated SQL in the JSON viewer. Click the saved search's config label → JSON viewer opens → they see the filter definitions. Advanced users can edit the JSON directly.

The actual SQL is never exposed directly — the filter config is translated to Django ORM queries server-side. But the config JSON IS the query in human-readable form.

---

## Dashboard (future)

Reports + Saved Searches + Scripts need a management dashboard:
- List all Report records grouped by category
- Quick-run any saved search
- Edit/create via DataBrowser or JSON viewer
- Alice helps organize — suggests grouping, flags unused, promotes popular

This is a DataBrowser view on the Report model filtered by category. No new page needed — just good field_access Settings and named views.

---

## Files

| File | Status | Purpose |
|------|--------|---------|
| `apps/core/models/report.py` | Exists | Report model stores saved searches |
| `apps/core/management/commands/seed_report_templates.py` | Exists | Can seed saved search templates |
| Saved search executor | Needs building | Apply filters + inject user scope + return queryset |
