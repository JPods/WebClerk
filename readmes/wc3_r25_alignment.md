WC3 ↔ R25 Field Alignment Guide
================================

This document maps canonical WC3 Action/BaseModel/CoreModel fields to their current R25 Kanban variable names. Update R25 files to match WC3 naming exactly.

dt_start marks the start of an action
dt_due as the deadline
dt_expected marks the expected end of an action
dt_completed marks the actual end of an action

IDENTITY
- id → id
- uuid → uuid
- ida → ida
- dt_created → dt_created
- dt_modified → dt_modified
- version → version
- is_active → is_active
- is_deleted → is_deleted
- is_archived → is_archived

HIERARCHY
- action_id → action_id

MULTILINGUAL
- action → action
- description → description
- languages → languages

ASSIGNMENT
- assigned_to → assigned_to
- contact_id → contact_id

PROJECT INFO
- project_name → project_name
- project_id → project_id
- project_metadata → project_metadata
- linkage → linkage

KANBAN FIELDS
- sequence → sequence
- kanban_column → kanban_column
- priority → priority
- difficulty → difficulty
- status → status
- percent_complete → percent_complete
- burndown → burndown

DATE FIELDS
dt_start → dt_start (actual start of action)
dt_expected → dt_expected (expected end of action)
dt_due → dt_due (committed deadline)
dt_completed → dt_completed (actual end of action – authoritative)

Deprecated
dt_end → dt_end (fully replaced by dt_completed; remove from all R25 mappings and components)
dt_updated → dt_updated
duration → duration

AUDIT FIELDS
- created_by → created_by
- updated_by → updated_by
- expected_by → expected_by
- due_by → due_by
- completed_by → completed_by
- start_by → start_by
- end_by → end_by

BASEMODEL ENVELOPE
- metadata → metadata
- refs → refs
- prefs → prefs
- comments → comments
- actions → actions
- health_rating → health_rating

NEXT STEPS
Update R25 TypeScript interfaces, mappers, and React props to strictly match these names.
Fine tuning phase initiated for full WC3 alignment across Kanban and Gantt modules.
