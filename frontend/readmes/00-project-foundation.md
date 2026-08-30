# CommerceExpert Project Foundation

> **For AI Assistants (Copilot, Claude, etc.)**
> 
> Read this document first to understand the project context, architecture, and working conventions.
> This enables consistent collaboration across all team members.

---

## Project Overview

**CommerceExpert** is a B2B commerce platform with 25+ years of evolution. The current architecture is the 3rd major iteration:

| Component | Tech Stack | Port | Purpose | Status |
|-----------|------------|------|---------|--------|
| **webClerk3 (wc3)** | Django 5.x, Python 3.13, PostgreSQL | `localhost:8000` | Backend API, business logic, database | **Active** |
| **React2025 (r25)** | React 18, TypeScript, Vite | `localhost:5173` | Modern frontend SPA | **Active** |
| **vue2020** | Vue 2, JavaScript | N/A | Previous frontend (2020-2024) | **Reference** |
| **webclerk2 (wc2)** | 4D Database | N/A | Original backend (1998-2023) | **Reference** |

### Platform Evolution

```
1998-2023: 4D Database (wc2) - Desktop app with integrated DB/UI
2020-2024: Vue 2 frontend (vue2020) - Web frontend against 4D backend  
2023-now:  Django backend (wc3) - Python/PostgreSQL migration
2024-now:  React frontend (r25) - TypeScript/Vite replacement for Vue
```

**Why this matters:** The legacy codebases (`vue2020/`, `Sources/`) contain working implementations of every feature. Use them as reference for:
- Business logic patterns
- Data structures and field names
- UI/UX conventions users expect
- API endpoint patterns

### Repository Structure

```
CommerceExpert/
├── webClerk3/           # Django backend (ACTIVE)
│   ├── apps/            # Django apps (core, orgs, products, transactions, etc.)
│   ├── common/          # Shared utilities, base models, registries
│   ├── readmes/         # Backend documentation
│   └── manage.py
├── React2025/           # React frontend (ACTIVE)
│   ├── src/
│   │   ├── api/         # API client functions
│   │   ├── apps/        # Feature modules
│   │   ├── components/  # Reusable UI components
│   │   ├── pages/       # Route pages
│   │   └── store/       # Redux store
│   └── readmes/         # Frontend documentation
├── vue2020/             # Vue frontend (REFERENCE)
│   └── src/
│       ├── components/  # Vue components (patterns to replicate)
│       ├── libs/        # Utilities (urls.js, datastore.js, eventbus.js)
│       └── views/       # Page views
└── Sources/             # 4D Database code (REFERENCE)
    ├── Methods/         # 4D methods (WCapi*, business logic)
    ├── Classes/         # 4D classes
    └── Forms/           # 4D form definitions
```

---

## Historical Reference: Legacy Systems

### vue2020 - Key Patterns to Replicate

The Vue frontend established UI patterns users expect:

| Component | Purpose | r25 Equivalent |
|-----------|---------|----------------|
| `KanbanPad.vue` | Kanban board with drag-drop | `KanbanBoardPage.tsx` |
| `GanttComponent.vue` | Gantt chart scheduling | TBD |
| `OrderForm.vue` | Order entry with line items | `OrderDetailPage.tsx` |
| `CustomerForm.vue` | Customer management | `CustomerDetailPage.tsx` |
| `QAForm.vue` | Question/Answer forms | `QAFormPage.tsx` |

**Key libs from vue2020:**
```javascript
// urls.js - API endpoint definitions
var URLs = {
  kanban: { getKanban: baseUrl + "/api/kanban/getKanban" },
  orders: { getById: ordersPath + "get", save: ordersPath + "save" },
  // ... mirrors wc3 WCAPI patterns
}

// datastore.js - Global state
var DataStore = { user: {}, currentItem: null, ... }

// eventbus.js - Cross-component communication
EventBus.$emit('EVENT_NAME', payload)
```

### wc2 (4D) - Business Logic Reference

The 4D codebase in `Sources/Methods/` contains 25 years of business logic:

| Method Pattern | Purpose | wc3 Equivalent |
|----------------|---------|----------------|
| `WCapiTask_*` | API task handlers | `apps/*/views.py` |
| `WCapi_*` | Generic CRUD operations | `common/wcapi/` |
| `DB_ORDA*` | Database queries | Django ORM |
| `Calc*`, `Parse*` | Business calculations | Model methods |
| `Prnt_*`, `P_*` | Print/report variables | Report services |

**Example: Finding existing logic**
```bash
# Looking for invoice calculation logic?
ls Sources/Methods/ | grep -i invoice
# calcInvoice.4dm, ParseInvoiceLines.4dm, InvoiceLinesBody.4dm, etc.
```

**4D to Django mapping:**
```
4D Tables      → Django Models
4D Methods     → Django Views/Services  
4D ORDA        → Django ORM
4D obGeneral   → JSONField (refs, meta)
4D idNum       → id (integer primary key)
4D id (UUID)   → uuid field
```

---

## Architecture Patterns

### Backend (wc3)

**WCAPI - Generic REST Interface**

All models are exposed through a generic API pattern:

```http
GET  /wcapi/get/?model_name=<model>&<filters>    # List/retrieve records
POST /wcapi/save/                                  # Create/update records
     { "model_name": "<model>", "id": <id>, ...fields }
```

**Key Models:**

| Model | App | Purpose | 4D Equivalent |
|-------|-----|---------|---------------|
| `Project` | transactions | Projects with linked contacts | `Objective` |
| `Action` | core | Kanban tasks, scheduled actions | `Task`, `Action` |
| `Contact` | orgs | People (staff + external) | `Contact` |
| `Organization` | orgs | Companies, vendors, customers | `Customer`, `Vendor` |
| `Order` | transactions | Sales orders | `Order` |
| `Invoice` | transactions | Invoices | `Invoice` |
| `Proposal` | transactions | Quotes/proposals | `Proposal` |
| `Item` | products | Products/inventory | `Item` |
| `Setting` | core | Configuration storage | `Default`, `Setup` |

**Choices & Select Lists:**

Each app has a `choices.py` with `DEFAULT_SELECT_LISTS` that defines dropdown options for the frontend. These are aggregated via `/wcapi/choices/`.

**JSONField Pattern - `refs`:**

Many models have a `refs` JSONField for flexible linked data (evolved from 4D's `obGeneral`/`obRelate` objects):

```python
refs = {
    "links": {
        "contact": [{"id": 101, "attention": "John Doe"}, ...],
        "document": [{"id": 5, "name": "Contract.pdf"}, ...]
    },
    "meta": { ... }
}
```

### Frontend (r25)

**API Layer:**

```typescript
// src/api/wcapi.ts - mirrors vue2020/src/libs/urls.js patterns
getRecords(model_name, params)   // GET /wcapi/get/
saveRecord(model_name, payload)  // POST /wcapi/save/
```

**State Management:**
- Redux Toolkit for global state (replaces vue2020 DataStore + EventBus)
- React hooks for local/component state
- `useAuth()` hook provides current user with `role` field

**Component Patterns:**
- Feature pages in `src/apps/<feature>/` (replaces vue2020 views/)
- Reusable components in `src/components/` (replaces vue2020 components/)
- Modals follow `<Feature>Modal.tsx` naming

---

## Key Conventions

### Naming

| Context | Convention | Example | 4D Equivalent |
|---------|------------|---------|---------------|
| Django models | PascalCase | `Order`, `Contact` | Table name |
| Django fields | snake_case | `is_active`, `created_at` | Field name (was camelCase) |
| React components | PascalCase | `KanbanBoardPage`, `ProjectContactManager` | N/A |
| React files | PascalCase.tsx | `KanbanTaskModal.tsx` | N/A |
| API functions | camelCase | `getRecords`, `saveRecord` | WCapi methods |
| CSS classes | Tailwind utility classes | `className="flex items-center gap-2"` | N/A |

### Database

- All models inherit from `BaseModel` which provides: `id`, `uuid`, `is_active`, `created_at`, `updated_at`, `refs`
- Soft delete pattern: set `is_active = false` rather than deleting
- JSONFields for flexible/denormalized data (refs, translations, metadata)

### Authentication

- Session-based auth with Django
- User roles: `admin`, `manager`, `owner`, `staff`, `guest`
- Frontend checks `user.role` for permissions

---

## Working Agreement

### Execution Mode: Full Autonomy

**AI can execute without approval:**
- File operations (create, modify, delete)
- Terminal commands (npm, python, git, etc.)
- Database operations (migrations, management commands, queries)
- Package installations
- Git operations (branch, commit, push to feature branches)

**AI will confirm before:**
- Push to `main` or `dev` branches
- Destructive production operations
- Major architectural changes outside agreed scope

### Workflow

```
1. Developer describes the task
2. AI outlines the plan briefly
3. Developer confirms
4. AI executes all steps without stopping
5. Review results; fix any issues
```

### VS Code Settings for Agent Mode

```json
{
  "chat.agent.enabled": true,
  "github.copilot.chat.agent.runTasks.setupShell": "always",
  "chat.tools.autoApprove": true
}
```

### Documentation Practice

All significant work must be documented:

| Work Type | Document Location |
|-----------|-------------------|
| New features | `readmes/topics/<feature>.md` |
| API changes | `readmes/topics/api/` |
| Infrastructure | `readmes/topics/infrastructure/` |
| Integrations | `readmes/topics/<system>-integration.md` |

---

## Current State (January 2026)

### Recently Implemented

**Kanban Board** ([kanban-integration.md](topics/kanban-integration.md))
- Project-scoped contacts via `project.refs.links.contact[]`
- Contact Manager modal for add/remove contacts (role-based)
- Assignee dropdown in task modals uses project contacts
- "All projects" mode fetches all active contacts
- `populate_project_contacts` management command

### Active Branches

Check `git branch -a` for current work. Feature branches follow: `<feature-name>` or `<developer>_dev`

### Feature Migration Status

| Feature | vue2020 | r25 | Notes |
|---------|---------|-----|-------|
| Kanban Board | `KanbanPad.vue` | ✅ `KanbanBoardPage.tsx` | Drag-drop, project contacts |
| Gantt Chart | `GanttComponent.vue` | 🔄 In progress | Scheduling view |
| Orders | `OrderForm.vue` | ✅ `OrderDetailPage.tsx` | CRUD, line items |
| Invoices | `InvoiceForm.vue` | ✅ `InvoiceDetailPage.tsx` | CRUD, line items |
| Proposals | `ProposalForm.vue` | ✅ `ProposalDetailPage.tsx` | CRUD, line items |
| Customers | `CustomerForm.vue` | ✅ `CustomerDetailPage.tsx` | CRUD, contacts |
| Q&A Forms | `QAForm.vue` | 🔄 In progress | Dynamic forms |
| Maps | `MapPad.vue` | ⏳ Planned | Customer mapping |

---

## Quick Reference

### Start Development Servers

```bash
# Backend (wc3)
cd webClerk3
source bin/activate  # or venv/bin/activate
python manage.py runserver

# Frontend (r25)
cd React2025
pnpm dev
```

### Common Commands

```bash
# Django
python manage.py makemigrations
python manage.py migrate
python manage.py shell_plus
python manage.py populate_project_contacts --dry-run

# React
pnpm dev          # Start dev server
pnpm build        # Production build
pnpm test         # Run tests

# Git
git checkout -B <branch> origin/dev   # New branch from dev
git push -u origin <branch>           # Push new branch
```

### Key Files

| Purpose | File |
|---------|------|
| WCAPI client | `React2025/src/api/wcapi.ts` |
| Auth hook | `React2025/src/hooks/useAuth.ts` |
| Redux store | `React2025/src/store/` |
| Django settings | `webClerk3/webclerk3_api/settings.py` |
| URL routing | `webClerk3/webclerk3_api/urls.py` |
| Choices registry | `webClerk3/common/choices_registry.py` |

### Legacy Reference Files

| Purpose | File |
|---------|------|
| Vue API URLs | `vue2020/src/libs/urls.js` |
| Vue global state | `vue2020/src/libs/datastore.js` |
| Vue event bus | `vue2020/src/libs/eventbus.js` |
| 4D API handlers | `Sources/Methods/WCapiTask_*.4dm` |
| 4D business logic | `Sources/Methods/calc*.4dm`, `Parse*.4dm` |

### Documentation Index

| Document | Purpose |
|----------|---------|
| [00-copilot-workflow.md](00-copilot-workflow.md) | AI collaboration workflow |
| [01-architecture.md](01-architecture.md) | System architecture |
| [02-env-setup.md](02-env-setup.md) | Development environment setup |
| [03-api-integration.md](03-api-integration.md) | API integration guide |
| [topics/kanban-integration.md](topics/kanban-integration.md) | Kanban wc3↔r25 integration |

---

## For New AI Sessions

When starting a new conversation, the developer should:

1. Reference this document: *"Read `readmes/00-project-foundation.md` first"*
2. Mention the current task/feature
3. Reference any relevant topic READMEs
4. Point to legacy files if replicating existing functionality:
   - *"See `vue2020/src/components/OrderForm.vue` for reference"*
   - *"Check `Sources/Methods/calcOrder.4dm` for business logic"*

This bootstraps the AI with project context quickly.

### Searching Legacy Code

```bash
# Find 4D methods related to a feature
ls Sources/Methods/ | grep -i <keyword>

# Search inside 4D methods
grep -r "<pattern>" Sources/Methods/

# Find Vue components
ls vue2020/src/components/ | grep -i <keyword>
```

---

## Team

- **Bill James** - Lead developer
- Teammates share this foundation document for consistent AI collaboration

---

*Last updated: January 12, 2026*
