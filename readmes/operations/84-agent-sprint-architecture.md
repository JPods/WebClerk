# Agent Sprint Architecture

**Last updated:** 2026-08-28
**Purpose:** Weekly agent sprint cycle — how agents observe, propose, escalate, execute, and measure.

---

## The Principle

The weekly sprint is the organizational hippocampus. Agents observe continuously, HC consolidates nightly, but Actions only surface at sprint review. The settle time between observation and action is the feature — it lets patterns stabilize before the team acts on them.

Agents are first-class participants. They create Actions, move cards, execute approved work, and measure outcomes. Humans approve and redirect. Once approved, agents own execution.

---

## The Cycle

```
Monday:    Sprint created automatically. Agents carry forward open items.
Tue-Wed:   Agents observe. HC consolidates nightly. Patterns accumulate.
Wednesday: Sprint review — proposed Actions surfaced. Humans approve/reject.
Thu-Fri:   Agents execute approved Actions. Claude escalation for complex work.
Friday:    Librarian measures outcomes. Sprint retrospection.
```

---

## Three-Capacity Architecture

Every agent has three voices:

| Capacity | Temp | Role | Sprint function |
|----------|------|------|-----------------|
| **ops** | 0.1 | Enforce standards, validate, flag violations | Creates Actions when violations detected |
| **hc** | 0.4 | Learn patterns, propose deviations | Creates Actions when patterns exceed confidence threshold |
| **lib** | 0.2 | Record intent, measure outcomes, grade A-F | Measures every completed Action against its stated intent |

---

## Agent Contacts (WC3)

| Agent | Email | Contact ID | Domain |
|-------|-------|-----------|--------|
| Alice | alice@jpods.com | 10628 | Commerce, pricing, billing, data quality |
| Allie | allie@jpods.com | 10629 | Cross-domain synthesis, ecosystem coherence |
| Claude | claude@jpods.com | 10627 | External LLM escalation |
| Noelle | noelle@jpods.com | 10709 | Network validation, load balance, ezone |
| Natalie | natalie@jpods.com | 10710 | Routing, trip scheduling, dispatch |
| Nora | nora@jpods.com | 10711 | Vehicle telemetry, calibration, maintenance |
| Sally | sally@jpods.com | 10712 | Station occupancy, slots, dwell time |

---

## Action Status Flow

```
proposed → approved → active → complete → measured
                  ↘ rejected
```

| Status | Kanban | Who moves it | What happens |
|--------|--------|-------------|--------------|
| proposed | backlog | Agent HC creates it | Pattern above confidence threshold becomes an Action |
| approved | todo | Human approves at sprint review | Human validates the proposal |
| active | doing | Agent or sprint runner | Work begins — local execution or Claude escalation |
| complete | done | Agent after execution | Result stored in Action.action JSON |
| measured | done | Librarian capacity | Outcome graded against intent (A-F) |
| rejected | rejected | Human rejects at sprint review | Pattern dismissed — stays in HC for reconsideration |

---

## Claude Escalation via Connection

Local agents (gpt-oss:20b) have limited capacity. When an Action needs deeper analysis, the agent composes a prompt and stores it in the Action record. The prompt is sent to Claude via a Connection record.

| Field | What it carries |
|-------|----------------|
| Connection.config | Provider, model, endpoint, max_tokens, credentials path |
| Connection.rules | Rate limits, cost caps, allowed agents, approval thresholds |
| Action.action.claude_prompt | The prompt to send |
| Action.action.claude_response | The response received |
| Action.action.claude_usage | Token counts for cost tracking |
| Action.metadata.requires_claude | Boolean flag for sprint runner |

**Connection rules enforce sovereignty:** agents cannot call Claude without an Action record. The Connection carries the rules — rate limits, cost thresholds, which agents can use it. Above a cost threshold, human approval is required.

---

## Sprint Project (WC3)

Each sprint is a Project record:
- `category`: `agent_sprint`
- `name`: `Agent Sprint W35`
- `config`: agents list, status flow, review day, retrospection day
- `dt_start` / `dt_end`: Monday to Friday
- Actions linked by `project_name`

All sprint Projects aggregate into a Gantt view via `agent-sprint.py gantt`.

---

## Scripts

| Script | What it does |
|--------|-------------|
| `agent-sprint.py seed` | Create agent contacts + Claude API connection |
| `agent-sprint.py create-sprint` | Create this week's sprint project |
| `agent-sprint.py propose` | HC → Action: patterns above threshold become proposed Actions |
| `agent-sprint.py review` | Show all proposed Actions pending human approval |
| `agent-sprint.py approve <id>` | Human approves an Action |
| `agent-sprint.py reject <id>` | Human rejects an Action |
| `agent-sprint.py execute` | Agents execute approved Actions (local or flag for Claude) |
| `agent-sprint.py run-prompts` | Send Claude-flagged Actions to external LLM |
| `agent-sprint.py status` | Sprint status summary |
| `agent-sprint.py gantt` | Export sprint data for Gantt display |
| `agent-build.py` | Build agent capacity models from Modelfiles |
| `alice-hc-consolidate.py` | Nightly HC memory consolidation |

---

## Leftshoe Integration

At session start, leftshoe now includes a TEAM LEARNING section:
- Each agent's ops standards count and violations
- HC patterns proposed and latest hypothesis
- Librarian grade distribution and informative gaps
- Consolidation status

Claude benefits from team learning without being told to look.

---

## Files

| File | Purpose |
|------|---------|
| `config/agent-capacities.json` | Universal three-capacity schema |
| `config/{agent}-{capacity}.Modelfile` | 18 Modelfiles (6 agents × 3 capacities) |
| `facets/{agent}/facet.json` | Per-agent capacity tracking |
| `facets/alice/intents.jsonl` | Librarian intent records |
| `facets/alice/outcomes.jsonl` | Librarian outcome measurements |
| `.chroma_db_{agent}_hc/` | Per-agent HC vector stores |
| `scripts/agent-sprint.py` | Sprint management |
| `scripts/agent-build.py` | Capacity model builder |
| `scripts/alice-hc-consolidate.py` | Nightly HC consolidation |
| `scripts/alice-mcp-server.py` | Alice MCP v2.0 (12 tools) |
| `scripts/leftshoe-mcp.py` | Team learning integration |
