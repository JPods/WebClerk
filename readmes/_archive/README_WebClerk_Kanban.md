# WebClerk Kanban — RESTful API & PostgreSQL JSON Patterns

**Project**: WebClerk Kanban  
**Author**: WebClerk Kanban
**Purpose**: This README documents the full RESTful API endpoints, JSON request/response formats, and PostgreSQL table schemas to store Kanban data. Use this as the canonical reference for building the backend and database migrations.

---
## Table of Contents
1. Overview
2. High-level data model (entities & relationships)
3. PostgreSQL schema (DDL)
4. JSON patterns (canonical payloads)
5. RESTful endpoints (detailed — path, method, params, body, responses)
6. Authentication
7. Real-time / WebSocket events
8. Indexing & performance notes
9. Example queries and pagination
10. Error format
11. Migration notes & suggestions
12. Postman / OpenAPI tips
13. License & attribution

---
## 1. Overview
This documentation describes the backend contract and DB layout for a production-ready Kanban board system. It is optimized for PostgreSQL (normalized relational schema with simple JSON columns for flexible metadata). The APIs are RESTful and follow predictable patterns for CRUD, filtering, reordering, and bulk operations.

---
## 2. High-level data model
Main entities:
- `users` — system users (assignees, creators)
- `boards` — a Kanban board containing columns & tasks
- `columns` — columns inside a board (Backlog, Planning, In Progress, Review, Done)
- `tasks` — cards in columns (with priority, progress, labels, assignees)
- `labels` — tag names & colors
- `attachments` — files for tasks
- `subtasks` — checklist items on tasks
- `comments` — comments on tasks
- `board_members` — users invited to boards with roles
- `activities` — activity feed entries
- `wip_rules` — optional rules per column
- `sessions` or `auth_tokens` — auth refresh tokens, etc.

Relationships:
- `board` 1 — N `columns`
- `column` 1 — N `tasks`
- `task` N — M `assignees` (via `task_assignees` join table)
- `task` 1 — N `attachments`, `subtasks`, `comments`, `activities`

---
## 3. PostgreSQL schema (recommended DDL)
Below are `CREATE TABLE` statements you can adapt to your migration tool (Knex, TypeORM, Sequelize, Flyway, etc.). Use `uuid` primary keys, `created_at`, `updated_at` timestamps, and sensible indexes.

Note: to use `uuid` in Postgres, enable the extension:
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### Users
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(255) NOT NULL,
  avatar_url TEXT,
  roles TEXT[] DEFAULT ARRAY['user']::TEXT[],
  meta JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
CREATE INDEX idx_users_email ON users(email);
```

### Boards
```sql
CREATE TABLE boards (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  title TEXT NOT NULL,
  description TEXT,
  visibility TEXT DEFAULT 'private', -- private | team | public
  settings JSONB DEFAULT '{}'::jsonb,
  created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
CREATE INDEX idx_boards_visibility ON boards(visibility);
```

### Columns
```sql
CREATE TABLE columns (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  slug TEXT,
  position INT NOT NULL, -- ordering index
  wip_limit INT, -- nullable
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  UNIQUE (board_id, position)
);
CREATE INDEX idx_columns_board_position ON columns(board_id, position);
```

### Tasks
```sql
CREATE TABLE tasks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
  column_id UUID NOT NULL REFERENCES columns(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  position INT NOT NULL, -- ordering inside column
  priority TEXT DEFAULT 'medium', -- low | medium | high | critical
  progress INT DEFAULT 0, -- 0..100
  due_date DATE,
  labels UUID[] DEFAULT '{}'::uuid[], -- array of label ids
  metadata JSONB DEFAULT '{}'::jsonb, -- store flexible fields: wip, custom fields
  created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
CREATE INDEX idx_tasks_column_position ON tasks(column_id, position);
CREATE INDEX idx_tasks_board ON tasks(board_id);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_due_date ON tasks(due_date);
```

### Task assignees (many-to-many)
```sql
CREATE TABLE task_assignees (
  task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  PRIMARY KEY (task_id, user_id)
);
CREATE INDEX idx_task_assignees_user ON task_assignees(user_id);
```

### Labels
```sql
CREATE TABLE labels (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  board_id UUID NOT NULL REFERENCES boards(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  color VARCHAR(20),
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
CREATE INDEX idx_labels_board ON labels(board_id);
```

### Attachments
```sql
CREATE TABLE attachments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  filename TEXT,
  size BIGINT,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
CREATE INDEX idx_attachments_task ON attachments(task_id);
```

### Subtasks
```sql
CREATE TABLE subtasks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  done BOOLEAN DEFAULT FALSE,
  position INT DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
CREATE INDEX idx_subtasks_task ON subtasks(task_id);
```

### Comments
```sql
CREATE TABLE comments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  text TEXT NOT NULL,
  mentions UUID[] DEFAULT '{}'::uuid[],
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
CREATE INDEX idx_comments_task ON comments(task_id);
```

### Board members (invitations & roles)
```sql
CREATE TABLE board_members (
  board_id UUID REFERENCES boards(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  role TEXT DEFAULT 'editor', -- viewer|editor|admin|owner
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  PRIMARY KEY (board_id, user_id)
);
CREATE INDEX idx_board_members_user ON board_members(user_id);
```

### Activities (audit)
```sql
CREATE TABLE activities (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  board_id UUID REFERENCES boards(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  action TEXT NOT NULL, -- e.g., task.created, task.moved
  payload JSONB DEFAULT '{}'::jsonb, -- small event payload
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
CREATE INDEX idx_activities_board ON activities(board_id);
```

### WIP rules (optional)
```sql
CREATE TABLE wip_rules (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  board_id UUID REFERENCES boards(id) ON DELETE CASCADE,
  column_id UUID REFERENCES columns(id) ON DELETE CASCADE,
  limit_count INT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

---
## 4. JSON patterns (canonical payloads)
Use these canonical shapes in API request/response bodies. Keep consistent property names and types.

### Task (full object)
```json
{
  "id": "uuid",
  "boardId": "uuid",
  "columnId": "uuid",
  "title": "Visual design refresh",
  "description": "Update typography and scale",
  "position": 1,
  "priority": "medium",
  "progress": 55,
  "dueDate": "2025-10-18",
  "labels": ["label-uuid-1","label-uuid-2"],
  "assignees": [
    { "id": "u1", "name": "Maya Patel", "avatarUrl": "..." }
  ],
  "attachments": [
    { "id":"att1","url":"https://...","filename":"specs.pdf" }
  ],
  "subtasksCount": 2,
  "metadata": { "wip": "2/5", "customFields": { "estimate": 3 } },
  "createdBy": { "id":"u2", "name":"Samir Lang" },
  "createdAt": "2025-09-20T12:00:00Z",
  "updatedAt": "2025-09-25T12:00:00Z"
}
```

### Create Task (request body)
```json
{
  "title": "New task title",
  "description": "Optional details",
  "columnId": "uuid",
  "position": 0,
  "priority": "high",
  "labels": ["uuid","uuid"],
  "assignees": ["user-uuid-1"],
  "dueDate": "2025-10-09",
  "metadata": { "customKey": "value" }
}
```

### Task Move (drag & drop)
```json
{
  "taskId": "uuid",
  "fromColumnId": "uuid",
  "toColumnId": "uuid",
  "toPosition": 2
}
```

### Error format (consistent)
```json
{
  "error": "WIP_LIMIT_REACHED",
  "message": "Cannot move task: column WIP limit reached",
  "details": { "columnId": "c_inprogress", "limit": 2, "current": 2 }
}
```

---
## 5. RESTful endpoints (full list with parameters & examples)
All endpoints that are authenticated require `Authorization: Bearer <jwt>` header. Responses use JSON and the HTTP status codes follow the usual semantics (200 OK, 201 Created, 204 No Content, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict, 500 Server Error).

### Authentication
#### `POST /auth/login`
- Body (JSON): `{ "email": "user@example.com", "password": "password123" }`
- Response `200`:
```json
{ "token": "<jwt>", "refreshToken": "<refresh>", "user": { "id":"u1","name":"Samir Lang","email":"..." } }
```

#### `GET /auth/me`
- Headers: `Authorization`
- Response `200` returns user object.

### Boards
#### `GET /boards`
- Query params: `page`, `pageSize`, `search`
- Response `200`:
```json
[{ "id":"b1","title":"Keep work flowing","description":"..." }]
```

#### `POST /boards`
- Body:
```json
{ "title":"Product Roadmap", "description":"Q4 roadmap", "visibility":"private", "settings": { "wipEnforced": true } }
```
- Response `201` returns created board object.

#### `GET /boards/{boardId}`
- Path: `boardId`
- Response `200` includes columns summary and settings.

#### `PATCH /boards/{boardId}`
- Body: partial update (title, settings, priorityLanes)
- Response `200` updated board

#### `DELETE /boards/{boardId}`
- Response `204`

#### `GET /boards/{boardId}/stats`
- Response `200`:
```json
{ "priorities": { "low":1,"medium":2,"high":3,"critical":1 }, "columns":[{ "id":"c_backlog","taskCount":1,"avgProgress":15 }], "totalTasks":7 }
```

### Columns
#### `GET /boards/{boardId}/columns`
- Response `200` ordered list of columns with `wipLimit` and `position`.

#### `POST /boards/{boardId}/columns`
- Body:
```json
{ "name":"BACKLOG", "position":0, "wipLimit": null }
```
- Response `201` returns column object.

#### `PATCH /boards/{boardId}/columns/{columnId}`
- Body: update name/wipLimit/metadata/position
- Response `200`

#### `PATCH /boards/{boardId}/columns/reorder`
- Body:
```json
{ "order":["c_backlog","c_planning","c_inprogress","c_review","c_done"] }
```
- Response `200`

### Tasks (core)

#### `GET /boards/{boardId}/tasks`
- Query params (filtering): `columnId`, `priority`, `assignee`, `label`, `search`, `dueBefore`, `dueAfter`, `progressMin`, `progressMax`, `page`, `pageSize`, `sort`
- Response `200` includes `total` and `tasks` array (see Task full object).

#### `POST /boards/{boardId}/tasks`
- Create new task.
- Body: see "Create Task" pattern above.
- Response `201` returns created task object.

#### `GET /boards/{boardId}/tasks/{taskId}`
- Response `200` full details incl. comments, attachments, subtasks if requested or via query `?embed=comments,attachments,subtasks`

#### `PATCH /boards/{boardId}/tasks/{taskId}`
- Body: partial update (title, description, priority, labels, assignees, progress, dueDate, metadata)
- Response `200` updated task object

#### `DELETE /boards/{boardId}/tasks/{taskId}`
- Response `204`

#### `PATCH /boards/{boardId}/tasks/{taskId}/move`
- Body: `{ "toColumnId":"uuid", "toPosition":2 }` (server validates WIP & ordering)
- Response `200` returns moved task and optionally affected tasks' new positions.

#### `PATCH /boards/{boardId}/tasks/reorder`
- Body:
```json
{ "columnId":"uuid", "order":["t10","t7","t1","t3"] }
```
- Response `200`

#### `POST /boards/{boardId}/tasks/bulk`
- Body example to bulk move:
```json
{ "action":"move","taskIds":["t1","t2"], "toColumnId":"c_done" }
```
- Response `200` array of per-task results with success/failure info

#### `PATCH /boards/{boardId}/tasks/{taskId}/progress`
- Body: `{ "progress": 80 }`

### Attachments
#### `POST /boards/{boardId}/tasks/{taskId}/attachments`
- `multipart/form-data` with file field `file`
- Response `201` metadata object `{ "id": "...", "url": "..." }`

#### `DELETE /boards/{boardId}/tasks/{taskId}/attachments/{attachmentId}`
- Response `204`

### Labels
CRUD endpoints: `GET/POST/PATCH/DELETE /boards/{boardId}/labels`

### Subtasks
`GET/POST/PATCH/DELETE /boards/{boardId}/tasks/{taskId}/subtasks`

### Comments
`GET/POST /boards/{boardId}/tasks/{taskId}/comments` (include `mentionUserIds` in body if needed)

### Members & Permissions
`GET/POST/DELETE /boards/{boardId}/members` — body `{ "userId":"...", "role":"editor" }`

### Activities / Audit
`GET /boards/{boardId}/activity` — supports `limit`, `page` params

### Validation
`POST /boards/{boardId}/validate-move`
- Body: `{ "taskId":"...", "toColumnId":"...", "toPosition": 1 }`
- Response `200 { "allowed": true }` or `{ "allowed": false, "reasons": [...] }`

### Search & Export
`GET /boards/{boardId}/search?q=...&labels=...`
`GET /boards/{boardId}/export?format=csv|json`

---
## 6. Authentication
- Use JWT Bearer tokens for APIs.
- Store refresh tokens in a secure DB `auth_tokens` table (or `sessions`) with `user_id`, `refresh_token`, `expires_at`, `created_at`.
- Protect endpoints; return `401` for missing/invalid token.
- Include `roles` on user object so APIs can enforce `admin/editor/viewer` actions.

Example token header:
```
Authorization: Bearer eyJhbGci...
```

---
## 7. Real-time / WebSocket events
Recommend Socket.IO or native WebSocket server with channel per-board `boards:{boardId}`. Broadcast minimal event payloads:

Event examples:
```json
{ "event":"task.created", "data": { "id":"t1","columnId":"c_backlog","position":0, "title":"..." } }
{ "event":"task.moved", "data": { "id":"t1","fromColumnId":"c_planning","toColumnId":"c_inprogress","toPosition":1 } }
{ "event":"column.reordered", "data": { "boardId":"b1", "order": ["c1","c2","c3"] } }
{ "event":"board.stats.updated", "data": { "priorities": {...} } }
```
Clients should optimistically update UI and reconcile on server ack or later snapshot.

---
## 8. Indexing & performance notes
- Index `tasks(column_id, position)` for fast ordering retrieval per column
- Index `tasks(board_id)` and `tasks(priority)` for board wide filters
- Use partial indexes for common queries (e.g., open tasks)
- Keep `metadata` JSONB but move frequently-filtered fields to explicit columns (e.g., `progress`, `priority`, `due_date`)
- Batch updates for reorder operations to reduce DB churn (use single transaction)
- Use `SELECT ... FOR UPDATE` in transactions when performing moves/reorder to avoid races

---
## 9. Example queries and pagination
Get tasks for a column (ordered):
```sql
SELECT t.*, array_agg(ta.user_id) AS assignee_ids
FROM tasks t
LEFT JOIN task_assignees ta ON t.id = ta.task_id
WHERE t.column_id = '...'
GROUP BY t.id
ORDER BY t.position ASC
LIMIT 50 OFFSET 0;
```

Pagination: use `page` & `pageSize` or cursor-based pagination for large boards. Cursor: return `lastPosition` or `lastUpdatedAt`.

---
## 10. Error format
Standardize error responses as:
```json
{ "error": "ERROR_CODE", "message": "Human readable message", "details": { ... } }
```

Common error codes:
- `VALIDATION_ERROR` (400)
- `AUTH_REQUIRED` (401)
- `FORBIDDEN` (403)
- `NOT_FOUND` (404)
- `WIP_LIMIT_REACHED` (409)
- `CONFLICT` (409)

---
## 11. Migration notes & suggestions
- Use migration tool (Flyway/Knex/TypeORM) and seed default columns and example board on initial migration
- Add `positions` as integers (dense ordering) or consider fractional positions (like 1.0, 1.1) to reduce reindexing on reorder.
- Add `version` or `updated_at` optimistic locking on `tasks` to avoid overwrite races.

---
## 12. Postman / OpenAPI tips
- Create an OpenAPI 3.0 spec using the endpoints above: attach security scheme `bearerAuth` and generate client SDKs.
- Provide example values for `boardId`, `columnId`, `taskId` in Postman environment variables.
- Export collection for frontend devs and QA.

---
## 13. License & attribution
This README was auto-generated for **WebClerk Kanban**. Use and adapt as needed.

---
## Appendix: Sample cURL commands

Create a board:
```bash
curl -X POST "https://api.example.com/boards" \
 -H "Authorization: Bearer $TOKEN" \
 -H "Content-Type: application/json" \
 -d '{"title":"Product Roadmap","description":"Q4","visibility":"team"}'
```

Create a task:
```bash
curl -X POST "https://api.example.com/boards/<boardId>/tasks" \
 -H "Authorization: Bearer $TOKEN" \
 -H "Content-Type: application/json" \
 -d '{"title":"Release checklist","description":"Consolidate rollout plan","columnId":"<columnId>","priority":"low","assignees":["<userId>"],"dueDate":"2025-10-20"}'
```

Move a task:
```bash
curl -X PATCH "https://api.example.com/boards/<boardId>/tasks/<taskId>/move" \
 -H "Authorization: Bearer $TOKEN" \
 -H "Content-Type: application/json" \
 -d '{"toColumnId":"<newColumnId>","toPosition":0}'
```

---
End of README
