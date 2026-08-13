# Layout ↔ Schema Drift Report

> Generated: 2026-08-12 04:34  
> Models scanned: 18  
> Total issues (excl. info): 339

**Trend:** 📉 declining (200 total corrections over 14 scans)

## Summary

| Severity | Count |
|----------|-------|
| 🔴 High (phantom fields) | 16 |
| 🟡 Medium (required unrendered) | 10 |
| 🔵 Low (optional unrendered) | 313 |
| ℹ️  Info (detail-only) | 0 |

## Audit

Django fields: 29 | Pages: display(1)

- 🔵 **changes** (`unrendered_field`): Django has 'changes' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:changes:unrendered_field`
- 🔵 **config** (`unrendered_field`): Django has 'config' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:config:unrendered_field`
- 🔵 **conflicts** (`unrendered_field`): Django has 'conflicts' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:conflicts:unrendered_field`
- 🔵 **dt_approved** (`unrendered_field`): Django has 'dt_approved' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:dt_approved:unrendered_field`
- 🔵 **dt_last_used** (`unrendered_field`): Django has 'dt_last_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:dt_last_used:unrendered_field`
- 🔵 **is_completed** (`unrendered_field`): Django has 'is_completed' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:is_completed:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:is_locked:unrendered_field`
- 🔵 **name** (`unrendered_field`): Django has 'name' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:name:unrendered_field`
- 🔵 **priority** (`unrendered_field`): Django has 'priority' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:priority:unrendered_field`
- 🔵 **purpose** (`unrendered_field`): Django has 'purpose' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:purpose:unrendered_field`
- 🔵 **rating** (`unrendered_field`): Django has 'rating' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:rating:unrendered_field`
- 🔵 **recommendations** (`unrendered_field`): Django has 'recommendations' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:recommendations:unrendered_field`
- 🔵 **times_used** (`unrendered_field`): Django has 'times_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:times_used:unrendered_field`
- 🔵 **config** (`unrendered_json`): JSONField 'config' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:config:unrendered_json`
- 🔵 **changes** (`unrendered_json`): JSONField 'changes' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:changes:unrendered_json`
- 🔵 **conflicts** (`unrendered_json`): JSONField 'conflicts' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:conflicts:unrendered_json`
- 🔵 **recommendations** (`unrendered_json`): JSONField 'recommendations' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:recommendations:unrendered_json`

## Bundle

Django fields: 35 | Pages: detail(1)
  **Detail** (17 fields): `alert`, `config`, `conflicts`, `connection_id`, `data`, `description`, `direction`, `duration`, `encryption`, `maps`, `name`, `payload`...

- 🔴 **data** (`phantom_field`): Layout references 'data' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:data:phantom_field`
- 🔴 **description** (`phantom_field`): Layout references 'description' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:description:phantom_field`
- 🔴 **name** (`phantom_field`): Layout references 'name' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:name:phantom_field`
- 🔵 **dt_approved** (`unrendered_field`): Django has 'dt_approved' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:dt_approved:unrendered_field`
- 🔵 **dt_last_used** (`unrendered_field`): Django has 'dt_last_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:dt_last_used:unrendered_field`
- 🔵 **dt_processed** (`unrendered_field`): Django has 'dt_processed' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:dt_processed:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:is_locked:unrendered_field`
- 🔵 **purpose** (`unrendered_field`): Django has 'purpose' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:purpose:unrendered_field`
- 🔵 **times_used** (`unrendered_field`): Django has 'times_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:times_used:unrendered_field`

## Catalog

Django fields: 38 | Pages: display(1)
  **Display** (5 fields): `category`, `description`, `metadata`, `name`, `price`

- 🔴 **category** (`phantom_field`): Layout references 'category' but Django model has no such field. Found in: display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:category:phantom_field`
- 🔴 **description** (`phantom_field`): Layout references 'description' but Django model has no such field. Found in: display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:description:phantom_field`
- 🔴 **price** (`phantom_field`): Layout references 'price' but Django model has no such field. Found in: display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:price:phantom_field`
- 🟡 **code** (`unrendered_field`): Django has 'code' (CharField) but no layout references it. Required field — likely needs a form input.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:code:unrendered_field`
- 🟡 **dt_effective_start** (`unrendered_field`): Django has 'dt_effective_start' (BigIntegerField) but no layout references it. Required field — likely needs a form input.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:dt_effective_start:unrendered_field`
- 🔵 **applies_to** (`unrendered_field`): Django has 'applies_to' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:applies_to:unrendered_field`
- 🔵 **config** (`unrendered_field`): Django has 'config' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:config:unrendered_field`
- 🔵 **currency** (`unrendered_field`): Django has 'currency' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:currency:unrendered_field`
- 🔵 **dt_approved** (`unrendered_field`): Django has 'dt_approved' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:dt_approved:unrendered_field`
- 🔵 **dt_effective_end** (`unrendered_field`): Django has 'dt_effective_end' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:dt_effective_end:unrendered_field`
- 🔵 **dt_last_used** (`unrendered_field`): Django has 'dt_last_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:dt_last_used:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:is_locked:unrendered_field`
- 🔵 **is_universal_pct** (`unrendered_field`): Django has 'is_universal_pct' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:is_universal_pct:unrendered_field`
- 🔵 **margin_floor** (`unrendered_field`): Django has 'margin_floor' (DecimalField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:margin_floor:unrendered_field`
- 🔵 **metrics** (`unrendered_field`): Django has 'metrics' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:metrics:unrendered_field`
- 🔵 **priority** (`unrendered_field`): Django has 'priority' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:priority:unrendered_field`
- 🔵 **purpose** (`unrendered_field`): Django has 'purpose' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:purpose:unrendered_field`
- 🔵 **times_used** (`unrendered_field`): Django has 'times_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:times_used:unrendered_field`
- 🔵 **universal_pct** (`unrendered_field`): Django has 'universal_pct' (DecimalField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:universal_pct:unrendered_field`
- 🔵 **config** (`unrendered_json`): JSONField 'config' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:config:unrendered_json`
- 🔵 **metrics** (`unrendered_json`): JSONField 'metrics' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:metrics:unrendered_json`
- 🔵 **applies_to** (`unrendered_json`): JSONField 'applies_to' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:applies_to:unrendered_json`

## Contact

Django fields: 54 | Pages: detail(1)

- 🟡 **email** (`unrendered_field`): Django has 'email' (CharField) but no layout references it. Required field — likely needs a form input.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:email:unrendered_field`
- 🔵 **address_full** (`unrendered_field`): Django has 'address_full' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:address_full:unrendered_field`
- 🔵 **address_id** (`unrendered_field`): Django has 'address_id' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:address_id:unrendered_field`
- 🔵 **attention** (`unrendered_field`): Django has 'attention' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:attention:unrendered_field`
- 🔵 **comment** (`unrendered_field`): Django has 'comment' (TextField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:comment:unrendered_field`
- 🔵 **company** (`unrendered_field`): Django has 'company' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:company:unrendered_field`
- 🔵 **config** (`unrendered_field`): Django has 'config' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:config:unrendered_field`
- 🔵 **department** (`unrendered_field`): Django has 'department' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:department:unrendered_field`
- 🔵 **domain** (`unrendered_field`): Django has 'domain' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:domain:unrendered_field`
- 🔵 **domain_id** (`unrendered_field`): Django has 'domain_id' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:domain_id:unrendered_field`
- 🔵 **dt_approved** (`unrendered_field`): Django has 'dt_approved' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:dt_approved:unrendered_field`
- 🔵 **dt_joined** (`unrendered_field`): Django has 'dt_joined' (DateTimeField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:dt_joined:unrendered_field`
- 🔵 **dt_last_used** (`unrendered_field`): Django has 'dt_last_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:dt_last_used:unrendered_field`
- 🔵 **email_id** (`unrendered_field`): Django has 'email_id' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:email_id:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:is_locked:unrendered_field`
- 🔵 **is_staff** (`unrendered_field`): Django has 'is_staff' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:is_staff:unrendered_field`
- 🔵 **name_first** (`unrendered_field`): Django has 'name_first' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:name_first:unrendered_field`
- 🔵 **name_last** (`unrendered_field`): Django has 'name_last' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:name_last:unrendered_field`
- 🔵 **name_middle** (`unrendered_field`): Django has 'name_middle' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:name_middle:unrendered_field`
- 🔵 **name_prefix** (`unrendered_field`): Django has 'name_prefix' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:name_prefix:unrendered_field`
- 🔵 **name_suffix** (`unrendered_field`): Django has 'name_suffix' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:name_suffix:unrendered_field`
- 🔵 **phone** (`unrendered_field`): Django has 'phone' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:phone:unrendered_field`
- 🔵 **phone_id** (`unrendered_field`): Django has 'phone_id' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:phone_id:unrendered_field`
- 🔵 **purpose** (`unrendered_field`): Django has 'purpose' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:purpose:unrendered_field`
- 🔵 **role** (`unrendered_field`): Django has 'role' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:role:unrendered_field`
- 🔵 **source_name** (`unrendered_field`): Django has 'source_name' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:source_name:unrendered_field`
- 🔵 **times_used** (`unrendered_field`): Django has 'times_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:times_used:unrendered_field`
- 🔵 **title** (`unrendered_field`): Django has 'title' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:title:unrendered_field`
- 🔵 **config** (`unrendered_json`): JSONField 'config' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:config:unrendered_json`

## Currency

Django fields: 26 | Pages: display(1)

- 🟡 **code** (`unrendered_field`): Django has 'code' (CharField) but no layout references it. Required field — likely needs a form input.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss currency:code:unrendered_field`
- 🔵 **config** (`unrendered_field`): Django has 'config' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss currency:config:unrendered_field`
- 🔵 **dt_approved** (`unrendered_field`): Django has 'dt_approved' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss currency:dt_approved:unrendered_field`
- 🔵 **dt_last_used** (`unrendered_field`): Django has 'dt_last_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss currency:dt_last_used:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss currency:is_locked:unrendered_field`
- 🔵 **name** (`unrendered_field`): Django has 'name' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss currency:name:unrendered_field`
- 🔵 **precision** (`unrendered_field`): Django has 'precision' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss currency:precision:unrendered_field`
- 🔵 **purpose** (`unrendered_field`): Django has 'purpose' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss currency:purpose:unrendered_field`
- 🔵 **symbol** (`unrendered_field`): Django has 'symbol' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss currency:symbol:unrendered_field`
- 🔵 **times_used** (`unrendered_field`): Django has 'times_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss currency:times_used:unrendered_field`
- 🔵 **config** (`unrendered_json`): JSONField 'config' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss currency:config:unrendered_json`

## Document

Django fields: 38 | Pages: display(1)
  **Display** (15 fields): `body`, `checksum`, `comment`, `confidential`, `description`, `metadata`, `mime_type`, `model_name`, `name`, `refs`, `retention_period`, `sequence`...

- 🔴 **model_name** (`phantom_field`): Layout references 'model_name' but Django model has no such field. Found in: display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss document:model_name:phantom_field`
- 🟡 **search_vector** (`unrendered_field`): Django has 'search_vector' (SearchVectorField) but no layout references it. Required field — likely needs a form input.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss document:search_vector:unrendered_field`
- 🔵 **config** (`unrendered_field`): Django has 'config' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss document:config:unrendered_field`
- 🔵 **copyright** (`unrendered_field`): Django has 'copyright' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss document:copyright:unrendered_field`
- 🔵 **count_accessed** (`unrendered_field`): Django has 'count_accessed' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss document:count_accessed:unrendered_field`
- 🔵 **dt_approved** (`unrendered_field`): Django has 'dt_approved' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss document:dt_approved:unrendered_field`
- 🔵 **dt_last_used** (`unrendered_field`): Django has 'dt_last_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss document:dt_last_used:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss document:is_locked:unrendered_field`
- 🔵 **path** (`unrendered_field`): Django has 'path' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss document:path:unrendered_field`
- 🔵 **purpose** (`unrendered_field`): Django has 'purpose' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss document:purpose:unrendered_field`
- 🔵 **times_used** (`unrendered_field`): Django has 'times_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss document:times_used:unrendered_field`
- 🔵 **config** (`unrendered_json`): JSONField 'config' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss document:config:unrendered_json`
- 🔵 **copyright** (`unrendered_json`): JSONField 'copyright' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss document:copyright:unrendered_json`
- 🔵 **path** (`unrendered_json`): JSONField 'path' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss document:path:unrendered_json`

## Ledger

Django fields: 40 | Pages: display(1)

- 🔵 **config** (`unrendered_field`): Django has 'config' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:config:unrendered_field`
- 🔵 **discount_potential** (`unrendered_field`): Django has 'discount_potential' (DecimalField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:discount_potential:unrendered_field`
- 🔵 **dt_approved** (`unrendered_field`): Django has 'dt_approved' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:dt_approved:unrendered_field`
- 🔵 **dt_discount_due** (`unrendered_field`): Django has 'dt_discount_due' (DateTimeField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:dt_discount_due:unrendered_field`
- 🔵 **dt_due** (`unrendered_field`): Django has 'dt_due' (DateTimeField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:dt_due:unrendered_field`
- 🔵 **dt_last_used** (`unrendered_field`): Django has 'dt_last_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:dt_last_used:unrendered_field`
- 🔵 **dt_posted** (`unrendered_field`): Django has 'dt_posted' (DateTimeField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:dt_posted:unrendered_field`
- 🔵 **dt_recorded** (`unrendered_field`): Django has 'dt_recorded' (DateTimeField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:dt_recorded:unrendered_field`
- 🔵 **dt_settled** (`unrendered_field`): Django has 'dt_settled' (DateTimeField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:dt_settled:unrendered_field`
- 🔵 **is_cleared** (`unrendered_field`): Django has 'is_cleared' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:is_cleared:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:is_locked:unrendered_field`
- 🔵 **is_settled** (`unrendered_field`): Django has 'is_settled' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:is_settled:unrendered_field`
- 🔵 **is_void** (`unrendered_field`): Django has 'is_void' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:is_void:unrendered_field`
- 🔵 **model_name** (`unrendered_field`): Django has 'model_name' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:model_name:unrendered_field`
- 🔵 **parent_id** (`unrendered_field`): Django has 'parent_id' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:parent_id:unrendered_field`
- 🔵 **purpose** (`unrendered_field`): Django has 'purpose' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:purpose:unrendered_field`
- 🔵 **source** (`unrendered_field`): Django has 'source' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:source:unrendered_field`
- 🔵 **times_used** (`unrendered_field`): Django has 'times_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:times_used:unrendered_field`
- 🔵 **value_available** (`unrendered_field`): Django has 'value_available' (DecimalField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:value_available:unrendered_field`
- 🔵 **value_original** (`unrendered_field`): Django has 'value_original' (DecimalField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:value_original:unrendered_field`
- 🔵 **config** (`unrendered_json`): JSONField 'config' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:config:unrendered_json`

## Manufacturer

Django fields: 54 | Pages: display(1)
  **Display** (9 fields): `attention`, `comments`, `display_name`, `email`, `id`, `is_active`, `phone`, `price_level`, `status`

- 🔵 **address_full** (`unrendered_field`): Django has 'address_full' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:address_full:unrendered_field`
- 🔵 **address_id** (`unrendered_field`): Django has 'address_id' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:address_id:unrendered_field`
- 🔵 **addresses** (`unrendered_field`): Django has 'addresses' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:addresses:unrendered_field`
- 🔵 **config** (`unrendered_field`): Django has 'config' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:config:unrendered_field`
- 🔵 **connections** (`unrendered_field`): Django has 'connections' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:connections:unrendered_field`
- 🔵 **contacts** (`unrendered_field`): Django has 'contacts' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:contacts:unrendered_field`
- 🔵 **docs** (`unrendered_field`): Django has 'docs' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:docs:unrendered_field`
- 🔵 **domain** (`unrendered_field`): Django has 'domain' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:domain:unrendered_field`
- 🔵 **domain_id** (`unrendered_field`): Django has 'domain_id' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:domain_id:unrendered_field`
- 🔵 **domains** (`unrendered_field`): Django has 'domains' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:domains:unrendered_field`
- 🔵 **dt_approved** (`unrendered_field`): Django has 'dt_approved' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:dt_approved:unrendered_field`
- 🔵 **dt_last_used** (`unrendered_field`): Django has 'dt_last_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:dt_last_used:unrendered_field`
- 🔵 **email_id** (`unrendered_field`): Django has 'email_id' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:email_id:unrendered_field`
- 🔵 **emails** (`unrendered_field`): Django has 'emails' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:emails:unrendered_field`
- 🔵 **financial** (`unrendered_field`): Django has 'financial' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:financial:unrendered_field`
- 🔵 **gl_accounts** (`unrendered_field`): Django has 'gl_accounts' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:gl_accounts:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:is_locked:unrendered_field`
- 🔵 **metrics** (`unrendered_field`): Django has 'metrics' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:metrics:unrendered_field`
- 🔵 **org_type** (`unrendered_field`): Django has 'org_type' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:org_type:unrendered_field`
- 🔵 **phone_id** (`unrendered_field`): Django has 'phone_id' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:phone_id:unrendered_field`
- 🔵 **phones** (`unrendered_field`): Django has 'phones' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:phones:unrendered_field`
- 🔵 **purpose** (`unrendered_field`): Django has 'purpose' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:purpose:unrendered_field`
- 🔵 **relations** (`unrendered_field`): Django has 'relations' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:relations:unrendered_field`
- 🔵 **relationship_stats** (`unrendered_field`): Django has 'relationship_stats' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:relationship_stats:unrendered_field`
- 🔵 **stats** (`unrendered_field`): Django has 'stats' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:stats:unrendered_field`
- 🔵 **tax_exempt_code** (`unrendered_field`): Django has 'tax_exempt_code' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:tax_exempt_code:unrendered_field`
- 🔵 **terms** (`unrendered_field`): Django has 'terms' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:terms:unrendered_field`
- 🔵 **times_used** (`unrendered_field`): Django has 'times_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:times_used:unrendered_field`
- 🔵 **type** (`unrendered_field`): Django has 'type' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:type:unrendered_field`
- 🔵 **relations** (`unrendered_json`): JSONField 'relations' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:relations:unrendered_json`
- 🔵 **financial** (`unrendered_json`): JSONField 'financial' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:financial:unrendered_json`
- 🔵 **domains** (`unrendered_json`): JSONField 'domains' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:domains:unrendered_json`
- 🔵 **config** (`unrendered_json`): JSONField 'config' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:config:unrendered_json`
- 🔵 **stats** (`unrendered_json`): JSONField 'stats' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:stats:unrendered_json`
- 🔵 **addresses** (`unrendered_json`): JSONField 'addresses' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:addresses:unrendered_json`
- 🔵 **gl_accounts** (`unrendered_json`): JSONField 'gl_accounts' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:gl_accounts:unrendered_json`
- 🔵 **relationship_stats** (`unrendered_json`): JSONField 'relationship_stats' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:relationship_stats:unrendered_json`
- 🔵 **emails** (`unrendered_json`): JSONField 'emails' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:emails:unrendered_json`
- 🔵 **metrics** (`unrendered_json`): JSONField 'metrics' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:metrics:unrendered_json`
- 🔵 **docs** (`unrendered_json`): JSONField 'docs' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:docs:unrendered_json`
- 🔵 **phones** (`unrendered_json`): JSONField 'phones' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:phones:unrendered_json`
- 🔵 **connections** (`unrendered_json`): JSONField 'connections' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:connections:unrendered_json`
- 🔵 **contacts** (`unrendered_json`): JSONField 'contacts' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:contacts:unrendered_json`

## Rep

Django fields: 54 | Pages: display(1)
  **Display** (9 fields): `attention`, `comments`, `display_name`, `email`, `id`, `is_active`, `phone`, `price_level`, `status`

- 🔵 **address_full** (`unrendered_field`): Django has 'address_full' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:address_full:unrendered_field`
- 🔵 **address_id** (`unrendered_field`): Django has 'address_id' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:address_id:unrendered_field`
- 🔵 **addresses** (`unrendered_field`): Django has 'addresses' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:addresses:unrendered_field`
- 🔵 **config** (`unrendered_field`): Django has 'config' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:config:unrendered_field`
- 🔵 **connections** (`unrendered_field`): Django has 'connections' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:connections:unrendered_field`
- 🔵 **contacts** (`unrendered_field`): Django has 'contacts' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:contacts:unrendered_field`
- 🔵 **docs** (`unrendered_field`): Django has 'docs' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:docs:unrendered_field`
- 🔵 **domain** (`unrendered_field`): Django has 'domain' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:domain:unrendered_field`
- 🔵 **domain_id** (`unrendered_field`): Django has 'domain_id' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:domain_id:unrendered_field`
- 🔵 **domains** (`unrendered_field`): Django has 'domains' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:domains:unrendered_field`
- 🔵 **dt_approved** (`unrendered_field`): Django has 'dt_approved' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:dt_approved:unrendered_field`
- 🔵 **dt_last_used** (`unrendered_field`): Django has 'dt_last_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:dt_last_used:unrendered_field`
- 🔵 **email_id** (`unrendered_field`): Django has 'email_id' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:email_id:unrendered_field`
- 🔵 **emails** (`unrendered_field`): Django has 'emails' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:emails:unrendered_field`
- 🔵 **financial** (`unrendered_field`): Django has 'financial' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:financial:unrendered_field`
- 🔵 **gl_accounts** (`unrendered_field`): Django has 'gl_accounts' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:gl_accounts:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:is_locked:unrendered_field`
- 🔵 **metrics** (`unrendered_field`): Django has 'metrics' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:metrics:unrendered_field`
- 🔵 **org_type** (`unrendered_field`): Django has 'org_type' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:org_type:unrendered_field`
- 🔵 **phone_id** (`unrendered_field`): Django has 'phone_id' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:phone_id:unrendered_field`
- 🔵 **phones** (`unrendered_field`): Django has 'phones' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:phones:unrendered_field`
- 🔵 **purpose** (`unrendered_field`): Django has 'purpose' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:purpose:unrendered_field`
- 🔵 **relations** (`unrendered_field`): Django has 'relations' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:relations:unrendered_field`
- 🔵 **relationship_stats** (`unrendered_field`): Django has 'relationship_stats' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:relationship_stats:unrendered_field`
- 🔵 **stats** (`unrendered_field`): Django has 'stats' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:stats:unrendered_field`
- 🔵 **tax_exempt_code** (`unrendered_field`): Django has 'tax_exempt_code' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:tax_exempt_code:unrendered_field`
- 🔵 **terms** (`unrendered_field`): Django has 'terms' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:terms:unrendered_field`
- 🔵 **times_used** (`unrendered_field`): Django has 'times_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:times_used:unrendered_field`
- 🔵 **type** (`unrendered_field`): Django has 'type' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:type:unrendered_field`
- 🔵 **relations** (`unrendered_json`): JSONField 'relations' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:relations:unrendered_json`
- 🔵 **financial** (`unrendered_json`): JSONField 'financial' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:financial:unrendered_json`
- 🔵 **domains** (`unrendered_json`): JSONField 'domains' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:domains:unrendered_json`
- 🔵 **config** (`unrendered_json`): JSONField 'config' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:config:unrendered_json`
- 🔵 **stats** (`unrendered_json`): JSONField 'stats' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:stats:unrendered_json`
- 🔵 **addresses** (`unrendered_json`): JSONField 'addresses' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:addresses:unrendered_json`
- 🔵 **gl_accounts** (`unrendered_json`): JSONField 'gl_accounts' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:gl_accounts:unrendered_json`
- 🔵 **relationship_stats** (`unrendered_json`): JSONField 'relationship_stats' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:relationship_stats:unrendered_json`
- 🔵 **emails** (`unrendered_json`): JSONField 'emails' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:emails:unrendered_json`
- 🔵 **metrics** (`unrendered_json`): JSONField 'metrics' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:metrics:unrendered_json`
- 🔵 **docs** (`unrendered_json`): JSONField 'docs' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:docs:unrendered_json`
- 🔵 **phones** (`unrendered_json`): JSONField 'phones' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:phones:unrendered_json`
- 🔵 **connections** (`unrendered_json`): JSONField 'connections' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:connections:unrendered_json`
- 🔵 **contacts** (`unrendered_json`): JSONField 'contacts' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:contacts:unrendered_json`

## Report

Django fields: 33 | Pages: display(1)

- 🔵 **category** (`unrendered_field`): Django has 'category' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:category:unrendered_field`
- 🔵 **config** (`unrendered_field`): Django has 'config' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:config:unrendered_field`
- 🔵 **description** (`unrendered_field`): Django has 'description' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:description:unrendered_field`
- 🔵 **dt_approved** (`unrendered_field`): Django has 'dt_approved' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:dt_approved:unrendered_field`
- 🔵 **dt_last_used** (`unrendered_field`): Django has 'dt_last_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:dt_last_used:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:is_locked:unrendered_field`
- 🔵 **model_name** (`unrendered_field`): Django has 'model_name' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:model_name:unrendered_field`
- 🔵 **name** (`unrendered_field`): Django has 'name' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:name:unrendered_field`
- 🔵 **output_type** (`unrendered_field`): Django has 'output_type' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:output_type:unrendered_field`
- 🔵 **purpose** (`unrendered_field`): Django has 'purpose' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:purpose:unrendered_field`
- 🔵 **record_id** (`unrendered_field`): Django has 'record_id' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:record_id:unrendered_field`
- 🔵 **role_required** (`unrendered_field`): Django has 'role_required' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:role_required:unrendered_field`
- 🔵 **script_after** (`unrendered_field`): Django has 'script_after' (TextField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:script_after:unrendered_field`
- 🔵 **script_before** (`unrendered_field`): Django has 'script_before' (TextField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:script_before:unrendered_field`
- 🔵 **script_during** (`unrendered_field`): Django has 'script_during' (TextField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:script_during:unrendered_field`
- 🔵 **sort_order** (`unrendered_field`): Django has 'sort_order' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:sort_order:unrendered_field`
- 🔵 **times_used** (`unrendered_field`): Django has 'times_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:times_used:unrendered_field`
- 🔵 **config** (`unrendered_json`): JSONField 'config' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:config:unrendered_json`

## Serial

Django fields: 31 | Pages: display(1)
  **Display** (5 fields): `description`, `item_id`, `metadata`, `serial_number`, `status`

- 🔴 **serial_number** (`phantom_field`): Layout references 'serial_number' but Django model has no such field. Found in: display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:serial_number:phantom_field`
- 🟡 **serial_ida** (`unrendered_field`): Django has 'serial_ida' (CharField) but no layout references it. Required field — likely needs a form input.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:serial_ida:unrendered_field`
- 🔵 **config** (`unrendered_field`): Django has 'config' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:config:unrendered_field`
- 🔵 **dt_approved** (`unrendered_field`): Django has 'dt_approved' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:dt_approved:unrendered_field`
- 🔵 **dt_last_used** (`unrendered_field`): Django has 'dt_last_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:dt_last_used:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:is_locked:unrendered_field`
- 🔵 **item_ida** (`unrendered_field`): Django has 'item_ida' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:item_ida:unrendered_field`
- 🔵 **model_ida** (`unrendered_field`): Django has 'model_ida' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:model_ida:unrendered_field`
- 🔵 **purpose** (`unrendered_field`): Django has 'purpose' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:purpose:unrendered_field`
- 🔵 **qr_code** (`unrendered_field`): Django has 'qr_code' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:qr_code:unrendered_field`
- 🔵 **site** (`unrendered_field`): Django has 'site' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:site:unrendered_field`
- 🔵 **times_used** (`unrendered_field`): Django has 'times_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:times_used:unrendered_field`
- 🔵 **warranty** (`unrendered_field`): Django has 'warranty' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:warranty:unrendered_field`
- 🔵 **config** (`unrendered_json`): JSONField 'config' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:config:unrendered_json`
- 🔵 **warranty** (`unrendered_json`): JSONField 'warranty' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:warranty:unrendered_json`
- 🔵 **site** (`unrendered_json`): JSONField 'site' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:site:unrendered_json`

## Service

Django fields: 33 | Pages: display(1)
  **Display** (7 fields): `cost`, `date`, `description`, `metadata`, `name`, `refs`, `status`

- 🔴 **cost** (`phantom_field`): Layout references 'cost' but Django model has no such field. Found in: display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:cost:phantom_field`
- 🔴 **date** (`phantom_field`): Layout references 'date' but Django model has no such field. Found in: display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:date:phantom_field`
- 🔴 **name** (`phantom_field`): Layout references 'name' but Django model has no such field. Found in: display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:name:phantom_field`
- 🔵 **billing** (`unrendered_field`): Django has 'billing' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:billing:unrendered_field`
- 🔵 **billing_audit** (`unrendered_field`): Django has 'billing_audit' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:billing_audit:unrendered_field`
- 🔵 **category** (`unrendered_field`): Django has 'category' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:category:unrendered_field`
- 🔵 **config** (`unrendered_field`): Django has 'config' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:config:unrendered_field`
- 🔵 **default_duration_minutes** (`unrendered_field`): Django has 'default_duration_minutes' (PositiveIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:default_duration_minutes:unrendered_field`
- 🔵 **display** (`unrendered_field`): Django has 'display' (TextField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:display:unrendered_field`
- 🔵 **dt_approved** (`unrendered_field`): Django has 'dt_approved' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:dt_approved:unrendered_field`
- 🔵 **dt_last_used** (`unrendered_field`): Django has 'dt_last_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:dt_last_used:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:is_locked:unrendered_field`
- 🔵 **process** (`unrendered_field`): Django has 'process' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:process:unrendered_field`
- 🔵 **purpose** (`unrendered_field`): Django has 'purpose' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:purpose:unrendered_field`
- 🔵 **times_used** (`unrendered_field`): Django has 'times_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:times_used:unrendered_field`
- 🔵 **travel** (`unrendered_field`): Django has 'travel' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:travel:unrendered_field`
- 🔵 **process** (`unrendered_json`): JSONField 'process' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:process:unrendered_json`
- 🔵 **travel** (`unrendered_json`): JSONField 'travel' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:travel:unrendered_json`
- 🔵 **config** (`unrendered_json`): JSONField 'config' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:config:unrendered_json`
- 🔵 **billing_audit** (`unrendered_json`): JSONField 'billing_audit' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:billing_audit:unrendered_json`
- 🔵 **billing** (`unrendered_json`): JSONField 'billing' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:billing:unrendered_json`

## Setting

Django fields: 28 | Pages: display(1)

- 🔵 **config** (`unrendered_field`): Django has 'config' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss setting:config:unrendered_field`
- 🔵 **contact_id** (`unrendered_field`): Django has 'contact_id' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss setting:contact_id:unrendered_field`
- 🔵 **dt_approved** (`unrendered_field`): Django has 'dt_approved' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss setting:dt_approved:unrendered_field`
- 🔵 **dt_last_used** (`unrendered_field`): Django has 'dt_last_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss setting:dt_last_used:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss setting:is_locked:unrendered_field`
- 🔵 **name** (`unrendered_field`): Django has 'name' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss setting:name:unrendered_field`
- 🔵 **org_id** (`unrendered_field`): Django has 'org_id' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss setting:org_id:unrendered_field`
- 🔵 **parent_model** (`unrendered_field`): Django has 'parent_model' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss setting:parent_model:unrendered_field`
- 🔵 **purpose** (`unrendered_field`): Django has 'purpose' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss setting:purpose:unrendered_field`
- 🔵 **role** (`unrendered_field`): Django has 'role' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss setting:role:unrendered_field`
- 🔵 **scope** (`unrendered_field`): Django has 'scope' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss setting:scope:unrendered_field`
- 🔵 **times_used** (`unrendered_field`): Django has 'times_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss setting:times_used:unrendered_field`
- 🔵 **config** (`unrendered_json`): JSONField 'config' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss setting:config:unrendered_json`

## Specification

Django fields: 32 | Pages: display(1)
  **Display** (5 fields): `description`, `metadata`, `name`, `requirements`, `version`

- 🔴 **requirements** (`phantom_field`): Layout references 'requirements' but Django model has no such field. Found in: display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:requirements:phantom_field`
- 🔵 **applies_to** (`unrendered_field`): Django has 'applies_to' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:applies_to:unrendered_field`
- 🔵 **config** (`unrendered_field`): Django has 'config' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:config:unrendered_field`
- 🔵 **description_long** (`unrendered_field`): Django has 'description_long' (TextField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:description_long:unrendered_field`
- 🔵 **details** (`unrendered_field`): Django has 'details' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:details:unrendered_field`
- 🔵 **docs** (`unrendered_field`): Django has 'docs' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:docs:unrendered_field`
- 🔵 **dt_approved** (`unrendered_field`): Django has 'dt_approved' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:dt_approved:unrendered_field`
- 🔵 **dt_last_used** (`unrendered_field`): Django has 'dt_last_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:dt_last_used:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:is_locked:unrendered_field`
- 🔵 **purpose** (`unrendered_field`): Django has 'purpose' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:purpose:unrendered_field`
- 🔵 **stats** (`unrendered_field`): Django has 'stats' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:stats:unrendered_field`
- 🔵 **status** (`unrendered_field`): Django has 'status' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:status:unrendered_field`
- 🔵 **times_used** (`unrendered_field`): Django has 'times_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:times_used:unrendered_field`
- 🔵 **unit** (`unrendered_field`): Django has 'unit' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:unit:unrendered_field`
- 🔵 **config** (`unrendered_json`): JSONField 'config' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:config:unrendered_json`
- 🔵 **stats** (`unrendered_json`): JSONField 'stats' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:stats:unrendered_json`
- 🔵 **details** (`unrendered_json`): JSONField 'details' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:details:unrendered_json`
- 🔵 **docs** (`unrendered_json`): JSONField 'docs' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:docs:unrendered_json`
- 🔵 **applies_to** (`unrendered_json`): JSONField 'applies_to' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:applies_to:unrendered_json`

## Tag

Django fields: 28 | Pages: display(1)
  **Display** (8 fields): `metadata`, `model_name`, `name`, `purpose`, `record_id`, `refs`, `sequence`, `status`

- 🔵 **config** (`unrendered_field`): Django has 'config' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss tag:config:unrendered_field`
- 🔵 **count_accessed** (`unrendered_field`): Django has 'count_accessed' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss tag:count_accessed:unrendered_field`
- 🔵 **dt_approved** (`unrendered_field`): Django has 'dt_approved' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss tag:dt_approved:unrendered_field`
- 🔵 **dt_last_used** (`unrendered_field`): Django has 'dt_last_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss tag:dt_last_used:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss tag:is_locked:unrendered_field`
- 🔵 **times_used** (`unrendered_field`): Django has 'times_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss tag:times_used:unrendered_field`
- 🔵 **config** (`unrendered_json`): JSONField 'config' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss tag:config:unrendered_json`

## Term

Django fields: 33 | Pages: display(1)
  **Display** (11 fields): `approved_by`, `day_cut_off_due`, `day_cut_off_invoice`, `days_discount`, `days_due`, `days_in_period`, `description`, `discount_rate`, `dt_begin`, `name`, `period_count`

- 🔵 **config** (`unrendered_field`): Django has 'config' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss term:config:unrendered_field`
- 🔵 **dt_approved** (`unrendered_field`): Django has 'dt_approved' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss term:dt_approved:unrendered_field`
- 🔵 **dt_last_used** (`unrendered_field`): Django has 'dt_last_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss term:dt_last_used:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss term:is_locked:unrendered_field`
- 🔵 **purpose** (`unrendered_field`): Django has 'purpose' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss term:purpose:unrendered_field`
- 🔵 **times_used** (`unrendered_field`): Django has 'times_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss term:times_used:unrendered_field`
- 🔵 **config** (`unrendered_json`): JSONField 'config' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss term:config:unrendered_json`

## Variant

Django fields: 29 | Pages: display(1)
  **Display** (5 fields): `attributes`, `description`, `item_id`, `metadata`, `name`

- 🔴 **attributes** (`phantom_field`): Layout references 'attributes' but Django model has no such field. Found in: display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss variant:attributes:phantom_field`
- 🔴 **name** (`phantom_field`): Layout references 'name' but Django model has no such field. Found in: display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss variant:name:phantom_field`
- 🟡 **canonical_key** (`unrendered_field`): Django has 'canonical_key' (CharField) but no layout references it. Required field — likely needs a form input.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss variant:canonical_key:unrendered_field`
- 🟡 **set_uuid** (`unrendered_field`): Django has 'set_uuid' (UUIDField) but no layout references it. Required field — likely needs a form input.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss variant:set_uuid:unrendered_field`
- 🟡 **variant_uuid** (`unrendered_field`): Django has 'variant_uuid' (UUIDField) but no layout references it. Required field — likely needs a form input.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss variant:variant_uuid:unrendered_field`
- 🔵 **attrs** (`unrendered_field`): Django has 'attrs' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss variant:attrs:unrendered_field`
- 🔵 **config** (`unrendered_field`): Django has 'config' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss variant:config:unrendered_field`
- 🔵 **dt_approved** (`unrendered_field`): Django has 'dt_approved' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss variant:dt_approved:unrendered_field`
- 🔵 **dt_last_used** (`unrendered_field`): Django has 'dt_last_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss variant:dt_last_used:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss variant:is_locked:unrendered_field`
- 🔵 **item_ida** (`unrendered_field`): Django has 'item_ida' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss variant:item_ida:unrendered_field`
- 🔵 **purpose** (`unrendered_field`): Django has 'purpose' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss variant:purpose:unrendered_field`
- 🔵 **times_used** (`unrendered_field`): Django has 'times_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss variant:times_used:unrendered_field`
- 🔵 **config** (`unrendered_json`): JSONField 'config' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss variant:config:unrendered_json`
- 🔵 **attrs** (`unrendered_json`): JSONField 'attrs' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss variant:attrs:unrendered_json`

## Warehouse

Django fields: 27 | Pages: display(1)
  **Display** (5 fields): `capacity`, `location`, `manager`, `metadata`, `name`

- 🔴 **capacity** (`phantom_field`): Layout references 'capacity' but Django model has no such field. Found in: display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:capacity:phantom_field`
- 🔴 **manager** (`phantom_field`): Layout references 'manager' but Django model has no such field. Found in: display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:manager:phantom_field`
- 🟡 **code** (`unrendered_field`): Django has 'code' (CharField) but no layout references it. Required field — likely needs a form input.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:code:unrendered_field`
- 🔵 **config** (`unrendered_field`): Django has 'config' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:config:unrendered_field`
- 🔵 **count** (`unrendered_field`): Django has 'count' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:count:unrendered_field`
- 🔵 **dt_approved** (`unrendered_field`): Django has 'dt_approved' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:dt_approved:unrendered_field`
- 🔵 **dt_last_used** (`unrendered_field`): Django has 'dt_last_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:dt_last_used:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:is_locked:unrendered_field`
- 🔵 **priority** (`unrendered_field`): Django has 'priority' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:priority:unrendered_field`
- 🔵 **purpose** (`unrendered_field`): Django has 'purpose' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:purpose:unrendered_field`
- 🔵 **site_code** (`unrendered_field`): Django has 'site_code' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:site_code:unrendered_field`
- 🔵 **times_used** (`unrendered_field`): Django has 'times_used' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:times_used:unrendered_field`
- 🔵 **config** (`unrendered_json`): JSONField 'config' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:config:unrendered_json`
- 🔵 **count** (`unrendered_json`): JSONField 'count' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:count:unrendered_json`

---

## Page File Inventory

| Model | Detail | List | Display |
|-------|--------|------|---------|
| audit | — | — | 1 |
| bundle | 1 | — | — |
| catalog | — | — | 1 |
| contact | 1 | — | — |
| currency | — | — | 1 |
| document | — | — | 1 |
| ledger | — | — | 1 |
| manufacturer | — | — | 1 |
| rep | — | — | 1 |
| report | — | — | 1 |
| serial | — | — | 1 |
| service | — | — | 1 |
| setting | — | — | 1 |
| specification | — | — | 1 |
| tag | — | — | 1 |
| term | — | — | 1 |
| variant | — | — | 1 |
| warehouse | — | — | 1 |

---

## Workflow

1. **Review** this report — focus on 🔴 High issues first
2. **Fix** real mismatches in the React/Django code
3. **Dismiss** intentional mismatches: `manage.py ai_intelligence --task layout --dismiss model:field:type --reason 'explanation'`
4. **Re-scan**: `manage.py ai_intelligence --task layout --report`
5. **Review corrections**: resolved issues are tracked automatically — the LLM learns from your fixes
