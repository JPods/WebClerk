# Gantt Chart Implementation

## Overview

Consolidated Gantt chart using SVAR Gantt (`@svar-ui/react-gantt`) supporting:
- **Single project view** - Display one project's tasks
- **Multi-project view** - Select and display multiple projects simultaneously  
- **Embeddable mode** - Use as component within other pages (e.g., ProjectDetail)
- **Critical path highlighting** - Identify tasks with zero slack
- **Baseline comparison** - Compare current vs original planned dates
- **Export options** - PNG and PDF export

---

## Architecture

```
src/apps/utils/gantt/
├── UnifiedGanttPage.tsx        # Main page wrapper (handles URL params) ✓
├── UnifiedGantt.tsx            # Core Gantt component (embeddable) ✓
├── GanttProjectSelector.tsx    # Multi-select project listbox ✓
├── GanttActionModal.tsx        # Task editing modal ✓
├── GanttTaskTemplate.tsx       # Custom task bar with badges ✓
├── ganttDataMapper.ts          # Transform API → SVAR format ✓
├── useGanttData.ts             # Data fetching hook ✓
├── GanttPage.tsx               # Shared utilities ✓
│
├── [DEPRECATED] KanbanGanttPage.tsx      # → Redirect to /gantt
├── [DEPRECATED] SvarGanttPage.tsx        # → Redirect to /gantt
├── [DEPRECATED] MultiProjectGanttPage.tsx # → Redirect to /gantt

src/context/
├── StaffBadgePrefsContext.tsx  # Fetches staff badge prefs on startup ✓
```

---

## Routes

| Route | Component | Description |
|-------|-----------|-------------|
| `/gantt` | UnifiedGanttPage | **Primary route** |
| `/gantt?project=123` | UnifiedGanttPage | Single project mode |
| `/gantt?projects=1,2,3` | UnifiedGanttPage | Pre-selected projects |
| `/kanban-gantt` | Redirect → `/gantt` | Legacy route |
| `/svar-gantt` | Redirect → `/gantt` | Legacy route |
| `/multi-project-gantt` | Redirect → `/gantt` | Legacy route |

---

## Usage Patterns

### 1. Full Page (Default)
```tsx
// Route: /gantt
<UnifiedGanttPage />
// Shows project selector sidebar + gantt chart
```

### 2. Pre-selected via URL
```tsx
// Route: /gantt?project=123  OR  /gantt?projects=123,456
<UnifiedGanttPage />
// Parses URL params, pre-selects projects
```

### 3. Embedded Single Project
```tsx
<UnifiedGantt 
  projectId="123" 
  showSelector={false}
  className="h-[600px]"
/>
```

### 4. Embedded Multi-Project
```tsx
<UnifiedGantt 
  initialProjectIds={["123", "456"]} 
  showSelector={true}
  compact={true}
/>
```

---

## Props API

```typescript
interface UnifiedGanttProps {
  // Single project mode
  projectId?: string;
  
  // Multi-project mode
  initialProjectIds?: string[];
  
  // UI options
  showSelector?: boolean;        // Default: true (false if projectId provided)
  showBreadcrumb?: boolean;      // Default: true for page, false for embedded
  compact?: boolean;             // Reduced padding/margins
  className?: string;
  
  // Behavior
  autoRefresh?: boolean;         // Default: true (5 min interval)
  onTaskClick?: (task: GanttMappedTask) => void;
}
```

---

## Data Flow

```
┌────────────────────────────────────────────────────────────────┐
│                    UnifiedGanttPage                            │
│  ┌──────────────┐   ┌────────────────────────────────────┐    │
│  │ GanttProject │   │           UnifiedGantt             │    │
│  │ Selector     │──▶│  ┌─────────────────────────────┐   │    │
│  │              │   │  │     useGanttData hook       │   │    │
│  │ [✓] Project1 │   │  │  - Fetches active projects  │   │    │
│  │ [✓] Project2 │   │  │  - Fetches actions per proj │   │    │
│  │ [ ] Project3 │   │  │  - Maps to SVAR format      │   │    │
│  └──────────────┘   │  └─────────────────────────────┘   │    │
│                     │          │                         │    │
│                     │          ▼                         │    │
│                     │  ┌─────────────────────────────┐   │    │
│                     │  │   SVAR <Gantt> Component    │   │    │
│                     │  │  - Timeline visualization   │   │    │
│                     │  │  - Drag to resize/move      │   │    │
│                     │  │  - Double-click edit modal  │   │    │
│                     │  └─────────────────────────────┘   │    │
│                     └────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
```

---

## Technical Details

### Date Fallback Logic

Tasks without explicit dates use this priority:

```typescript
const resolveTaskStartDate = (task: ApiKanbanItem): Date => {
  // Priority order:
  // 1. dt_start (explicit start date)
  // 2. dt_expected (expected date)
  // 3. dt_deadline (use as proxy)
  // 4. Fallback: today - 5 days
};
```

### Project Color Coding

```typescript
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
```

### Auto-Refresh
- Every 5 minutes when idle
- Paused when edit modal is open
- Manual refresh button available

### Task Bar Badges

Each task bar displays badges for priority and assignee:

```
┌──────────────────────────────────────────────────┐
│ [M] [WJ] Task title here...                      │
│  │    │                                          │
│  │    └── Assignee initials (colored badge)      │
│  └─────── Priority: L/M/H/! (colored badge)      │
└──────────────────────────────────────────────────┘
```

**Priority Badge Colors:**
| Priority | Label | Color |
|----------|-------|-------|
| Low | L | Emerald |
| Medium | M | Amber |
| High | H | Orange |
| Critical | ! | Rose |

**Assignee Badge Colors:**
- **Staff contacts** - Auto-assigned unique color from 8-color palette
- **Non-staff** - Gray default
- **Custom** - Via `contact.prefs.badge`

### Badge Customization (contact.prefs.badge)

Staff members can customize their badge appearance by setting `prefs.badge` on their Contact record:

```json
{
  "prefs": {
    "badge": {
      "bg_color": "#dbeafe",    // Hex color for badge background
      "text_color": "#1d4ed8",  // Hex color for badge text
      "initials": "WJ"          // Optional: custom initials override
    }
  }
}
```

**Priority order for badge prefs:**
1. Inline prefs from `action.assigned_to[].prefs.badge` (task-level)
2. Context prefs from `contact.prefs.badge` (fetched on app startup)
3. Auto-assigned color (staff) or gray default (non-staff)

**StaffBadgePrefsContext:**
- Fetches all `is_staff=true` contacts on app startup
- Caches `prefs.badge` in React context
- Used by `GanttTaskTemplate` for badge rendering

---

## Advanced Features

### Critical Path Highlighting

Tasks with zero slack (float) are on the critical path and displayed with a **red border**. The critical path represents the longest sequence of dependent tasks that determines the minimum project duration.

```typescript
// ganttDataMapper.ts - markCriticalPath()
// Calculates slack for each task using forward/backward pass
// Tasks with slack === 0 get task.critical = true
```

### Milestone Markers

Tasks with `duration = 0` are automatically displayed as **diamond (◆) markers** instead of bars:

```
Regular task:  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓
Milestone:     ◆
```

### Baseline Comparison (Δ Base Column)

Compare current schedule vs original planned dates:

| Column | Shows |
|--------|-------|
| Δ Base | Variance in days: `+3d` (delayed, red), `-2d` (ahead, green), `—` (no baseline) |

**Backend fields (Action model):**
- `dt_start_original` - Original planned start date (BigIntegerField, ms timestamp)
- `dt_end_original` - Original planned end date (BigIntegerField, ms timestamp)

**Set Baseline button:**
- Saves current `dt_start` → `dt_start_original` 
- Saves current `dt_deadline` → `dt_end_original`
- For all visible tasks

### Slack/Float Display

The **Slack** column shows how much buffer each task has before it impacts the project:

| Value | Meaning |
|-------|---------|
| `0d` (red) | Critical path - no buffer |
| `3d` | 3 days of slack available |
| `—` | Cannot calculate (missing dependencies) |

### Export Options

Located in the toolbar dropdown:

- **Export PNG** - Captures the Gantt chart using `html2canvas`
- **Export PDF** - Opens browser print dialog (Ctrl+P) for PDF save

### Undo/Redo

Track changes to task dates with full undo/redo support:

| Action | Shortcut |
|--------|----------|
| Undo | `Ctrl+Z` (Mac: `Cmd+Z`) |
| Redo | `Ctrl+Shift+Z` or `Ctrl+Y` |

- Up to 50 actions stored in history
- Toolbar buttons show count: `↶ (3)`, `↷ (1)`
- Only tracks date changes (drag operations)

### Link Deletion

Right-click on a dependency link arrow to delete:

```
Task A ──────▶ Task B
        (right-click)
        ┌─────────────┐
        │ Delete Link │
        └─────────────┘
```

---

## API Integration

| Endpoint | Purpose |
|----------|---------|
| `getRecords("project", { is_active: true })` | Fetch active projects |
| `Actions.get({ project_id, is_active: true })` | Fetch actions per project |
| `patchAction(payload)` | Update task dates/progress |

---

## Implementation Status

### ✅ Completed

- [x] Core `UnifiedGantt` component with props API
- [x] `UnifiedGanttPage` wrapper with URL param parsing
- [x] `GanttProjectSelector` multi-select listbox
- [x] `useGanttData` hook for data fetching
- [x] `ganttDataMapper.ts` API → SVAR transformation
- [x] Project color coding
- [x] Scale presets (Month/Week)
- [x] Task drag to resize/move
- [x] Double-click edit modal
- [x] Auto-refresh (5 min) with pause on modal
- [x] Manual refresh button
- [x] Route configuration (`/gantt`)
- [x] Redirects from legacy routes
- [x] `GanttTaskTemplate` with priority/assignee badges
- [x] `StaffBadgePrefsContext` for badge customization
- [x] Support for `contact.prefs.badge` customization

### ⏳ Remaining Work

- [ ] **Type Cleanup** - Remove `@ts-nocheck` from `UnifiedGantt.tsx`
  - Field name alignment: `priority` → `priority_value`
  - BoardData: `columnOrder` → `column_order`
  - KanbanColumn: `taskIds` → `task_ids`
  
- [ ] **Navigation Update** - Update AppSidebar links to use `/gantt`
  - Current: `/svar-gantt` and `/multi-project-gantt` (line 179, 184)
  - Target: Single `/gantt` link
  
- [ ] **Deprecation Cleanup** - Remove old files after testing
  - `KanbanGanttPage.tsx`
  - `SvarGanttPage.tsx`  
  - `MultiProjectGanttPage.tsx`
  
- [ ] **Documentation** - Remove old README files
  - `README-GANTT-IMPLEMENTATION.md`
  - `README-UNIFIED-GANTT.md`

### ✅ Recently Completed

- [x] **Critical Path Highlighting** - Tasks on critical path have red borders (Feb 2026)
- [x] **Milestone Support** - Tasks with duration=0 displayed as diamond markers
- [x] **Link Deletion** - Right-click context menu to delete task dependencies
- [x] **Baseline Comparison** - "Δ Base" column shows variance from original dates
  - New fields: `dt_start_original`, `dt_end_original` on Action model
  - Set Baseline button saves current dates as baseline
- [x] **Slack/Float Display** - "Slack" column shows buffer in days (0d = red/critical)
- [x] **Export to PNG** - Uses html2canvas to capture chart
- [x] **Export to PDF** - Opens print dialog for printing/PDF
- [x] **Undo/Redo** - History stacks for task changes
  - Keyboard: `Ctrl+Z` (undo), `Ctrl+Shift+Z` or `Ctrl+Y` (redo)
  - Toolbar buttons with history count indicators

### 🔮 Future Enhancements

- [ ] Resource view (grouped by assignee)
- [ ] Gantt baseline bars (visual ghost bars showing original schedule)

---

## Features

| Feature | Status |
|---------|--------|
| Task drag to resize (change dates) | ✓ |
| Task drag to move (change start/end) | ✓ |
| Double-click to edit (modal) | ✓ |
| Progress bar visualization | ✓ |
| Project color coding | ✓ |
| Priority badges on task bars | ✓ |
| Assignee badges with unique colors | ✓ |
| Custom badge prefs (contact.prefs.badge) | ✓ |
| Scale presets (Month/Week) | ✓ |
| Auto-refresh (5 min interval) | ✓ |
| Manual refresh button | ✓ |
| Multi-language task titles | ✓ |
| URL-based project selection | ✓ |
| Embeddable component | ✓ |
| **Critical path highlighting** | ✓ |
| **Milestone markers (♦)** | ✓ |
| **Link deletion (right-click)** | ✓ |
| **Baseline comparison (Δ Base column)** | ✓ |
| **Slack/float display column** | ✓ |
| **Export to PNG** | ✓ |
| **Export to PDF** | ✓ |
| **Undo/Redo (Ctrl+Z/Y)** | ✓ |
| **Set Baseline button** | ✓ |

---

## Quick Start

```bash
# Navigate to /gantt in browser
# Select projects from left sidebar
# Use Month/Week buttons to change scale
# Drag tasks to resize or move dates
# Double-click task to open edit modal
```
