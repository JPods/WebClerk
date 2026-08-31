# WCAPI: Saved Queries and Saved Record Sets

Persist ad‑hoc queries per person/role/job and manage reusable record ID sets.

## Saved Queries

Storage:
- Setting rows with purpose="saved_query", model_name=<model>
- data: { dsl, scope, labels[], owner_id }

Scope rules (access):
- person: owner_id must match current user
- role: value must be in user roles (SUPER/ADMIN/GROUPS/USER)
- job: header X-Job or ?job= must match scope.value
- Admins can access all

Endpoints:
- Save: POST /wcapi/<model>/_query/save
  - { name, dsl: {...}, scope: {type, value}, labels?:[], comment? }
- Run saved: POST /wcapi/<model>/_query with { "saved": "<id|name>" }

Example save:
{
  "name": "My Contacts",
  "dsl": { "where": [{ "field": "company", "op": "icontains", "value": "Acme" }] },
  "scope": { "type": "person", "value": "123" },
  "labels": ["favorite"]
}

## Saved Record Sets

Purpose: freeze a list of record IDs so teams can revisit the same cohort.

Storage:
- Setting rows with purpose="saved_set"
- data: { ids[], scope, labels[], owner_id }

Endpoints:
- Create: POST /wcapi/<model>/_sets
  - { name, ids: [..], scope: {type, value}, labels?:[], comment? }
- Update: PATCH /wcapi/<model>/_sets/<id|name>
  - { op: add|remove|replace|clear, ids?: [..] }
- Fetch records: GET /wcapi/<model>/_sets/<id|name>
  - Returns serialized records; respects soft delete and role-based fields
- Delete: DELETE /wcapi/<model>/_sets/<id|name>

Use with queries:
- Restrict an open-query to a set: add ?set=<id|name> to /_query calls.

Examples:
- Create:
  curl -sS -X POST http://localhost:8000/wcapi/contact/_sets \
    -H "Content-Type: application/json" \
    -d '{"name":"S1","ids":[1,2,3],"scope":{"type":"person","value":"123"}}'

- Add/remove:
  curl -sS -X PATCH http://localhost:8000/wcapi/contact/_sets/S1 \
    -H "Content-Type: application/json" \
    -d '{"op":"remove","ids":[2]}'

- Fetch:
  curl -sS http://localhost:8000/wcapi/contact/_sets/S1

## Soft Delete + Purge

- Most models enable soft_delete with retention_days=60.
- Soft-deleted rows are hidden from lists.
- Purge expired items daily:
  ./run.sh manage purge_soft_deleted