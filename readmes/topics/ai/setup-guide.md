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
6. Run a health check

### Other script modes

```bash
./tools/setup_ai.sh --check   # Check prerequisites only
./tools/setup_ai.sh --index   # Re-index docs only
./tools/setup_ai.sh --reset   # Wipe and rebuild the index
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

### From the Frontend (React2025)

A floating chat widget (`AiHelpWidget`) appears in the bottom-right corner of every page. Click it to open.

- Ask questions in natural language
- The assistant knows about your orders, invoices, inventory, API endpoints, etc.
- Thumbs up/down feedback helps improve retrieval quality over time

### From the API

```bash
# Ask a question
curl -X POST http://localhost:8000/wcapi/ai/ask/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{"question": "How do I transfer an order to an invoice?"}'

# Check health
curl http://localhost:8000/wcapi/ai/health/

# Submit feedback
curl -X POST http://localhost:8000/wcapi/ai/feedback/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{"message_id": 42, "feedback": 1}'
```

### From the Django Shell

```python
from apps.ai_assistant.services.rag_service import RAGService

rag = RAGService()
result = rag.ask("What fields does the Order model have?")
print(result["answer"])
print(result["sources"])
```

---

## Keeping the Index Fresh

The vector index should be rebuilt when documentation or code changes significantly:

```bash
# Quick re-index (updates existing + adds new)
python manage.py index_docs

# Full rebuild (wipe + re-index)
python manage.py index_docs --reset
```

**Automation ideas** (future):
- Git post-commit hook: `python manage.py index_docs --source readmes`
- Celery beat task: re-index nightly
- CI/CD: re-index on deploy

---

## Configuration

All settings can be overridden in `.env` or `webclerk3_api/settings.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `deepseek-coder-v2` | Model to use for generation |
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
│        ↓           └────────────────────┘     │
│  Contextual answer                           │
└─────────────────────────────────────────────┘
```

### File Map

| File | Purpose |
|------|---------|
| `apps/ai_assistant/apps.py` | Django app config |
| `apps/ai_assistant/models.py` | Conversation & Message models |
| `apps/ai_assistant/views.py` | API views (ask, feedback, health, history) |
| `apps/ai_assistant/urls.py` | URL routing |
| `apps/ai_assistant/admin.py` | Django admin integration |
| `apps/ai_assistant/services/ollama_client.py` | Ollama HTTP client |
| `apps/ai_assistant/services/vector_store.py` | ChromaDB wrapper |
| `apps/ai_assistant/services/rag_service.py` | RAG orchestration |
| `apps/ai_assistant/management/commands/index_docs.py` | Document indexer |
| `apps/ai_assistant/management/commands/ai_health.py` | Health check CLI |
| `tools/setup_ai.sh` | One-command automated setup |
| `React2025/src/components/AiHelpWidget.tsx` | Frontend chat widget |
| `React2025/src/apps/support/services/aiApi.ts` | Frontend API client |
