# Email Thread Documents — Architecture

**Established:** 2026-07-26
**Applies to:** All WC3 installations with email integration

---

## Principle

Email threads are Documents, not comments. One Document per conversation thread. The thread is the unit of value. Messages append to `config.messages[]`. Searchable in databrowser. Alice manages the lifecycle.

---

## Document Record Structure

```json
{
  "ida": "email-thread-18abc123def",
  "name": "JPods Apple Collaboration — Adrian Perica",
  "model_name": "contact",
  "record_id": 10617,
  "category": "email_thread",
  "status": "active",
  "health_rating": 5,
  "config": {
    "thread_type": "email",
    "provider": "gmail",
    "provider_thread_id": "thread_18abc123def",
    "contact_ids": [10617, 6437],
    "last_message_dt": 1785100000000,
    "last_direction": "sent",
    "awaiting_reply": true,
    "follow_up_days": 7,
    "message_count": 3,
    "messages": [
      {
        "provider_msg_id": "msg_001abc",
        "subject": "JPods MOA + Apple collaboration",
        "from": "bill.james@jpods.com",
        "to": ["perica@apple.com"],
        "cc": ["brad@example.com"],
        "bcc": [],
        "dt": 1785100000000,
        "direction": "sent",
        "summary": "MOU at MOA, Physical Internet 3 layers, free tools, Cupertino crash data",
        "has_attachment": true,
        "attachment_names": ["CA_Apple_Crashes.png", "CA_Apple_Park_MM.png"]
      },
      {
        "provider_msg_id": "msg_002def",
        "subject": "Re: JPods MOA + Apple collaboration",
        "from": "perica@apple.com",
        "to": ["bill.james@jpods.com"],
        "cc": [],
        "bcc": [],
        "dt": 1785200000000,
        "direction": "received",
        "summary": "Interested in campus demo, scheduling call with facilities team",
        "has_attachment": false,
        "attachment_names": []
      }
    ]
  }
}
```

---

## Message Array Element — Field Reference

Every element in `config.messages[]` must have enough data for search, display, and decision-making without fetching the full email body.

| Field | Type | Purpose | Searchable |
|-------|------|---------|-----------|
| `provider_msg_id` | string | Gmail/Outlook message ID — link back to source | No |
| `subject` | string | Email subject line | Yes — databrowser text search |
| `from` | string | Sender email | Yes — find all emails from person |
| `to` | string[] | Recipients | Yes — find all emails to person |
| `cc` | string[] | CC recipients | Yes |
| `bcc` | string[] | BCC recipients | Internal only |
| `dt` | number | Epoch ms — when sent/received | Yes — sort, filter by date |
| `direction` | string | `sent` or `received` | Yes — filter outbound vs inbound |
| `summary` | string | 10-15 word summary of content | Yes — the key search field |
| `has_attachment` | boolean | Whether email has attachments | Yes — filter |
| `attachment_names` | string[] | File names of attachments | Yes — find by document name |

### Fields NOT stored (fetch from provider if needed):
- Full email body (too large, use provider API)
- HTML content
- Inline images
- Full headers

---

## Thread-Level Fields (config root)

| Field | Type | Purpose |
|-------|------|---------|
| `thread_type` | string | `email` (future: `sms`, `slack`, `call_log`) |
| `provider` | string | `gmail`, `outlook`, `protonmail` |
| `provider_thread_id` | string | Provider's thread ID for API calls |
| `contact_ids` | number[] | All WC3 contacts involved in this thread |
| `last_message_dt` | number | Epoch ms of most recent message |
| `last_direction` | string | `sent` or `received` — who spoke last |
| `awaiting_reply` | boolean | True if last message was sent (we're waiting) |
| `follow_up_days` | number | Days before Alice flags for follow-up |
| `message_count` | number | Total messages in thread |

---

## databrowser Display

### In db.list (Document model, filtered by category=email_thread):

| Column | Source | What user sees |
|--------|--------|---------------|
| Name | `name` | Thread subject / contact name |
| Last Message | `config.last_message_dt` | "Jul 26, 2026" |
| Direction | `config.last_direction` | "sent" or "received" |
| Messages | `config.message_count` | "3" |
| Awaiting | `config.awaiting_reply` | ✓ or — |
| Health | `health_rating` | Color indicator |
| Contact | `record_id` → Contact | "Adrian Perica" |

### In db.detail (right panel):

The `config.messages[]` array renders as a scrollable timeline:
```
→ Jul 26 2026  TO: perica@apple.com
  MOU at MOA, Physical Internet 3 layers, free tools, Cupertino crash data
  📎 CA_Apple_Crashes.png, CA_Apple_Park_MM.png

← Jul 27 2026  FROM: perica@apple.com
  Interested in campus demo, scheduling call with facilities team

→ Jul 28 2026  TO: perica@apple.com
  Confirmed. Available Tuesday 2PM Pacific. Will bring crash data for Cupertino.
```

Arrow direction: `→` sent, `←` received. Attachments shown with 📎. Summary is the display text. Click to open full email in Gmail.

---

## Contact Integration

### Contact.refs.links.email_threads[]

Each contact gets an array of Document IDs for their email threads:

```json
{
  "refs": {
    "links": {
      "email_threads": [
        {"document_id": 42, "name": "JPods Apple Collaboration", "last_dt": 1785200000000}
      ]
    }
  }
}
```

This lets the Contact detail page show "Email Threads (3)" as a tab/panel, linking to the Documents.

### Multi-contact threads

When an email has multiple recipients who are WC3 contacts:
- One Document record (not duplicated)
- `config.contact_ids = [10617, 6437]` — both Adrian and Tim Cook
- Both contacts get the Document ID in their `refs.links.email_threads[]`
- databrowser shows the thread on both contacts

---

## Alice's Role

### On sync (periodic or manual):
1. Read sent/received emails from Gmail Connection
2. Match `from/to/cc` addresses to Contact.email
3. If thread exists (by `provider_thread_id`), append new messages
4. If new thread, create Document record
5. Update `last_message_dt`, `last_direction`, `awaiting_reply`, `message_count`
6. Update Contact `refs.links.email_threads[]`
7. Generate summary using Tier 2 LLM (or Tier 1 if subject line is sufficient)

### Health rating:
- **5** — Active thread, recent exchange
- **4** — Sent, awaiting reply, within follow_up_days
- **3** — Awaiting reply, past follow_up_days (Alice flags)
- **2** — No activity 30+ days
- **1** — Bounced or failed delivery
- **0** — Thread closed/resolved

### Coaching:
- "You sent Adrian an email 7 days ago. No reply. Follow up?"
- "This thread has 12 messages over 3 months. Consider scheduling a call."
- "3 threads with Apple contacts are awaiting reply."

---

## Connection Model

```json
{
  "ida": "gmail-bill",
  "connection_type": "email_provider",
  "provider": "gmail",
  "config": {
    "email": "bill.james@jpods.com",
    "oauth_token": "...",
    "sync_frequency": "hourly",
    "sync_direction": "both",
    "last_sync_dt": 1785200000000,
    "sync_labels": ["SENT", "INBOX"],
    "exclude_labels": ["SPAM", "PROMOTIONS"],
    "auto_summary": true,
    "summary_tier": 2
  }
}
```

---

## Future: Beyond Email

The same Document structure works for:

| Channel | thread_type | Provider |
|---------|------------|----------|
| Email | `email` | gmail, outlook |
| SMS/Text | `sms` | twilio, google_voice |
| Slack | `slack` | slack_api |
| Call log | `call` | phone_system |
| LinkedIn message | `linkedin` | linkedin_api |
| WhatsApp | `whatsapp` | whatsapp_business |

Same array, same fields, same databrowser display. Alice tracks all channels on the same contact timeline.

---

## Relates To

- `readmes/topics/architecture/pending-flow-picture.md` — communications as flow records
- `readmes/topics/architecture/campaign-reseller-collaboration.md` — Connection/Bundle sync
- `readmes/21-sync-integration.md` — sync model
- Action #31058 — Gmail integration build
