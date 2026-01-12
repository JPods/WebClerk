# Kanban Board Integration: wc3 ↔ r25

> **Last Updated:** January 2026

This document describes how the Kanban board feature works between **webClerk3 (wc3)** — the Django backend — and **React2025 (r25)** — the React frontend.

---

## Overview

| Component | Role | Location |
|-----------|------|----------|
| **wc3 (backend)** | Serves data via WCAPI endpoints | `/Users/.../webClerk3/` |
| **r25 (frontend)** | Renders Kanban board UI | `/Users/.../React2025/` |

When the user navigates to **`http://localhost:5173/kanban-board`**, r25 calls wc3 APIs to:
1. Load the list of **active projects** (`is_active = true`), each with linked contacts in `refs.links.contact`
2. Populate **Contact dropdowns** (filter bar & task assignee):
   - **If a project is selected**: Uses the project's linked contacts from `refs.links.contact`
   - **If "All projects" is selected**: Fetches all active contacts via API
3. Fetch **Action** records filtered by project and/or contact (assignee)

> **📣 External Sharing:** Kanban actions can be shared with contacts outside the company (vendors, customers, partners). The contact list includes all active contacts linked to the project, not just internal staff. This enables external collaboration on project tasks.

---

## Route & Page Mapping

| Route | Page Component | Description |
|-------|----------------|-------------|
| `/kanban-board` | [KanbanBoardPage.tsx](../../src/apps/utils/kanban/KanbanBoardPage.tsx) | Main Kanban board |
| `/kanban-board-data` | [KanbanBoardDataPage.tsx](../../src/apps/utils/kanban/KanbanBoardDataPage.tsx) | Data-focused variant |
| `/kanban-gantt` | [KanbanGanttPage.tsx](../../src/apps/utils/kanban/KanbanGanttPage.tsx) | Gantt chart view |

Route definitions: [Routes.ts](../../src/routes/Routes.ts)

---

## Data Flow

```
┌────────────────────────────────────────────────────────────────────┐
│                         r25 (React Frontend)                        │
│                     http://localhost:5173/kanban-board              │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. On page load:                                                  │
│     └─► fetchProjects()   ──► GET /wcapi/get/?model_name=project   │
│                                &is_active=true&status=active       │
│         (Each project includes refs.links.contact[])               │
│                                                                     │
│  2. When project selected:                                         │
│     ├─► updateContactsFromProject() ← Uses project.refs.links.contact │
│     │   (No separate API call - contacts come from project data)   │
│     │                                                              │
│     └─► fetchActions()    ──► GET /wcapi/get/?model_name=action    │
│                                &project_id=<selected>              │
│                                                                     │
│  3. Contact Manager Modal (cog button):                            │
│     ├─► fetchAvailableContacts() ─► GET /wcapi/get/?model_name=contact │
│     │                                  &is_active=true              │
│     └─► saveRecord()      ──► POST /wcapi/save/                    │
│                                {model_name: "project", id, refs}   │
│                                                                     │
│  4. On card drag/drop:                                             │
│     └─► patchAction()     ──► POST /wcapi/save/                    │
│                                {model_name: "action", ...}         │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────┐
│                          wc3 (Django Backend)                       │
│                       http://localhost:8000                         │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Endpoint                      Model                Handler         │
│  ─────────────────────────────────────────────────────────────────  │
│  /wcapi/get/?model_name=...    Any registered      WcapiGetView    │
│  /wcapi/save/                  Any registered      WcapiSaveView   │
│                                                                     │
│  Key Models:                                                        │
│  • Project   (apps.transactions.models.project.Project)            │
│  • Action    (apps.core.models.action.Action)                      │
│  • Contact   (apps.orgs.models.contact.Contact)                    │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## API Endpoints Used

### 1. Get Active Projects

```http
GET /wcapi/get/?model_name=project&is_active=true&status=active&limit=500
```

**Response shape:**
```json
{
  "status": "success",
  "code": 200,
  "data": {
    "model_name": "project",
    "results": [
      {
        "id": 1,
        "name": "Project Alpha",
        "intent": "Build feature X",
        "status": "active",
        "is_active": true,
        "refs": {
          "links": {
            "contact": [101, 102, 103]
          }
        }
      }
    ],
    "total": 1
  }
}
```

### 2. Get Contacts (for Contact Manager)

```http
GET /wcapi/get/?model_name=contact&is_active=true&limit=500
```

> **Note:** This endpoint is called by the **Contact Manager Modal** when adding new contacts to a project. The main Contact dropdown now uses `project.refs.links.contact` data directly (no separate API call).

**Response shape:**
```json
{
  "status": "success",
  "code": 200,
  "data": {
    "model_name": "contact",
    "results": [
      {
        "id": 101,
        "name_first": "John",
        "name_last": "Doe",
        "attention": "John Doe",
        "email": "john@example.com",
        "is_active": true
      }
    ],
    "total": 1
  }
}
```

### 3. Get Actions (Kanban Tasks)

```http
GET /wcapi/get/?model_name=action&project_id=<id>
```

**Response shape:**
```json
{
  "status": "success",
  "code": 200,
  "data": {
    "model_name": "action",
    "results": [
      {
        "id": 1,
        "action": { "en": "Implement login", "es": "Implementar inicio de sesión" },
        "description": { "en": "Build OAuth2 flow" },
        "kanban_column": "InProcess",
        "priority": 2,
        "difficulty": 5,
        "percent_complete": 50,
        "assigned_to": [{ "id": 101, "name": "John Doe" }],
        "project_id": 1,
        "project_name": "Project Alpha"
      }
    ],
    "total": 1
  }
}
```

### 4. Update Action (Drag/Drop or Edit)

```http
POST /wcapi/save/
Content-Type: application/json

{
  "model_name": "action",
  "id": 1,
  "kanban_column": "Review",
  "sequence": 0
}
```

---

## r25 Frontend Components

### Key Files

| File | Purpose |
|------|---------|
| [KanbanBoardPage.tsx](../../src/apps/utils/kanban/KanbanBoardPage.tsx) | Main page component with project/contact selectors |
| [kanbanDataMapper.ts](../../src/apps/utils/kanban/kanbanDataMapper.ts) | Transforms API responses → board state |
| [KanbanColumn.tsx](../../src/components/kanban/KanbanColumn.tsx) | Individual column component |
| [KanbanTaskModal.tsx](../../src/components/kanban/KanbanTaskModal.tsx) | Task create/edit modal |
| [ProjectContactManager.tsx](../../src/components/kanban/ProjectContactManager.tsx) | Modal for managing project contacts |
| [userProfile.ts](../../src/api/userProfile.ts) | API functions: `Actions()`, `patchAction()` |
| [wcapi.ts](../../src/api/wcapi.ts) | Generic WCAPI helpers: `getRecords()`, `saveRecord()` |

### Project Select Logic

```typescript
// KanbanBoardPage.tsx ~line 866
const fetchProjects = useCallback(async () => {
  const response = await getRecords("project", {
    active: true,
    is_active: true,
    status: "active",
    limit: 500,
  });
  // Filter for active projects and extract refs.links.contact from each
  const activeRecords = rawRecords.filter((record) => resolveProjectActivity(record));
  const options = activeRecords.map(createProjectOption);
  // createProjectOption extracts contacts from refs.links.contact
  // ...
}, []);
```

### Contact Select Logic (Project-Scoped or All Contacts)

Contacts are populated based on the project selection:

**When a project is selected:** Uses the project's `refs.links.contact` data—no separate API call:

```typescript
// KanbanBoardPage.tsx
const updateContactsFromProject = useCallback((project: ProjectOption | undefined) => {
  if (!project?.contacts?.length) return;
  const options = project.contacts.map((contact) => ({
    id: String(contact.id),
    label: contact.attention || String(contact.id),
    searchName: (contact.attention || String(contact.id)).toLowerCase(),
  }));
  setContactOptions(options);
}, []);
```

**When "All projects" is selected:** Fetches all active contacts via API:

```typescript
// KanbanBoardPage.tsx
const fetchAllContacts = useCallback(async () => {
  const response = await getRecords("contact", { is_active: true, limit: 500 });
  // Build options from all active contacts
  const options = records.map((r) => ({
    id: String(r.id),
    label: r.attention || `Contact #${r.id}`,
    searchName: (r.attention || r.id).toLowerCase(),
  }));
  setContactOptions(options);
}, []);

// Triggered when project selection changes
useEffect(() => {
  if (selectedProjectId && selectedProject) {
    updateContactsFromProject(selectedProject);
  } else {
    // "All projects" - fetch all contacts
    void fetchAllContacts();
  }
}, [selectedProjectId, selectedProject, ...]);
```

This allows users to:
- Filter by contact across **all projects** when "All projects" is selected
- Filter by contact within a **specific project** when a project is selected

### Task Modal Assignee Dropdown

The **Assignee** field in the Create/Edit Task modals uses the same contacts (project-scoped or all):

```typescript
// KanbanTaskModal.tsx receives assigneeOptions from KanbanBoardPage
<KanbanTaskModal
  ...
  assigneeOptions={contactOptions}  // Same contacts as filter dropdown
  ...
/>

// In the modal, renders as a select dropdown when options exist
{assigneeOptions.length > 0 ? (
  <select value={formState.assignee} onChange={...}>
    <option value="">Select assignee...</option>
    {assigneeOptions.map((option) => (
      <option key={option.id} value={option.id}>{option.label}</option>
    ))}
  </select>
) : (
  <input placeholder="No contacts available" ... />
)}
```

### Contact Manager Modal

The **Contact Manager** (⚙️ cog button next to Contact dropdown) allows authorized users to manage which contacts are linked to a project:

```typescript
// ProjectContactManager.tsx

// Role-based permissions
const EDITABLE_ROLES = ["admin", "manager", "owner"];
const canEdit = hasEditPermission(user?.role);

// Add contact to project
const handleAddContact = (contact: ContactRecord) => {
  setContacts((prev) => [...prev, { id: contact.id, attention: contact.attention }]);
};

// Remove contact from project
const handleRemoveContact = (contactId: number | string) => {
  setContacts((prev) => prev.filter((c) => String(c.id) !== String(contactId)));
};

// Save changes to project.refs.links.contact
const handleSave = async () => {
  const payload = {
    id: Number(projectId),
    refs: {
      links: {
        contact: contacts.map((c) => ({ id: Number(c.id), attention: c.attention || "" })),
      },
    },
  };
  await saveRecord("project", payload);
};
```

---

## wc3 Backend Models

### Action Model

Location: [apps/core/models/action.py](../../../webClerk3/apps/core/models/action.py)

```python
class Action(BaseModel):
    # Multilingual titles and descriptions
    action = models.JSONField(default=dict)          # {"en": "...", "es": "..."}
    description = models.JSONField(default=dict)
    
    # Project linkage
    project_name = models.CharField(max_length=255)
    project_id = models.BigIntegerField(db_index=True)
    
    # Kanban workflow
    sequence = models.PositiveIntegerField(default=0)
    kanban_column = models.CharField(
        max_length=50, 
        choices=ACTION_KANBAN_COLUMNS, 
        default='Backlog'
    )
    priority = models.PositiveIntegerField(default=1)
    difficulty = models.PositiveIntegerField(default=10)
    percent_complete = models.PositiveIntegerField(default=0)
    
    # Assignment (JSON array of contact objects)
    assigned_to = models.JSONField(blank=True, null=True)
```

### Kanban Columns (Choices)

Location: [apps/core/choices.py](../../../webClerk3/apps/core/choices.py)

```python
ACTION_KANBAN_COLUMNS = (
    ('Backlog', 'Backlog'),
    ('Planning', 'Planning'),
    ('InProcess', 'In Process'),
    ('Review', 'Review'),
    ('Complete', 'Complete'),
)
```

### Project Model

Location: [apps/transactions/models/project.py](../../../webClerk3/apps/transactions/models/project.py)

```python
class Project(BaseModel):
    name = models.CharField(max_length=255)
    status = models.CharField(choices=STATUS_CHOICES, default="draft")
    is_active = models.BooleanField(default=True)  # inherited from BaseModel
    
    # refs.links.contact[] holds linked contact IDs
    refs = models.JSONField(default=default_refs)
```

---

## Project-Scoped Contacts (Implemented)

> **✅ IMPLEMENTED**
> 
> The Contact dropdown now shows only contacts linked to the selected project via `project.refs.links.contact[]`. Users can manage this list via the **Contact Manager Modal** (⚙️ cog button).

### Data Structure

Contacts are stored in each project's `refs.links.contact` as:
```json
{
  "refs": {
    "links": {
      "contact": [
        {"id": 101, "attention": "John Doe"},
        {"id": 102, "attention": "Jane Smith"}
      ]
    }
  }
}
```

### Populating Project Contacts (Backend)

A management command exists to populate all active projects with contact references:

```bash
# Populate all active projects with all active contacts
python manage.py populate_project_contacts

# Dry run to see what would change
python manage.py populate_project_contacts --dry-run

# Update a specific project only
python manage.py populate_project_contacts --project-id=123

# Clear existing contacts before populating
python manage.py populate_project_contacts --clear-first
```

### Managing Project Contacts (Frontend)

Users with appropriate roles (admin, manager, owner) can manage contacts via the **Contact Manager Modal**:

1. Select a project from the Project dropdown
2. Click the ⚙️ (cog) button next to the Contact dropdown
3. **Current Contacts**: Shows contacts linked to this project (can remove with 🗑️ button)
4. **Add Contacts**: Search and add available contacts (filtered by `is_active=true`)
5. Click **Save Changes** to persist to `project.refs.links.contact`

Role-based permissions:
- **Admin, Manager, Owner**: Can add/remove contacts
- **Other roles**: View-only access

---

## Testing

### Manual Testing Checklist

- [ ] Navigate to `/kanban-board` → Project dropdown populates with active projects
- [ ] "All projects" selected → Contact dropdown shows ALL active contacts
- [ ] "All projects" + Contact selected → Actions load for that contact across all projects
- [ ] Select a project → Actions load into columns (Backlog, Planning, InProcess, Review, Complete)
- [ ] Contact dropdown shows contacts from project's `refs.links.contact` (project-scoped)
- [ ] Click ⚙️ cog button → Contact Manager modal opens
- [ ] Contact Manager shows current project contacts
- [ ] Click "New Task" → Assignee dropdown shows available contacts
- [ ] Assignee dropdown shows "Select a project to see contacts" hint when no project selected
- [ ] Create task with assignee → Saves correctly with contact ID
- [ ] Edit task → Assignee dropdown pre-selects current assignee
- [ ] (If admin/manager/owner) Can remove contacts with 🗑️ button
- [ ] (If admin/manager/owner) Can search and add new contacts
- [ ] Save Changes in Contact Manager → Updates project.refs.links.contact
- [ ] Contact dropdown reflects changes after saving
- [ ] Drag a card between columns → API call made, card stays in new column after refresh
- [ ] Create new action → Modal works, saves to selected project
- [ ] Edit existing action → Modal pre-fills, changes persist
- [ ] Assign action to external contact (non-staff) → Saves correctly

### API Testing (curl)

```bash
# Get active projects (includes refs.links.contact for each)
curl "http://localhost:8000/wcapi/get/?model_name=project&is_active=true" \
  -H "Authorization: Bearer <token>"

# Get all active contacts (used by Contact Manager modal)
curl "http://localhost:8000/wcapi/get/?model_name=contact&is_active=true" \
  -H "Authorization: Bearer <token>"

# Get actions for project
curl "http://localhost:8000/wcapi/get/?model_name=action&project_id=1" \
  -H "Authorization: Bearer <token>"

# Update project contacts
curl -X POST "http://localhost:8000/wcapi/save/" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "project",
    "id": 1,
    "refs": {
      "links": {
        "contact": [
          {"id": 101, "attention": "John Doe"},
          {"id": 102, "attention": "Jane Smith"}
        ]
      }
    }
  }'

# Populate project contacts (Django management command)
python manage.py populate_project_contacts --dry-run
```

---

## Related Documentation

- [WCAPI Usage Guide](../../../webClerk3/readmes/04-wcapi-usage.md)
- [API Integration](../03-api-integration.md)
- [Action Model](../../../webClerk3/apps/core/models/action.py)
- [Project Model](../../../webClerk3/apps/transactions/models/project.py)
- [Populate Project Contacts Command](../../../webClerk3/apps/transactions/management/commands/populate_project_contacts.py)
- [Project Contact Manager Component](../../src/components/kanban/ProjectContactManager.tsx)
