# QA System — Wisdom of the Many + Retrospection
**Status:** Design complete, QAResult model needs building | **Source:** Bill 2026-07-04

---

## Why QA Matters

QA isn't forms. It's the mechanism for:
- **Wisdom of the Many** — aggregated QA across companies reveals patterns no single company can see
- **Retrospection** — QA results measured against previous answers = the gap where real lessons are
- **Preemption** — non-critical defects aggregated by ID reveal batch/vendor problems BEFORE failure
- **Small-Stings** — customers assess fines for unresolved problems; JPods pays customers for retrospections

---

## Architecture

### Questions (Setting records)

```
Setting (purpose='qa_questions', parent_model='item' or 'serial' or 'contact')
  config: {
    questions: [
      {
        unique_id: "Q001",              // stable within company
        uuid: "a1b2c3...",             // stable across companies (for WCHQ aggregation)
        text: "Is the flue liner intact?",
        type: "select",                 // select | text | number | boolean | photo
        required: true,
        answer_set_id: "AS001",         // points to answer Setting
        sequence: 10
      },
      ...
    ]
  }
```

### Answers (Setting records)

```
Setting (purpose='qa_answers', name='AS001')
  config: {
    answers: [
      {
        unique_id: "A001",
        uuid: "d4e5f6...",
        text: "Yes, intact",
        value: "intact",
        is_default: true               // likely answer (90% case)
      },
      {
        unique_id: "A002",
        uuid: "g7h8i9...",
        text: "No, damaged",
        value: "damaged",
        severity: "critical"
      },
      ...
    ]
  }
```

### QAResult (NEW MODEL — needs building)

```
QAResult
  ├── parent_model         → what this QA is about: 'serial', 'item', 'contact', 'invoice', etc.
  ├── parent_id            → FK to the specific record
  ├── question_set_id      → which Setting (qa_questions) was used
  ├── inspector_id         → who performed the inspection (Contact FK)
  ├── dt_inspected         → when
  ├── results              → JSON: [{question_unique_id, answer_unique_id, value, freeform_text, photo_doc_id}]
  ├── summary              → text: inspector's overall assessment
  ├── severity             → highest severity found: none | minor | major | critical
  ├── refs.links           → {serial_id, item_id, customer_id, invoice_id, workorder_id}
  └── metadata             → {question_set_uuid, answer_uuids[], dt_reported_to_wchq}
```

---

## Use Cases

### 1. Fireplace Installation Inspection

```
Inspector arrives at site
  → opens QA for 'installation_inspection' question set
  → answers: flue liner? Yes. Clearance? 3 inches (below code). Gas line? Passed.
  → QAResult created with parent_model='contact', parent_id=customer_id
  → severity='major' (clearance below code)
  → Action created: "Clearance issue at Smith residence — requires remediation"
```

Aggregation: across 500 inspections, "clearance below code" appears in 12%. That's an industry signal — WCHQ shares the pattern (anonymized): "12% of installations in the Midwest have clearance issues."

### 2. Serialized Item Inspection

```
Technician inspects serial #WIL-2026-0001
  → opens QA for 'annual_service' question set
  → answers defined questions + adds freeform note: "slight vibration at high RPM"
  → QAResult created with parent_model='serial', parent_id=serial.id
  → severity='minor'
```

Over 50 inspections of the same model, "slight vibration" appears 8 times — all from the same production batch. The unique_id on that answer aggregates the signal. Before any failure, the pattern is visible.

### 3. Vendor Quality Tracking

```
QAResults filtered by refs.links.vendor_id
  → vendor A: 2% defect rate across 200 inspections
  → vendor B: 8% defect rate across 150 inspections
  → Alice flags: "Vendor B defect rate 4x vendor A for the same product"
```

---

## ID Strategy

| ID | Scope | Purpose |
|---|---|---|
| `unique_id` | Within one company | Stable reference for local aggregation and reporting |
| `uuid` | Across all companies | WCHQ aggregation — same question in different companies carries the same uuid |

Questions evolve within a company (unique_id stays, text changes). Across companies, the uuid lets WCHQ know "this is the same question being asked everywhere."

---

## WCHQ Integration (sovereignty)

Same permission model as Alice coaching:
- `none` — QA data stays local
- `aggregate_only` — share answer patterns (no company identity)
- `full` — share with company context

WCHQ aggregates: "Question uuid X answered 'damaged' in 12% of inspections across the network." That's the Wisdom of the Many — no single company sees it, the network does.

---

## Retrospection Loop

```
Inspection 1: QAResult {Q001: intact, Q002: 3 inches, Q003: passed}
Inspection 2: QAResult {Q001: intact, Q002: 4 inches, Q003: passed}
                                        ↑ improved from 3 to 4
Gap analysis: Q002 improved — remediation worked. Grade: B+.
```

QA results compared against previous results for the same parent = the retrospection measurement. The gap is where the learning is.

---

## What Needs Building

1. **QAResult model** — as described above
2. **QA service** — create_qa_result, list_results_for_parent, aggregate_by_question
3. **DataBrowser spawn link** — any record → [Q&A ↗] opens QAResults for that record
4. **API endpoints** — CRUD for QAResults
5. **Alice integration** — pattern detection on aggregated answers, severity escalation
6. **WCHQ export** — anonymized QA patterns (with permission)

---

## Files (current + planned)

| File | Status | Purpose |
|------|--------|---------|
| `apps/docs/models/question_answer.py` | Exists | Basic QuestionAnswer model (needs QAResult extension) |
| `apps/core/models/setting.py` | Exists | Stores qa_questions and qa_answers |
| `apps/docs/services/qa_services.py` | Needs building | QA operations |
| `apps/docs/views/qa_views.py` | Needs building | API endpoints |
