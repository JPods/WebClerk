# webClerk3

## Project Docs

[Google Docs](https://docs.google.com/document/d/1a8ZYgSVpJsa6VhhEPkW5bOreRfY4mZ0tuRk0NHJIFJI/edit?usp=sharing)

## Contributors

- Antor Ahmed
- Riju Karar
- Samir Biswas
- Sanjutka Patra
- CoPilot
- Bill James

## Data Basics

Location: `common/management/commands/`  
Data file: `all_tables_export.json`

Export/import data (avoid exporting or importing rows still marked pending):

```bash
python manage.py demo_data_import_export export
python manage.py demo_data_import_export import
```

3-column admin reference: [Grok Link](https://grok.com/share/c2hhcmQtMg%3D%3D_427dc198-2378-41ef-b3c5-c77d1e4e1062)

## Path Basics

```text
webClerk3/
├── apps/
│   ├── core/
│   │   ├── models/
│   │   ├── views/
│   │   ├── services/
│   │   ├── templates/
│   │   └── ...
│   ├── communications/
│   │   ├── models/
│   │   ├── views/
│   │   └── ...
│   └── accounts/
│       ├── models/
│       └── ...
├── templates/
├── common/
│   └── management/commands/
└── webclerk3_api/
  ├── settings.py
  ├── celery_app.py
  └── ...
```

## Install

Prerequisites:

- Celery
- Redis
- Pydantic (optional – JSON typing) – video: [YouTube](https://www.youtube.com/watch?v=XIdQ6gO3Anc)

## Data Consistency

Commands (in `common/management/commands`):

```bash
python manage.py demo_data_import_export export
python manage.py demo_data_import_export import
```

If needed (example):

```sql
DROP TABLE IF EXISTS pending CASCADE;
```

## Runbook

### Normal run

```bash
source ./bin/activate
python manage.py runserver
```

### Port already in use

```bash
kill -9 $(lsof -t -i :8000)
```

### Schema changes (add/remove/modify columns)

```bash
source ./bin/activate
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

### First time setup

```bash
python -m venv .
source ./bin/activate
pip install -r requirements.txt
psql -U an7or -d postgres
# or: psql -U williamjames -d postgres
CREATE DATABASE commerce_expert;
rm */migrations/0*.py || true
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py view_edit_to_settings
python manage.py runserver
```

### Reset Postgres (if issues)

```bash
source ./bin/activate
psql -U an7or -d postgres
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'commerce_expert' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS commerce_expert;
CREATE DATABASE commerce_expert;
rm */migrations/0*.py || true
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py view_edit_to_settings
python manage.py runserver
```

## Git Workflow

Daily start:

```bash
API requests and errors are logged to `webclerk3.log`.
python manage.py check_services  # or ./check_services.sh
```

After changes:

```bash

## Running Tests

```

Create PR:

1. Visit: <https://github.com/JPods/webClerk3/branches>
2. Open Pull Requests tab
3. New pull request (dev <- your_branch)
4. Complete review steps

## 🎯 Architecture Overview

**Universal API System** – One API pattern handles all data operations (contacts, actions, emails, phones, domains, addresses).

### Pattern Structure (dev without front end)

```text
core/templates/
├── base.html
├── core/
│   ├── home.html
│   ├── about.html
│   └── contact.html
└── auth/
  ├── login.html
  └── signup.html
```

### Universal API Endpoints

Details listed below with examples.

## Universal API Usage Examples

Source: `webclerk3/core/urls.py`

### View All Contacts

`http://localhost:8000/wcapi/manage/?table_name=contacts`

### View Specific Contact

`http://localhost:8000/wcapi/manage/?table_name=contacts&id=123`

### Manage Contact's Emails

`http://localhost:8000/wcapi/manage/?table_name=emails&contact_id=123`

### Create New Action

`http://localhost:8000/wcapi/manage/?table_name=actions&mode=create`

### API Data Retrieval

`http://localhost:8000/wcapi/get/?table_name=contacts&id=123`

### Key Features

✅ **Universal API** – One pattern for all tables  
✅ **Contact-Centric** – Everything revolves around contacts  
✅ **Relationship Management** – JSON refs system  
✅ **Lesson1-Style Navigation** – Clean, emoji-driven nav  
✅ **Bootstrap 5 UI** – Modern, responsive design  
✅ **Django Default 404** – Developer-friendly error pages  
✅ **Consolidated Patterns** – All in core/templates/  
✅ **Future-Proof** – Ready for React front-end migration

### Navigation Structure

🏠 **Home** – Landing page with system overview  
**About** – System documentation and features  
**Contacts** – `/wcapi/manage/?table_name=contacts`  
**Actions** – `/wcapi/manage/?table_name=actions`  
**Communications** – `/wcapi/manage/?table_name=emails`  
🥳 **New Contact** – Quick create contact  
**Admin** – Django admin (superusers only)  
🤚 **Logout** – Session termination

## Model Visualization

```bash
pip install pydot
brew install graphviz   # macOS for image output
python manage.py graph_models --pydot -a -g -o webclerk3_visualized.png
```

Graphviz docs: <https://graphviz.org/doc/build.html>

## Celery Monitoring

Flower is a web-based tool for monitoring and administrating Celery clusters.

**To install and run Flower:**

```bash
pip install flower
celery -A webclerk3_api flower
```

Visit <http://localhost:5555> in your browser to view the dashboard.

If you see warnings like `Inspect method ... failed`, it usually means there are no active tasks.

## Keyword Refresh System (Universal API Search Index)

We defer expensive keyword extraction for BaseModel derivatives to keep write latency low.

Flow:

1. On each save, `metadata.flags.keywords_pending` is set True.
2. A periodic Celery task `common.tasks.refresh_keywords_task` (every 10 minutes) processes pending rows, updates `refs.keywords`, clears the flag.
3. Manual runs:

```bash
python manage.py refresh_keywords --dry-run
python manage.py refresh_keywords --limit 500
python manage.py audit_base_models --limit 5
```

Force immediate refresh of all pending rows:

```bash
python manage.py refresh_keywords --limit 0
```

Relevant code: `common/models.py`, commands in `common/management/commands/`, task `common/tasks.py`, scheduling in `common/__init__.py`.

Planned enhancements:

- Dirty-field tracking for change log
- Optional materialized keyword table for analytics

## API Rate Limiting

All API endpoints are rate limited using Django REST Framework:

- Authenticated users: 1000 requests/day
- Unauthenticated users: 100 requests/day

## Logging

API requests and errors are logged to `webclerk3.log`.

## Transaction Line & Aggregation Endpoints

All transaction parent and line resources share a consistent CRUD pattern under `tx/`:

Parents (headers):

```text
GET/POST   /tx/proposals/
GET/PUT    /tx/proposals/{id}/
GET/POST   /tx/orders/
GET/PUT    /tx/orders/{id}/
... (invoices, purchases, workorders, requisitions)
```

Lines:

```text
GET/POST   /tx/proposal-lines/?parent_ref_id={id}
GET/PUT    /tx/proposal-lines/{id}/
... (order-lines, invoice-lines, purchase-lines, workorder-lines, requisition-lines)
```

Filtering / Searching / Ordering (lines):

- Filter: `?parent_ref_id=123&status=open`
- Search: `?search=widget`
- Order: `?ordering=parent_ref_id` (prefix with `-` for descending)

Aggregation:

```text
GET /tx/lines/aggregate/?parent_ref_id={id}[&model=proposal-line][&ttl=120][&include_breakdown=1]
```
Parameters:

- parent_ref_id (required): Parent transaction id.
- model (optional): Scope to single line model code (proposal-line, order-line, invoice-line, purchase-line, workorder-line, requisition-line).
- ttl (optional int >=5): Override cache TTL seconds (default 60 or project setting).
- include_breakdown (optional 0/1/true/false): When scoping to a single model include per-model breakdown (normally only returned when unscoped).

Unscoped example (no model param) response:

```json
{
  "parent_ref_id": 42,
  "total_lines": 7,
  "total_price_extended": "123.45",
  "total_cost_extended": "97.10",
  "breakdown": {
    "proposal-line": {"lines": 3, "price_extended": "80.00", "cost_extended": "60.00"},
    "order-line": {"lines": 4, "price_extended": "43.45", "cost_extended": "37.10"}
  },
  "ttl_seconds": 60,
  "cache_window": 29123456
}
```

Scoped example with breakdown forced:

```json
{
  "parent_ref_id": 42,
  "model": "proposal-line",
  "total_lines": 3,
  "total_price_extended": "80.00",
  "total_cost_extended": "60.00",
  "breakdown": {
    "proposal-line": {"lines": 3, "price_extended": "80.00", "cost_extended": "60.00"}
  },
  "ttl_seconds": 30,
  "cache_window": 29123457
}
```

Notes:

- Decimal totals are stringified for precision.
- `ttl_seconds` reflects actual TTL used (min 5). `cache_window` aids debugging (floor(now / ttl)).
- Cache invalidates automatically on any line create/update/delete.
- Set a project-wide default TTL via Django settings (if provided) or rely on built-in default (60s).
- Configure default aggregation TTL globally by adding `TX_AGGREGATE_TTL_SECONDS = 120` (example) to `settings.py`.

Authentication:

- JWT or session auth required (HTTP 401/403 if missing).

Throttle Scopes:

- Parents: `tx_parent`
- Lines: `tx_line`
- Aggregate: `tx_aggregate`

OpenAPI generation (drf-spectacular) will include summaries for these endpoints.

### Field-Level Authorization (view_edit)

Field visibility & editability are driven by rows in `settings` with `purpose="view_edit"` and `table_name` matching the model DB table (e.g. `transactions_proposalline`). The JSON structure:

```json
{
  "USER": {"view": ["id", "status"], "edit": ["status"]},
  "ADMIN": {"view": ["id", "status", "probability"], "edit": ["status", "probability"]},
  "PUBLIC": {"view": ["id"], "edit": []}
}
```

API layer effects:

- Responses filter out fields not in the role's `view` list.
- Writes (POST/PATCH/PUT) are rejected if attempting to change fields not in `edit` list.
- Authorization matrix endpoint: `GET /tx/auth/fields/?model=proposal-line` returns `{ role, rules:{view,edit} }` for the authenticated user.

Add new permissions simply by editing the JSON in the Setting record; caching auto-invalidation occurs on modification timestamp change.

Frontend consumption (React example):

1. Fetch rules on component mount:

```js
const res = await fetch('/tx/auth/fields/?model=proposal-line', { headers: { Authorization: `Bearer ${token}` }});
const { rules } = await res.json();
```

1. Helpers:

```js
const canView = f => rules.view.includes(f);
const canEdit = f => rules.edit.includes(f);
```

1. Conditional render:

```jsx
{canView('status') && <span>{line.status}</span>}
{canEdit('status') && <input value={status} onChange={e=>setStatus(e.target.value)} />}
```

1. Submit only editable fields; backend returns 400 with per-field errors if unauthorized fields included.

Authorization matrix (single model):

```text
GET /tx/auth/fields/?model=proposal-line
```

Batch authorization matrix:

Two options (choose based on URL length / convenience):

1. GET (comma separated model list)

```text
GET /tx/auth/fields/batch/?models=proposal-line,order-line,invoice-line
```

1. POST (JSON body – preferred for many models)

```http
POST /tx/auth/fields/batch/
Content-Type: application/json

{"models": ["proposal-line", "order-line", "invoice-line"]}
```

Response shape:

```json
{
  "role": "USER",
  "models": {
    "proposal-line": {"view": ["id", "status"], "edit": ["status"]},
    "order-line": {"view": ["id"], "edit": []},
    "bad-line": {"error": "invalid-model"}
  }
}
```

CLI inspection of active matrices:

```bash
python manage.py list_view_edit_matrices --pretty
python manage.py list_view_edit_matrices --table proposal_line --role user --pretty
```

Example output:

```json
{
  "proposal_line": {
    "id": 42,
    "modified_dt": "2025-08-29T06:50:00.123456Z",
    "data": {
      "USER": {"view": ["id", "status"], "edit": ["status"]}
    }
  }
}
```

## Running Tests

```bash
python manage.py test
```

## Deployment (Placeholder)

Add instructions for gunicorn, nginx, HTTPS (Let's Encrypt), environment hardening.

## Environment Variables

Create a `.env` file in the project root with:

```env
SECRET_KEY=your_secret_key
DEBUG=True
DATABASE_NAME=your_db_name
DATABASE_USER=your_db_user
DATABASE_PASS=your_db_password
DATABASE_HOST=localhost
DATABASE_PORT=5432
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=your_email@example.com
EMAIL_HOST_PASSWORD=your_email_password
SENTRY_DSN=
```

## API Documentation Access (Placeholder)

Document how to access OpenAPI/Swagger (e.g., `/api/schema/`, `/api/docs/`).

## Internationalization (i18n)

We will use multiple languages ONLY for warning messages where clarity and speed are both required. React will manage all other language issues.

To add a new language:

1. Add the language code to `LANGUAGES` in `settings.py`.
2. Mark all user-facing strings with `{% trans %}` or `gettext_lazy`.
3. Run `python manage.py makemessages -l <lang>`.
4. Edit the `.po` files in `locale/<lang>/LC_MESSAGES/`.
5. Run `python manage.py compilemessages`.

```bash
python manage.py test
```

## Production Deployment (Placeholder)










