# AiMessage — Unified Interaction Model

**Table:** `ai_message`
**Model:** `apps.ai_assistant.models.message.AiMessage`
**Registry:** `ai_message` (aliases: `ai_messages`, `message`)

## What it does

Every interaction between any two actors — user-to-AI, AI-to-user, AI-to-AI — is an AiMessage. One model for all inter-actor communication.

```
Bill types feedback about bill_to
    -> AiMessage(sender='bill', receiver='alice', kind='feedback')

Alice forwards to WCHQ
    -> AiMessage(sender='alice', receiver='wchq', kind='forward')

Allie sends pattern to Alice
    -> AiMessage(sender='allie', receiver='alice', kind='observation')
```

## Actors

Actors are identified by name, not FK. Agents aren't contacts.

| Actor | Type | Example messages |
|-------|------|-----------------|
| `bill`, `karen`, etc. | User | feedback, help_lookup, question, chat |
| `alice` | Commerce agent | answer, observation, directive |
| `allie` | Persistent intelligence | observation, directive |
| `noelle` | Network validator | observation |
| `natalie` | Router | observation |
| `nora` | Vehicle | observation |
| `sally` | Station processor | observation |
| `athena` | Security reviewer | directive (clearance decisions) |
| `wchq` | HQ instance | forward, answer |

When the sender is a user, `sender_contact_id` links to their Contact record.

## Message kinds

| Kind | Direction | What it is |
|------|-----------|-----------|
| `feedback` | user->ai | Tip, correction, change request |
| `help_lookup` | user->ai | Shift-for-Help query (frequency = confusion signal) |
| `chat` | both | Conversational exchange |
| `question` | both | Explicit question expecting an answer |
| `answer` | both | Response to a question |
| `observation` | ai->ai | Pattern detected by an agent |
| `directive` | ai->ai | Instruction from one agent to another |
| `forward` | ai->ai | Message forwarded to another instance |

## Data security

**Rule: commercial and personal data never leave the instance.**

Every message has a `classification`:

| Classification | Can leave? | Example |
|----------------|-----------|---------|
| `technical` | Yes (after Athena review) | "bill_to is a communications model" |
| `operational` | Athena reviews | "3 users looked up bill_to this week" |
| `commercial` | **Never** | Customer names, prices, order amounts |
| `personal` | **Never** | Contact info, email, phone, login data |

**Athena clearance gate:**

| Clearance | Meaning |
|-----------|---------|
| `local` | Not submitted for review — stays on this instance |
| `pending` | Submitted for Athena review |
| `cleared` | Safe to forward |
| `blocked` | Contains sensitive data — auto-set for commercial/personal |

```python
msg.can_forward()  # True only when: technical + cleared + scrubbed
msg.request_clearance()  # Sets to pending (or blocked if commercial/personal)
```

**Auto-enforcement in save():**
- `classification='commercial'` or `'personal'` -> `clearance='blocked'` automatically
- `kind='forward'` with `clearance='local'` -> `clearance='pending'` automatically

**PII scrubbing:** `scrubbed=True` after scrubbing has been applied. Forward requires scrubbed=True.

## Threading and forwarding

```
Original question (parent=None)
    -> Reply 1 (parent=original)
    -> Reply 2 (parent=original)
        -> Forward to WCHQ (forward_of=original, kind='forward')
```

- `parent` FK: threads conversations
- `forward_of` FK: tracks provenance when messages are forwarded
- `batch_id`: groups related messages (e.g., all messages from one help session)

## Sync

Messages flow through the Connection/Bundle infrastructure like Episodes:
- `source_instance` UUID identifies which WC3 instance created the message
- Only `technical` messages with `clearance='cleared'` and `scrubbed=True` can be bundled
- WCHQ harvests cleared messages from connected instances

## Admin console

**DataBrowser:** model=ai_message, filter by kind/sender/receiver/classification/clearance

**Key views for Alice's console:**
- Pending feedback: `kind=feedback, status=pending`
- Help frequency: `kind=help_lookup`, group by `subject`, count — high counts = confusion
- Pending clearance: `clearance=pending` — Athena's review queue
- Blocked messages: `clearance=blocked` — audit trail of what was stopped
- AI-AI traffic: sender and receiver both non-user — agent coordination visibility

## What replaced what

| Before | After |
|--------|-------|
| Document (purpose='help-alice') | AiMessage (kind='feedback') |
| alice_observation (event='help_lookup') | AiMessage (kind='help_lookup') |
| Conversation + Message (chat) | AiMessage (kind='chat', threaded via parent) |
| manageAction('request_field_change') | AiMessage (kind='feedback') |
