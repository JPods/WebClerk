# How Alice Learns
**Extracted from:** `~/Allie/readmes/74-allie-alice-learning.md`
**Purpose:** Alice-specific learning pathways for WC3 deployments

---

## The Problem

Alice is the team's durable commerce memory — but only if knowledge is explicitly
written to her. **Asking Alice questions does not teach her anything.** The `ask_alice`
and `alice_search` tools are read-only. Without explicit `alice_observe` calls,
decisions made during a session evaporate.

---

## How Alice Learns — 5 Active Pathways

| # | Pathway | Tool / Script | When | What it writes | Durability |
|---|---------|--------------|------|---------------|------------|
| 1 | **alice_observe** | MCP via `alice-mcp-server.py` | Claude calls during session | `alice_log` table (PostgreSQL `allie` DB) | **Permanent** |
| 2 | **alice-patterns.py** | LaunchAgent every 4 hours | Automatic | Scans `commerce_expert` DB → `alice_log` observations | **Permanent** |
| 3 | **Vector store** | `.chroma_db_alice` loaded at server start | On MCP server start | WC3 source + readmes + models indexed | **Semi-permanent** |
| 4 | **Conversation log** | `alice-mcp-server.py` | Every MCP exchange | `~/Allie/exchange/alice-conversation.jsonl` | **Log only** |
| 5 | **Quiz engine** | Document records in WC3 | When quiz created | Document model in `commerce_expert` DB | **Permanent** |

---

## What Does NOT Teach Alice

| Action | Why it doesn't persist |
|--------|----------------------|
| `ask_alice` | Read-only — searches vector store + calls Ollama but writes nothing |
| `alice_search` | Read-only — vector store semantic search, no writes |
| `alice_recall` | Read-only — queries alice_log but doesn't add entries |
| `alice_quiz` | Read-only — serves questions but doesn't learn from answers |

---

## Alice's Memory Architecture

```
alice_observe → alice_log table (PostgreSQL allie DB)
                    │
                    ▼
              alice_recall reads alice_log
              ask_alice searches vector store + calls Ollama

alice-patterns.py (every 4 hours)
  reads: commerce_expert DB (items, invoices, payments, orders)
  detects: reorder, past-due, MAP violations, commission anomalies
  writes: alice_log observations with dedup keys
                    │
                    ▼
              Pattern → Recommend → Promote loop
              (observe > log > pattern > recommend > promote)

Vector store (.chroma_db_alice)
  WC3 source + readmes + models
  Loaded at MCP server start
  ask_alice searches this for context before calling Ollama
```

---

## Alice's Storage Locations

| Store | Path / Location | What's in it |
|-------|----------------|-------------|
| Pattern log | `alice_log` table in `allie` PostgreSQL DB | All observations: event, model_name, message, source, data, action_taken |
| Vector store | `~/.chroma_db_alice/` | WC3 code + docs (cosine similarity search) |
| Conversation log | `~/Allie/exchange/alice-conversation.jsonl` | All MCP exchanges (log only — not auto-read) |
| Quiz questions | Document records in `commerce_expert` DB | `model_name='quiz'`, body JSON with questions array |

---

## The Learning Protocol — What Claude Must Do

### During Session
1. Use `ask_alice` / `alice_search` for consultation (read-only, no learning)
2. Note significant decisions for end-of-session teaching

### Before Session End
3. Call `alice_observe` with `event=pattern` and structured `data` for every new
   architecture decision or commerce workflow change
4. Write session file — feeds the harvest → reflect pipeline for Allie
5. Write retrospection with commerce-relevant lessons

---

## What Breaks When Learning Fails

| Failure mode | What happens | How to detect |
|-------------|-------------|---------------|
| MCP servers down | No observe during session | leftshoe reports status |
| No `alice_observe` calls | Alice doesn't learn new architecture | alice_log has no entries for today |
| Ollama down | ask_alice gets no LLM response | Check `curl localhost:11434` |
| PostgreSQL down | alice_observe fails | alice_log table unreachable |

---

## MCP Server

| Server | Script | Tools |
|--------|--------|-------|
| **alice-commerce** | `scripts/alice-mcp-server.py` | ask_alice, alice_search, alice_observe, alice_recall, alice_quiz |

Uses: `/Users/williamjames/Allie/venv/bin/python3`

---

## For Allie Integration

The full combined Allie+Alice learning reference lives at `~/Allie/readmes/74-allie-alice-learning.md`.
This file covers Alice's portion only — what a WC3 deployment needs to know.
Allie's learning pathways (teach_allie, nightly reflect, harvest, TFTS) are not
relevant to WC3 deployments and stay in the Allie repo.

## Key Files

| File | What it does |
|------|-------------|
| `scripts/alice-mcp-server.py` | Alice's MCP server — ask, search, observe, recall, quiz |
| `scripts/alice-patterns.py` | Every-4-hour commerce pattern detection |
| `~/.chroma_db_alice/` | Alice's vector store |
| `~/Allie/exchange/alice-conversation.jsonl` | Alice conversation log |
