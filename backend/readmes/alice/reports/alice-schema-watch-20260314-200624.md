# Alice Schema Watch Report

- Timestamp (UTC): 2026-03-14 20:06:24
- Commit: working-tree
- Schema files touched: 1
- Models touched: (none inferred)
- Drift issues: total=949, high=148, medium=309, low=492

## Schema Files
- apps/orgs/models.py

## Likely Impacted Pages (Field-Level)
- (none detected)

## Per-Model Drift Summary
- address: 18 issues
- audit: 28 issues
- bundle: 28 issues
- catalog: 24 issues
- connection: 28 issues
- contact: 38 issues
- currency: 18 issues
- customer: 30 issues
- document: 41 issues
- domain: 21 issues
- email: 16 issues
- employee: 25 issues
- invoice: 52 issues
- item: 53 issues
- manufacturer: 25 issues
- notification: 21 issues
- order: 52 issues
- payment: 38 issues
- phone: 17 issues
- project: 20 issues
- proposal: 28 issues
- purchase: 24 issues
- receipt: 9 issues
- rep: 25 issues
- report: 28 issues
- requisition: 30 issues
- serial: 20 issues
- service: 24 issues
- setting: 16 issues
- specification: 21 issues
- tag: 24 issues
- template: 17 issues
- variant: 19 issues
- vendor: 30 issues
- warehouse: 17 issues
- workorder: 24 issues

## Admin.py Field Usage

## User Overrides
<!-- Alice-Instruction: Add alternative instructions below. Example: model=customer; list_display=ida,company; detail_order=company,status,metadata,refs -->
- To provide alternative instructions, add a note via /wcapi/ai/note/ with:
  category=pending, role=config_suggestion, name='Schema report override',
  details={model, list_display, detail_order, rationale}
