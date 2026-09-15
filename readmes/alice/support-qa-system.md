# Support Q&A System — How Users Get Help and How Alice Learns

**Built:** 2026-08-12
**Owner:** Alice (search, answer, escalate), Bill + Claude + Allie + Andi (answer at WCHQ)
**Applies to:** Every WC3 installation

---

## What This Is

A closed-loop help system where users ask questions, Alice searches for answers,
and unanswered questions flow to WCHQ (webclerk.com) where the whole team answers
them. Every answer becomes permanent — synced to all deployments via UUID.

Two complementary systems built from the same source material:

| System | Purpose | Who asks | Who answers |
|--------|---------|----------|-------------|
| **Support Q&A** | Help desk — user is stuck | User | Alice → Claude → Bill |
| **Quiz / Training** | Reinforcement — Alice tests learning | Alice | User |

---

## The Question Lifecycle

```
User types question in GetHelpDialog (Cmd+?)
    │
    ├── Step 1: SEARCH existing Q&A (311+ answers)
    │   └── search_support_qa — full-text search on Documents
    │       └── Match found? → show answer + user scores 1-5
    │
    ├── Step 2: No match → Alice tries from vector store (7,451 chunks)
    │   └── ask_alice — RAG search + Ollama
    │       └── Alice answers? → saved as Q&A Document (source=alice)
    │
    ├── Step 3: Alice can't → CREATE question + POST to WCHQ
    │   ├── ask_support_qa — creates draft Document
    │   └── post_qa_to_wchq — Bundle on wchq-conn-upstream
    │       └── Includes diagnostic context (see below)
    │
    ├── Step 4: Team answers at WCHQ
    │   ├── Bill, Claude, Allie, Andi, Alice all see the queue
    │   ├── answer_support_qa — sets status=published
    │   └── Answer syncs back to all deployments via UUID
    │
    └── Step 5: User scores the answer (1-5)
        ├── score_support_qa — running average
        ├── score_avg < 2.0 after 3+ ratings → needs_review
        └── Low-scored answers get re-queued for improvement
```

---

## Six Manage Actions

All via `POST /wcapi/manage/` with `{ action, params }`:

| Action | What it does | Who calls it |
|--------|-------------|-------------|
| `search_support_qa` | Full-text search existing Q&A | React GetHelpDialog |
| `ask_support_qa` | Create draft question Document | React when no match found |
| `answer_support_qa` | Answer a draft question (→ published) | Bill, Claude, Alice, Andi |
| `score_support_qa` | Rate an answer 1-5 | User after reading answer |
| `escalate_support_qa` | Mark as needs-Bill; auto-posts to WCHQ | Alice or Claude |
| `post_qa_to_wchq` | Post question + context to WCHQ via Bundle | Auto on escalate, or manual |

---

## Diagnostic Context — What Ships with Every Question

When a question posts to WCHQ, `collectSupportContext()` (React) gathers
operational context so the team can understand WHERE the user was and WHAT
was happening. No screenshots. No user data. Just operational signal.

| Field | What it captures | Example |
|-------|-----------------|---------|
| `screen` | URL path where user was | `/db/invoice` |
| `model` | Model being viewed | `invoice` |
| `field` | Field in focus | `total` |
| `recent_nav` | Last 5 pages visited | `["14:32 /db/order", "14:33 /db/invoice"]` |
| `recent_actions` | Last 5 manage actions called | `["recalculate_totals", "apply_line_pricing"]` |
| `recent_errors` | Last 3 console errors | `["TypeError: Cannot read 'lines'"]` |
| `recent_console` | Last 10 console entries (log+warn+error) | `["[log] Fetched 42 invoices", "[warn] Slow query"]` |
| `memory_mb` | Browser heap used | `187` |
| `viewport` | Browser window size | `{ width: 1440, height: 900 }` |
| `user_agent` | Browser/platform | `Chrome/126 macOS` |
| `user_role` | Contact role | `staff` |
| `alice_hints` | Alice hints currently visible | `["3 invoices past due > 90 days"]` |
| `uptime_min` | Minutes since app boot | `47` |
| `pasted_element` | HTML element user pasted in GetHelp | `<div data-wc="db-detail-pane"...` |

### Why This Matters

A question like "How do I apply a payment?" without context could mean anything.
The same question with `screen: /db/invoice, recent_actions: [recalculate_totals],
recent_errors: [TypeError]` tells the team: user was on an invoice, tried to
recalculate, got an error, and now they're confused about payments. The answer
can address the actual situation, not the generic question.

### Privacy

- No data values (no customer names, invoice amounts, product details)
- No screenshots or images
- No credentials or tokens
- Only operational context: where, what function, what error, how long
- User agent and viewport help reproduce browser-specific issues

---

## User Experience — Search Before Ask

The GetHelpDialog (Cmd+?) now follows a two-step flow:

1. **Type question → click Search** — searches 311+ existing Q&A answers
2. **Matches shown** with scores — user may find their answer without asking
3. **No match?** → "Ask WCHQ" button appears — submits with full context
4. **Answer arrives** via sync — user sees it next time they search

This prevents duplicate questions and builds the corpus. The same question
phrased 5 different ways will match the same answer via full-text search.
Long-tail questions that only one user asks may reveal a design gap — those
are the most valuable.

---

## The Q&A Corpus — ~300 Questions Seeded

`seed_qa_from_readmes.py` mined 33 WC3 readmes and produced:

- **311 free-form Q&A Documents** (config.purpose='support_qa')
- **292 structured quiz questions** across 32 quiz Documents

### Free-form Q&A (help desk)
Each `##` heading in a readme becomes a question. The section body is the answer.
Status: `published`. Searchable via full-text. User-scored.

```
Document:
  ida: QA-databrowser-overview
  name: "What is the databrowser?"
  body: "databrowser is the universal record browser. Any model, one interface..."
  config.purpose: support_qa
  config.score_avg: 0  (no ratings yet)
  status: published
```

### Structured Quiz (training)
Key concepts extracted from tables, bold definitions, and rules become
multiple-choice questions with correct answers + WHY.

```
Document:
  ida: QUIZ-pending-policy
  name: "Quiz: Pending Policy"
  config.purpose: qa-alice-system
  config.questions: [
    { id: 1,
      question: "What is the rule for financial balances?",
      answers: [
        { id: 1, text: "Pending always", correct: true },
        { id: 2, text: "Apply immediately", correct: false },
      ],
      why: "Any change affecting inventory or cash creates a Pending record" }
  ]
```

### How They Reinforce Each Other

- Q&A reveals what users don't understand → Alice creates quiz questions for those gaps
- Quiz results where users score poorly → Alice creates better Q&A explanations
- Both grow the corpus: every question asked, every quiz taken, every score given

---

## WCHQ Connection

Questions flow to WCHQ via the `wchq-conn-upstream` Connection (ida: `wchq-conn-upstream`,
type: `api`, purpose: `sync`). The Connection carries 5 content types:

1. `template_contribution` — user-submitted templates
2. `schema_feedback` — schema change requests
3. `layout_submission` — databrowser layouts
4. `alice_observation` — pattern detection findings
5. `support_qa` — **user questions + diagnostic context**

Each question creates a Bundle (direction: outbound) with the question text,
answer (if any), escalation chain, and full diagnostic context.

---

## Questions for Bill Pipeline

A dedicated queue for questions only Bill can answer:

- **Category:** `bill_question` on AliceObservation
- **Saved search:** "Questions for Bill" in databrowser (`/db/action`)
- **How it fills:** `escalate_support_qa` marks questions that Alice and Claude
  both tried to answer but couldn't
- **How Bill sees it:** databrowser filter, or Alice surfaces at session start

---

## Document Record Integration

Every Q&A answer is a Document record with:

| Field | Content |
|-------|---------|
| `name` | The question |
| `description` | Short summary of answer |
| `body` | Full answer (markdown) |
| `status` | `draft` (unanswered), `published` (answered), `needs_review` (low score) |
| `config.purpose` | `support_qa` |
| `config.source` | `readme_mining`, `alice`, `claude`, `bill`, `user` |
| `config.score_count` | Number of user ratings |
| `config.score_sum` | Sum of all ratings |
| `config.score_avg` | Running average (1-5) |
| `config.escalation_chain` | Who tried to answer and couldn't |
| `config.context` | Diagnostic context from when question was asked |
| `config.wchq_posted` | Whether posted to WCHQ |
| `refs.tags` | `['support', 'qa', '<domain>']` |

---

## Seed Commands

```bash
# Seed Q&A corpus from readmes (311 Q&A + 292 quiz questions)
python manage.py seed_qa_from_readmes

# Seed the support Q&A infrastructure (search presets, schema)
python manage.py seed_support_qa

# Seed Questions for Bill pipeline
python manage.py seed_bill_questions

# Seed Document records for readmes (body content + published status)
python manage.py seed_alice_docs
python manage.py seed_wc3_system_docs
python manage.py seed_wc3_commerce_docs
python manage.py seed_wc3_operations_docs
```

---

## Files

| File | What it does |
|------|-------------|
| `apps/ai_assistant/services/support_qa.py` | 6 functions: search, ask, answer, score, escalate, post_to_wchq |
| `apps/core/views/manage_view.py` | Dispatch table — 6 support_qa actions registered |
| `apps/core/management/commands/seed_qa_from_readmes.py` | Mine readmes → Q&A + Quiz Documents |
| `apps/core/management/commands/seed_support_qa.py` | Seed search presets and schema |
| `apps/core/management/commands/seed_bill_questions.py` | Seed bill_question pipeline |
| `apps/core/management/commands/_seed_docs_utils.py` | Shared: read git body, set published |
| `React2025/src/utils/supportContext.ts` | Collect diagnostic context in browser |
| `React2025/src/components/common/GetHelpDialog.tsx` | Search-first → Ask WCHQ with context |

---

## Training Videos Needed

| IDA | Video | Duration |
|-----|-------|----------|
| — | Support Q&A: user searches, finds answer, scores it | 2 min |
| — | Support Q&A: user asks new question, sees it post to WCHQ | 2 min |
| — | Alice quiz drill: user runs training quiz, sees score | 2 min |

`qq_movie_here_2026-08-12`
