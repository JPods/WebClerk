# Project Kanban Generation

Action: Create weekly kanban Project records
Function: generate_kanban_projects
Frequency: As needed to seed or extend the kanban project queue
Process: POST to /wcapi/manage/ with action generate_kanban_projects and a start_date; the function snaps to the first Wednesday on or after that date and creates weekly Project rows

The canonical implementation lives in /Users/williamjames/Documents/CommerceExpert/webClerk3/apps/core/views/manage_view.py in `_generate_kanban_projects()`.

What it does:
- Creates `Project` rows.
- Sets `name` to `kanban-YYYY-MM-DD`.
- Sets `dt_kanban` to midnight UTC for each generated Wednesday.
- Defaults to `status="active"`, `attention="normal"`, and `priority=3`.

Behavior:
- `start_date` is required.
- The function computes the first Wednesday on or after `start_date`.
- `interval_days` defaults to `7`, so the created records stay on Wednesdays.
- The response returns both the requested date and the effective Wednesday-aligned `start_date`.

Manage action example:

```json
{
  "action": "generate_kanban_projects",
  "params": {
    "count": 5,
    "start_date": "2026-04-06",
    "interval_days": 7
  }
}
```

Expected first record:
- Requested `start_date`: `2026-04-06` (Tuesday)
- Effective first Wednesday: `2026-04-08`
- First project name: `kanban-2026-04-08`

Related files:
- /Users/williamjames/Documents/CommerceExpert/webClerk3/apps/core/views/manage_view.py
- /Users/williamjames/Documents/CommerceExpert/webClerk3/apps/transactions/models/project.py
- /Users/williamjames/Documents/CommerceExpert/webClerk3/tests/test_manage_kanban_projects_action.py