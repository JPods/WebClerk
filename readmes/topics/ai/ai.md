# AI Integration Plan

> I have DeepSeek installed on my computer. Is it practical to integrate it or some other localized AI to watch, learn, and adapt to our writing and using the software to provide user support for both use and writing user functions in the future?

**Answer: Yes — practical and increasingly common.**

---

## What's Feasible Today

### Local AI for Code Assistance (high value, low effort)

- DeepSeek (or Ollama-hosted models like CodeLlama, Mistral) can already be used as a local coding copilot via VS Code extensions like Continue.dev or Ollama integrations
- Feed it codebase context (Django models, API patterns, 4D methods) to get project-aware suggestions

### Local AI for User Support (medium effort, high value)

- A **RAG (Retrieval-Augmented Generation)** pipeline is the practical path:
  - Index docs, readmes, and code comments into a vector store (ChromaDB, FAISS)
  - Query DeepSeek with relevant context at inference time
- This could power an in-app help chatbot in React2025 or vue2020 that answers questions like *"how do I create a price tier?"* using actual codebase as ground truth

---

## What's Hard (for now)

### "Watch, Learn, and Adapt" Continuously

True continuous learning from user behavior requires fine-tuning infrastructure. DeepSeek can be fine-tuned locally if you have a GPU with ~24GB+ VRAM, but:

- You'd need to collect and curate training data (user interactions, support tickets, code patterns)
- Fine-tuning cycles take time and expertise to get right
- **RAG-based approaches get you 80% of the benefit at 10% of the complexity**

### Key Complexities

| Complexity | Impact | Mitigation |
|---|---|---|
| Model size vs. hardware | Larger models need more VRAM/RAM | Use quantized models (GGUF) via Ollama |
| Context window limits | Models can only see ~8K-128K tokens at once | RAG retrieves only relevant chunks |
| Keeping index current | Code/docs change frequently | Automate re-indexing on git push or file save |
| Quality of answers | Local models are weaker than GPT-4/Claude | Compensate with better retrieval and prompt engineering |
| 4D language support | No local model is trained on 4D code | Include 4D method examples in RAG corpus; consider few-shot prompting |
| Multi-stack context | Project spans Django, React, Vue, 4D | Namespace documents by stack in vector store |

---

## Recommended Architecture

```
┌─────────────────────────────────────────────┐
│  React2025 / vue2020  (Help Widget)         │
│         ↓  user question                    │
│  webClerk3 Django API  (/api/ai/ask/)       │
│         ↓                                   │
│  RAG Pipeline                               │
│  ┌──────────┐    ┌────────────────────┐     │
│  │ Vector DB │◄──│ Indexed docs/code  │     │
│  │ (Chroma)  │    │ readmes, models,   │     │
│  └─────┬─────┘    │ 4D methods         │     │
│        │ context   └────────────────────┘     │
│        ↓                                     │
│  Local DeepSeek / Ollama                     │
│        ↓                                     │
│  Contextual answer                           │
└─────────────────────────────────────────────┘
```

### Component Breakdown

| Component | Technology | Purpose |
|---|---|---|
| LLM Runtime | Ollama + DeepSeek-Coder | Local inference, no API costs, full privacy |
| Vector Store | ChromaDB | Lightweight, Python-native, embeds in Django process |
| Embeddings | `sentence-transformers` (local) | Convert docs/code into vectors for similarity search |
| Django App | `apps/ai_assistant/` | API endpoint, RAG orchestration, conversation history |
| Frontend Widget | React component | Chat UI, streams responses, in-app contextual help |
| Indexer | Management command | Crawls readmes, docstrings, 4D methods; builds vector index |

---

## Implementation Plan

### Phase 1 — Foundation (scaffold) ✅ DONE

1. ✅ **Install Ollama** + load DeepSeek-Coder — local API endpoint (`localhost:11434`)
2. ✅ **Create Django app** `apps/ai_assistant/` in webClerk3 with:
   - `/wcapi/ai/ask/` endpoint (accepts question, returns streamed answer)
   - `/wcapi/ai/feedback/` endpoint (thumbs up/down)
   - `/wcapi/ai/health/` endpoint (system status)
   - `/wcapi/ai/history/` endpoint (conversation history)
   - RAG service class that queries ChromaDB and constructs prompts
   - Management commands: `index_docs`, `ai_health`
3. ✅ **Index documentation** — readmes, models, services, views, 4D methods, instructions, React types
4. ✅ **Automated setup** — `tools/setup_ai.sh` one-command setup for team members

### Phase 2 — Frontend Integration ✅ DONE

5. ✅ **Help widget** — `AiHelpWidget.tsx` floating chat in React2025
6. ✅ **Conversation history** — Conversation & Message models track Q&A per user
7. ✅ **Contextual awareness** — passes current page URL as context
8. ✅ **Feedback system** — thumbs up/down on each assistant response

### Phase 3 — Multi-Mode Intelligence ✅ DONE

9. ✅ **Mode system** — 6 specialized modes with tailored system prompts:
   - `general` — Conversational help about CommerceExpert
   - `developer` — Code-aware with file paths, conventions, import patterns
   - `debugger` — Error analysis: paste a traceback, get a diagnosis + fix
   - `user_support` — Plain-language help for end users (no jargon)
   - `code_review` — Review code against project conventions
   - `test_writer` — Generate tests following pytest/vitest patterns
10. ✅ **Specialized endpoints**:
    - `POST /wcapi/ai/debug/` — paste a traceback for instant diagnosis
    - `POST /wcapi/ai/review/` — submit code for convention review
    - `POST /wcapi/ai/generate/` — generate code or tests
    - `GET /wcapi/ai/modes/` — list available modes
    - `POST /wcapi/ai/reindex/` — trigger reindex (staff only)
11. ✅ **Enhanced indexing** — added settings, tasks, tests, common, React services/pages
12. ✅ **Auto-reindex** — git post-commit hook runs targeted reindex in background
13. ✅ **Mode-aware React widget** — mode selector dropdown, color-coded per mode

### Phase 4 — Continuous Improvement (next)

14. ✅ **Console capture** — `useConsoleCapture` hook auto-captures `console.error`, `window.onerror`, unhandled promise rejections; paste panel in debugger mode
15. ✅ **Developer tools documentation** — `readmes/topics/developer-tools.md` catalogues all dev tools (DevTools panel, AI widget, Whitelist Tester, Swagger UI)
16. ✅ **Copilot context system** — `.copilot-context/` directory with auto-generated reference files:
    - `models/model-reference.md` — every Django model's fields, types, relations (80 models, 3,400+ lines)
    - `models/model-hierarchy.md` — CoreModel → BaseModel mixin chain overview
    - `fixtures/*.json` — golden API response shapes for all 80 models
    - `imports/django-imports.md` — canonical import paths for models, services, views
    - `imports/react-imports.md` — canonical import paths for React services, hooks, pages, types
    - `maps/endpoint-map.md` — all 600+ URL patterns with view classes and names
    - `errors/error-patterns.md` — curated known error patterns with diagnosis and fixes
17. ✅ **Context generator command** — `python manage.py generate_context` generates all context files in 0.6s
18. **Feedback analytics** — track thumbs up/down patterns to improve prompts
19. **Server log access** — give debugger mode access to Django/Celery logs
20. **SSE streaming in widget** — real-time token output (backend ready, frontend TODO)
21. **Scheduled reindex** — Celery periodic task for full reindex overnight

> **Setup guide for team members:** see [setup-guide.md](setup-guide.md)
---

## Key Design Decisions

- **RAG over fine-tuning**: Documents change frequently; re-indexing a vector store takes seconds, while re-training a model takes hours
- **Local-first**: No data leaves the machine, no API costs, works offline
- **Ollama as runtime**: Standard API interface means we can swap models (DeepSeek → Mistral → Llama) without code changes
- **ChromaDB**: Zero-config, embeds in Django, good enough for our corpus size (~thousands of documents, not millions)


