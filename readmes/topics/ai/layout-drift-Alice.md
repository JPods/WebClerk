# Layout ↔ Schema Drift Report

> Generated: 2026-03-06 15:58  
> Models scanned: 36  
> Total issues (excl. info): 547

## Summary

| Severity | Count |
|----------|-------|
| 🔴 High (phantom fields) | 84 |
| 🟡 Medium (required unrendered) | 8 |
| 🔵 Low (optional unrendered) | 455 |
| ℹ️  Info (detail-only) | 96 |

## Action

Django fields: 51 | Pages: detail(1), list(1)
  **Detail** (24 fields): `action`, `action_ar`, `action_bn`, `action_by`, `action_en`, `description`, `description_ar`, `description_bn`, `description_en`, `difficulty`, `dt_action`, `dt_completed`...
  **List** (8 fields): `assigned_to`, `dt_deadline`, `id`, `kanban_column`, `percent_complete`, `priority`, `project_name`, `status`

- 🔴 **dt_action** (`phantom_field`): Layout references 'dt_action' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:dt_action:phantom_field`
- 🔴 **dt_end** (`phantom_field`): Layout references 'dt_end' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:dt_end:phantom_field`
- 🔴 **hours** (`phantom_field`): Layout references 'hours' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:hours:phantom_field`
- 🔴 **percent** (`phantom_field`): Layout references 'percent' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:percent:phantom_field`
- 🔴 **quality** (`phantom_field`): Layout references 'quality' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:quality:phantom_field`
- 🔵 **burndown** (`unrendered_field`): Django has 'burndown' (SmallIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:burndown:unrendered_field`
- 🔵 **completed_by** (`unrendered_field`): Django has 'completed_by' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:completed_by:unrendered_field`
- 🔵 **contact_id** (`unrendered_field`): Django has 'contact_id' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:contact_id:unrendered_field`
- 🔵 **created_by** (`unrendered_field`): Django has 'created_by' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:created_by:unrendered_field`
- 🔵 **deadline_by** (`unrendered_field`): Django has 'deadline_by' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:deadline_by:unrendered_field`
- 🔵 **dt_end_original** (`unrendered_field`): Django has 'dt_end_original' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:dt_end_original:unrendered_field`
- 🔵 **dt_expected** (`unrendered_field`): Django has 'dt_expected' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:dt_expected:unrendered_field`
- 🔵 **dt_start_original** (`unrendered_field`): Django has 'dt_start_original' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:dt_start_original:unrendered_field`
- 🔵 **duration** (`unrendered_field`): Django has 'duration' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:duration:unrendered_field`
- 🔵 **end_by** (`unrendered_field`): Django has 'end_by' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:end_by:unrendered_field`
- 🔵 **expected_by** (`unrendered_field`): Django has 'expected_by' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:expected_by:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:is_locked:unrendered_field`
- 🔵 **languages** (`unrendered_field`): Django has 'languages' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:languages:unrendered_field`
- 🔵 **linkage** (`unrendered_field`): Django has 'linkage' (PositiveIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:linkage:unrendered_field`
- 🔵 **project_id** (`unrendered_field`): Django has 'project_id' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:project_id:unrendered_field`
- 🔵 **project_ida** (`unrendered_field`): Django has 'project_ida' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:project_ida:unrendered_field`
- 🔵 **project_metadata** (`unrendered_field`): Django has 'project_metadata' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:project_metadata:unrendered_field`
- 🔵 **sequence** (`unrendered_field`): Django has 'sequence' (PositiveIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:sequence:unrendered_field`
- 🔵 **start_by** (`unrendered_field`): Django has 'start_by' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:start_by:unrendered_field`
- 🔵 **updated_by** (`unrendered_field`): Django has 'updated_by' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:updated_by:unrendered_field`
- 🔵 **completed_by** (`unrendered_json`): JSONField 'completed_by' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:completed_by:unrendered_json`
- 🔵 **languages** (`unrendered_json`): JSONField 'languages' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:languages:unrendered_json`
- 🔵 **updated_by** (`unrendered_json`): JSONField 'updated_by' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:updated_by:unrendered_json`
- 🔵 **created_by** (`unrendered_json`): JSONField 'created_by' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:created_by:unrendered_json`
- 🔵 **end_by** (`unrendered_json`): JSONField 'end_by' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:end_by:unrendered_json`
- 🔵 **deadline_by** (`unrendered_json`): JSONField 'deadline_by' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:deadline_by:unrendered_json`
- 🔵 **start_by** (`unrendered_json`): JSONField 'start_by' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:start_by:unrendered_json`
- 🔵 **project_metadata** (`unrendered_json`): JSONField 'project_metadata' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:project_metadata:unrendered_json`
- 🔵 **expected_by** (`unrendered_json`): JSONField 'expected_by' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:expected_by:unrendered_json`
- ℹ️ **action** (`detail_only`): 'action' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:action:detail_only`
- ℹ️ **description** (`detail_only`): 'description' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:description:detail_only`
- ℹ️ **difficulty** (`detail_only`): 'difficulty' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:difficulty:detail_only`
- ℹ️ **dt_completed** (`detail_only`): 'dt_completed' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:dt_completed:detail_only`
- ℹ️ **dt_start** (`detail_only`): 'dt_start' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:dt_start:detail_only`
- ℹ️ **dt_updated** (`detail_only`): 'dt_updated' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss action:dt_updated:detail_only`

## Address

Django fields: 29 | Pages: detail(1), list(2)
  **Detail** (11 fields): `address1`, `address2`, `address_type`, `city`, `country`, `full`, `instructions`, `latitude`, `longitude`, `state`, `zip`
  **List** (6 fields): `address1`, `address_type`, `city`, `country`, `id`, `refs`

- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss address:is_locked:unrendered_field`
- ℹ️ **address2** (`detail_only`): 'address2' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss address:address2:detail_only`
- ℹ️ **full** (`detail_only`): 'full' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss address:full:detail_only`
- ℹ️ **instructions** (`detail_only`): 'instructions' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss address:instructions:detail_only`
- ℹ️ **latitude** (`detail_only`): 'latitude' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss address:latitude:detail_only`
- ℹ️ **longitude** (`detail_only`): 'longitude' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss address:longitude:detail_only`
- ℹ️ **state** (`detail_only`): 'state' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss address:state:detail_only`
- ℹ️ **zip** (`detail_only`): 'zip' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss address:zip:detail_only`

## Audit

Django fields: 25 | Pages: detail(1), list(1), display(1)
  **Detail** (4 fields): `action`, `date`, `description`, `user`
  **List** (5 fields): `action`, `date`, `description`, `id`, `user`

- 🔴 **action** (`phantom_field`): Layout references 'action' but Django model has no such field. Found in: detail, list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:action:phantom_field`
- 🔴 **date** (`phantom_field`): Layout references 'date' but Django model has no such field. Found in: detail, list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:date:phantom_field`
- 🔴 **description** (`phantom_field`): Layout references 'description' but Django model has no such field. Found in: detail, list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:description:phantom_field`
- 🔴 **user** (`phantom_field`): Layout references 'user' but Django model has no such field. Found in: detail, list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:user:phantom_field`
- 🔵 **changes** (`unrendered_field`): Django has 'changes' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:changes:unrendered_field`
- 🔵 **conflicts** (`unrendered_field`): Django has 'conflicts' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:conflicts:unrendered_field`
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
- 🔵 **conflicts** (`unrendered_json`): JSONField 'conflicts' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:conflicts:unrendered_json`
- 🔵 **recommendations** (`unrendered_json`): JSONField 'recommendations' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:recommendations:unrendered_json`
- 🔵 **changes** (`unrendered_json`): JSONField 'changes' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss audit:changes:unrendered_json`

## Bundle

Django fields: 30 | Pages: detail(1), list(1)
  **Detail** (17 fields): `alert`, `config`, `conflicts`, `connection_id`, `data`, `description`, `direction`, `duration`, `encryption`, `maps`, `name`, `payload`...
  **List** (4 fields): `description`, `id`, `name`, `version`

- 🔴 **data** (`phantom_field`): Layout references 'data' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:data:phantom_field`
- 🔴 **description** (`phantom_field`): Layout references 'description' but Django model has no such field. Found in: detail, list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:description:phantom_field`
- 🔴 **name** (`phantom_field`): Layout references 'name' but Django model has no such field. Found in: detail, list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:name:phantom_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:is_locked:unrendered_field`
- ℹ️ **alert** (`detail_only`): 'alert' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:alert:detail_only`
- ℹ️ **config** (`detail_only`): 'config' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:config:detail_only`
- ℹ️ **conflicts** (`detail_only`): 'conflicts' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:conflicts:detail_only`
- ℹ️ **direction** (`detail_only`): 'direction' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:direction:detail_only`
- ℹ️ **duration** (`detail_only`): 'duration' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:duration:detail_only`
- ℹ️ **encryption** (`detail_only`): 'encryption' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:encryption:detail_only`
- ℹ️ **maps** (`detail_only`): 'maps' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:maps:detail_only`
- ℹ️ **payload** (`detail_only`): 'payload' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:payload:detail_only`
- ℹ️ **response** (`detail_only`): 'response' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:response:detail_only`
- ℹ️ **rules** (`detail_only`): 'rules' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:rules:detail_only`
- ℹ️ **size** (`detail_only`): 'size' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:size:detail_only`
- ℹ️ **status** (`detail_only`): 'status' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss bundle:status:detail_only`

## Catalog

Django fields: 32 | Pages: detail(1), list(1), display(1)
  **Detail** (4 fields): `category`, `description`, `name`, `price`
  **List** (4 fields): `category`, `description`, `id`, `name`
  **Display** (5 fields): `category`, `description`, `metadata`, `name`, `price`

- 🔴 **category** (`phantom_field`): Layout references 'category' but Django model has no such field. Found in: detail, list, display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:category:phantom_field`
- 🔴 **description** (`phantom_field`): Layout references 'description' but Django model has no such field. Found in: detail, list, display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:description:phantom_field`
- 🔴 **price** (`phantom_field`): Layout references 'price' but Django model has no such field. Found in: detail, display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:price:phantom_field`
- 🟡 **code** (`unrendered_field`): Django has 'code' (CharField) but no layout references it. Required field — likely needs a form input.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:code:unrendered_field`
- 🟡 **dt_effective_start** (`unrendered_field`): Django has 'dt_effective_start' (BigIntegerField) but no layout references it. Required field — likely needs a form input.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:dt_effective_start:unrendered_field`
- 🔵 **currency** (`unrendered_field`): Django has 'currency' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:currency:unrendered_field`
- 🔵 **dt_effective_end** (`unrendered_field`): Django has 'dt_effective_end' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:dt_effective_end:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:is_locked:unrendered_field`
- 🔵 **metrics** (`unrendered_field`): Django has 'metrics' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:metrics:unrendered_field`
- 🔵 **metrics** (`unrendered_json`): JSONField 'metrics' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss catalog:metrics:unrendered_json`

## Contact

Django fields: 68 | Pages: detail(7), list(2)
  **Detail** (38 fields): `actions`, `address_full`, `attention`, `cnf_password`, `company`, `contact_status`, `contact_type`, `customer_id`, `department`, `domain`, `dt_joined`, `email`...
  **List** (8 fields): `company`, `email`, `id`, `is_active`, `is_staff`, `name_first`, `name_last`, `role`

- 🔴 **cnf_password** (`phantom_field`): Layout references 'cnf_password' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:cnf_password:phantom_field`
- 🔴 **contact_status** (`phantom_field`): Layout references 'contact_status' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:contact_status:phantom_field`
- 🔴 **contact_type** (`phantom_field`): Layout references 'contact_type' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:contact_type:phantom_field`
- 🔴 **first_name** (`phantom_field`): Layout references 'first_name' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:first_name:phantom_field`
- 🔴 **job_title** (`phantom_field`): Layout references 'job_title' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:job_title:phantom_field`
- 🔴 **last_name** (`phantom_field`): Layout references 'last_name' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:last_name:phantom_field`
- 🔴 **middle_name** (`phantom_field`): Layout references 'middle_name' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:middle_name:phantom_field`
- 🔴 **nickname** (`phantom_field`): Layout references 'nickname' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:nickname:phantom_field`
- 🔴 **notes** (`phantom_field`): Layout references 'notes' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:notes:phantom_field`
- 🔴 **prefix** (`phantom_field`): Layout references 'prefix' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:prefix:phantom_field`
- 🔴 **suffix** (`phantom_field`): Layout references 'suffix' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:suffix:phantom_field`
- 🔵 **address_id** (`unrendered_field`): Django has 'address_id' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:address_id:unrendered_field`
- 🔵 **comment** (`unrendered_field`): Django has 'comment' (TextField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:comment:unrendered_field`
- 🔵 **domain_id** (`unrendered_field`): Django has 'domain_id' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:domain_id:unrendered_field`
- 🔵 **email_id** (`unrendered_field`): Django has 'email_id' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:email_id:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:is_locked:unrendered_field`
- 🔵 **phone_id** (`unrendered_field`): Django has 'phone_id' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:phone_id:unrendered_field`
- 🔵 **profile_id** (`unrendered_field`): Django has 'profile_id' (OneToOneField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:profile_id:unrendered_field`
- ℹ️ **address_full** (`detail_only`): 'address_full' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:address_full:detail_only`
- ℹ️ **attention** (`detail_only`): 'attention' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:attention:detail_only`
- ℹ️ **department** (`detail_only`): 'department' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:department:detail_only`
- ℹ️ **domain** (`detail_only`): 'domain' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:domain:detail_only`
- ℹ️ **dt_joined** (`detail_only`): 'dt_joined' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:dt_joined:detail_only`
- ℹ️ **name_middle** (`detail_only`): 'name_middle' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:name_middle:detail_only`
- ℹ️ **name_prefix** (`detail_only`): 'name_prefix' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:name_prefix:detail_only`
- ℹ️ **name_suffix** (`detail_only`): 'name_suffix' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:name_suffix:detail_only`
- ℹ️ **other_id** (`detail_only`): 'other_id' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:other_id:detail_only`
- ℹ️ **phone** (`detail_only`): 'phone' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:phone:detail_only`
- ℹ️ **title** (`detail_only`): 'title' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss contact:title:detail_only`

## Currency

Django fields: 21 | Pages: detail(1), list(1), display(1)
  **Detail** (4 fields): `code`, `name`, `rate`, `symbol`
  **List** (5 fields): `code`, `id`, `name`, `rate`, `symbol`

- 🔴 **rate** (`phantom_field`): Layout references 'rate' but Django model has no such field. Found in: detail, list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss currency:rate:phantom_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss currency:is_locked:unrendered_field`
- 🔵 **precision** (`unrendered_field`): Django has 'precision' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss currency:precision:unrendered_field`

## Customer

Django fields: 76 | Pages: detail(1), list(2)
  **Detail** (23 fields): `address_full`, `address_id`, `attention`, `connections`, `contact_id`, `data`, `display_name`, `domain`, `domain_id`, `email`, `email_id`, `financial`...
  **List** (6 fields): `display_name`, `id`, `is_active`, `org_type`, `status`, `version`

- 🔵 **addresses** (`unrendered_field`): Django has 'addresses' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:addresses:unrendered_field`
- 🔵 **contacts** (`unrendered_field`): Django has 'contacts' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:contacts:unrendered_field`
- 🔵 **docs** (`unrendered_field`): Django has 'docs' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:docs:unrendered_field`
- 🔵 **domains** (`unrendered_field`): Django has 'domains' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:domains:unrendered_field`
- 🔵 **emails** (`unrendered_field`): Django has 'emails' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:emails:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:is_locked:unrendered_field`
- 🔵 **phones** (`unrendered_field`): Django has 'phones' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:phones:unrendered_field`
- 🔵 **relationship_stats** (`unrendered_field`): Django has 'relationship_stats' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:relationship_stats:unrendered_field`
- 🔵 **stats** (`unrendered_field`): Django has 'stats' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:stats:unrendered_field`
- 🔵 **domains** (`unrendered_json`): JSONField 'domains' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:domains:unrendered_json`
- 🔵 **docs** (`unrendered_json`): JSONField 'docs' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:docs:unrendered_json`
- 🔵 **relationship_stats** (`unrendered_json`): JSONField 'relationship_stats' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:relationship_stats:unrendered_json`
- 🔵 **phones** (`unrendered_json`): JSONField 'phones' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:phones:unrendered_json`
- 🔵 **addresses** (`unrendered_json`): JSONField 'addresses' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:addresses:unrendered_json`
- 🔵 **contacts** (`unrendered_json`): JSONField 'contacts' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:contacts:unrendered_json`
- 🔵 **emails** (`unrendered_json`): JSONField 'emails' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:emails:unrendered_json`
- 🔵 **stats** (`unrendered_json`): JSONField 'stats' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:stats:unrendered_json`
- ℹ️ **address_full** (`detail_only`): 'address_full' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:address_full:detail_only`
- ℹ️ **address_id** (`detail_only`): 'address_id' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:address_id:detail_only`
- ℹ️ **attention** (`detail_only`): 'attention' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:attention:detail_only`
- ℹ️ **connections** (`detail_only`): 'connections' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:connections:detail_only`
- ℹ️ **data** (`detail_only`): 'data' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:data:detail_only`
- ℹ️ **domain** (`detail_only`): 'domain' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:domain:detail_only`
- ℹ️ **domain_id** (`detail_only`): 'domain_id' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:domain_id:detail_only`
- ℹ️ **email** (`detail_only`): 'email' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:email:detail_only`
- ℹ️ **email_id** (`detail_only`): 'email_id' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:email_id:detail_only`
- ℹ️ **financial** (`detail_only`): 'financial' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:financial:detail_only`
- ℹ️ **gl_accounts** (`detail_only`): 'gl_accounts' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:gl_accounts:detail_only`
- ℹ️ **metrics** (`detail_only`): 'metrics' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:metrics:detail_only`
- ℹ️ **phone** (`detail_only`): 'phone' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:phone:detail_only`
- ℹ️ **phone_id** (`detail_only`): 'phone_id' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:phone_id:detail_only`
- ℹ️ **price_level** (`detail_only`): 'price_level' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:price_level:detail_only`
- ℹ️ **relations** (`detail_only`): 'relations' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:relations:detail_only`
- ℹ️ **terms** (`detail_only`): 'terms' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss customer:terms:detail_only`

## Document

Django fields: 35 | Pages: detail(1), list(1), display(1)
  **Detail** (17 fields): `body`, `checksum`, `comment`, `confidential`, `copyright`, `count_accessed`, `data`, `description`, `mime_type`, `model_name`, `name`, `path`...
  **List** (1 fields): `id`
  **Display** (15 fields): `body`, `checksum`, `comment`, `confidential`, `description`, `metadata`, `mime_type`, `model_name`, `name`, `refs`, `retention_period`, `sequence`...

- 🟡 **search_vector** (`unrendered_field`): Django has 'search_vector' (SearchVectorField) but no layout references it. Required field — likely needs a form input.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss document:search_vector:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss document:is_locked:unrendered_field`
- ℹ️ **copyright** (`detail_only`): 'copyright' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss document:copyright:detail_only`
- ℹ️ **count_accessed** (`detail_only`): 'count_accessed' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss document:count_accessed:detail_only`
- ℹ️ **data** (`detail_only`): 'data' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss document:data:detail_only`
- ℹ️ **path** (`detail_only`): 'path' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss document:path:detail_only`

## Domain

Django fields: 24 | Pages: detail(1), list(2)
  **Detail** (6 fields): `comment`, `count_accessed`, `path`, `security_level`, `sequence`, `status`
  **List** (3 fields): `id`, `path`, `refs`

- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss domain:is_locked:unrendered_field`
- 🔵 **type** (`unrendered_field`): Django has 'type' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss domain:type:unrendered_field`
- ℹ️ **comment** (`detail_only`): 'comment' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss domain:comment:detail_only`
- ℹ️ **count_accessed** (`detail_only`): 'count_accessed' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss domain:count_accessed:detail_only`
- ℹ️ **sequence** (`detail_only`): 'sequence' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss domain:sequence:detail_only`
- ℹ️ **status** (`detail_only`): 'status' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss domain:status:detail_only`

## Email

Django fields: 25 | Pages: detail(1), list(2)
  **Detail** (7 fields): `attention`, `email`, `is_primary`, `is_verified`, `name`, `opt_out`, `status_display`
  **List** (7 fields): `attention`, `email`, `id`, `is_primary`, `is_verified`, `name`, `refs`

- 🔴 **status_display** (`phantom_field`): Layout references 'status_display' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss email:status_display:phantom_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss email:is_locked:unrendered_field`
- 🔵 **type** (`unrendered_field`): Django has 'type' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss email:type:unrendered_field`
- ℹ️ **opt_out** (`detail_only`): 'opt_out' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss email:opt_out:detail_only`

## Employee

Django fields: 76 | Pages: detail(1), list(1)
  **List** (6 fields): `display_name`, `email`, `id`, `is_active`, `phone`, `status`

- 🔵 **address_full** (`unrendered_field`): Django has 'address_full' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:address_full:unrendered_field`
- 🔵 **address_id** (`unrendered_field`): Django has 'address_id' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:address_id:unrendered_field`
- 🔵 **addresses** (`unrendered_field`): Django has 'addresses' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:addresses:unrendered_field`
- 🔵 **attention** (`unrendered_field`): Django has 'attention' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:attention:unrendered_field`
- 🔵 **connections** (`unrendered_field`): Django has 'connections' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:connections:unrendered_field`
- 🔵 **contacts** (`unrendered_field`): Django has 'contacts' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:contacts:unrendered_field`
- 🔵 **data** (`unrendered_field`): Django has 'data' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:data:unrendered_field`
- 🔵 **docs** (`unrendered_field`): Django has 'docs' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:docs:unrendered_field`
- 🔵 **domain** (`unrendered_field`): Django has 'domain' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:domain:unrendered_field`
- 🔵 **domain_id** (`unrendered_field`): Django has 'domain_id' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:domain_id:unrendered_field`
- 🔵 **domains** (`unrendered_field`): Django has 'domains' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:domains:unrendered_field`
- 🔵 **email_id** (`unrendered_field`): Django has 'email_id' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:email_id:unrendered_field`
- 🔵 **emails** (`unrendered_field`): Django has 'emails' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:emails:unrendered_field`
- 🔵 **financial** (`unrendered_field`): Django has 'financial' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:financial:unrendered_field`
- 🔵 **gl_accounts** (`unrendered_field`): Django has 'gl_accounts' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:gl_accounts:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:is_locked:unrendered_field`
- 🔵 **metrics** (`unrendered_field`): Django has 'metrics' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:metrics:unrendered_field`
- 🔵 **org_type** (`unrendered_field`): Django has 'org_type' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:org_type:unrendered_field`
- 🔵 **phone_id** (`unrendered_field`): Django has 'phone_id' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:phone_id:unrendered_field`
- 🔵 **phones** (`unrendered_field`): Django has 'phones' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:phones:unrendered_field`
- 🔵 **price_level** (`unrendered_field`): Django has 'price_level' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:price_level:unrendered_field`
- 🔵 **relations** (`unrendered_field`): Django has 'relations' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:relations:unrendered_field`
- 🔵 **relationship_stats** (`unrendered_field`): Django has 'relationship_stats' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:relationship_stats:unrendered_field`
- 🔵 **stats** (`unrendered_field`): Django has 'stats' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:stats:unrendered_field`
- 🔵 **terms** (`unrendered_field`): Django has 'terms' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:terms:unrendered_field`
- 🔵 **domains** (`unrendered_json`): JSONField 'domains' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:domains:unrendered_json`
- 🔵 **connections** (`unrendered_json`): JSONField 'connections' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:connections:unrendered_json`
- 🔵 **financial** (`unrendered_json`): JSONField 'financial' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:financial:unrendered_json`
- 🔵 **data** (`unrendered_json`): JSONField 'data' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:data:unrendered_json`
- 🔵 **relations** (`unrendered_json`): JSONField 'relations' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:relations:unrendered_json`
- 🔵 **docs** (`unrendered_json`): JSONField 'docs' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:docs:unrendered_json`
- 🔵 **metrics** (`unrendered_json`): JSONField 'metrics' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:metrics:unrendered_json`
- 🔵 **relationship_stats** (`unrendered_json`): JSONField 'relationship_stats' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:relationship_stats:unrendered_json`
- 🔵 **gl_accounts** (`unrendered_json`): JSONField 'gl_accounts' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:gl_accounts:unrendered_json`
- 🔵 **phones** (`unrendered_json`): JSONField 'phones' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:phones:unrendered_json`
- 🔵 **addresses** (`unrendered_json`): JSONField 'addresses' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:addresses:unrendered_json`
- 🔵 **contacts** (`unrendered_json`): JSONField 'contacts' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:contacts:unrendered_json`
- 🔵 **emails** (`unrendered_json`): JSONField 'emails' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:emails:unrendered_json`
- 🔵 **stats** (`unrendered_json`): JSONField 'stats' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss employee:stats:unrendered_json`

## Invoice

Django fields: 48 | Pages: detail(1), list(1)
  **List** (9 fields): `customer_name`, `dt_created`, `id`, `invoice_no`, `line_count`, `margin_percentage`, `status`, `total`, `vendor_name`

- 🔴 **customer_name** (`phantom_field`): Layout references 'customer_name' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:customer_name:phantom_field`
- 🔴 **invoice_no** (`phantom_field`): Layout references 'invoice_no' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:invoice_no:phantom_field`
- 🔴 **line_count** (`phantom_field`): Layout references 'line_count' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:line_count:phantom_field`
- 🔴 **margin_percentage** (`phantom_field`): Layout references 'margin_percentage' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:margin_percentage:phantom_field`
- 🔴 **vendor_name** (`phantom_field`): Layout references 'vendor_name' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:vendor_name:phantom_field`
- 🔵 **address_full** (`unrendered_field`): Django has 'address_full' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:address_full:unrendered_field`
- 🔵 **attention** (`unrendered_field`): Django has 'attention' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:attention:unrendered_field`
- 🔵 **balance** (`unrendered_field`): Django has 'balance' (DecimalField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:balance:unrendered_field`
- 🔵 **conditions_description** (`unrendered_field`): Django has 'conditions_description' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:conditions_description:unrendered_field`
- 🔵 **conditions_id** (`unrendered_field`): Django has 'conditions_id' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:conditions_id:unrendered_field`
- 🔵 **cost** (`unrendered_field`): Django has 'cost' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:cost:unrendered_field`
- 🔵 **email** (`unrendered_field`): Django has 'email' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:email:unrendered_field`
- 🔵 **finance** (`unrendered_field`): Django has 'finance' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:finance:unrendered_field`
- 🔵 **flow** (`unrendered_field`): Django has 'flow' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:flow:unrendered_field`
- 🔵 **is_commission** (`unrendered_field`): Django has 'is_commission' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:is_commission:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:is_locked:unrendered_field`
- 🔵 **line_increment** (`unrendered_field`): Django has 'line_increment' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:line_increment:unrendered_field`
- 🔵 **parent_id** (`unrendered_field`): Django has 'parent_id' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:parent_id:unrendered_field`
- 🔵 **parent_model** (`unrendered_field`): Django has 'parent_model' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:parent_model:unrendered_field`
- 🔵 **phone** (`unrendered_field`): Django has 'phone' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:phone:unrendered_field`
- 🔵 **price_level** (`unrendered_field`): Django has 'price_level' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:price_level:unrendered_field`
- 🔵 **priority** (`unrendered_field`): Django has 'priority' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:priority:unrendered_field`
- 🔵 **sell** (`unrendered_field`): Django has 'sell' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:sell:unrendered_field`
- 🔵 **source** (`unrendered_field`): Django has 'source' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:source:unrendered_field`
- 🔵 **terms** (`unrendered_field`): Django has 'terms' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:terms:unrendered_field`
- 🔵 **totals** (`unrendered_field`): Django has 'totals' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:totals:unrendered_field`
- 🔵 **cost** (`unrendered_json`): JSONField 'cost' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:cost:unrendered_json`
- 🔵 **source** (`unrendered_json`): JSONField 'source' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:source:unrendered_json`
- 🔵 **totals** (`unrendered_json`): JSONField 'totals' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:totals:unrendered_json`
- 🔵 **flow** (`unrendered_json`): JSONField 'flow' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:flow:unrendered_json`
- 🔵 **sell** (`unrendered_json`): JSONField 'sell' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:sell:unrendered_json`
- 🔵 **finance** (`unrendered_json`): JSONField 'finance' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss invoice:finance:unrendered_json`

## Item

Django fields: 56 | Pages: detail(1), list(1)
  **Detail** (45 fields): `base_uom`, `catalog`, `catalog_attributes_json`, `catalog_categories`, `catalog_flags_json`, `catalog_web_short`, `catalog_web_slug`, `catalog_web_title`, `category`, `cost`, `cost_avg`, `cost_components_json`...
  **List** (16 fields): `category`, `category_name`, `description`, `external_id`, `group`, `id`, `item_code`, `item_id`, `item_name`, `item_number`, `name`, `price`...

- 🔴 **category** (`phantom_field`): Layout references 'category' but Django model has no such field. Found in: detail, list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:category:phantom_field`
- 🔴 **category_name** (`phantom_field`): Layout references 'category_name' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:category_name:phantom_field`
- 🔴 **external_id** (`phantom_field`): Layout references 'external_id' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:external_id:phantom_field`
- 🔴 **group** (`phantom_field`): Layout references 'group' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:group:phantom_field`
- 🔴 **item_code** (`phantom_field`): Layout references 'item_code' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:item_code:phantom_field`
- 🔴 **item_id** (`phantom_field`): Layout references 'item_id' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:item_id:phantom_field`
- 🔴 **item_name** (`phantom_field`): Layout references 'item_name' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:item_name:phantom_field`
- 🔴 **item_number** (`phantom_field`): Layout references 'item_number' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:item_number:phantom_field`
- 🔴 **segment** (`phantom_field`): Layout references 'segment' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:segment:phantom_field`
- 🔴 **title** (`phantom_field`): Layout references 'title' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:title:phantom_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:is_locked:unrendered_field`
- 🔵 **stats** (`unrendered_field`): Django has 'stats' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:stats:unrendered_field`
- 🔵 **variant_row_id** (`unrendered_field`): Django has 'variant_row_id' (OneToOneField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:variant_row_id:unrendered_field`
- 🔵 **stats** (`unrendered_json`): JSONField 'stats' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:stats:unrendered_json`
- ℹ️ **base_uom** (`detail_only`): 'base_uom' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:base_uom:detail_only`
- ℹ️ **catalog** (`detail_only`): 'catalog' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:catalog:detail_only`
- ℹ️ **cost** (`detail_only`): 'cost' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:cost:detail_only`
- ℹ️ **flags** (`detail_only`): 'flags' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:flags:detail_only`
- ℹ️ **gls** (`detail_only`): 'gls' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:gls:detail_only`
- ℹ️ **kind** (`detail_only`): 'kind' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:kind:detail_only`
- ℹ️ **qr_code** (`detail_only`): 'qr_code' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:qr_code:detail_only`
- ℹ️ **quantity** (`detail_only`): 'quantity' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:quantity:detail_only`
- ℹ️ **specification_id** (`detail_only`): 'specification_id' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:specification_id:detail_only`
- ℹ️ **tax_code** (`detail_only`): 'tax_code' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:tax_code:detail_only`
- ℹ️ **uom** (`detail_only`): 'uom' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss item:uom:detail_only`

## Ledger

Django fields: 34 | Pages: list(1), display(1)
  **List** (3 fields): `balance`, `id`, `name`

- 🔴 **balance** (`phantom_field`): Layout references 'balance' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:balance:phantom_field`
- 🔴 **name** (`phantom_field`): Layout references 'name' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:name:phantom_field`
- 🔵 **discount_potential** (`unrendered_field`): Django has 'discount_potential' (FloatField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:discount_potential:unrendered_field`
- 🔵 **dt_discount_due** (`unrendered_field`): Django has 'dt_discount_due' (DateTimeField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:dt_discount_due:unrendered_field`
- 🔵 **dt_due** (`unrendered_field`): Django has 'dt_due' (DateTimeField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:dt_due:unrendered_field`
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
- 🔵 **source** (`unrendered_field`): Django has 'source' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:source:unrendered_field`
- 🔵 **value_available** (`unrendered_field`): Django has 'value_available' (FloatField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:value_available:unrendered_field`
- 🔵 **value_original** (`unrendered_field`): Django has 'value_original' (FloatField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss ledger:value_original:unrendered_field`

## Manufacturer

Django fields: 76 | Pages: list(2), display(1)
  **List** (6 fields): `display_name`, `id`, `is_active`, `org_type`, `status`, `version`
  **Display** (4 fields): `display_name`, `id`, `is_active`, `status`

- 🔵 **address_full** (`unrendered_field`): Django has 'address_full' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:address_full:unrendered_field`
- 🔵 **address_id** (`unrendered_field`): Django has 'address_id' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:address_id:unrendered_field`
- 🔵 **addresses** (`unrendered_field`): Django has 'addresses' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:addresses:unrendered_field`
- 🔵 **attention** (`unrendered_field`): Django has 'attention' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:attention:unrendered_field`
- 🔵 **connections** (`unrendered_field`): Django has 'connections' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:connections:unrendered_field`
- 🔵 **contacts** (`unrendered_field`): Django has 'contacts' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:contacts:unrendered_field`
- 🔵 **data** (`unrendered_field`): Django has 'data' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:data:unrendered_field`
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
- 🔵 **email** (`unrendered_field`): Django has 'email' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:email:unrendered_field`
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
- 🔵 **phone** (`unrendered_field`): Django has 'phone' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:phone:unrendered_field`
- 🔵 **phone_id** (`unrendered_field`): Django has 'phone_id' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:phone_id:unrendered_field`
- 🔵 **phones** (`unrendered_field`): Django has 'phones' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:phones:unrendered_field`
- 🔵 **price_level** (`unrendered_field`): Django has 'price_level' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:price_level:unrendered_field`
- 🔵 **relations** (`unrendered_field`): Django has 'relations' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:relations:unrendered_field`
- 🔵 **relationship_stats** (`unrendered_field`): Django has 'relationship_stats' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:relationship_stats:unrendered_field`
- 🔵 **stats** (`unrendered_field`): Django has 'stats' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:stats:unrendered_field`
- 🔵 **terms** (`unrendered_field`): Django has 'terms' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:terms:unrendered_field`
- 🔵 **domains** (`unrendered_json`): JSONField 'domains' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:domains:unrendered_json`
- 🔵 **connections** (`unrendered_json`): JSONField 'connections' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:connections:unrendered_json`
- 🔵 **financial** (`unrendered_json`): JSONField 'financial' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:financial:unrendered_json`
- 🔵 **data** (`unrendered_json`): JSONField 'data' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:data:unrendered_json`
- 🔵 **relations** (`unrendered_json`): JSONField 'relations' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:relations:unrendered_json`
- 🔵 **docs** (`unrendered_json`): JSONField 'docs' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:docs:unrendered_json`
- 🔵 **metrics** (`unrendered_json`): JSONField 'metrics' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:metrics:unrendered_json`
- 🔵 **relationship_stats** (`unrendered_json`): JSONField 'relationship_stats' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:relationship_stats:unrendered_json`
- 🔵 **gl_accounts** (`unrendered_json`): JSONField 'gl_accounts' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:gl_accounts:unrendered_json`
- 🔵 **phones** (`unrendered_json`): JSONField 'phones' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:phones:unrendered_json`
- 🔵 **addresses** (`unrendered_json`): JSONField 'addresses' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:addresses:unrendered_json`
- 🔵 **contacts** (`unrendered_json`): JSONField 'contacts' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:contacts:unrendered_json`
- 🔵 **emails** (`unrendered_json`): JSONField 'emails' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:emails:unrendered_json`
- 🔵 **stats** (`unrendered_json`): JSONField 'stats' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss manufacturer:stats:unrendered_json`

## Order

Django fields: 45 | Pages: detail(1), list(1)
  **List** (8 fields): `dt_created`, `id`, `ida`, `line_count`, `margin_percentage`, `refs`, `status`, `total`

- 🔴 **line_count** (`phantom_field`): Layout references 'line_count' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:line_count:phantom_field`
- 🔴 **margin_percentage** (`phantom_field`): Layout references 'margin_percentage' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:margin_percentage:phantom_field`
- 🔵 **address_full** (`unrendered_field`): Django has 'address_full' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:address_full:unrendered_field`
- 🔵 **attention** (`unrendered_field`): Django has 'attention' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:attention:unrendered_field`
- 🔵 **balance** (`unrendered_field`): Django has 'balance' (DecimalField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:balance:unrendered_field`
- 🔵 **conditions_description** (`unrendered_field`): Django has 'conditions_description' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:conditions_description:unrendered_field`
- 🔵 **conditions_id** (`unrendered_field`): Django has 'conditions_id' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:conditions_id:unrendered_field`
- 🔵 **cost** (`unrendered_field`): Django has 'cost' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:cost:unrendered_field`
- 🔵 **email** (`unrendered_field`): Django has 'email' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:email:unrendered_field`
- 🔵 **finance** (`unrendered_field`): Django has 'finance' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:finance:unrendered_field`
- 🔵 **flow** (`unrendered_field`): Django has 'flow' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:flow:unrendered_field`
- 🔵 **is_commission** (`unrendered_field`): Django has 'is_commission' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:is_commission:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:is_locked:unrendered_field`
- 🔵 **line_increment** (`unrendered_field`): Django has 'line_increment' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:line_increment:unrendered_field`
- 🔵 **parent_id** (`unrendered_field`): Django has 'parent_id' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:parent_id:unrendered_field`
- 🔵 **parent_model** (`unrendered_field`): Django has 'parent_model' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:parent_model:unrendered_field`
- 🔵 **phone** (`unrendered_field`): Django has 'phone' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:phone:unrendered_field`
- 🔵 **price_level** (`unrendered_field`): Django has 'price_level' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:price_level:unrendered_field`
- 🔵 **priority** (`unrendered_field`): Django has 'priority' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:priority:unrendered_field`
- 🔵 **sell** (`unrendered_field`): Django has 'sell' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:sell:unrendered_field`
- 🔵 **source** (`unrendered_field`): Django has 'source' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:source:unrendered_field`
- 🔵 **terms** (`unrendered_field`): Django has 'terms' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:terms:unrendered_field`
- 🔵 **totals** (`unrendered_field`): Django has 'totals' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:totals:unrendered_field`
- 🔵 **cost** (`unrendered_json`): JSONField 'cost' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:cost:unrendered_json`
- 🔵 **source** (`unrendered_json`): JSONField 'source' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:source:unrendered_json`
- 🔵 **totals** (`unrendered_json`): JSONField 'totals' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:totals:unrendered_json`
- 🔵 **flow** (`unrendered_json`): JSONField 'flow' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:flow:unrendered_json`
- 🔵 **sell** (`unrendered_json`): JSONField 'sell' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:sell:unrendered_json`
- 🔵 **finance** (`unrendered_json`): JSONField 'finance' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss order:finance:unrendered_json`

## Phone

Django fields: 24 | Pages: detail(1), list(2)
  **Detail** (6 fields): `attention`, `country_code`, `format`, `name`, `number`, `opt_out`
  **List** (6 fields): `country_code`, `id`, `name`, `number`, `opt_out`, `refs`

- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss phone:is_locked:unrendered_field`
- ℹ️ **attention** (`detail_only`): 'attention' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss phone:attention:detail_only`
- ℹ️ **format** (`detail_only`): 'format' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss phone:format:detail_only`

## Project

Django fields: 34 | Pages: detail(1), list(1)
  **List** (6 fields): `description`, `end_date`, `id`, `name`, `start_date`, `status`

- 🔴 **description** (`phantom_field`): Layout references 'description' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:description:phantom_field`
- 🔴 **end_date** (`phantom_field`): Layout references 'end_date' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:end_date:phantom_field`
- 🔴 **start_date** (`phantom_field`): Layout references 'start_date' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:start_date:phantom_field`
- 🔵 **attention** (`unrendered_field`): Django has 'attention' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:attention:unrendered_field`
- 🔵 **burndown** (`unrendered_field`): Django has 'burndown' (PositiveSmallIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:burndown:unrendered_field`
- 🔵 **category** (`unrendered_field`): Django has 'category' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:category:unrendered_field`
- 🔵 **data** (`unrendered_field`): Django has 'data' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:data:unrendered_field`
- 🔵 **dt_kanban** (`unrendered_field`): Django has 'dt_kanban' (DateTimeField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:dt_kanban:unrendered_field`
- 🔵 **id_contact** (`unrendered_field`): Django has 'id_contact' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:id_contact:unrendered_field`
- 🔵 **intent** (`unrendered_field`): Django has 'intent' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:intent:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:is_locked:unrendered_field`
- 🔵 **logistics** (`unrendered_field`): Django has 'logistics' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:logistics:unrendered_field`
- 🔵 **objective** (`unrendered_field`): Django has 'objective' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:objective:unrendered_field`
- 🔵 **priority** (`unrendered_field`): Django has 'priority' (PositiveSmallIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:priority:unrendered_field`
- 🔵 **profit** (`unrendered_field`): Django has 'profit' (DecimalField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:profit:unrendered_field`
- 🔵 **profit_velocity** (`unrendered_field`): Django has 'profit_velocity' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:profit_velocity:unrendered_field`
- 🔵 **situation** (`unrendered_field`): Django has 'situation' (TextField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:situation:unrendered_field`
- 🔵 **slug** (`unrendered_field`): Django has 'slug' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:slug:unrendered_field`
- 🔵 **tasks** (`unrendered_field`): Django has 'tasks' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:tasks:unrendered_field`
- 🔵 **objective** (`unrendered_json`): JSONField 'objective' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:objective:unrendered_json`
- 🔵 **tasks** (`unrendered_json`): JSONField 'tasks' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:tasks:unrendered_json`
- 🔵 **logistics** (`unrendered_json`): JSONField 'logistics' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:logistics:unrendered_json`
- 🔵 **data** (`unrendered_json`): JSONField 'data' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss project:data:unrendered_json`

## Proposal

Django fields: 45 | Pages: detail(2), list(2)
  **Detail** (12 fields): `cost`, `cost_unit`, `item_description`, `line_number`, `physical`, `price`, `price_level`, `price_unit`, `quantity`, `quantity_placed`, `status`, `tax`
  **List** (11 fields): `customer_name`, `dt_created`, `id`, `line_count`, `margin_percentage`, `price`, `proposal_no`, `quantity`, `status`, `total_amount`, `vendor_name`

- 🔴 **customer_name** (`phantom_field`): Layout references 'customer_name' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:customer_name:phantom_field`
- 🔴 **item_description** (`phantom_field`): Layout references 'item_description' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:item_description:phantom_field`
- 🔴 **line_count** (`phantom_field`): Layout references 'line_count' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:line_count:phantom_field`
- 🔴 **line_number** (`phantom_field`): Layout references 'line_number' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:line_number:phantom_field`
- 🔴 **margin_percentage** (`phantom_field`): Layout references 'margin_percentage' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:margin_percentage:phantom_field`
- 🔴 **physical** (`phantom_field`): Layout references 'physical' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:physical:phantom_field`
- 🔴 **price** (`phantom_field`): Layout references 'price' but Django model has no such field. Found in: detail, list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:price:phantom_field`
- 🔴 **price_unit** (`phantom_field`): Layout references 'price_unit' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:price_unit:phantom_field`
- 🔴 **proposal_no** (`phantom_field`): Layout references 'proposal_no' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:proposal_no:phantom_field`
- 🔴 **quantity** (`phantom_field`): Layout references 'quantity' but Django model has no such field. Found in: detail, list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:quantity:phantom_field`
- 🔴 **quantity_placed** (`phantom_field`): Layout references 'quantity_placed' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:quantity_placed:phantom_field`
- 🔴 **tax** (`phantom_field`): Layout references 'tax' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:tax:phantom_field`
- 🔴 **total_amount** (`phantom_field`): Layout references 'total_amount' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:total_amount:phantom_field`
- 🔴 **vendor_name** (`phantom_field`): Layout references 'vendor_name' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:vendor_name:phantom_field`
- 🔵 **address_full** (`unrendered_field`): Django has 'address_full' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:address_full:unrendered_field`
- 🔵 **attention** (`unrendered_field`): Django has 'attention' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:attention:unrendered_field`
- 🔵 **balance** (`unrendered_field`): Django has 'balance' (DecimalField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:balance:unrendered_field`
- 🔵 **conditions_description** (`unrendered_field`): Django has 'conditions_description' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:conditions_description:unrendered_field`
- 🔵 **conditions_id** (`unrendered_field`): Django has 'conditions_id' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:conditions_id:unrendered_field`
- 🔵 **email** (`unrendered_field`): Django has 'email' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:email:unrendered_field`
- 🔵 **finance** (`unrendered_field`): Django has 'finance' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:finance:unrendered_field`
- 🔵 **flow** (`unrendered_field`): Django has 'flow' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:flow:unrendered_field`
- 🔵 **is_commission** (`unrendered_field`): Django has 'is_commission' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:is_commission:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:is_locked:unrendered_field`
- 🔵 **line_increment** (`unrendered_field`): Django has 'line_increment' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:line_increment:unrendered_field`
- 🔵 **parent_id** (`unrendered_field`): Django has 'parent_id' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:parent_id:unrendered_field`
- 🔵 **parent_model** (`unrendered_field`): Django has 'parent_model' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:parent_model:unrendered_field`
- 🔵 **phone** (`unrendered_field`): Django has 'phone' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:phone:unrendered_field`
- 🔵 **priority** (`unrendered_field`): Django has 'priority' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:priority:unrendered_field`
- 🔵 **sell** (`unrendered_field`): Django has 'sell' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:sell:unrendered_field`
- 🔵 **source** (`unrendered_field`): Django has 'source' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:source:unrendered_field`
- 🔵 **terms** (`unrendered_field`): Django has 'terms' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:terms:unrendered_field`
- 🔵 **total** (`unrendered_field`): Django has 'total' (DecimalField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:total:unrendered_field`
- 🔵 **totals** (`unrendered_field`): Django has 'totals' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:totals:unrendered_field`
- 🔵 **source** (`unrendered_json`): JSONField 'source' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:source:unrendered_json`
- 🔵 **totals** (`unrendered_json`): JSONField 'totals' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:totals:unrendered_json`
- 🔵 **flow** (`unrendered_json`): JSONField 'flow' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:flow:unrendered_json`
- 🔵 **sell** (`unrendered_json`): JSONField 'sell' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:sell:unrendered_json`
- 🔵 **finance** (`unrendered_json`): JSONField 'finance' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:finance:unrendered_json`
- ℹ️ **cost** (`detail_only`): 'cost' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:cost:detail_only`
- ℹ️ **price_level** (`detail_only`): 'price_level' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss proposal:price_level:detail_only`

## Purchase

Django fields: 46 | Pages: detail(1), list(1)
  **List** (3 fields): `dt_created`, `id`, `purchase_no`

- 🔴 **purchase_no** (`phantom_field`): Layout references 'purchase_no' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:purchase_no:phantom_field`
- 🔵 **address_full** (`unrendered_field`): Django has 'address_full' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:address_full:unrendered_field`
- 🔵 **attention** (`unrendered_field`): Django has 'attention' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:attention:unrendered_field`
- 🔵 **balance** (`unrendered_field`): Django has 'balance' (DecimalField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:balance:unrendered_field`
- 🔵 **conditions_description** (`unrendered_field`): Django has 'conditions_description' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:conditions_description:unrendered_field`
- 🔵 **conditions_id** (`unrendered_field`): Django has 'conditions_id' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:conditions_id:unrendered_field`
- 🔵 **cost** (`unrendered_field`): Django has 'cost' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:cost:unrendered_field`
- 🔵 **email** (`unrendered_field`): Django has 'email' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:email:unrendered_field`
- 🔵 **finance** (`unrendered_field`): Django has 'finance' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:finance:unrendered_field`
- 🔵 **flow** (`unrendered_field`): Django has 'flow' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:flow:unrendered_field`
- 🔵 **is_commission** (`unrendered_field`): Django has 'is_commission' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:is_commission:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:is_locked:unrendered_field`
- 🔵 **line_increment** (`unrendered_field`): Django has 'line_increment' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:line_increment:unrendered_field`
- 🔵 **parent_id** (`unrendered_field`): Django has 'parent_id' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:parent_id:unrendered_field`
- 🔵 **parent_model** (`unrendered_field`): Django has 'parent_model' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:parent_model:unrendered_field`
- 🔵 **phone** (`unrendered_field`): Django has 'phone' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:phone:unrendered_field`
- 🔵 **price_level** (`unrendered_field`): Django has 'price_level' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:price_level:unrendered_field`
- 🔵 **priority** (`unrendered_field`): Django has 'priority' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:priority:unrendered_field`
- 🔵 **sell** (`unrendered_field`): Django has 'sell' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:sell:unrendered_field`
- 🔵 **source** (`unrendered_field`): Django has 'source' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:source:unrendered_field`
- 🔵 **status** (`unrendered_field`): Django has 'status' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:status:unrendered_field`
- 🔵 **terms** (`unrendered_field`): Django has 'terms' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:terms:unrendered_field`
- 🔵 **total** (`unrendered_field`): Django has 'total' (DecimalField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:total:unrendered_field`
- 🔵 **totals** (`unrendered_field`): Django has 'totals' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:totals:unrendered_field`
- 🔵 **cost** (`unrendered_json`): JSONField 'cost' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:cost:unrendered_json`
- 🔵 **source** (`unrendered_json`): JSONField 'source' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:source:unrendered_json`
- 🔵 **totals** (`unrendered_json`): JSONField 'totals' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:totals:unrendered_json`
- 🔵 **flow** (`unrendered_json`): JSONField 'flow' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:flow:unrendered_json`
- 🔵 **sell** (`unrendered_json`): JSONField 'sell' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:sell:unrendered_json`
- 🔵 **finance** (`unrendered_json`): JSONField 'finance' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss purchase:finance:unrendered_json`

## Receipt

Django fields: 23 | Pages: detail(1), list(1)
  **List** (6 fields): `dt_received`, `id`, `ida`, `notes`, `source_type`, `status`

- 🔴 **status** (`phantom_field`): Layout references 'status' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss receipt:status:phantom_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss receipt:is_locked:unrendered_field`

## Rep

Django fields: 76 | Pages: list(2), display(1)
  **List** (6 fields): `display_name`, `id`, `is_active`, `org_type`, `status`, `version`
  **Display** (4 fields): `display_name`, `id`, `is_active`, `status`

- 🔵 **address_full** (`unrendered_field`): Django has 'address_full' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:address_full:unrendered_field`
- 🔵 **address_id** (`unrendered_field`): Django has 'address_id' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:address_id:unrendered_field`
- 🔵 **addresses** (`unrendered_field`): Django has 'addresses' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:addresses:unrendered_field`
- 🔵 **attention** (`unrendered_field`): Django has 'attention' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:attention:unrendered_field`
- 🔵 **connections** (`unrendered_field`): Django has 'connections' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:connections:unrendered_field`
- 🔵 **contacts** (`unrendered_field`): Django has 'contacts' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:contacts:unrendered_field`
- 🔵 **data** (`unrendered_field`): Django has 'data' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:data:unrendered_field`
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
- 🔵 **email** (`unrendered_field`): Django has 'email' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:email:unrendered_field`
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
- 🔵 **phone** (`unrendered_field`): Django has 'phone' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:phone:unrendered_field`
- 🔵 **phone_id** (`unrendered_field`): Django has 'phone_id' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:phone_id:unrendered_field`
- 🔵 **phones** (`unrendered_field`): Django has 'phones' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:phones:unrendered_field`
- 🔵 **price_level** (`unrendered_field`): Django has 'price_level' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:price_level:unrendered_field`
- 🔵 **relations** (`unrendered_field`): Django has 'relations' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:relations:unrendered_field`
- 🔵 **relationship_stats** (`unrendered_field`): Django has 'relationship_stats' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:relationship_stats:unrendered_field`
- 🔵 **stats** (`unrendered_field`): Django has 'stats' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:stats:unrendered_field`
- 🔵 **terms** (`unrendered_field`): Django has 'terms' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:terms:unrendered_field`
- 🔵 **domains** (`unrendered_json`): JSONField 'domains' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:domains:unrendered_json`
- 🔵 **connections** (`unrendered_json`): JSONField 'connections' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:connections:unrendered_json`
- 🔵 **financial** (`unrendered_json`): JSONField 'financial' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:financial:unrendered_json`
- 🔵 **data** (`unrendered_json`): JSONField 'data' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:data:unrendered_json`
- 🔵 **relations** (`unrendered_json`): JSONField 'relations' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:relations:unrendered_json`
- 🔵 **docs** (`unrendered_json`): JSONField 'docs' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:docs:unrendered_json`
- 🔵 **metrics** (`unrendered_json`): JSONField 'metrics' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:metrics:unrendered_json`
- 🔵 **relationship_stats** (`unrendered_json`): JSONField 'relationship_stats' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:relationship_stats:unrendered_json`
- 🔵 **gl_accounts** (`unrendered_json`): JSONField 'gl_accounts' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:gl_accounts:unrendered_json`
- 🔵 **phones** (`unrendered_json`): JSONField 'phones' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:phones:unrendered_json`
- 🔵 **addresses** (`unrendered_json`): JSONField 'addresses' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:addresses:unrendered_json`
- 🔵 **contacts** (`unrendered_json`): JSONField 'contacts' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:contacts:unrendered_json`
- 🔵 **emails** (`unrendered_json`): JSONField 'emails' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:emails:unrendered_json`
- 🔵 **stats** (`unrendered_json`): JSONField 'stats' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss rep:stats:unrendered_json`

## Report

Django fields: 22 | Pages: detail(1), list(1), display(1)
  **Detail** (4 fields): `description`, `is_active`, `parameters`, `title`
  **List** (4 fields): `description`, `id`, `is_active`, `title`

- 🔴 **description** (`phantom_field`): Layout references 'description' but Django model has no such field. Found in: detail, list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:description:phantom_field`
- 🔴 **parameters** (`phantom_field`): Layout references 'parameters' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:parameters:phantom_field`
- 🔴 **title** (`phantom_field`): Layout references 'title' but Django model has no such field. Found in: detail, list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:title:phantom_field`
- 🔵 **data** (`unrendered_field`): Django has 'data' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:data:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:is_locked:unrendered_field`
- 🔵 **model_name** (`unrendered_field`): Django has 'model_name' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:model_name:unrendered_field`
- 🔵 **name** (`unrendered_field`): Django has 'name' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:name:unrendered_field`
- 🔵 **purpose** (`unrendered_field`): Django has 'purpose' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:purpose:unrendered_field`
- 🔵 **record_id** (`unrendered_field`): Django has 'record_id' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:record_id:unrendered_field`
- 🔵 **data** (`unrendered_json`): JSONField 'data' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss report:data:unrendered_json`

## Requisition

Django fields: 21 | Pages: detail(1), list(1)
  **List** (3 fields): `dt_created`, `id`, `requisition_no`

- 🔴 **requisition_no** (`phantom_field`): Layout references 'requisition_no' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss requisition:requisition_no:phantom_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss requisition:is_locked:unrendered_field`
- 🔵 **name** (`unrendered_field`): Django has 'name' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss requisition:name:unrendered_field`
- 🔵 **purpose** (`unrendered_field`): Django has 'purpose' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss requisition:purpose:unrendered_field`
- 🔵 **status** (`unrendered_field`): Django has 'status' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss requisition:status:unrendered_field`

## Serial

Django fields: 28 | Pages: detail(1), list(1), display(1)
  **Detail** (4 fields): `description`, `item_id`, `serial_number`, `status`
  **List** (5 fields): `description`, `id`, `item_id`, `serial_number`, `status`
  **Display** (5 fields): `description`, `item_id`, `metadata`, `serial_number`, `status`

- 🔴 **serial_number** (`phantom_field`): Layout references 'serial_number' but Django model has no such field. Found in: detail, list, display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:serial_number:phantom_field`
- 🟡 **serial_ida** (`unrendered_field`): Django has 'serial_ida' (CharField) but no layout references it. Required field — likely needs a form input.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:serial_ida:unrendered_field`
- 🔵 **data** (`unrendered_field`): Django has 'data' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:data:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:is_locked:unrendered_field`
- 🔵 **item_ida** (`unrendered_field`): Django has 'item_ida' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:item_ida:unrendered_field`
- 🔵 **model_ida** (`unrendered_field`): Django has 'model_ida' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:model_ida:unrendered_field`
- 🔵 **qr_code** (`unrendered_field`): Django has 'qr_code' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:qr_code:unrendered_field`
- 🔵 **site** (`unrendered_field`): Django has 'site' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:site:unrendered_field`
- 🔵 **warranty** (`unrendered_field`): Django has 'warranty' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:warranty:unrendered_field`
- 🔵 **warranty** (`unrendered_json`): JSONField 'warranty' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:warranty:unrendered_json`
- 🔵 **site** (`unrendered_json`): JSONField 'site' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:site:unrendered_json`
- 🔵 **data** (`unrendered_json`): JSONField 'data' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss serial:data:unrendered_json`

## Service

Django fields: 29 | Pages: detail(1), list(1), display(1)
  **Detail** (4 fields): `cost`, `date`, `description`, `name`
  **List** (5 fields): `cost`, `date`, `description`, `id`, `name`
  **Display** (7 fields): `cost`, `date`, `description`, `metadata`, `name`, `refs`, `status`

- 🔴 **cost** (`phantom_field`): Layout references 'cost' but Django model has no such field. Found in: detail, list, display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:cost:phantom_field`
- 🔴 **date** (`phantom_field`): Layout references 'date' but Django model has no such field. Found in: detail, list, display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:date:phantom_field`
- 🔴 **name** (`phantom_field`): Layout references 'name' but Django model has no such field. Found in: detail, list, display
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
- 🔵 **default_duration_minutes** (`unrendered_field`): Django has 'default_duration_minutes' (PositiveIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:default_duration_minutes:unrendered_field`
- 🔵 **display** (`unrendered_field`): Django has 'display' (TextField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:display:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:is_locked:unrendered_field`
- 🔵 **process** (`unrendered_field`): Django has 'process' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:process:unrendered_field`
- 🔵 **purpose** (`unrendered_field`): Django has 'purpose' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:purpose:unrendered_field`
- 🔵 **travel** (`unrendered_field`): Django has 'travel' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:travel:unrendered_field`
- 🔵 **billing** (`unrendered_json`): JSONField 'billing' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:billing:unrendered_json`
- 🔵 **travel** (`unrendered_json`): JSONField 'travel' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:travel:unrendered_json`
- 🔵 **billing_audit** (`unrendered_json`): JSONField 'billing_audit' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:billing_audit:unrendered_json`
- 🔵 **process** (`unrendered_json`): JSONField 'process' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss service:process:unrendered_json`

## Setting

Django fields: 23 | Pages: detail(1), list(1), display(1)
  **Detail** (7 fields): `data`, `is_active`, `model_name`, `name`, `parent_model`, `purpose`, `role`
  **List** (6 fields): `id`, `is_active`, `name`, `parent_model`, `purpose`, `role`

- 🔴 **model_name** (`phantom_field`): Layout references 'model_name' but Django model has no such field. Found in: detail
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss setting:model_name:phantom_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss setting:is_locked:unrendered_field`
- ℹ️ **data** (`detail_only`): 'data' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss setting:data:detail_only`

## Specification

Django fields: 27 | Pages: detail(1), list(1), display(1)
  **Detail** (4 fields): `description`, `name`, `requirements`, `version`
  **List** (4 fields): `description`, `id`, `name`, `version`
  **Display** (5 fields): `description`, `metadata`, `name`, `requirements`, `version`

- 🔴 **requirements** (`phantom_field`): Layout references 'requirements' but Django model has no such field. Found in: detail, display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:requirements:phantom_field`
- 🔵 **applies_to** (`unrendered_field`): Django has 'applies_to' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:applies_to:unrendered_field`
- 🔵 **description_long** (`unrendered_field`): Django has 'description_long' (TextField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:description_long:unrendered_field`
- 🔵 **details** (`unrendered_field`): Django has 'details' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:details:unrendered_field`
- 🔵 **docs** (`unrendered_field`): Django has 'docs' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:docs:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:is_locked:unrendered_field`
- 🔵 **stats** (`unrendered_field`): Django has 'stats' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:stats:unrendered_field`
- 🔵 **status** (`unrendered_field`): Django has 'status' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:status:unrendered_field`
- 🔵 **unit** (`unrendered_field`): Django has 'unit' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:unit:unrendered_field`
- 🔵 **applies_to** (`unrendered_json`): JSONField 'applies_to' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:applies_to:unrendered_json`
- 🔵 **stats** (`unrendered_json`): JSONField 'stats' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:stats:unrendered_json`
- 🔵 **details** (`unrendered_json`): JSONField 'details' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:details:unrendered_json`
- 🔵 **docs** (`unrendered_json`): JSONField 'docs' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss specification:docs:unrendered_json`

## Tag

Django fields: 25 | Pages: list(1), display(1)
  **List** (4 fields): `color`, `description`, `id`, `name`
  **Display** (8 fields): `metadata`, `model_name`, `name`, `purpose`, `record_id`, `refs`, `sequence`, `status`

- 🔴 **color** (`phantom_field`): Layout references 'color' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss tag:color:phantom_field`
- 🔴 **description** (`phantom_field`): Layout references 'description' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss tag:description:phantom_field`
- 🔵 **count_accessed** (`unrendered_field`): Django has 'count_accessed' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss tag:count_accessed:unrendered_field`
- 🔵 **data** (`unrendered_field`): Django has 'data' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss tag:data:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss tag:is_locked:unrendered_field`
- 🔵 **data** (`unrendered_json`): JSONField 'data' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss tag:data:unrendered_json`

## Template

Django fields: 21 | Pages: detail(1), list(1), display(1)
  **Detail** (4 fields): `data`, `is_active`, `name`, `purpose`
  **List** (5 fields): `dt_processed`, `id`, `is_active`, `name`, `purpose`

- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss template:is_locked:unrendered_field`
- ℹ️ **data** (`detail_only`): 'data' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss template:data:detail_only`

## Term

Django fields: 29 | Pages: list(1), display(1)
  **List** (4 fields): `description`, `duration`, `id`, `name`
  **Display** (11 fields): `approved_by`, `day_cut_off_due`, `day_cut_off_invoice`, `days_discount`, `days_due`, `days_in_period`, `description`, `discount_rate`, `dt_begin`, `name`, `period_count`

- 🔴 **duration** (`phantom_field`): Layout references 'duration' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss term:duration:phantom_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss term:is_locked:unrendered_field`

## Variant

Django fields: 24 | Pages: detail(1), list(1), display(1)
  **Detail** (4 fields): `attributes`, `description`, `item_id`, `name`
  **List** (4 fields): `description`, `id`, `item_id`, `name`
  **Display** (5 fields): `attributes`, `description`, `item_id`, `metadata`, `name`

- 🔴 **attributes** (`phantom_field`): Layout references 'attributes' but Django model has no such field. Found in: detail, display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss variant:attributes:phantom_field`
- 🔴 **name** (`phantom_field`): Layout references 'name' but Django model has no such field. Found in: detail, list, display
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
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss variant:is_locked:unrendered_field`
- 🔵 **item_ida** (`unrendered_field`): Django has 'item_ida' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss variant:item_ida:unrendered_field`
- 🔵 **attrs** (`unrendered_json`): JSONField 'attrs' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss variant:attrs:unrendered_json`

## Vendor

Django fields: 76 | Pages: detail(1), list(2)
  **Detail** (23 fields): `address_full`, `address_id`, `attention`, `connections`, `contact_id`, `data`, `display_name`, `domain`, `domain_id`, `email`, `email_id`, `financial`...
  **List** (6 fields): `display_name`, `id`, `is_active`, `org_type`, `status`, `version`

- 🔵 **addresses** (`unrendered_field`): Django has 'addresses' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:addresses:unrendered_field`
- 🔵 **contacts** (`unrendered_field`): Django has 'contacts' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:contacts:unrendered_field`
- 🔵 **docs** (`unrendered_field`): Django has 'docs' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:docs:unrendered_field`
- 🔵 **domains** (`unrendered_field`): Django has 'domains' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:domains:unrendered_field`
- 🔵 **emails** (`unrendered_field`): Django has 'emails' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:emails:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:is_locked:unrendered_field`
- 🔵 **phones** (`unrendered_field`): Django has 'phones' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:phones:unrendered_field`
- 🔵 **relationship_stats** (`unrendered_field`): Django has 'relationship_stats' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:relationship_stats:unrendered_field`
- 🔵 **stats** (`unrendered_field`): Django has 'stats' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:stats:unrendered_field`
- 🔵 **domains** (`unrendered_json`): JSONField 'domains' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:domains:unrendered_json`
- 🔵 **docs** (`unrendered_json`): JSONField 'docs' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:docs:unrendered_json`
- 🔵 **relationship_stats** (`unrendered_json`): JSONField 'relationship_stats' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:relationship_stats:unrendered_json`
- 🔵 **phones** (`unrendered_json`): JSONField 'phones' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:phones:unrendered_json`
- 🔵 **addresses** (`unrendered_json`): JSONField 'addresses' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:addresses:unrendered_json`
- 🔵 **contacts** (`unrendered_json`): JSONField 'contacts' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:contacts:unrendered_json`
- 🔵 **emails** (`unrendered_json`): JSONField 'emails' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:emails:unrendered_json`
- 🔵 **stats** (`unrendered_json`): JSONField 'stats' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:stats:unrendered_json`
- ℹ️ **address_full** (`detail_only`): 'address_full' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:address_full:detail_only`
- ℹ️ **address_id** (`detail_only`): 'address_id' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:address_id:detail_only`
- ℹ️ **attention** (`detail_only`): 'attention' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:attention:detail_only`
- ℹ️ **connections** (`detail_only`): 'connections' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:connections:detail_only`
- ℹ️ **data** (`detail_only`): 'data' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:data:detail_only`
- ℹ️ **domain** (`detail_only`): 'domain' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:domain:detail_only`
- ℹ️ **domain_id** (`detail_only`): 'domain_id' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:domain_id:detail_only`
- ℹ️ **email** (`detail_only`): 'email' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:email:detail_only`
- ℹ️ **email_id** (`detail_only`): 'email_id' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:email_id:detail_only`
- ℹ️ **financial** (`detail_only`): 'financial' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:financial:detail_only`
- ℹ️ **gl_accounts** (`detail_only`): 'gl_accounts' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:gl_accounts:detail_only`
- ℹ️ **metrics** (`detail_only`): 'metrics' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:metrics:detail_only`
- ℹ️ **phone** (`detail_only`): 'phone' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:phone:detail_only`
- ℹ️ **phone_id** (`detail_only`): 'phone_id' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:phone_id:detail_only`
- ℹ️ **price_level** (`detail_only`): 'price_level' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:price_level:detail_only`
- ℹ️ **relations** (`detail_only`): 'relations' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:relations:detail_only`
- ℹ️ **terms** (`detail_only`): 'terms' appears in Detail page but not in List columns
  - 💡 *Consider adding a column for this field in the List page for quick scanning.  Not always needed — dismiss if the field is too verbose for a list view.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss vendor:terms:detail_only`

## Warehouse

Django fields: 26 | Pages: detail(1), list(1), display(1)
  **Detail** (4 fields): `capacity`, `location`, `manager`, `name`
  **List** (5 fields): `capacity`, `id`, `location`, `manager`, `name`
  **Display** (5 fields): `capacity`, `location`, `manager`, `metadata`, `name`

- 🔴 **capacity** (`phantom_field`): Layout references 'capacity' but Django model has no such field. Found in: detail, list, display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:capacity:phantom_field`
- 🔴 **manager** (`phantom_field`): Layout references 'manager' but Django model has no such field. Found in: detail, list, display
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:manager:phantom_field`
- 🟡 **code** (`unrendered_field`): Django has 'code' (CharField) but no layout references it. Required field — likely needs a form input.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:code:unrendered_field`
- 🔵 **count** (`unrendered_field`): Django has 'count' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:count:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:is_locked:unrendered_field`
- 🔵 **priority** (`unrendered_field`): Django has 'priority' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:priority:unrendered_field`
- 🔵 **site_code** (`unrendered_field`): Django has 'site_code' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:site_code:unrendered_field`
- 🔵 **count** (`unrendered_json`): JSONField 'count' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss warehouse:count:unrendered_json`

## Workorder

Django fields: 46 | Pages: detail(1), list(1)
  **List** (3 fields): `dt_created`, `id`, `workorder_no`

- 🔴 **workorder_no** (`phantom_field`): Layout references 'workorder_no' but Django model has no such field. Found in: list
  - 💡 *Remove the field reference from the React component, or add a matching field to the Django model.  If this is a UI-only field (e.g., password confirmation), dismiss it with --dismiss.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:workorder_no:phantom_field`
- 🔵 **address_full** (`unrendered_field`): Django has 'address_full' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:address_full:unrendered_field`
- 🔵 **attention** (`unrendered_field`): Django has 'attention' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:attention:unrendered_field`
- 🔵 **balance** (`unrendered_field`): Django has 'balance' (DecimalField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:balance:unrendered_field`
- 🔵 **conditions_description** (`unrendered_field`): Django has 'conditions_description' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:conditions_description:unrendered_field`
- 🔵 **conditions_id** (`unrendered_field`): Django has 'conditions_id' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:conditions_id:unrendered_field`
- 🔵 **cost** (`unrendered_field`): Django has 'cost' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:cost:unrendered_field`
- 🔵 **email** (`unrendered_field`): Django has 'email' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:email:unrendered_field`
- 🔵 **finance** (`unrendered_field`): Django has 'finance' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:finance:unrendered_field`
- 🔵 **flow** (`unrendered_field`): Django has 'flow' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:flow:unrendered_field`
- 🔵 **is_commission** (`unrendered_field`): Django has 'is_commission' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:is_commission:unrendered_field`
- 🔵 **is_locked** (`unrendered_field`): Django has 'is_locked' (BooleanField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:is_locked:unrendered_field`
- 🔵 **line_increment** (`unrendered_field`): Django has 'line_increment' (IntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:line_increment:unrendered_field`
- 🔵 **parent_id** (`unrendered_field`): Django has 'parent_id' (BigIntegerField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:parent_id:unrendered_field`
- 🔵 **parent_model** (`unrendered_field`): Django has 'parent_model' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:parent_model:unrendered_field`
- 🔵 **phone** (`unrendered_field`): Django has 'phone' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:phone:unrendered_field`
- 🔵 **price_level** (`unrendered_field`): Django has 'price_level' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:price_level:unrendered_field`
- 🔵 **priority** (`unrendered_field`): Django has 'priority' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:priority:unrendered_field`
- 🔵 **sell** (`unrendered_field`): Django has 'sell' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:sell:unrendered_field`
- 🔵 **source** (`unrendered_field`): Django has 'source' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:source:unrendered_field`
- 🔵 **status** (`unrendered_field`): Django has 'status' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:status:unrendered_field`
- 🔵 **terms** (`unrendered_field`): Django has 'terms' (CharField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:terms:unrendered_field`
- 🔵 **total** (`unrendered_field`): Django has 'total' (DecimalField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:total:unrendered_field`
- 🔵 **totals** (`unrendered_field`): Django has 'totals' (JSONField) but no layout references it. Optional field — may be intentionally hidden.
  - 💡 *Add a form input (register/Controller) or ScalarCard entry for this field in the Detail page, or a column in the List page.  If intentionally hidden, dismiss it.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:totals:unrendered_field`
- 🔵 **cost** (`unrendered_json`): JSONField 'cost' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:cost:unrendered_json`
- 🔵 **source** (`unrendered_json`): JSONField 'source' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:source:unrendered_json`
- 🔵 **totals** (`unrendered_json`): JSONField 'totals' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:totals:unrendered_json`
- 🔵 **flow** (`unrendered_json`): JSONField 'flow' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:flow:unrendered_json`
- 🔵 **sell** (`unrendered_json`): JSONField 'sell' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:sell:unrendered_json`
- 🔵 **finance** (`unrendered_json`): JSONField 'finance' has no sub-field references and no JsonCard in any layout
  - 💡 *Add a JsonCard for this JSONField, or individual sub-field form inputs if users need to edit its contents.*
  - To dismiss: `manage.py ai_intelligence --task layout --dismiss workorder:finance:unrendered_json`

---

## Page File Inventory

| Model | Detail | List | Display |
|-------|--------|------|---------|
| action | 1 | 1 | — |
| address | 1 | 2 | — |
| audit | 1 | 1 | 1 |
| bundle | 1 | 1 | — |
| catalog | 1 | 1 | 1 |
| contact | 7 | 2 | — |
| currency | 1 | 1 | 1 |
| customer | 1 | 2 | — |
| document | 1 | 1 | 1 |
| domain | 1 | 2 | — |
| email | 1 | 2 | — |
| employee | 1 | 1 | — |
| invoice | 1 | 1 | — |
| item | 1 | 1 | — |
| ledger | — | 1 | 1 |
| manufacturer | — | 2 | 1 |
| order | 1 | 1 | — |
| phone | 1 | 2 | — |
| project | 1 | 1 | — |
| proposal | 2 | 2 | — |
| purchase | 1 | 1 | — |
| receipt | 1 | 1 | — |
| rep | — | 2 | 1 |
| report | 1 | 1 | 1 |
| requisition | 1 | 1 | — |
| serial | 1 | 1 | 1 |
| service | 1 | 1 | 1 |
| setting | 1 | 1 | 1 |
| specification | 1 | 1 | 1 |
| tag | — | 1 | 1 |
| template | 1 | 1 | 1 |
| term | — | 1 | 1 |
| variant | 1 | 1 | 1 |
| vendor | 1 | 2 | — |
| warehouse | 1 | 1 | 1 |
| workorder | 1 | 1 | — |

---

## Workflow

1. **Review** this report — focus on 🔴 High issues first
2. **Fix** real mismatches in the React/Django code
3. **Dismiss** intentional mismatches: `manage.py ai_intelligence --task layout --dismiss model:field:type --reason 'explanation'`
4. **Re-scan**: `manage.py ai_intelligence --task layout --report`
5. **Review corrections**: resolved issues are tracked automatically — the LLM learns from your fixes
