# Allie ↔ WebClerk Integration

> **Reading order**: [← 01-architecture-overview](../../01-architecture-overview.md) | [03-wcapi-gateway →](../../03-wcapi-gateway.md)

---

## Overview

**Allie** is Bill's personal AI companion — his agent in the world. **WebClerk** is her enterprise backbone for collaborative, shared data. Together they follow a clear division of labor:

| Agent | Role |
|-------|------|
| **Allie** | Bill's agent — acts on his behalf, reads/writes his data, manages his relationships and schedule |
| **Alice** | Database agent — governs the WebClerk database, enforces rules, maintains data integrity |

Allie talks to WebClerk through the `wcapi` gateway. Alice governs what happens on the database side. Allie does not need to know the internals; she just needs to know the five models and the two endpoints.

---

## The Five Models Allie Accesses

Everything Allie does in WebClerk goes through five models. `contact` is the center of gravity — the other four orbit it.

| Model | What it holds | Key relationship |
|-------|--------------|-----------------|
| `contact` | People and organizations Bill knows | Root of all data |
| `action` | Tasks, follow-ups, next steps | Belongs to a contact |
| `communication` | Email (inbound and outbound) | Belongs to a contact |
| `connection` | Calendar events, meeting invites | Belongs to a contact |
| `setting` | Allie's scoped preferences and flags | Belongs to Bill's contact record |

**Contact is not just another model.** Every action, email, calendar event, and setting traces back to a contact. When Allie meets someone new, she creates a contact first, then hangs everything else off it.

---

## Email and Calendar Live Inside WebClerk

Email and calendar are not external integrations bolted on — they are first-class WebClerk models:

- **Email** → `communication` model. Allie writes outbound email as `communication` records with `direction=outbound`. Inbound email is synced in by Alice. Allie reads it via `wcapi/get/`.
- **Calendar** → `connection` model. Meeting invites, scheduled calls, events — all stored as `connection` records linked to the relevant contact.

This means Bill's email and calendar history live in the same database as his contacts and tasks. Allie can query across all of them in a single call.

---

## wcapi Patterns

### Endpoint summary

```
GET  /wcapi/get/    — fetch a record or list
POST /wcapi/save/   — create or update a record
```

All responses use the standard envelope:

```json
{
  "status": "success",
  "data": { ... },
  "error": null,
  "meta": { "count": 1, "model": "contact" }
}
```

### Creating a new record (no `id`)

```http
POST /wcapi/save/
Authorization: Bearer <allie-token>
Content-Type: application/json

{
  "model_name": "contact",
  "first_name": "Maya",
  "last_name": "Chen",
  "email": "maya@example.com"
}
```

Response:
```json
{
  "status": "success",
  "data": { "id": 4471, "first_name": "Maya", "last_name": "Chen" },
  "error": null,
  "meta": { "created": true }
}
```

> `model_name` is always **singular** — `contact`, not `contacts`.

### Updating an existing record (include `id`)

```http
POST /wcapi/save/
Authorization: Bearer <allie-token>
Content-Type: application/json

{
  "model_name": "contact",
  "id": 4471,
  "phone": "+1-415-555-0192"
}
```

### Fetching a single record

```http
GET /wcapi/get/?model_name=contact&id=4471
Authorization: Bearer <allie-token>
```

### Fetching a list

```http
GET /wcapi/get/?model_name=action&contact_id=4471
Authorization: Bearer <allie-token>
```

### Creating an action (task) for a contact

```http
POST /wcapi/save/
Authorization: Bearer <allie-token>

{
  "model_name": "action",
  "contact_id": 4471,
  "title": "Follow up on proposal",
  "due_date": "2026-04-07",
  "status": "pending"
}
```

### Logging an outbound email

```http
POST /wcapi/save/
Authorization: Bearer <allie-token>

{
  "model_name": "communication",
  "contact_id": 4471,
  "direction": "outbound",
  "channel": "email",
  "subject": "Re: Q2 proposal",
  "body": "Hi Maya, following up on our conversation..."
}
```

### Creating a calendar event

```http
POST /wcapi/save/
Authorization: Bearer <allie-token>

{
  "model_name": "connection",
  "contact_id": 4471,
  "connection_type": "meeting",
  "title": "Intro call with Maya",
  "start_datetime": "2026-04-08T14:00:00Z",
  "end_datetime": "2026-04-08T14:30:00Z"
}
```

---

## Allie's Scoped Token

Allie authenticates with a **scoped API token** — not Bill's full admin credentials. The token is provisioned by Alice and carries a fixed permission set.

**What the token can do:**

| Model | Read | Write |
|-------|------|-------|
| `contact` | Yes | Yes (Bill's contacts only) |
| `action` | Yes | Yes (Bill's actions only) |
| `communication` | Yes | Yes (outbound only) |
| `connection` | Yes | Yes |
| `setting` | Yes | Yes (Allie's namespace only) |

**What the token cannot do:**

- Access transaction models (`invoice`, `order`, `proposal`) — those are enterprise commerce data
- Access other users' records
- Delete records (Allie queues soft-deletes; Alice executes them)
- Access `manage/` or admin endpoints
- Bypass field-level permission rules enforced by Alice

The token is stored on `/Volumes/Allie` in the carryon — not in any cloud service.

---

## Sovereignty Rule

Data has two homes, determined by whether it is **sovereign** (belongs only to Bill) or **collaborative** (shared with others or actionable across systems).

| Data type | Home | Reason |
|-----------|------|--------|
| Credentials, passwords, API keys | `/Volumes/Allie` (local) | Never leaves Bill's device |
| Medical records, biometrics | `/Volumes/Allie` (local) | Sovereign; no cloud exposure |
| Carryon (Allie's working memory) | `/Volumes/Allie` (local) | Runtime state, not persisted to cloud |
| Contacts | WebClerk | Shared, actionable, relational |
| Actions / tasks | WebClerk | Tracked, assignable, reportable |
| Email | WebClerk (`communication`) | Archived, searchable, linked to contacts |
| Calendar events | WebClerk (`connection`) | Shared scheduling |
| Allie settings | WebClerk (`setting`) | Preferences that survive device loss |

**The carryon is not a copy of WebClerk data.** It holds pointers:

```json
{
  "webclerk_contact_id": 4471,
  "webclerk_base_url": "https://webclerk.example.com"
}
```

Allie looks up the full record from WebClerk when she needs it. The carryon does not duplicate contact fields, history, or communications.

---

## Offline Behavior

When WebClerk is unreachable (no network, maintenance, token expired), Allie does not drop writes. She queues them as **pending items** in the carryon.

### Pending item format

```json
{
  "pending_writes": [
    {
      "id": "local-uuid-001",
      "model_name": "action",
      "payload": {
        "contact_id": 4471,
        "title": "Send follow-up email",
        "status": "pending"
      },
      "queued_at": "2026-04-01T09:15:00Z",
      "attempts": 0
    }
  ]
}
```

### Sync behavior on reconnect

1. Allie detects WebClerk is reachable (health check against `webclerk_base_url`).
2. She replays pending writes in `queued_at` order.
3. On success, each item is removed from the queue.
4. On conflict (record changed by another party while offline), Alice's conflict resolution rules apply — Allie does not overwrite silently.
5. Allie reports any unresolved conflicts to Bill before clearing them.

---

## Design Principles

1. **Allie acts, Alice governs.** Allie makes requests; Alice enforces rules, field permissions, and data integrity.
2. **Contact first.** Before writing any action, email, or event, ensure the contact record exists in WebClerk. The `webclerk_contact_id` in the carryon is the proof.
3. **Sovereign data stays local.** If it touches credentials, health, or Allie's internal state — it lives on `/Volumes/Allie`, not WebClerk.
4. **Pointers, not copies.** The carryon references WebClerk IDs. It does not cache full records.
5. **Offline-safe.** Every write Allie attempts while offline is queued and retried. No writes are silently dropped.
