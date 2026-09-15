# KanbanTaskModal Integration Plan

> **Goal**: Create a generic task/action modal for transaction contexts that can be reused across Order, Invoice, and other transaction detail pages.
>
> **Status**: ✅ IMPLEMENTED (2026-02-05)

---

## 📋 Implementation Summary

### Files Created

| File                            | Purpose                             |
| ------------------------------- | ----------------------------------- |
| `TransactionTaskModal.types.ts` | Type definitions for task modal     |
| `TransactionTaskModal.tsx`      | Generic task/action modal component |
| `useTransactionTasks.ts`        | Hook for CRUD operations on tasks   |

### Files Modified

| File                        | Changes                                |
| --------------------------- | -------------------------------------- |
| `TransactionToolbar.tsx`    | Added "Task" button with badge support |
| `TransactionDetailBase.tsx` | Added task-related props passthrough   |
| `index.ts`                  | Exported new components and types      |
| `OrderDetail.tsx`           | Integrated TransactionTaskModal        |

---

## 📋 Current State Analysis

### Existing Components

| Component                | Location                                                  | Purpose                                                             |
| ------------------------ | --------------------------------------------------------- | ------------------------------------------------------------------- |
| `KanbanTaskModal`        | `src/apps/utils/kanban/KanbanTaskModal.tsx`               | Full-featured Kanban task modal with translations, assignees, dates |
| `KanbanTaskModal` (copy) | `src/components/kanban/KanbanTaskModal.tsx`               | Duplicate - needs consolidation                                     |
| `ActionsModal`           | `src/apps/transactions/components/ActionsModal.tsx`       | Simple action modal for transactions (type, priority, description)  |
| `TransactionToolbar`     | `src/apps/transactions/components/TransactionToolbar.tsx` | Toolbar with save, clone, transfer, print, email, delete            |

### Gap Analysis

| Feature                     | KanbanTaskModal | ActionsModal   | Needed   |
| --------------------------- | --------------- | -------------- | -------- |
| Create/Edit modes           | ✅              | ✅             | ✅       |
| Multi-language translations | ✅              | ❌             | Optional |
| Priority selection          | ✅              | ✅             | ✅       |
| Assignee selection          | ✅              | Partial (text) | ✅       |
| Due date                    | ✅              | ✅             | ✅       |
| Start date                  | ✅              | ❌             | ✅       |
| Completed date              | ✅              | ❌             | Optional |
| Progress/Status             | ✅              | ❌             | ✅       |
| Difficulty                  | ✅              | ❌             | Optional |
| Project link                | ✅              | ❌             | ✅       |
| Transaction link            | ❌              | Implicit       | ✅       |
| Slide-out panel             | ✅              | ✅             | ✅       |
| Portal rendering            | ✅              | ✅             | ✅       |

---

## 🎯 Implementation Plan

### Phase 1: Create Generic TransactionTaskModal Component

**Location**: `D:\JPods\React2025\src\apps\transactions\components\TransactionTaskModal.tsx`

**Purpose**: A reusable task/action modal that bridges Kanban-style features with transaction context.

```
┌─────────────────────────────────────────────────────────────────┐
│  TransactionTaskModal (slide-out panel)                        │
├─────────────────────────────────────────────────────────────────┤
│  Header: "Create Task" / "Edit Task"                    [X]    │
├─────────────────────────────────────────────────────────────────┤
│  Form Fields:                                                   │
│  ┌───────────────────────┬───────────────────────────────────┐ │
│  │ Left Column           │ Right Column                      │ │
│  │ • Title*              │ • Priority (low/med/high/critical)│ │
│  │ • Description         │ • Status (todo/progress/done)     │ │
│  │ • Action Type         │ • Due Date                        │ │
│  │                       │ • Start Date                      │ │
│  │                       │ • Assigned To (dropdown)          │ │
│  └───────────────────────┴───────────────────────────────────┘ │
│                                                                 │
│  Optional Sections (collapsible):                              │
│  • Progress: [slider 0-100%]                                   │
│  • Difficulty: [fibonacci scale]                               │
│  • Project Link: [dropdown]                                    │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  Footer: [Cancel] [Delete (edit mode)] [Save]                  │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 2: Create Types File

**Location**: `D:\JPods\React2025\src\apps\transactions\components\TransactionTaskModal.types.ts`

```typescript
// Task form state aligned with wc3 Action model
interface TransactionTaskFormState {
  id?: number;
  title: string;
  description?: string;
  kind: TaskKind;
  priority: TaskPriority;
  status: TaskStatus;
  dt_start?: string;
  dt_deadline?: string;
  dt_completed?: string;
  progress?: number;
  difficulty?: number;
  assigned_to?: AssigneeInfo[];
  project_id?: number;
  // Transaction context
  parent_type?: string; // 'order', 'invoice', etc.
  parent_id?: number;
}
```

### Phase 3: Integrate with TransactionToolbar

**Modifications to**: `D:\JPods\React2025\src\apps\transactions\components\TransactionToolbar.tsx`

Add:

- "Add Task" button in toolbar
- Props for task management callbacks
- State management for modal open/close

### Phase 4: Integrate with OrderDetail

**Modifications to**: `D:\JPods\React2025\src\apps\transactions\models\order\pages\OrderDetail.tsx`

- Replace or augment `ActionsModal` with `TransactionTaskModal`
- Connect to Actions tab
- Wire up CRUD operations via `wcapi`

---

## 📁 File Structure After Implementation

```
src/apps/transactions/components/
├── index.ts                           # Updated exports
├── TransactionTaskModal.tsx           # NEW - Main modal component
├── TransactionTaskModal.types.ts      # NEW - Type definitions
├── TransactionTaskForm.tsx            # NEW - Form component (extracted)
├── ActionsModal.tsx                   # KEEP - Backward compatibility wrapper
├── TransactionToolbar.tsx             # MODIFIED - Add task button
└── ... (other existing components)
```

---

## 🔧 Implementation Steps

### Step 1: Create Type Definitions

- [ ] Create `TransactionTaskModal.types.ts`
- [ ] Define `TransactionTaskFormState`, `TaskKind`, `TaskPriority`, `TaskStatus`
- [ ] Define `TransactionTaskModalProps`

### Step 2: Create TransactionTaskModal Component

- [ ] Create base modal structure (slide-out panel)
- [ ] Implement form fields (title, description, type, priority, status)
- [ ] Add date pickers (start, due, completed)
- [ ] Add assignee dropdown with search
- [ ] Add progress slider
- [ ] Add project selector (optional)
- [ ] Implement create/edit mode logic

### Step 3: Create Hook for Task Management

- [ ] Create `useTransactionTasks.ts` hook
- [ ] Implement CRUD operations via wcapi
- [ ] Handle optimistic updates
- [ ] Error handling

### Step 4: Update TransactionToolbar

- [ ] Add "Add Task" button
- [ ] Add props: `onAddTask`, `showTaskButton`
- [ ] Handle modal state if managed internally

### Step 5: Integrate with OrderDetail

- [ ] Import TransactionTaskModal
- [ ] Connect to existing actions table
- [ ] Wire up create/edit/delete handlers
- [ ] Test full flow

### Step 6: Testing & Documentation

- [ ] Test create task flow
- [ ] Test edit task flow
- [ ] Test delete task
- [ ] Update README

---

## 🔄 API Integration

### Endpoints Used

```typescript
// Create action linked to transaction
POST /api/v1/action/
{
  action: { en: "Task title" },
  description: { en: "Description" },
  priority: 2,
  status: "In progress",
  dt_start: 1738800000000,
  dt_deadline: 1739404800000,
  parent_type: "order",
  parent_id: 123,
  project_id: 456,
  contact_id: 789
}

// Update action
PATCH /api/v1/action/{id}/

// Delete action
DELETE /api/v1/action/{id}/
```

---

## ✅ Acceptance Criteria

1. **Generic Modal**: `TransactionTaskModal` works standalone without Kanban context
2. **Create Mode**: Can create new task with required fields
3. **Edit Mode**: Can load existing task and update fields
4. **Transaction Context**: Task is linked to parent transaction (order_id, invoice_id, etc.)
5. **Toolbar Integration**: "Add Task" button appears in TransactionToolbar
6. **Backward Compatible**: Existing `ActionsModal` still works
7. **Consistent UX**: Matches existing slide-out panel styling

---

## 📅 Estimated Effort

| Phase                            | Effort        |
| -------------------------------- | ------------- |
| Phase 1: TransactionTaskModal    | 2-3 hours     |
| Phase 2: Types                   | 30 mins       |
| Phase 3: Toolbar integration     | 1 hour        |
| Phase 4: OrderDetail integration | 1-2 hours     |
| Testing & polish                 | 1 hour        |
| **Total**                        | **5-7 hours** |

---

## 🚀 Next Steps

1. **Confirm approach**: Review this plan
2. **Start Phase 1**: Create `TransactionTaskModal.tsx`
3. **Iterate**: Test with OrderDetail first, then expand to other transactions

---

## Questions to Resolve

1. Should translations be required for transaction tasks? (Recommend: No, optional)
2. Should Kanban columns be visible in transaction context? (Recommend: No, use status only)
3. Should we deprecate `ActionsModal` or keep both? (Recommend: Keep for simple cases)
