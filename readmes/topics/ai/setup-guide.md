# AI Assistant — Team Setup Guide

> One-command setup for the CommerceExpert AI assistant.
> This guide gets any team member from zero to a working local AI in ~10 minutes.

---

## Quick Start (Automated)

```bash
# From the webClerk3 directory:
./tools/setup_ai.sh
```

This single script will:
1. Check all prerequisites
2. Install Python packages (chromadb, sentence-transformers, httpx)
3. Install/start Ollama and pull the DeepSeek model
4. Run Django migrations
5. Index all project documentation
6. Install git hooks for auto-reindex
7. Run a health check

### Other script modes

```bash
./tools/setup_ai.sh --check   # Check prerequisites only
./tools/setup_ai.sh --index   # Re-index docs only
./tools/setup_ai.sh --reset   # Wipe and rebuild the index
./tools/setup_ai.sh --hooks   # Install git hooks for auto-reindex
```

---

## Manual Setup (Step by Step)

### 1. Install Ollama

```bash
# macOS
brew install ollama

# Or download from https://ollama.ai
```

### 2. Start Ollama & Pull the Model

```bash
# Start the server (runs on localhost:11434)
ollama serve

# In another terminal, pull the model:
ollama pull deepseek-coder-v2

# Verify:
ollama list
```

**Alternative models** (if your hardware struggles with deepseek-coder-v2):

| Model | Size | Good for |
|-------|------|----------|
| `deepseek-coder-v2` | ~16GB | Best code quality (default) |
| `codellama:13b` | ~7GB | Good balance of speed/quality |
| `mistral` | ~4GB | Fast, good general knowledge |
| `llama3.2:3b` | ~2GB | Very fast, lower quality |

To switch models, set in `.env`:
```
OLLAMA_MODEL=codellama:13b
```

### 3. Install Python Dependencies

```bash
cd webClerk3
source bin/activate
pip install chromadb sentence-transformers httpx
```

### 4. Run Django Migrations

```bash
python manage.py migrate ai_assistant
```

### 5. Index Documentation

```bash
# Index everything (readmes, code, 4D methods, instructions)
python manage.py index_docs

# Index only specific sources
python manage.py index_docs --source readmes
python manage.py index_docs --source models
python manage.py index_docs --source 4d_methods

# See what would be indexed without doing it
python manage.py index_docs --dry-run

# Check index stats
python manage.py index_docs --stats
```

### 6. Health Check

```bash
python manage.py ai_health
```

Expected output:
```
══════════════════════════════════════════════════
  AI Assistant Health Check
══════════════════════════════════════════════════
  Ollama: CONNECTED (http://localhost:11434)
  Model: deepseek-coder-v2
  Vector store: 847 chunks indexed

  Overall: OK
```

---

## Using the AI Assistant

### AI Modes

The assistant has 6 specialized modes — each changes how it thinks about your question:

| Mode | Best For | Example |
|------|----------|---------|
| **General** | Quick help on any topic | "What is the Pending system?" |
| **Developer** | Code-aware answers with file paths | "How do I register a new model in WCAPI?" |
| **Debugger** | Error analysis from tracebacks | Paste a Python/JS error for diagnosis + fix |
| **User Support** | End-user help in plain language | "How do I create a purchase order?" |
| **Code Review** | Convention compliance checks | Paste code to get a review against project rules |
| **Test Writer** | Generate tests | "Write tests for the OrderService.create method" |

### From the Frontend (React2025)

A floating chat widget (`AiHelpWidget`) appears in the bottom-right corner of every page.

- Click the bot icon to open
- Use the **mode dropdown** in the header to switch modes
- Mode badges show on quick-select chips when the chat is empty
- Each mode has a different color theme and placeholder text
- Thumbs up/down feedback helps improve retrieval quality over time

### From the API

```bash
# Ask a question (default: general mode)
curl -X POST http://localhost:8000/wcapi/ai/ask/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{"question": "How do I transfer an order to an invoice?", "mode": "developer"}'

# Debug an error
curl -X POST http://localhost:8000/wcapi/ai/debug/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{"error": "TypeError: Cannot read property id of undefined", "file_context": "OrderDetailPage.tsx"}'

# Review code
curl -X POST http://localhost:8000/wcapi/ai/review/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{"code": "class MyView(APIView): ...", "file_path": "apps/core/views/my_view.py"}'

# Generate tests
curl -X POST http://localhost:8000/wcapi/ai/generate/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{"task": "test", "description": "Write tests for the Order model create flow"}'

# List available modes
curl http://localhost:8000/wcapi/ai/modes/

# Trigger reindex (staff only)
curl -X POST http://localhost:8000/wcapi/ai/reindex/ \
  -H "Authorization: Bearer <admin-jwt-token>" \
  -d '{"source": "all"}'

# Check health
curl http://localhost:8000/wcapi/ai/health/
```

### From the Django Shell

```python
from apps.ai_assistant.services.rag_service import RAGService

rag = RAGService()

# General question
result = rag.ask("What fields does the Order model have?")

# Developer mode
result = rag.ask("How do I add inventory allocation?", mode="developer")

# Debug an error
result = rag.ask("TypeError in line_save", mode="debugger", extra_context=traceback_text)

# Code review
result = rag.ask("Review this code", mode="code_review", extra_context=code_text)

print(result["answer"])
print(result["sources"])
print(result["mode"])
```

---

## Keeping the Index Fresh

### Automatic (git hooks)

When you run `tools/setup_ai.sh --hooks` (or `--full`), a git post-commit hook is installed that:
- Detects which files changed in the commit
- Maps them to source categories (readmes, models, services, etc.)
- Runs targeted `index_docs --source <category>` in the background
- Does **not** slow down your commits

### Manual

```bash
# Quick re-index (updates existing + adds new)
python manage.py index_docs

# Index specific category only
python manage.py index_docs --source readmes
python manage.py index_docs --source models
python manage.py index_docs --source tests
python manage.py index_docs --source react_services

# Full rebuild (wipe + re-index)
python manage.py index_docs --reset

# View stats
python manage.py index_docs --stats
```

### Via API (staff only)

```bash
curl -X POST http://localhost:8000/wcapi/ai/reindex/ \
  -H "Authorization: Bearer <admin-jwt-token>" \
  -d '{"source": "all"}'
```

### Available index sources

| Source | What it indexes |
|--------|----------------|
| `readmes` | Markdown docs from wc3 and r25 |
| `instructions` | Copilot/team instruction files |
| `models` | Django model definitions |
| `services` | Django service/business logic files |
| `views` | Django views and URL configs |
| `settings` | Django settings, urls, celery config |
| `tasks` | Celery tasks and management commands |
| `tests` | Test files and conftest |
| `common` | Shared utilities from common/ |
| `4d_methods` | Legacy 4D method files |
| `react_types` | TypeScript type/model definitions |
| `react_services` | React API services and SDK code |
| `react_pages` | React page components |
| `copilot_context` | Auto-generated context files (.copilot-context/) |

---

## Configuration

All settings can be overridden in `.env` or `webclerk3_api/settings.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `deepseek-r1:8b` | Model to use for generation |
| `OLLAMA_TIMEOUT` | `120` | Request timeout in seconds |
| `CHROMA_PERSIST_DIR` | `.chroma_db/` | Where ChromaDB stores its data |
| `CHROMA_COLLECTION` | `commerce_expert_docs` | Collection name in ChromaDB |

---

## Troubleshooting

### "Cannot connect to Ollama"
```bash
# Is Ollama running?
curl http://localhost:11434/api/tags

# If not, start it:
ollama serve
```

### "Model not found"
```bash
ollama pull deepseek-coder-v2
ollama list  # verify it appears
```

### "Vector store: EMPTY"
```bash
python manage.py index_docs
python manage.py index_docs --stats  # verify count > 0
```

### Slow responses
- Try a smaller model: `OLLAMA_MODEL=mistral`
- Check available RAM: the model needs to fit in memory
- Reduce context: edit `MAX_CONTEXT_CHARS` in `rag_service.py`

### Widget not appearing in React
- Ensure `AiHelpWidget` is imported in `App.tsx`
- Check browser console for errors
- Verify the backend is running on `:8000`

---

## Architecture Reference

```
┌─────────────────────────────────────────────┐
│  React2025  (AiHelpWidget.tsx)              │
│         ↓  POST /wcapi/ai/ask/              │
│  webClerk3  (apps/ai_assistant/)            │
│         ↓                                   │
│  RAGService                                 │
│  ┌──────────┐    ┌────────────────────┐     │
│  │ ChromaDB  │◄──│ Indexed content:   │     │
│  │ (.chroma_ │    │ • readmes          │     │
│  │   db/)    │    │ • Django models    │     │
│  └─────┬─────┘    │ • services/views   │     │
│        │ context   │ • 4D methods       │     │
│        ↓           │ • instructions     │     │
│  Ollama (DeepSeek) │ • React types      │     │
│        ↓           │ • copilot-context  │     │
│  Contextual answer └────────────────────┘     │
└─────────────────────────────────────────────┘
```

### File Map

| File | Purpose |
|------|---------|
| `apps/ai_assistant/apps.py` | Django app config |
| `apps/ai_assistant/models.py` | Conversation & Message models |
| `apps/ai_assistant/views.py` | API views (ask, debug, review, generate, feedback, health, history, modes, reindex) |
| `apps/ai_assistant/urls.py` | URL routing (9 endpoints) |
| `apps/ai_assistant/admin.py` | Django admin integration |
| `apps/ai_assistant/services/ollama_client.py` | Ollama HTTP client (mode-aware) |
| `apps/ai_assistant/services/vector_store.py` | ChromaDB wrapper |
| `apps/ai_assistant/services/rag_service.py` | RAG orchestration (mode-aware) |
| `apps/ai_assistant/services/prompt_templates.py` | Mode-specific system prompts & query wrappers |
| `apps/ai_assistant/management/commands/index_docs.py` | Document indexer (14 source categories) |
| `apps/ai_assistant/management/commands/generate_context.py` | Copilot context generator (models, fixtures, imports, endpoints) |
| `apps/ai_assistant/management/commands/ai_health.py` | Health check CLI |
| `tools/setup_ai.sh` | One-command automated setup |
| `tools/hooks/post-commit` | Git hook for auto-reindex |
| `React2025/src/components/AiHelpWidget.tsx` | Frontend chat widget (mode selector + console capture) |
| `React2025/src/hooks/useConsoleCapture.ts` | Browser error capture hook (console.error, window.onerror, rejections) |
| `React2025/src/apps/support/services/aiApi.ts` | Frontend API client (all endpoints + types) |
| `.copilot-context/` | Auto-generated model reference, fixtures, import paths, error patterns, endpoint map |
