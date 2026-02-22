# Copilot Context System

> Machine-readable context files that give Copilot (and DeepSeek) structured data about the codebase — model fields, API shapes, import paths, error patterns, and relationship maps.

---

## Why This Exists

Copilot and the AI assistant work best when they have **exact, machine-readable facts** instead of parsing source code on the fly. This directory contains auto-generated reference files that are:

1. **Indexed by the AI assistant** — ChromaDB includes these in RAG retrieval
2. **Readable by Copilot** — structured markdown that Copilot can reference during code generation
3. **Auto-generated** — management commands regenerate them so they stay current
4. **Committed to git** — versioned with the codebase, diff-friendly

---

## Directory Structure

```
.copilot-context/
├── README.md                  ← this file
├── models/
│   ├── model-reference.md     ← every Django model's fields, types, relations
│   └── model-hierarchy.md     ← CoreModel → BaseModel mixin chain overview
├── fixtures/
│   ├── contact.json           ← real API response shape for Contact
│   ├── order.json             ← real API response shape for Order
│   └── ...                    ← one per model
├── imports/
│   ├── django-imports.md      ← canonical import paths for Django services/models
│   └── react-imports.md       ← canonical import paths for React components/services
├── errors/
│   └── error-patterns.md      ← known errors with causes and fixes
└── maps/
    └── endpoint-map.md        ← API endpoints → Django views → React pages
```

---

## Generating / Updating

### All at once
```bash
python manage.py generate_context
```

### Individual generators
```bash
python manage.py generate_context --target models      # model field reference
python manage.py generate_context --target fixtures     # golden API response shapes
python manage.py generate_context --target imports      # canonical import paths
python manage.py generate_context --target endpoints    # endpoint → view → component map
```

### When to regenerate
- After adding or modifying Django models
- After adding new React services or components
- After changing API endpoints
- The git post-commit hook auto-reindexes, but context files need explicit regeneration

---

## What's in Each File

### `models/model-reference.md`
Every Django model with:
- Full class name and inheritance chain
- Every field: name, type, nullable, default, choices, help_text
- Foreign keys with related model and related_name
- JSON envelope fields with their documented structure
- Meta options (ordering, indexes, constraints)

### `fixtures/*.json`
Real API response shapes from `/wcapi/get/`, one per model. These are:
- **Not test data** — they're shape references showing every field with its type
- Used by Copilot to generate correct TypeScript interfaces
- Used by the AI assistant to answer "what fields does X have?"

### `imports/django-imports.md`
Every public Django class/function with its exact import path:
```
OrderService      → from apps.transactions.services.order_service import OrderService
Contact           → from apps.core.models import Contact
transaction_save  → from apps.transactions.services.transaction_save import transaction_save
```

### `imports/react-imports.md`
Every public React component/hook/service with its exact import path:
```
useTransactionForm → import { useTransactionForm } from '@/apps/transactions/models/order/hooks/useTransactionForm'
OrderType          → import type { OrderType } from '@/apps/transactions/models/order/types/orderType'
apiClient          → import apiClient from '@/api/axios'
```

### `errors/error-patterns.md`
Known error patterns with diagnosis and fix:
- CSRF 403 on save
- Line save 500 (required fields)
- Pending stuck in processing
- Model resolver KeyError
- React hydration mismatches

### `maps/endpoint-map.md`
API endpoint → Django view → React consumer mapping:
```
POST /wcapi/save/ → WCAPISaveView → useTransactionForm.handleSave()
GET  /wcapi/get/  → WCAPIGetView  → useModelList(), useModelDetail()
```

---

## Integration Points

| Consumer | How it uses context files |
|----------|-------------------------|
| **AI Assistant (DeepSeek)** | Indexed into ChromaDB via `index_docs --source copilot_context` |
| **Copilot (VS Code)** | Reads files directly when referenced in instructions or via workspace search |
| **Developers** | Quick reference for field names, import paths, known errors |
| **Test Writer mode** | Uses model reference to generate correct field assertions |
| **Code Review mode** | Uses import paths to flag incorrect imports |

---

## Adding New Context

1. Add a generator method in `apps/ai_assistant/management/commands/generate_context.py`
2. Output to the appropriate subdirectory
3. Add the `--target` choice to the command
4. Update this README
5. Run `python manage.py index_docs --source copilot_context` to reindex
