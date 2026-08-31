# Alice Escalation Protocol — Three-Tier Chain

> **Last updated**: 2026-08-31
> **Owner**: Alice + Claude Code
> **Applies to**: All Alice AI interactions
> **Implementation**: `apps/ai_assistant/services/escalation.py`

---

## The Architecture

Three tiers. Each tier is a better answer at higher cost. Alice always
tries locally first. No individual installation ever needs a Claude API key.

| Tier | Where it runs | Cost | Trigger |
|------|--------------|------|---------|
| 1. Alice local | Installation (Ollama RAG) | Free | Always first |
| 2. Alice at WCHQ | WCHQ server (larger model) | $4/person/mo (standard) | Confidence < 40% |
| 3. Alice+Claude at WCHQ | WCHQ calls Claude | $9/person/mo (professional) | WCHQ Alice also low confidence |

WCHQ manages the Claude API key centrally. Users just subscribe.
Individual installations never handle API keys — that burden kills adoption.

---

## Confidence Scoring

Every answer is scored before deciding whether to escalate.

**Formula**: `score = (context_quality × 0.60) + (answer_quality × 0.40)`

**Context quality** (from RAG retrieval):
- Vector distance of best match (closer = better)
- Number of relevant chunks returned

**Answer quality** (from content analysis):
- Length (very short = suspicious)
- Hedging phrases detected ("I'm not sure", "I don't know", etc.)

**Threshold**: Score below **0.40** → escalate to WCHQ.

---

## PII Scrubbing

All text is scrubbed before leaving the installation:
- Email addresses → `<email>`
- Phone numbers → `<phone>`
- SSN patterns → `<ssn>`
- Credit card numbers → `<card>`
- Street addresses → `<address>`
- Names after prefixes (Customer, Mr., Dr.) → `<name>`

Implementation: `apps/ai_assistant/services/pii_scrub.py`

---

## Endpoints

### Downstream (calling upstream)
The installation's `escalation.py` calls these on the upstream WC3:

- `POST /wcapi/alice/ask/` — WCHQ Alice answers (standard tier)
- `POST /wcapi/alice/ask-claude/` — WCHQ Alice + Claude (professional tier)

Auth: `Authorization: Athena <token>`

### Upstream (serving downstream)
Any WC3 can serve these — WCHQ is just a WC3 instance:

- `AliceAskUpstreamView` — runs question through local RAG, no re-escalation
- `AliceAskClaudeUpstreamView` — local RAG + Claude fallback (key in `Setting(purpose='wchq_claude_key')`)

---

## What Alice Can Do Locally (8B/20B)

- Answer questions about WC3 features, fields, and workflows
- Draft simple markdown templates with field tokens
- Suggest field paths for a given model
- Review template syntax and fix formatting
- Create Action records, Document records, observations
- Run quiz questions for training
- Flag data quality issues
- Basic calculations and lookups

---

## When Alice Escalates

Alice escalates automatically when confidence is low. She also recognizes
capability boundaries and escalates for:

- **Code changes** — schema, migrations, new fields
- **Complex logic** — multi-step conditionals, cross-model joins
- **Architecture decisions** — new model vs. extend metadata
- **Bug diagnosis** — requires reading multiple source files
- **Security concerns** — permissions, RBAC, credentials

---

## Logging

Every escalation is logged as `AliceObservation(category='escalation')`:
- Confidence score at time of escalation
- Tier used (alice_local, wchq_alice, wchq_claude)
- Reason (low_confidence, capability_boundary)
- Question (PII-scrubbed)

---

## Multi-Location Pattern

The same escalation pipe serves multi-location companies:

```
Location A (WC3) ──→ HQ (WC3) ←── Location B (WC3)
```

HQ is upstream for both. Same Connection, same Bundle infrastructure.
The pipe also carries GL journal bundles for accounting consolidation
(see `apps/sync/services/gl_journal_bundle.py`).

**GL journals are never loaded into HQ's GL tables.** They arrive as
Bundle records and are curated for accounting program handoff
(QuickBooks, Xero).

---

## Seed Records

| Model | ida / purpose | What it configures |
|-------|--------------|-------------------|
| Setting | `wc:escalation` | Confidence thresholds, tier definitions, privacy rules |
| Setting | `wc:subscription` | Subscription tier, pricing, feature gates |
| Connection | `conn-ai-escalation` | Full escalation chain config with endpoints and rules |
| Connection | `conn-upstream-hq` | Multi-location upstream with GL journal and escalation |

---

## What Alice Should Never Do

- **Pretend** she can handle something she can't
- **Lose context** — the escalation must carry enough detail to act
- **Send raw business data** upstream — questions only, PII scrubbed
- **Require API keys** from individual users

---

*Established 2026-08-05. Reworked 2026-08-31: three-tier chain, WCHQ
manages Claude centrally, per-person pricing, PII scrubbing, multi-location
GL journal consolidation.*
