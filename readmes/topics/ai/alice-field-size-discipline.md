# Alice — Field Size Discipline

## The Principle

No large data lives inline in JSON fields. Data above the inline threshold
belongs in a Document record, linked by ID. This keeps queries fast, sync
payloads small, and databases healthy.

## Thresholds (system defaults, overridable per Setting)

| Field | Max bytes | Purpose |
|-------|-----------|---------|
| metadata | 128,000 | System behavior — workflow, flags, history |
| prefs | 96,000 | User preferences — UI state, display |
| config | 64,000 | Application data — form fields, content |
| refs | 64,000 | Relationships — links, parents, pointers |
| actions | 32,000 | Task/action list — small, query-friendly |

Progressive telemetry fires at 30%, 60%, 75% of each limit.

## Alice's Role

### Observe
Alice watches `check_size` telemetry. Every time a field crosses a threshold,
she sees it. She tracks which users, which models, which fields.

### Coach
At 75%: "Your config on Action #4521 is 48KB. The specs section is 40KB.
Want me to move it to a Document?"

Repeat pattern: "You have 12 Actions over 50KB. All have large attachment
data inline. I can convert them to Document references."

### Enforce at the write boundary
Alice prevents oversized inline data — she does not coach after the fact.
Behavior that harms the user is not a preference to respect.

- **Documents over threshold** → stored as files, referenced by path
- **Images** → stored as files, always. Thumbnail in metadata if needed.
  No one searches the bit structure of an image.
- **Reports** → generated on demand, cached as files, path in the record.
  No one reads a 20-page document inline. Give them the path.

At save time, if content exceeds the inline threshold:
1. Create a Document record (or file) with the oversized content
2. Replace the inline data with a pointer: `{"_document_id": <id>, "_path": "<path>"}`
3. Log what she did in the record's metadata.history
4. This is automatic, not optional. The user gets the same data faster.

### Auto-offload (learned behavior)
For patterns Alice observes over time — same model type always producing
large content — she can preemptively route to Document at creation time
instead of waiting for the threshold to trigger. She learns which content
types are always large and skips the inline step entirely.

## For Sync

The sync system uses the same principle:
- Payload below 4KB: inline in bundle (encrypted)
- Payload above 4KB: encrypted to Document, path + key in bundle
- Receiver creates per-document Pending records
- Each document retries independently until received + verified

## Vector Store Entry

This document should be indexed into Alice's vector store so she can
reference it when making field-size decisions. Key concepts:
- inline threshold
- auto-offload to Document
- progressive telemetry
- repeat offender pattern
- coach before acting
