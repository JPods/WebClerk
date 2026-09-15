# JSON Editing Authority — Why Alice Controls Access

**Created:** 2026-07-11
**Owner:** Bill James

---

## The Problem

JSON fields are the most powerful and most dangerous fields in WC3. They hold pricing tiers, inventory quantities, totals, refs links, metadata, and configuration. A bad edit to a JSON field can:

- Zero out an invoice balance
- Break a BOM cost rollup
- Corrupt refs.links and orphan related records
- Override RBAC field_access by editing the Setting directly
- Create data that passes validation but produces wrong reports

Unrestricted JSON editing is the equivalent of handing someone the database password.

---

## The Design

### Three Modes for JSON Fields

| Mode | Who | What they see | How they get it |
|---|---|---|---|
| **Read-only** | Everyone by default | Collapsed summary: `{12 keys}` or `[3 items]`. Click opens floating JSON viewer (read-only) | Default — no permission needed |
| **Inspect** | Anyone with field_access for the model | Full JSON viewer in floating window. Navigate nested structures, click links to related records. Still read-only | Click the JSON field label |
| **Edit** | Users with explicit JSON edit authority | Unlock button appears in floating viewer. Edit, save through wcapi, backend validates | Requires field_access + Setting permission |

### The Floating JSON Viewer

- Opens via `window.open('/json-viewer?model=X&id=Y&field=Z')`
- Independent browser window — not a modal, not a dialog
- Read-only by default
- Unlock button visible only if user has authority
- When unlocked: parent BrowserDetail locks that field (no two windows editing same data)
- Save goes through wcapi — same path as every other edit
- Close refreshes the parent with backend-validated values

---

## Why Alice Controls Authority

### The Problem with Static Permissions

Traditional RBAC says: "User X has role Y, role Y can edit field Z." This is set once and forgotten. It doesn't account for:

- A user who has never edited JSON before suddenly editing pricing tiers
- A user who normally edits metadata accidentally editing totals
- A user editing the same field 50 times in an hour (possible script, possible mistake)
- A user editing JSON on a record they've never viewed before

Static permissions answer "can this user edit this field?" but not "should this user be editing this field right now?"

### Alice's Role

Alice sits between the permission check and the edit action. She doesn't block — she observes, learns, and advises.

**What Alice does:**

1. **Tracks JSON edit patterns** — who edits what, how often, what changes
2. **Flags anomalies** — first-time JSON editor on a critical field gets a coaching tip, not a block
3. **Suggests authority levels** — "Bill edits refs.links weekly. Promote to auto-unlock for refs fields?"
4. **Posts patterns to WCHQ** — if 40% of users struggle with the same JSON field, that field needs a better widget, not more training
5. **Schedules review** — monthly WCHQ settings review includes JSON edit authority as a line item
6. **Logs every edit** — alice_log captures model, field, before/after values, user, timestamp

**What Alice does NOT do:**

- Block users who have authority — she advises, she doesn't gatekeep
- Make authority decisions alone — admin approves, Alice suggests
- Override RBAC — field_access is the hard gate, Alice is the soft layer on top

### The Authority Cascade

```
1. field_access Setting → does this role see this field at all?
   No  → field hidden. Stop.
   Yes → continue.

2. field_access Setting → does this role have edit permission?
   No  → read-only. Can inspect but not edit. Stop.
   Yes → continue.

3. Setting record → does this model allow JSON editing?
   No  → read-only. Stop.
   Yes → continue.

4. Alice check → is this user's first JSON edit on this field?
   Yes → show coaching tip: "This field affects [totals/pricing/inventory]. Changes are saved immediately."
   No  → unlock button available.

5. User clicks Unlock → edit mode active.
   Alice logs: edit_started, model, field, user, timestamp.

6. User saves → wcapi validates → backend recalculates.
   Alice logs: edit_saved, before_value, after_value, delta.
   If JS calculated column disagrees with backend → FAULT.

7. Alice accumulates patterns → suggests promotions/demotions at monthly review.
```

---

## The Payoff

- Users who need to edit JSON can do it safely
- Users who shouldn't are guided away without being blocked
- Every edit is logged, auditable, and recoverable
- Patterns across the community improve the tools for everyone
- The path through the front door is always easier than going to psql

---

## Connection to Other Rules

| Rule | How it connects |
|---|---|
| **No List.tsx** | DataBrowser is the only UI — JSON editing happens here or nowhere |
| **JS display, backend saves** | JSON viewer shows data, wcapi saves it, backend validates |
| **Front-back mismatch = FAULT** | If a JSON edit produces a calculation mismatch, Alice and Athena alert |
| **zz/qq exclusion** | Training records can be edited freely — they never tally into reports |
| **WCHQ monthly review** | JSON edit authority is reviewed monthly by admin with Alice |
| **All CRUD through wcapi** | JSON saves go through the same audited path as everything else |
