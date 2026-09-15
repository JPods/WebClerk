# Flag System and Ouch List — Operational Risk Architecture

**Established:** 2026-07-17

---

## Two Tools, Two Problems

| | **Flag System** | **Ouch List** |
|---|----------------|---------------|
| **What** | Operational events happening now | Risks we know about but consciously defer |
| **Colors** | 🔴 Red / 🟠 Orange / 🟡 Yellow | None — no urgency until materialized |
| **Urgency** | Immediate → planned → investigate | None — consciously accepted |
| **Required fields** | Agent, data, Action + human owner | Why long-tail, why not addressing, what proves us wrong |
| **When it moves** | Flag → Action → resolution → TFTS | Ouch list risk materializes → becomes a flag |
| **Learning** | "Why didn't we catch this earlier?" | "What did we misjudge — probability, severity, or timeline?" |

These are not the same thing. Confusing them weakens both.

---

## Flag System — Operational Events

Full detail: `readmes/agents/agent-flags.md`

### The Three Flags

| Flag | Meaning | Urgency | What Happens |
|------|---------|---------|-------------|
| 🔴 **RED** | **Stop everything** | Immediate — all stop | JPods: no new trips, existing trips exit guideway ASAP. WebClerk: all transactions halt. Chaos and unhappiness. |
| 🟠 **ORANGE** | **Known problem, fix by date** | Planned deadline | Understood problem, scheduled fix. If deadline missed → escalates to red. |
| 🟡 **YELLOW** | **Do not understand** | Investigate | Agent sees anomaly, can't diagnose. Honest signal: "I need help understanding this." |

### Red Is Nuclear

A red flag stops everything. Not part of everything. Everything.

There will be chaos and unhappiness. That pain is the point. It forces
the team to think ahead — to catch problems as oranges and yellows before
they become reds.

> *"Suffer now, so our children do not suffer later."*

**The goal is zero red flags.** Not because problems don't exist — because
problems are caught as yellows, diagnosed into oranges, and fixed before
they become reds. A mature system has many oranges, some yellows, and
no reds.

### Who Does What

```
Nora/Sally/Alice raises flag (any color)
    ↓
Noelle manages (physical) / Alice manages (commerce)
    ↓
Andi observes 24/7 — checks baselines, cross-correlates
    ↓
Allie adds context — Bill's recent work, history, design changes
    ↓
Alice creates Action record with human owner assigned
```

**Hard rule:** Every flag — red, orange, or yellow — results in an Action
record created by Alice in WC3 with a human responsible person assigned.
No orphaned flags. No Actions without owners.

### Flag Raisers

| Agent | Domain | What They Flag |
|-------|--------|---------------|
| **Nora** | Vehicle | Motor current, ToF, encoders, trip completion, hardware faults |
| **Sally** | Station | Slot occupancy, dwell times, queue depth, conveyor events |
| **Alice** | Commerce | Transaction integrity, payment failures, API health, security |

### Escalation Rules

| Condition | What Happens |
|-----------|-------------|
| 🟡 Persists > 24 hours | Alice creates Action |
| 🟡 Multiple yellows correlate | Noelle raises 🔴 red |
| 🟡 Diagnosed | Convert to 🟠 orange with fix_by date |
| 🟠 Deadline missed | Escalates to 🔴 red |
| 🟠 Condition worsens | Escalates to 🔴 red |
| 🔴 Unresolved > 4 hours | Re-notify, Action marked overdue |
| 🔴 Repeats 3x same root cause | Systemic flag → design review |

### Every Red Flag Gets a Retrospection

Five questions after every red:

1. What orange should have been raised, and when?
2. What yellow was visible but not investigated?
3. What baseline should Andi have been tracking?
4. What maintenance task should have been scheduled?
5. What design change would prevent this class of failure?

The red flag was the tuition. The lesson is what we paid for.

---

## Ouch List — Deferred Risks

Full detail: `readmes/system/ouch-list.md`

The ouch list is a register of risks we think we know about but are
intentionally not addressing at this time. It is not an alerting system.
It has no colors.

### Required Fields Per Entry

Every ouch list entry must include:

1. **What the risk is** — specific enough to recognize if it materializes
2. **Why we think it's long-tail** — our reasoning for deferring
3. **Why we are not addressing it** — resource constraint, design immaturity,
   insufficient data, other priorities
4. **What would prove us wrong** — the observable event that moves this
   from "accepted risk" to "active problem"

### When an Ouch List Risk Materializes

It becomes a flag. The ouch list entry's "why we think it's long-tail"
reasoning becomes the retrospection lesson:

- Was our probability estimate wrong?
- Was our severity estimate wrong?
- Was our timeline estimate wrong?
- What information would have changed our assessment?

This is how the team calibrates its risk judgment over time. The ouch
list is not a place to forget risks — it is a place to document our
reasoning so we can learn from being wrong.

### Example Entry

```
| C-01 | Gradual guideway settlement in soft soils |
| Why long-tail | Years to manifest; pre-deployment geotech survey catches
                  worst sites; settlement monitoring is standard civil practice |
| Why not addressing | No physical deployment yet; will address in
                       site-specific engineering phase |
| What proves us wrong | Nora reports increasing encoder slip on the same
                         segment over months — geometry is shifting |
```

---

## How They Connect

```
Ouch List entry exists: "M-03 Drive mechanism wear at high cycle"
    ↓ risk accepted, reasoning documented
    ↓
    ... months/years pass ...
    ↓
Andi detects: Nora motor current drifting up on pod_03
    ↓ 🟡 yellow flag — don't understand yet
    ↓
Investigated: bearing wear from high cycle count
    ↓ 🟠 orange flag — replace bearing by Friday
    ↓
Retrospection: M-03 materialized. Our reasoning said "not yet
characterized" — now we have data. Update M-03 with cycle count
thresholds. Add preventive maintenance schedule to oranges before
they happen again.
    ↓
Learning: M-03 is no longer long-tail. It has a known cycle count.
Schedule bearing replacement as orange at 15,000 cycles. What was
an unknown risk is now a maintenance schedule.
```

The ouch list feeds the flag system. The flag system feeds retrospection.
Retrospection feeds the ouch list (revised risk assessments) and the
maintenance schedule (new oranges). The loop closes.

---

## Related Files

| File | What |
|------|------|
| `readmes/agents/agent-flags.md` | Full flag system — data structures, MQTT topics, escalation rules |
| `readmes/system/ouch-list.md` | Full risk register — all domains |
| `readmes/agents/andi.md` | Andi's monitoring responsibilities — baselines, cross-correlation |
| `readmes/agents/noelle.md` | Noelle's flag management responsibility |
| `readmes/agents/README.md` | Agent team index with cross-agent protocols |
