# SVAR Gantt Implementation Plan

## Overview

Implement a multi-project Gantt chart view using SVAR Gantt (`@svar-ui/react-gantt` v2.3.3) that allows users to:
- Select multiple active projects via a listbox
- View all active actions across selected projects
- Automatically position actions without start dates to **today - 5 days**
- Edit, drag, and update tasks inline with API synchronization

---

## Architecture

### Component Structure

```
src/apps/utils/gantt/
├── SvarGanttPage.tsx           # Main page component (exists - needs refactoring)
├── GanttProjectSelector.tsx    # Multi-select project listbox (NEW)
├── ganttDataMapper.ts          # Transform API data → SVAR format (NEW)
├── useGanttData.ts             # Data fetching hook (NEW)
└── README-GANTT-IMPLEMENTATION.md
```

### Key Differences from Kanban

| Feature | Kanban | Gantt |
|---------|--------|-------|
| Project Selection | Single dropdown | Multi-select listbox |
| Data Scope | Single project OR all | Multiple selected projects |
| Default Date Handling | Today | Today - 5 days |
| Visual Layout | Columns (status-based) | Timeline (date-based) |

---

## Implementation Phases

### Phase 1: Project Multi-Select Component

**File:** `GanttProjectSelector.tsx`

```tsx
interface GanttProjectSelectorProps {
  projects: ProjectOption[];
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
  isLoading: boolean;
}
```

**Features:**
- Listbox with checkboxes for multi-selection
- "Select All" / "Clear All" buttons
- Search/filter within project list
- Show project name and action count badge
- Keyboard navigation support (Shift+Click for range)

**Styling:**
- Fixed height with scroll (max 300px)
- Visual indication of selected items
- Loading skeleton state

---

### Phase 2: Data Fetching Strategy

**File:** `useGanttData.ts`

```tsx
interface UseGanttDataOptions {
  projectIds: string[];
  enabled?: boolean;
}

interface UseGanttDataResult {
  tasks: ITask[];
  links: ILink[];
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}
```

**API Calls:**
1. Fetch all active projects: `getRecords("project", { is_active: true })`
2. For each selected project, fetch actions: `Actions.get({ project_id: projectId, is_active: true })`
3. Batch requests to avoid API overload (max 3 concurrent)

**Caching Strategy:**
- Cache project list for 5 minutes
- Cache actions per project for 2 minutes
- Invalidate on manual refresh or task update

---

### Phase 3: Date Fallback Logic

**Default Start Date Rule:**
```tsx
const DEFAULT_START_OFFSET_DAYS = -5; // Today minus 5 days

const resolveTaskStartDate = (task: ApiKanbanItem): Date => {
  // Priority order:
  // 1. dt_start (explicit start date)
  // 2. dt_expected (expected date)
  // 3. dt_due (due date - use as proxy for start)
  // 4. Fallback: today - 5 days
  
  const candidates = [
    task.dt_start,
    task.dt_expected,
    task.dt_due,
  ];
  
  for (const candidate of candidates) {
    const parsed = parseDateValue(candidate);
    if (parsed) {
      return parsed;
    }
  }
  
  // Fallback: today - 5 days
  const fallback = new Date();
  fallback.setDate(fallback.getDate() + DEFAULT_START_OFFSET_DAYS);
  return fallback;
};
```

---

### Phase 4: Gantt Data Mapping

**File:** `ganttDataMapper.ts`

Transform from API response to SVAR Gantt format:

```tsx
interface GanttMappedTask extends ITask {
  // Core SVAR fields
  id: string;
  text: string;
  start: Date;
  end: Date;
  duration: number;
  progress?: number;
  parent?: string;
  type: "task" | "milestone" | "summary";
  
  // Custom metadata
  projectId: string;
  projectName: string;
  columnId?: string;
  columnTitle?: string;
  priority?: string;
  assignee?: string;
}

const mapApiActionToGanttTask = (
  action: ApiKanbanItem,
  projectId: string,
  projectName: string
): GanttMappedTask => {
  const start = resolveTaskStartDate(action);
  const end = resolveTaskEndDate(action, start);
  const duration = calculateDurationDays(start, end);
  
  return {
    id: action.id,
    text: action.action_en || "Untitled",
    start,
    end,
    duration,
    progress: normalizeProgress(action.progress),
    type: action.refs?.links?.parent ? "task" : "task",
    parent: action.refs?.links?.parent,
    projectId,
    projectName,
    columnId: action.kanban_column,
    columnTitle: action.kanban_column,
    priority: mapPriorityLabel(action.priority),
    assignee: action.assigned_to?.[0]?.name,
  };
};
```

---

### Phase 5: Gantt Column Configuration

```tsx
const ganttColumns: IColumnConfig[] = [
  { 
    id: "text", 
    header: "Task", 
    flexgrow: 1, 
    sort: true,
    template: (task) => (
      <span title={task.details}>{task.text}</span>
    ),
  },
  {
    id: "projectName",
    header: "Project",
    width: 150,
    sort: true,
    template: (task) => (
      <span className="text-xs text-gray-500">{task.projectName}</span>
    ),
  },
  {
    id: "start",
    header: "Start",
    width: 100,
    align: "center",
    sort: true,
    template: (task) => formatShortDate(task.start),
  },
  {
    id: "duration",
    header: "Days",
    width: 60,
    align: "center",
    template: (task) => task.duration || "-",
  },
  {
    id: "progress",
    header: "%",
    width: 50,
    align: "center",
    template: (task) => `${Math.round((task.progress || 0) * 100)}%`,
  },
];
```

---

### Phase 6: Color Coding by Project

Each selected project gets a unique color from a preset palette:

```tsx
const PROJECT_COLOR_PALETTE = [
  "#3b82f6", // blue
  "#10b981", // emerald
  "#f59e0b", // amber
  "#8b5cf6", // violet
  "#ef4444", // red
  "#06b6d4", // cyan
  "#f97316", // orange
  "#84cc16", // lime
];

const getProjectColor = (projectId: string, selectedIds: string[]): string => {
  const index = selectedIds.indexOf(projectId);
  return PROJECT_COLOR_PALETTE[index % PROJECT_COLOR_PALETTE.length];
};
```

---

### Phase 7: Auto-Refresh & Manual Reload

Reuse the pattern from Kanban:

```tsx
// Auto-refresh every 5 minutes
const AUTO_REFRESH_INTERVAL = 5 * 60 * 1000;

// Pause when modal is open
const isAnyModalOpen = isEditModalOpen || isCreateModalOpen;

useEffect(() => {
  if (isAnyModalOpen) return;
  
  const interval = setInterval(() => {
    refetchActions();
  }, AUTO_REFRESH_INTERVAL);
  
  return () => clearInterval(interval);
}, [isAnyModalOpen, refetchActions]);
```

---

### Phase 8: Task Editing Modal

Reuse existing `KanbanTaskModal` component with minor adaptations:
- Pre-populate with task data
- On save, call `patchAction()` API
- Refresh Gantt data after successful save

---

## UI Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Gantt Chart                                    [Refresh] 2m ago│
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐  ┌────────────────────────────────────────┐ │
│ │ Projects        │  │ [Month] [Week]     Scale Controls      │ │
│ │ ┌─────────────┐ │  ├────────────────────────────────────────┤ │
│ │ │☑ Project A  │ │  │                                        │ │
│ │ │☑ Project B  │ │  │  ████████ Task 1                       │ │
│ │ │☐ Project C  │ │  │      ██████ Task 2                     │ │
│ │ │☐ Project D  │ │  │          ████████████ Task 3           │ │
│ │ │☑ Project E  │ │  │  ████ Task 4                           │ │
│ │ └─────────────┘ │  │                                        │ │
│ │ [Select All]    │  │                                        │ │
│ │ [Clear]         │  │                                        │ │
│ └─────────────────┘  └────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## State Management

```tsx
// Main page state
const [selectedProjectIds, setSelectedProjectIds] = useState<string[]>([]);
const [projectOptions, setProjectOptions] = useState<ProjectOption[]>([]);
const [isLoadingProjects, setIsLoadingProjects] = useState(true);

// Gantt data state
const [ganttTasks, setGanttTasks] = useState<ITask[]>([]);
const [ganttLinks, setGanttLinks] = useState<ILink[]>([]);
const [isLoadingActions, setIsLoadingActions] = useState(false);

// UI state
const [lastRefreshTime, setLastRefreshTime] = useState<Date | null>(null);
const [isAnyModalOpen, setIsAnyModalOpen] = useState(false);
```

---

## API Integration

### Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `getRecords("project", { is_active: true })` | Fetch active projects |
| `Actions.get({ project_id, is_active: true })` | Fetch actions per project |
| `patchAction(payload)` | Update task (dates, progress, etc.) |

### Payload for Task Update

```typescript
const updatePayload = {
  model_name: "action",
  id: taskId,
  dt_start: { mode: "update", value: newStartTimestamp },
  dt_end: { mode: "update", value: newEndTimestamp },
  "prefs.userdefined.progress": { mode: "update", value: progressPercent },
};
```

---

## Implementation Checklist

- [ ] **Phase 1:** Create `GanttProjectSelector` component
  - [ ] Multi-select listbox UI
  - [ ] Select All / Clear All buttons
  - [ ] Search filter
  - [ ] Loading state

- [ ] **Phase 2:** Create `useGanttData` hook
  - [ ] Fetch projects on mount
  - [ ] Fetch actions when selection changes
  - [ ] Batch API requests
  - [ ] Error handling

- [ ] **Phase 3:** Implement date fallback logic
  - [ ] Default to today - 5 days
  - [ ] Priority: dt_start → dt_expected → dt_due → fallback

- [ ] **Phase 4:** Create `ganttDataMapper.ts`
  - [ ] Map API response to SVAR format
  - [ ] Include project metadata

- [ ] **Phase 5:** Refactor `SvarGanttPage.tsx`
  - [ ] Add project selector sidebar
  - [ ] Connect to useGanttData hook
  - [ ] Apply project colors

- [ ] **Phase 6:** Add refresh functionality
  - [ ] Manual refresh button
  - [ ] Auto-refresh every 5 minutes
  - [ ] Pause when modal open

- [ ] **Phase 7:** Test & Polish
  - [ ] Performance with many projects
  - [ ] Edge cases (no actions, no dates)
  - [ ] Dark mode styling

---

## Notes

- The existing `SvarGanttPage.tsx` (1668 lines) has working SVAR Gantt integration but uses single-project filtering via column filters
- Reuse existing utilities from `kanbanDataMapper.ts` where applicable
- The `KanbanTaskModal` can be shared between Kanban and Gantt views
- Consider adding a "Link to Kanban" button for cross-navigation

---

## Timeline Estimate

| Phase | Effort |
|-------|--------|
| Phase 1-2 | 2-3 hours |
| Phase 3-4 | 1-2 hours |
| Phase 5-6 | 3-4 hours |
| Phase 7 | 1-2 hours |
| **Total** | **~8-12 hours** |
