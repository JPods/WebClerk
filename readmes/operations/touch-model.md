# Touch Model — Communication Event Log

**Created:** 2026-08-12
**Status:** Active — deployed to dev

## What It Is

Touch records that a communication happened — a phone call, email, visit, text, or meeting. A Touch is NOT an Action (work to be done). An Action may trigger a Touch, and a Touch may spawn an Action, but they have different lifecycles.

- **Action** = work item (kanban, priority, retrospection)
- **Touch** = event (timestamp, channel, summary, done)

## Backend

**Model:** `apps/communications/models/touch.py`
**Table:** `touches`
**Registry:** `model_registry.py` key `touch`, `settings.py` WCAPI_MODEL_MAP

### Fields

| Field | Type | Purpose |
|-------|------|---------|
| contact | FK → Contact | Who was touched |
| channel | call / email / visit / text / meeting | Communication type |
| direction | out / in | Outbound or inbound |
| subject | CharField | Brief description |
| summary | TextField | What happened, next steps |
| duration | PositiveInteger | Minutes (calls, meetings) |
| email_message_id | CharField | Cross-reference to email program |
| action | FK → Action | Action that triggered this touch |
| org_id + org_model | Polymorphic | Links to customer/vendor/manufacturer |
| project_id | BigInteger | Project context |
| logged_by | BigInteger | Contact ID of who recorded it |

### Auto-resolution

On save, `_resolve_org_from_contact()` populates `org_id` and `org_model` from the contact's customer/vendor/manufacturer FKs if not already set.

## Frontend

**File:** `React2025/src/pages/admin/DataBrowser.tsx`

### TouchBar Component

Renders at the top of the detail pane for these models: action, contact, customer, vendor, manufacturer, rep, employee, other_org.

**Buttons:**
- **☎ Call** — fires `tel:` URI (or `facetime:`/`facetime-audio:` per prefs), opens touch form
- **✉ Email** — fires `mailto:` URI, opens touch form
- **💬 Text** — fires `sms:` URI, opens touch form
- **📝 Log** — always visible, opens touch form without initiating communication

Call/Email/Text buttons only appear when the record has phone/email data. Log always appears.

### Touch Form Dialog

Opens on any touch button click. Contains:
- **Channel selector:** Call | Email | Visit | Text | Meeting (tab-style buttons)
- **Direction:** Outbound / Inbound radio
- **Subject:** pre-filled from parent record's action/subject field
- **Summary:** free text
- **Duration:** shown for Call and Meeting channels
- **Email Message ID:** shown for Email channel (paste from email program)

### Spawn Links

"Touches ↗" appears in the Related bar for: contact, action, customer, vendor. Opens a new databrowser window filtered to that record's touches.

## Touch Preferences (config.touch)

Stored in `contact.config.touch` on each user's contact record. Set by admins via the databrowser JSON envelope panel. Applied to all 5683 contacts on 2026-08-12.

**Pydantic schema:** `common/schemas/contact.py` → `TouchConfig`

```json
{
  "default_channel": "call",
  "default_direction": "out",
  "phone_action": "tel",
  "email_action": "mailto",
  "text_action": "sms",
  "auto_log": true
}
```

### phone_action Options

| Value | What happens |
|-------|-------------|
| `tel` | Apple Continuity — Mac tells iPhone to dial (default) |
| `facetime` | FaceTime video call |
| `facetime-audio` | FaceTime audio only |
| `log_only` | Just open the touch form, don't initiate |

### email_action Options

| Value | What happens |
|-------|-------------|
| `mailto` | Opens default mail client (default) |
| `log_only` | Just open the touch form |

### text_action Options

| Value | What happens |
|-------|-------------|
| `sms` | Opens Messages via SMS URI (default) |
| `log_only` | Just open the touch form |

### auto_log

When `true` (default), clicking Call/Email/Text fires the URI AND opens the touch form. The user completes the call/email, then fills in what happened.

## Mac Setup for tel: / mailto: / sms:

### Phone Calls (tel:)

**Mac:** System Settings → General → AirDrop & Continuity → enable "Allow Handoff between this Mac and your iCloud devices"

**iPhone:** Settings → Phone → Calls on Other Devices → toggle your Mac on

**Both devices:** same Apple ID, same WiFi network

**Skype conflict:** If Skype intercepts `tel:` links, fix by:
1. Open **FaceTime** → Settings (Cmd+,) → check "Calls from iPhone"
2. In the Skype intercept dialog, do NOT check "Always allow" — click Cancel
3. If Skype persists: right-click Skype.app → Get Info → uncheck "URL Types" or uninstall Skype
4. Alternative: set `phone_action` to `facetime-audio` in config.touch to bypass `tel:` entirely

### Email (mailto:)

The `mailto:` URI opens whatever app is registered as the default mail handler.

**To set Gmail as default (Chrome):**
1. Open Gmail in Chrome
2. Click the diamond/handler icon in the address bar (or go to `chrome://settings/handlers`)
3. Allow Gmail to handle mailto links

**To set Gmail as default (Safari/system-wide):**
1. Open Mail.app → Settings → General → Default email reader → select your Gmail client
2. Or use a helper app like "Choosy" to route mailto to Chrome/Gmail

### Text Messages (sms:)

**iPhone:** Settings → Messages → Text Message Forwarding → toggle your Mac on

The `sms:` URI opens Messages.app on Mac, which forwards through your iPhone.

## Double-Click Avatar

Double-clicking the user avatar or name in the TopBar opens the user's own contact record in the databrowser. This is where admins can edit their `config.touch` preferences.

**Implementation:** MacTopBar.tsx sets `sessionStorage.db_auto_select` with the user's contact ID, then navigates to `/contact`. The `useDataBrowser` hook reads this on record load and auto-selects.

## refs.parents — Canonical Relationship Graph

Touch is both a data point and a communications port. It sits at the intersection of action, contact, org, and transaction models. `refs.parents` captures the full communication graph:

```json
{
  "from": 8,            // contact_id of who initiated (outbound = logged_by user)
  "to": 10631,          // contact_id of who received (outbound = external contact)
  "contact": 10631,     // the external contact (always present)
  "customer": 5495,     // org context — which customer
  "vendor": null,       // org context — which vendor
  "manufacturer": null, // org context — which manufacturer
  "rep": null,          // org context — which rep
  "action": null        // triggering action (if any)
}
```

**from/to flip with direction:** Outbound = user→contact. Inbound = contact→user.

**Dedicated FK columns** (`contact`, `action`, `org_id+org_model`) are indexed copies of `refs.parents` entries — they exist for query speed. `refs.parents` is the canonical relationship.

**Rule:** Before adding new fields to Touch (or any model), use what CoreModel/BaseModel already provides. `refs.parents` for direct lineage, `refs.links` for loose associations, `metadata` for system data, `config` for application data.

## Architecture Notes

- Touch records save through wcapi `saveRecord('touch', {...})` — standard CRUD
- SaveWcapiView deep-merges refs — passing `refs: { parents }` merges into existing refs without overwriting keywords
- Auth endpoints (login + /me/) return `config` alongside `prefs` so the frontend has touch preferences at login time
- The frontend reads `user.config.touch` from the Redux auth state
- The Pydantic schema ensures validation — new contacts get defaults automatically via `TouchConfig` default factory
- TouchBar resolves contact phone/email via async `getRecord('contact', contactId)` for models that don't carry phone/email directly (e.g. action)

## Fields Added (2026-08-16/17/18)

| Field | Type | Purpose |
|-------|------|---------|
| `outcome` | CharField | connected / voicemail / no_answer / bounced / rescheduled |
| `impact` | PositiveSmallIntegerField 1-5 | Rep judgment of touch importance |
| `plan` | PositiveSmallIntegerField | Follow-up in N days — 0 = none |
| `dt_next` | BigIntegerField (indexed) | Auto-computed: dt_created + (plan × 86400000). Query: WHERE dt_next > 0 AND dt_next <= now() |
| `linkage_id` | BigIntegerField (indexed) | Ties touch to transaction graph (proposal→order→invoice) |
| `purpose` | CharField (from CoreModel) | Per-model selectlist from wc-model-touch Setting |

## UI Components (2026-08-17/18)

| Component | File | What |
|-----------|------|------|
| **TouchForm** | `React2025/src/pages/admin/TouchForm.tsx` | Unified dialog + inline modes. Channel tabs, direction, from/to ContactPickers with search, subject, summary, outcome, impact, plan, purpose. Save/Cancel at top. |
| **TouchBadge** | `React2025/src/pages/admin/TouchBadge.tsx` | `📞 N · Xd` — count + days until follow-up. Overdue=red, due soon=amber. Badge IS the interface. |
| **TouchBar** | `React2025/src/pages/admin/TouchBar.tsx` | Badge only — click opens TouchForm dialog. No Call/Email/Text buttons in the bar. |
| **ContactPicker** | Inside TouchForm.tsx | Type-ahead search, copy badges on phone/email, "missing" shown, ✎ edit opens contact window, ↻ refresh. Labels (From/To) are clickable buttons. |

## Agenda VIEW (2026-08-18)

Touch records appear in the `agenda` PostgreSQL VIEW alongside actions. DataBrowser at `/databrowser?model=agenda` shows both. See `readmes/topics/architecture/database-views.md`.

## Files Changed (2026-08-12)

| File | What |
|------|------|
| `apps/communications/models/touch.py` | Touch model |
| `apps/communications/migrations/0009_add_touch_model.py` | Migration |
| `apps/communications/migrations/0010_add_touch_org_fields.py` | Org fields migration |
| `common/schemas/contact.py` | TouchConfig Pydantic model |
| `apps/core/views/auth_views.py` | Added config to login + /me/ responses |
| `apps/core/views/wcapi.py` | Fixed 500 on model-specific GET route |
| `React2025/src/pages/admin/DataBrowser.tsx` | TouchBar, SPAWN_CONFIG, TOUCH_MODELS |
| `React2025/src/layout/MacTopBar.tsx` | Double-click avatar → contact record |
| `React2025/src/hooks/useDataBrowser.ts` | Auto-select from sessionStorage |
| `React2025/src/store/slices/authSlice.ts` | Added config to User interface |
| `React2025/src/api/auth.ts` | Map config in mapApiProfileToUser |
