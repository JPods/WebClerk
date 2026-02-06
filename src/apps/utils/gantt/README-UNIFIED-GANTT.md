# Unified Gantt Component

## Overview

Consolidated Gantt chart implementation using SVAR Gantt (`@svar-ui/react-gantt`) that supports:
- **Single project view** - Display one project's tasks
- **Multi-project view** - Select and display multiple projects simultaneously
- **Embeddable mode** - Use as a component within other pages (e.g., ProjectDetail)

## Architecture

```
src/apps/utils/gantt/
├── UnifiedGanttPage.tsx        # Main unified page component (NEW)
├── UnifiedGantt.tsx            # Core Gantt component (embeddable)
├── GanttProjectSelector.tsx    # Multi-select project listbox ✓
├── ganttDataMapper.ts          # Transform API → SVAR format ✓
├── useGanttData.ts             # Data fetching hook ✓
├── GanttPage.tsx               # Shared utilities ✓
│
├── [DEPRECATED] KanbanGanttPage.tsx      # Custom DnD implementation
├── [DEPRECATED] SvarGanttPage.tsx        # Single-project SVAR
├── [DEPRECATED] MultiProjectGanttPage.tsx # Multi-project SVAR
```

## Usage Patterns

### 1. Full Page with Project Selector (Default)

```tsx
// Route: /gantt
<UnifiedGanttPage />

// User sees:
// - Left sidebar: Project selector (multi-select)
// - Main area: Gantt chart with selected projects' tasks
```

### 2. Pre-selected Project(s) via URL

```tsx
// Route: /gantt?project=123
// Route: /gantt?projects=123,456,789
<UnifiedGanttPage />

// Parses URL params and pre-selects those projects
// Selector still visible for adding/removing
```

### 3. Single Project Mode (No Selector)

```tsx
// Embedded in ProjectDetailPage
<UnifiedGantt 
  projectId="123" 
  showSelector={false}
  className="h-[600px]"
/>

// Shows only project 123's tasks
// No sidebar selector
```

### 4. Embeddable Multi-Project

```tsx
// Dashboard widget showing specific projects
<UnifiedGantt 
  initialProjectIds={["123", "456"]} 
  showSelector={true}
  compact={true}
/>
```

## Props API

```typescript
interface UnifiedGanttProps {
  // Single project mode - provide ID, hide selector
  projectId?: string;
  
  // Multi-project mode - initial selection
  initialProjectIds?: string[];
  
  // UI options
  showSelector?: boolean;        // Default: true (false if projectId provided)
  showBreadcrumb?: boolean;      // Default: true for page, false for embedded
  compact?: boolean;             // Reduced padding/margins
  className?: string;            // Additional container classes
  
  // Behavior
  autoRefresh?: boolean;         // Default: true
  onTaskClick?: (task: GanttMappedTask) => void;
}
```

## Route Configuration

```typescript
// Routes.ts
static readonly gantt: string = "/gantt";

// protectedRoutesConfig.tsx
{ path: PageRoutes.gantt, element: <UnifiedGanttPage /> }

// Old routes (redirect to /gantt for backwards compat)
{ path: "/kanban-gantt", element: <Navigate to="/gantt" replace /> }
{ path: "/svar-gantt", element: <Navigate to="/gantt" replace /> }
{ path: "/multi-project-gantt", element: <Navigate to="/gantt" replace /> }
```

## Data Flow

```
┌────────────────────────────────────────────────────────────────┐
│                    UnifiedGanttPage                            │
│  ┌──────────────┐   ┌────────────────────────────────────┐    │
│  │ GanttProject │   │           UnifiedGantt             │    │
│  │ Selector     │──▶│  ┌─────────────────────────────┐   │    │
│  │              │   │  │     useGanttData hook       │   │    │
│  │ [projects]   │   │  │  - Fetches active projects  │   │    │
│  │ [✓] Project1 │   │  │  - Fetches actions per proj │   │    │
│  │ [✓] Project2 │   │  │  - Maps to SVAR format      │   │    │
│  │ [ ] Project3 │   │  └─────────────────────────────┘   │    │
│  └──────────────┘   │          │                         │    │
│                     │          ▼                         │    │
│                     │  ┌─────────────────────────────┐   │    │
│                     │  │   SVAR <Gantt> Component   │   │    │
│                     │  │  - Timeline visualization   │   │    │
│                     │  │  - Drag to resize/move      │   │    │
│                     │  │  - Task editing modal       │   │    │
│                     │  └─────────────────────────────┘   │    │
│                     └────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────┘
```

## Implementation Steps

### Phase 1: Create Core Component ✓
- [x] Extract reusable UnifiedGantt from MultiProjectGanttPage
- [x] Support projectId prop for single-project mode
- [x] Support initialProjectIds for multi-project mode
- [x] Conditional selector visibility

### Phase 2: Page Wrapper
- [x] UnifiedGanttPage handles URL params
- [x] Breadcrumb and page layout
- [x] Passes parsed params to UnifiedGantt

### Phase 3: Route Updates
- [ ] Add new /gantt route
- [ ] Add redirects for old routes
- [ ] Update navigation links

### Phase 4: Deprecation
- [ ] Add deprecation notices to old files
- [ ] Update documentation
- [ ] Remove old files after testing period

## Migration Notes

### From KanbanGanttPage
The custom DnD implementation (1949 lines) is replaced by SVAR's built-in drag support. All task editing functionality is preserved via the modal.

### From SvarGanttPage  
Single-project mode is now: `<UnifiedGantt projectId="123" showSelector={false} />`

### From MultiProjectGanttPage
This is the base for UnifiedGantt. The main change is extracting reusable props.

## Features Preserved

- ✓ Task drag to resize (change dates)
- ✓ Task drag to move (change start/end)
- ✓ Double-click to edit (modal)
- ✓ Progress bar visualization
- ✓ Project color coding
- ✓ Scale presets (Month/Week)
- ✓ Auto-refresh (5 min interval)
- ✓ Manual refresh button
- ✓ Multi-language support for task titles

## Known Issues & Future Work

### Type Cleanup Needed

The `UnifiedGantt.tsx` component currently uses `@ts-nocheck` because it was extracted
from `MultiProjectGanttPage.tsx` which has patterns that diverged from current type
definitions. The following areas need alignment:

1. **TaskFormState** - Field names changed (e.g., `priority` → `priority_value`)
2. **BoardData** - Property names changed (e.g., `columnOrder` → `column_order`)
3. **KanbanColumn** - Property names changed (e.g., `taskIds` → `task_ids`)
4. **KanbanTask** - Structure evolved to use `properties` object

**Priority:** Medium - Component works, but types should be cleaned up when refactoring.

### Future Enhancements

- [ ] Add task dependency links visualization
- [ ] Export to PNG/PDF
- [ ] Critical path highlighting
- [ ] Resource allocation view
- [ ] Baseline comparison
