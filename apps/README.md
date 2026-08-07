# Apps — Backend Model Organization

## Structure

```
apps/{domain}/
  models/           — Django models (database tables)
  management/       — seed commands, maintenance scripts
  services/         — business logic (totals, transfers, journalizer)
  views/            — API endpoints (save_view, bootstrap)
  signals.py        — post-save hooks, auto-calculations
  choices.py        — choice lists, purpose values
```

## App → domain mapping (mirrors React frontend)

| App | Models | What it owns |
|-----|--------|-------------|
| core | contact, action, setting, report, template, pending, audit, notification | BaseModel, save_view, bootstrap, wcapi |
| orgs | customer, vendor, manufacturer, employee, rep, organization | All inherit OrgBase |
| products | item, serial, warehouse, variant, specification, catalog, bom, org_item, flow, usage, service, item_xref | Inventory, serial lifecycle |
| transactions | order, invoice, proposal, purchase, receipt, requisition, work_order, payment, project + all line models | Totals, transfers, GL journalizing |
| communications | email, phone, address, domain | Contact communications |
| docs | document, tag, question_answer, linkage | File storage, tagging |
| sync | connection, bundle | Bidirectional sync, carrier APIs |
| support | campaign, quality | QA, campaigns |
| ai_assistant | alice models, observation, coaching, prompt history | Alice agent layer |
| accounts | authentication | Django auth integration |
| conversion | data import pipeline | CSV/Excel → WC3 via bundles |

## JSON envelope schemas

Every model's JSON fields (.config, .metadata, .prefs, .refs, .comments,
.actions) are defined in common/schemas/{model}.py with Pydantic validation.

See: readmes/topics/architecture/pydantic-envelope-schemas.md

## UI rendering

The backend does NOT control how models look in the UI. Layouts are Setting
records (detail_layout, workbench_fields) read by the React frontend's
Data-Driven UI renderer.

See: readmes/topics/architecture/data-driven-ui.md
