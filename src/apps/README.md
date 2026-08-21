# Apps — Where Model Code Lives

## Data-Driven UI Architecture

Most models do NOT have custom detail pages. The UI is data-driven:

```
Setting (config.layout)  →  DataBrowser  →  BehaviorField  →  Widget
   JSON in database         one renderer    field behaviors    20 widgets
```

To change how a model's detail page looks, edit its layout Setting in Design
Mode — not code. See: readmes/topics/architecture/data-driven-ui.md

## Three Rendering Paths

Every model uses exactly one:

| Path | Where the UI comes from | Examples |
|------|------------------------|----------|
| **form** | Setting record (config.layout.form) → DynamicDetail | order, contact, item, invoice |
| **detail** | DataBrowser auto-renders from model fields (config.layout.detail) | gl_account, currency, tag, audit |
| **custom** | Custom .tsx component in this folder | Kanban, Gantt, sprint burndown |

**Terms established 2026-08-18:** list, detail, form, column. See `db-layout-schema.md`.

## What's in each model folder

```
apps/{domain}/models/{model}/
  {Model}.ts          — field list, display config
  index.ts            — exports
  services/           — API calls (wcapi wrappers)
  types/              — TypeScript interfaces
  utils/              — validation schemas (Zod)
  pages/              — ONLY if this model has a custom path
  components/         — ONLY if this model has custom embedded components
```

If a model folder has no pages/ subfolder, its detail UI comes from a
Setting record — look in the database, not in the code.

## App → domain mapping (mirrors WC3 backend)

| App | Models | Notes |
|-----|--------|-------|
| core | contact, action, setting, report, template, pending, audit, notification | Contact is the richest — has ContactDetailJson.tsx |
| orgs | customer, vendor, manufacturer, employee, rep, organization | All share OrgDetail.json.tsx |
| products | item, serial, warehouse, variant, specification, catalog, bom, org_item, flow, usage, service, item_xref | Item has ItemDetailJson.tsx |
| transactions | order, invoice, proposal, purchase, receipt, requisition, work_order, payment, project + all line models | All share TransactionDetail.tsx |
| communications | email, phone, address, domain | All rendered via CommCard/CommPanel |
| docs | document, tag, question_answer, linkage | |
| sync | connection, bundle | Bundle has BundleDetail.tsx |
| support | campaign, quality | |

## Shared renderers (in components/common/)

| Component | What it renders | Lines |
|-----------|----------------|-------|
| DynamicDetail.tsx | Any model with a form layout Setting | 616 |
| GroupedDetailFields.tsx | Any model in admin/detail mode | 101 |
| BehaviorField.tsx | Individual fields based on field_behaviors Setting | 36 |

## Where to look when something is wrong

1. **Layout wrong** → Setting record with purpose=wc:model, parent_model={model}, check config.layout
2. **Field behavior wrong** → Same Setting, check config.behaviors
3. **Widget broken** → components/fields/{WidgetName}.tsx
4. **Print broken** → apps/transactions/components/print/
5. **List columns wrong** → Same Setting, check config.layout.list
