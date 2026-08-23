# Alice — WebClerk AI Assistant

**What Alice is:** The AI assistant embedded in every WebClerk installation. She watches
what happens, learns from patterns, coaches users, enforces data quality, and manages
the bridge between human commerce and machine intelligence.

**What Alice is not:** A chatbot. Alice is a working agent — she acts on data, moves
files, detects duplicates, polishes records, enforces field sizes, and escalates what
she cannot handle. The chat interface is one surface; the scheduled tasks and signal
handlers are where most of her work happens.

---

## Capability Map

| Capability | Document | What it covers |
|-----------|----------|---------------|
| **Pattern Recognition** | [pattern-recognition.md](pattern-recognition.md) | observe > log > pattern > recommend > promote pipeline; Setting promotion; friction signals; happiness metric |
| **Observation Setup** | [observation-setup.md](observation-setup.md) | AliceObservation, AlicePreset, AliceCoachingLog models; console capture; wcapi access; coaching UI; quiz engine |
| **Data Quality** | [data-quality.md](data-quality.md) | Three-tier processing (hard algo > Alice LLM > general LLM); data polishing (guess/review/validate); field size discipline; file storage enforcement |
| **Dedup** | [dedup.md](dedup.md) | Duplicate detection and extraction; matching strategies; bundle files; user operations (copy/remove/done); Claude escalation |
| **Escalation** | [escalation.md](escalation.md) | What Alice can do vs. what needs Claude Code; Action-based handoff; capability gap tracking |
| **Toolkit** | [toolkit.md](toolkit.md) | Vector stores, MCP servers, quiz engine, diagramming, PDF generation, data conversion (Ingrid), Chrome DevTools |
| **How Alice Learns** | [learning.md](learning.md) | 5 learning pathways; what does NOT teach Alice; memory architecture; MCP servers; failure modes |
| **Support Q&A System** | [support-qa-system.md](support-qa-system.md) | Full help lifecycle: search → ask → answer → score → WCHQ escalation; diagnostic context; quiz training; ~300 seeded Q&A |
| **TSX Archive** | [tsx-archive.md](tsx-archive.md) | File replacement study protocol; layout evolution tracking |
| **Setup Guide** | [setup-guide.md](setup-guide.md) | One-command setup; manual steps; AI modes; console capture; index management; troubleshooting |

---

## Document Records — WC_HQ Sync

Each readme ships as a Document record in every WC3 installation. WC_HQ updates
these via UUID sync. The Document record is a pointer — the content lives in git.

| IDA | Document name | Git path | Sequence |
|-----|--------------|----------|----------|
| `ALICE-README` | Alice — Overview | `readmes/alice/README.md` | 0 |
| `ALICE-PATTERN-RECOGNITION` | Alice — Pattern Recognition | `readmes/alice/pattern-recognition.md` | 10 |
| `ALICE-OBSERVATION-SETUP` | Alice — Observation Setup | `readmes/alice/observation-setup.md` | 20 |
| `ALICE-DATA-QUALITY` | Alice — Data Quality | `readmes/alice/data-quality.md` | 30 |
| `ALICE-DEDUP` | Alice — Dedup | `readmes/alice/dedup.md` | 40 |
| `ALICE-ESCALATION` | Alice — Escalation Protocol | `readmes/alice/escalation.md` | 50 |
| `ALICE-TOOLKIT` | Alice — Toolkit | `readmes/alice/toolkit.md` | 60 |
| `ALICE-LEARNING` | Alice — How Alice Learns | `readmes/alice/learning.md` | 70 |
| `ALICE-SUPPORT-QA` | Alice — Support Q&A System | `readmes/alice/support-qa-system.md` | 75 |
| `ALICE-TSX-ARCHIVE` | Alice — TSX Archive | `readmes/alice/tsx-archive.md` | 80 |
| `ALICE-SETUP-GUIDE` | Alice — Setup Guide | `readmes/alice/setup-guide.md` | 90 |

**How sync works:**
- Each Document has a stable `uuid` and `ida` (e.g., `ALICE-DATA-QUALITY`)
- `config.git_path` points to the markdown file in the WC3 repo
- WC_HQ pushes updates via bundle sync — the Document record updates, the
  installation pulls the latest git content
- `sequence` controls display order in training interfaces
- `refs.tags` = `["alice", "readme", "training"]` for filtering

**For CodeMap:** The `wc3-alice-system.dot` flowchart links nodes to these
Document IDAs. Alice walks the graph to answer "how do I...?" questions.

---

## Cross-References

| Topic | Location | Why it's there, not here |
|-------|----------|------------------------|
| JPods trip pricing | `~/Allie/readmes/35-jpods-alice-trip-api.md` | JPods-specific; not every WC3 installation runs JPods |
| Small Stings | `~/Allie/readmes/44-small-stings.md` | JPods service quality penalties — domain-specific |
| Fare and Payment | `~/Allie/readmes/45-fare-and-payment.md` | JPods fare architecture — domain-specific |
| Allie-Alice Learning (full) | `~/Allie/readmes/74-allie-alice-learning.md` | Combined Allie+Alice reference; `learning.md` here has Alice's portion |
| Agent coordination | `~/Allie/readmes/19-agent-coordination.md` | Cross-agent protocol for all agents, not Alice-specific |
| Alice agent file | `~/Allie/readmes/agents/alice.md` | Role, design decisions, interfaces — team memory, not deployment docs |

---

## For New Deployments

1. Run `tools/setup_ai.sh` (creates models, indexes, pulls LLM)
2. Run `python3 manage.py seed_alice_docs` (creates Document records from this index)
3. Alice is ready — console capture starts at app boot, pattern detection runs every 4 hours
4. First admin session: review Alice's observation categories, set up quiz drills

The Document records are the deployment artifact. The git content is the source of truth.
WC_HQ keeps them in sync.
