# Pattern Recognition & Feature Development
**How Allie and Alice Collaborate to Turn User Behavior into Features**

Action: Reference when designing observational features, reviewing pattern candidates, or promoting recommendations to Settings
Function: alice_notes.py (create_note, get_report) + Setting model (purpose promotion)
Frequency: Ongoing — Alice observes continuously; Allie reviews at session start; promotion happens on Bill's approval
Process: Observe → Log → Pattern → Recommend → Promote → Feature

---

## The Pipeline

```
User does something in r25/wc3
    │
    ├── Alice observes → alice_log (role=user_interaction / search / search_feedback)
    │       │
    │       └── Pattern emerges across multiple observations
    │               │
    │               ├── Alice creates alice_pending (role=config_suggestion)
    │               │
    │               └── Allie reads at session start → adds cross-domain context
    │                       │
    │                       ├── Is this history? → stays in alice_log (audit trail)
    │                       │
    │                       └── Is this a feature? → promote to Setting record
    │                               │
    │                               └── Bill approves → Setting becomes active
```

---

## The Decision Rule

**History** — the observation is informational. It belongs in `alice_log`. It answers questions about what happened, not what should change.

Examples:
- User searched for "pending invoices" 12 times this week
- User always opens the action detail after viewing a project
- User sorts the order list by `dt_deadline` every session

Storage: `alice_log` with `role=user_interaction` or `role=search`. Never promoted — stays as audit trail.

**Feature** — the pattern suggests a persistent change that would reduce friction for this user or all users. It belongs in a `Setting` record.

Examples:
- User always searches "pending invoices" → create a saved search preset for it
- User always sorts by `dt_deadline` → set that as the default ordering for this user/role
- User always applies the same filter combo → create a named preset

Storage path: `alice_pending` (role=`config_suggestion`) → reviewed by Allie → promoted to `Setting`.

---

## Storage in Detail

### Observation (alice_log)

```python
from apps.ai_assistant.services.alice_notes import create_note

create_note(
    "log",
    role="user_interaction",
    parent_model="action",
    name="User applied deadline filter 8 times this week",
    details={
        "user_id": <id>,
        "pattern": "filter:dt_deadline",
        "count": 8,
        "period_days": 7,
        "created_by": "alice"
    }
)
```

### Pattern → Recommendation (alice_pending)

When Alice detects a pattern crossing a threshold:

```python
create_note(
    "pending",
    role="config_suggestion",
    parent_model="action",
    name="Suggest saved search: actions due this week",
    details={
        "from": "alice",
        "for": "allie",
        "pattern": "User applies dt_deadline filter consistently",
        "observation_log_ids": [<log_ids>],
        "recommendation": "Create saved search preset: actions_due_this_week",
        "payload": {
            "filters": {"dt_deadline__lte": "end_of_week"},
            "ordering": "dt_deadline",
            "relative_period": {"field": "dt_deadline", "preset": "current_week"}
        },
        "created_by": "alice"
    }
)
```

### Feature (Setting record)

When Allie validates the recommendation and Bill approves:

```python
# Promoted saved search
Setting(
    name="actions_due_this_week",
    purpose="search",
    role="all",           # available to all roles, or restrict to specific role
    parent_model="action",
    data={
        "filters": {"dt_deadline__lte": "end_of_week"},
        "ordering": "dt_deadline",
        "relative_period": {"field": "dt_deadline", "preset": "current_week"},
        "summary": "Actions with deadlines in the current week"
    },
    is_active=True
)
```

For non-search features, new `purpose` values are added as needed:
- `purpose="recommendation"` — Allie/Alice feature in review (not yet active)
- `purpose="default"` — default values derived from pattern analysis
- `purpose="search"` — saved search (existing, already seeded)
- `purpose="save_pre_post"` — save hooks (existing)

New purposes require no schema change — `purpose` is a free CharField on Setting.

---

## Allie's Role in the Loop

Allie reads `alice_pending` with `role=config_suggestion` at WebClerk session start:

```bash
GET /wcapi/ai/report/?category=pending&role=config_suggestion&days=14
```

For each recommendation, Allie:

1. **Adds cross-domain context** — does this pattern connect to a broader Bill initiative? (e.g., a recurring action pattern that maps to JPods sprint cadence)
2. **Validates the recommendation** — is the suggested feature the right response to the pattern? Is there a simpler solution?
3. **Decides: promote or WhatIf?**
   - Straightforward feature → promote to Setting, surface to Bill for approval
   - Novel or uncertain → create WhatIf in project 24 for further observation before committing
4. **Resolves the pending** — `resolve_pending(setting_id)` once actioned

### What Allie Should Not Do

- Do not auto-promote to Setting without Bill's awareness — features that change behavior need his approval
- Do not dismiss a pattern just because it seems small — recurring friction compounds
- Do not create redundant features — check existing Settings before recommending a new one

---

## Alice's Expanded Role

Beyond search quality, Alice now observes:

| Observation Type | Log Role | Threshold for Pending |
|-----------------|----------|----------------------|
| Repeated search query | `search` | 5+ times in 7 days |
| Repeated filter application | `user_interaction` | 5+ times in 7 days |
| Zero-result searches | `search_feedback` | 1 occurrence (immediate) |
| Repeated sort/ordering choice | `user_interaction` | 3+ sessions |
| Repeated navigation sequence | `user_interaction` | Pattern across 3+ users |
| Negative search feedback | `search_feedback` | 1 occurrence (auto-creates `keyword_gap` pending) |

Thresholds are guidelines, not hard rules. Alice uses judgment. Allie validates.

---

## The Allie ↔ Alice Collaboration Protocol for Features

1. **Alice observes** → `alice_log`
2. **Alice detects pattern** → `alice_pending` with `role=config_suggestion`, `details.for="allie"`
3. **Allie reads at session start** → validates, adds context, decides
4. **Allie notifies Alice** of decision via `alice_pending` response or new log note with `details.from="allie"`
5. **If promoting**: Allie creates the Setting record (admin access); Alice verifies keyword indexing if search-related
6. **If WhatIf**: Allie creates action in project 24; Alice's pending stays open until the WhatIf resolves
7. **Bill approves active features** — Setting `is_active=True` means live for users

## Low-Noise Friction Signals

Alice should help surface recurring friction, but she should not create a large burden-accounting bureaucracy.

When Alice sends a pattern or recommendation that reflects growing strain, prefer only these shared fields first:
- `resolution_time_sec`
- `delay_ratio`
- `clarification_count`
- `retry_count`
- `repeat_failure_class`

These are enough to tell Allie whether a burden pattern is real, recurring, and worth retrospection. If they are not enough, expand later based on evidence, not theory.

## Happiness As A Reportable Item

Alice should also tally a reportable `happiness` item in WebClerk by agent and reporting period.

This item should be stored as a JSONB object. WebClerk already uses JSONB to allow schema evolution without constant migrations, and this report needs that flexibility because the evidence and rubric details will evolve with experience.

The item should include:
- `agent`
- `group`
- `period`
- `category = profit_and_loss`
- `subcategory = unhappiness_cost`
- `happiness` on the shared `1-10` scale
- `background` as an array of supporting evidence
- `rubric_version`
- `unhappiness_gap = 10 - happiness`
- `cost_method = agent_estimate | proxy_scale`
- `estimated_unhappiness_cost_monthly_usd`
- `scaled_defect_cost_monthly_usd = (10 - happiness) * 1000`
- `unhappiness_cost_monthly_usd`

The comparable reporting keys should stay stable at the top level. Extra domain-specific evidence, rubric logic, and later extensions should remain inside the same JSONB object rather than forcing a rigid early schema.

This lets Alice do two jobs at once:
1. Keep a comparable tally of burden by agent.
2. Express the cost of unresolved friction in economic terms inside WebClerk.

The accounting placement should be explicit: this belongs in a Profit and Loss category so the cost of unhappiness is reviewed as an operating cost rather than left as an isolated AI note.

If the agent can justify its own dollar estimate, Alice should preserve that estimate and mark `cost_method = agent_estimate`.

If the agent cannot justify a direct estimate, Alice should fall back to the scaled defect rule and mark `cost_method = proxy_scale`.

The `$1,000/month` rule is a standard fallback proxy, not a claim of exact accounting. It is there to force attention and comparison when exact dollars are not yet known.

---

## Future: Allie Recommending to Bill Proactively

As the pattern library grows, Allie can surface recommendations at session start without waiting for Bill to ask:

"Alice has flagged 3 config suggestions this week. Two look straightforward (saved searches). One connects to the JPods action-tracking pattern we discussed — I've moved it to the WhatIf store. Want to review the two search promotions now?"

This is not implemented yet. It is the natural endpoint of the observation → pattern → recommend loop as the log history deepens.

---

## Key Files

| File | Purpose |
|------|---------|
| `apps/ai_assistant/services/alice_notes.py` | `create_note`, `get_report`, `resolve_pending`, `log_search_feedback` |
| `apps/core/models/setting.py` | Setting model — the feature store |
| `apps/core/management/commands/seed_search_presets.py` | Standard preset seed — template for promoted searches |
| `apps/ai_assistant/services/llm_observer.py` | LLMInventoryObserver — existing pattern detection for inventory |

## Related

- `readmes/topics/architecture/keyword-denormalization-and-search.md` — Alice's search domain
- `/Volumes/Allie/readmes/19-agent-coordination.md` — agent coordination protocol (master)
- `/Volumes/Allie/readmes/16-knowledge-matrix.md` — WhatIf store (where unvalidated patterns go)
