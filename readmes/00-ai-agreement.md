# AI Collaboration Agreement

This document establishes shared context for AI-assisted development across the CommerceExpert team.

---

## 📚 Reading Order

New to the project? Read these in order:

| # | File | Description |
|---|------|-------------|
| 00 | `00-ai-agreement.md` | **Start here** - Project overview & AI collaboration |
| 01 | `01-architecture-overview.md` | System design, layers, key principles |
| 02 | `02-dev-setup.md` | Local environment setup |
| 03 | `03-wcapi-gateway.md` | Unified API gateway design |
| 04 | `04-wcapi-usage.md` | API endpoint examples & patterns |
| 05 | `05-model-registry.md` | Available models & their capabilities |
| 06 | `06-api-conventions.md` | Request/response standards |
| 07 | `07-react-integration.md` | Frontend ↔ Backend integration |

### Additional References (by topic)

**`topics/api/`** - API deep-dives
- `envelope.md` - Response structure
- `wcapi-queries.md` - Query syntax  
- `schema-whitelist.md` - Field permissions
- `save-hooks.md` - Pre/post save behavior

**`topics/models/`** - Data models
- `webclerk3_data_models.md` - Detailed model documentation
- `model_capability_matrix.md` - What each model can do
- `refs_setting_by_model/` - Per-model refs configuration

**`topics/transactions/`** - Business flows
- `transaction_flows.md` - Proposal → Order → Invoice
- `transactions-totals.md` - Calculating totals
- `workorders.md` - Work order management

**`topics/inventory/`** - Stock management
- `inventory.md` - Core concepts
- `flow-vs-inventory.md` - Flow vs physical inventory

**`topics/verification/`** - Communication verification
- `email-verification.md`, `phone-verification.md`, etc.

**`topics/infrastructure/`** - DevOps & tooling
- `testing.md` - Test conventions
- `migrations-squash.md` - Database migrations
- `connections.md` - External integrations

**`topics/ai/`** - AI agent collaboration
- `pattern-recognition.md` - Allie + Alice observation → pattern → feature pipeline

**Data files (root):**
- `model-registry.json` - Machine-readable model list
- `model-fields.json` - Field definitions

**`_archive/`** - Historical docs (not for active development)

---

## Project Framework

| Alias | Project | Stack | Purpose |
|-------|---------|-------|---------|
| **wc3** | WebClerk3 | Django / PostgreSQL / Python | Backend API |
| **r25** | React2025 | React / TypeScript / Vite | Frontend SPA |
| **wc2** | Sources | 4D | Legacy backend (being migrated) |
| **vue2020** | vue2020 | Vue.js | Legacy frontend for wc2 |

## Architecture Principles

### 1. Model Hierarchy (wc3)

All PostgreSQL tables inherit from a composable model system in `common/models.py`:

```
CoreModel (identity + timestamps + version)
├── MetadataMixin (historized metadata, flags)
├── RefsMixin (keywords, tags, links)
├── PrefsMixin (user preferences)
├── CommentsMixin (threaded notes)
├── ActionsMixin (next-step tracking)
├── HealthMixin (data quality scores)
├── LifecycleMixin (soft delete/archive)
├── UniversalDictMixin (stable serialization)
└── AtomicJSONMixin (partial JSON updates)
    └── BaseModel (full composition)
```

### 2. Unified API Gateway (wcapi)

All CRUD operations route through centralized endpoints:

| Endpoint | Purpose |
|----------|---------|
| `/wcapi/get/` | Fetch records (list or single) |
| `/wcapi/save/` | Create or update records |
| `/wcapi/query/` | Complex queries |
| `/wcapi/manage/` | Administrative operations |

**Why?** Concentrates security surface area into a single flow for tighter control.

### 3. Folder Structure Alignment

r25 `src/apps/` mirrors wc3 `apps/`:

```
wc3: apps/{core,transactions,products,docs,accounts,communications,...}
r25: src/apps/{core,transactions,products,docs,accounts,communications,...}
```

Each model follows:
```
apps/{app}/models/{model}/
├── pages/       # React components (Detail, List, Display)
├── services/    # API integration ({model}Api.ts)
├── types/       # TypeScript definitions
├── utils/       # Schemas, helpers
└── index.ts
```

### 4. Naming Conventions

- **Model names, not table names** - Use singular form (`invoice` not `invoices`) to avoid pluralization complexity
- **Consistent casing** - snake_case in Python, camelCase in TypeScript
- **File naming** - `{Model}Detail.tsx`, `{Model}List.tsx`, `{model}Api.ts`

### 5. Response Envelope

All API responses use a standard envelope:

```json
{
  "status": "success|error",
  "data": { ... },
  "error": null,
  "meta": { "count": 0, "page": 1 }
}
```

## Documentation Requirements

**Readmes are essential.** Document as you build:

- **wc3**: `webClerk3/readmes/` (numbered files for onboarding)
- **r25**: `React2025/readmes/`

Files prefixed `00-` through `07-` are the core onboarding sequence. Other files are topic-specific references.

## AI Agents

Three agents collaborate in this codebase. Each has a defined role and a defined boundary.

| Agent | Spec | Role |
|-------|------|------|
| **Alice** | `.github/agents/Alice.agent.md` | Search quality, keyword denormalization, alice notes, user behavior observation, pattern → feature recommendations |
| **Allie** | `.github/agents/Allie.agent.md` | Bill's personal AI companion; cross-domain synthesis; WhatIf store (project 24); validates Alice's pattern candidates; sovereign agent into WebClerk |
| **Claude Code** | `.github/instructions/copilot.instructions.md` | Code generation, architecture, multi-file edits, deep codebase research |

**Pattern recognition loop:** Alice observes → logs to `alice_log` → detects pattern → creates `alice_pending config_suggestion` → Allie validates → promotes to `Setting` feature or routes to WhatIf store → Bill activates. See `topics/ai/pattern-recognition.md`.

**Coordination protocol (master):** `/Volumes/Allie/readmes/19-agent-coordination.md`

---

## Working With AI

When starting a session, share this context:

1. **Which project?** (wc3, r25, wc2, vue2020)
2. **Which app/model?** (e.g., transactions/invoice)
3. **What task?** (new feature, bug fix, refactor)

### Things AI Should Know

- JSONB fields (`metadata`, `refs`, `prefs`, `comments`) allow schema evolution without migrations
- `TransactionBaseModel` extends `BaseModel` with transaction-specific fields (totals, status, flow)
- Line items follow `{Header}Line` naming (e.g., `InvoiceLine`, `OrderLine`)
- Soft deletes via `LifecycleMixin` - records are archived, not destroyed

### Common Pitfalls

- Don't duplicate `/wcapi` prefix (check `VITE_API_URL`)
- Use model names in API calls, not table names
- Check `wcapi_registry.py` for allowed models
- Run wc3 on port 8000, r25 on 5173

## Team Sharing

All team members should:
1. Reference this document at session start
2. Update it when architectural decisions are made
3. Keep readmes current with implementation changes

---

*Last updated: April 2026*
