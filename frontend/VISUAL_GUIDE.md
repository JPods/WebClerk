# 🎨 Advanced Data Table - Visual Guide

## Component Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        ADVANCED DATA TABLE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────┐  ┌──────────────────────────────────┐│
│  │ 🔍 Search...              ✕ │  │ [Filters] [Clear] [Export ▼] │+ │││
│  └─────────────────────────────┘  └──────────────────────────────────┘│
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ 🔍 FILTERS PANEL (when enabled)                                 │  │
│  ├─────────────┬─────────────┬─────────────┬─────────────┐        │  │
│  │   Status ▼  │  Project ▼  │  Column ▼   │ Priority ▼  │        │  │
│  └─────────────┴─────────────┴─────────────┴─────────────┘        │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ Total: 250  │  Filtered: 42  │  Selected: 5                    │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ ☑ Action         │Project│Status│Column│Priority│Progress│...   │  │
│  ├─────────────────────────────────────────────────────────────────┤  │
│  │ ☑ Update login  │ PRJ1  │Active│  To Do│  High │ ████░░ 60%│  │  │
│  │ ☐ Fix bug #123  │ PRJ2  │Active│ Done  │  Low  │ ██████100%│  │  │
│  │ ☑ Add feature   │ PRJ1  │Active│Prog..│Medium │ ███░░░ 50%│  │  │
│  │ ☐ Review code   │ PRJ3  │Active│Review│Critical█░░░░░ 20%│  │  │
│  │ ☑ Write docs    │ PRJ1  │Active│ Done  │  Low  │ ██████100%│  │  │
│  │                         ...                                     │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │     ◀ Previous  │  1  2  [3]  4  5  │  Next ▶  │  Rows: [10▼]│  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Export Dropdown Menu

```
                       ┌───────────────────────────┐
                       │  EXPORT ALL DATA          │
                       ├───────────────────────────┤
  [Export ▼]  ────────▶│ 📗 Excel (250 rows)       │
  (hover to open)      │ 📕 PDF (250 rows)         │
                       ├───────────────────────────┤
                       │  EXPORT SELECTED          │
                       ├───────────────────────────┤
                       │ 📗 Excel (5 selected)     │
                       │ 📕 PDF (5 selected)       │
                       └───────────────────────────┘
```

---

## Action List Page Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Actions List                                               Home > Actions│
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ 🔍 Search actions, projects, assignees...                   ✕   │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  [🔍 Filters 3] [✕ Clear] [📥 Export ▼] [🗑️ Delete (5)] [+ New Action]│
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ Total: 127 │ Filtered: 45 │ Selected: 5                        │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────────┐│
│  │☑│Action              │Project │Status│Column│Prior│Prog│Assign│⚙│││
│  ├──┼────────────────────┼────────┼──────┼──────┼─────┼────┼──────┼─┤││
│  │☑│Update user login   │WebClerk│🟢 Act│ToDo  │🔴High│60% │John  │⚙│││
│  │ │Add logout feature  │        │      │      │     │    │Jane  │ │││
│  ├──┼────────────────────┼────────┼──────┼──────┼─────┼────┼──────┼─┤││
│  │☐│Fix navigation bug  │CRM App │🟢 Act│Prog  │🟡Med │30% │-     │⚙│││
│  │ │Broken mobile menu  │        │      │      │     │    │      │ │││
│  ├──┼────────────────────┼────────┼──────┼──────┼─────┼────┼──────┼─┤││
│  │☑│Write documentation │WebClerk│🟢 Act│Done  │🟢Low │100%│John  │⚙│││
│  │ │API endpoint docs   │        │      │      │     │    │+2    │ │││
│  ├──┼────────────────────┼────────┼──────┼──────┼─────┼────┼──────┼─┤││
│  │☐│Review PR #456      │ERP Sys │🟢 Act│Review│⚫Crit│20% │Sarah │⚙│││
│  │ │Security updates    │        │      │      │     │    │Mike  │ │││
│  ├──┼────────────────────┼────────┼──────┼──────┼─────┼────┼──────┼─┤││
│  │☑│Deploy to staging   │WebClerk│🟢 Act│Test  │🟡Med │85% │DevOps│⚙│││
│  │ │                    │        │      │      │     │    │      │ │││
│  └────────────────────────────────────────────────────────────────────┘│
│                                                                         │
│  Pagination: ◀ Previous │ 1 2 [3] 4 5 │ Next ▶ │ Rows per page: 10 ▼ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

Legend:
  ☑ = Selected checkbox
  ☐ = Unselected checkbox
  ⚙ = Actions dropdown (View/Edit/Delete)
  🟢 = Green badge (Active status)
  🔴 = Red badge (High priority)
  🟡 = Yellow badge (Medium priority)
  🟢 = Green badge (Low priority)
  ⚫ = Black badge (Critical priority)
```

---

## Badge & Progress Examples

### Status Badges
```
┌─────────┐  ┌───────────┐  ┌──────────┐
│ 🟢 Active│  │ ⚪ Inactive│  │ 🔵 Pending│
└─────────┘  └───────────┘  └──────────┘
```

### Priority Badges
```
┌──────────┐  ┌─────────┐  ┌──────────┐  ┌───────────┐
│ 🟢 Low    │  │🟡 Medium│  │🔴 High   │  │⚫ Critical│
└──────────┘  └─────────┘  └──────────┘  └───────────┘
```

### Progress Bars
```
0%:   ░░░░░░░░░░ 0%
20%:  ██░░░░░░░░ 20%
50%:  █████░░░░░ 50%
75%:  ███████░░░ 75%
100%: ██████████ 100%
```

### Assignee Pills
```
┌──────┐ ┌──────┐
│ John │ │ Jane │
└──────┘ └──────┘

┌──────┐ ┌──────┐ ┌────┐
│ John │ │ Jane │ │ +2 │  (when more than 2 assignees)
└──────┘ └──────┘ └────┘
```

---

## Filter Panel (Expanded)

```
┌─────────────────────────────────────────────────────────────────────┐
│  🔍 FILTER PANEL                                          [Toggle ▲]│
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌──────┐│
│  │ Status        │  │ Project       │  │ Column        │  │ Prior││
│  │ ▼ Active      │  │ ▼ WebClerk    │  │ ▼ In Progress │  │ ▼ All││
│  │   All         │  │   All         │  │   All         │  │      ││
│  │   Active      │  │   WebClerk    │  │   To Do       │  │      ││
│  │   Inactive    │  │   CRM App     │  │   In Progress │  │      ││
│  │   Pending     │  │   ERP System  │  │   Done        │  │      ││
│  └───────────────┘  └───────────────┘  └───────────────┘  └──────┘│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Mobile View (< 768px)

```
┌─────────────────────────┐
│  Actions List        ≡  │
├─────────────────────────┤
│                         │
│  ┌───────────────────┐  │
│  │ 🔍 Search...    ✕ │  │
│  └───────────────────┘  │
│                         │
│  [🔍] [✕] [📥] [+]     │
│  (icon buttons)         │
│                         │
│  ┌───────────────────┐  │
│  │ Total: 127        │  │
│  │ Selected: 5       │  │
│  └───────────────────┘  │
│                         │
│  ┌───────────────────┐  │
│  │ ☑ Update login    │  │
│  │ 📘 WebClerk       │  │
│  │ 🟢 Active | ToDo  │  │
│  │ 🔴 High | 60%     │  │
│  │ 👤 John, Jane     │  │
│  │ [👁️] [✏️] [🗑️]    │  │
│  └───────────────────┘  │
│                         │
│  ┌───────────────────┐  │
│  │ ☐ Fix nav bug     │  │
│  │ 📘 CRM App        │  │
│  │ 🟢 Active | Prog  │  │
│  │ 🟡 Medium | 30%   │  │
│  │ 👤 Unassigned     │  │
│  │ [👁️] [✏️] [🗑️]    │  │
│  └───────────────────┘  │
│                         │
│  (swipe to scroll →)    │
│                         │
│  ◀  1 2 [3] 4  ▶       │
│                         │
└─────────────────────────┘
```

---

## Loading State

```
┌─────────────────────────────────────────┐
│                                         │
│            ⟳ Loading...                 │
│                                         │
│         ┌─────────────┐                 │
│         │   ●●●●●●●   │                 │
│         │   Spinner   │                 │
│         │   Animation │                 │
│         └─────────────┘                 │
│                                         │
│       Loading data...                   │
│                                         │
└─────────────────────────────────────────┘
```

---

## Empty State

```
┌─────────────────────────────────────────┐
│                                         │
│           No actions found              │
│                                         │
│      Try adjusting your search          │
│          or filters                     │
│                                         │
│         [+ Add New Action]              │
│                                         │
└─────────────────────────────────────────┘
```

---

## Color Palette

### Light Mode
```
Background:     #FFFFFF (white)
Surface:        #F9FAFB (gray-50)
Border:         #E5E7EB (gray-200)
Text Primary:   #111827 (gray-900)
Text Secondary: #6B7280 (gray-500)

Primary:        #3B82F6 (blue-600)
Success:        #10B981 (green-600)
Warning:        #F59E0B (yellow-600)
Error:          #EF4444 (red-600)
```

### Dark Mode
```
Background:     #111827 (gray-900)
Surface:        #1F2937 (gray-800)
Border:         #374151 (gray-700)
Text Primary:   #F9FAFB (gray-50)
Text Secondary: #9CA3AF (gray-400)

Primary:        #60A5FA (blue-400)
Success:        #34D399 (green-400)
Warning:        #FBBF24 (yellow-400)
Error:          #F87171 (red-400)
```

---

## Interactive Elements

### Hover States
```
Button:           background lightens +10%
Row:              background: gray-50 / gray-800
Link:             underline appears
Icon Button:      background circle appears
```

### Active States
```
Selected Row:     border-left: 4px blue
Active Filter:    background: blue-100 / blue-900
Sorted Column:    arrow icon visible
```

### Focus States
```
Input:            ring-2 ring-blue-500
Button:           ring-2 ring-offset-2
Checkbox:         ring-2 ring-blue-500
```

---

## Accessibility Features

- ✅ Keyboard navigation (Tab, Enter, Space)
- ✅ ARIA labels on interactive elements
- ✅ Screen reader support
- ✅ Focus indicators
- ✅ Semantic HTML
- ✅ Color contrast ratios (WCAG AA)
- ✅ Touch targets (min 44x44px)

---

## Animation & Transitions

```
Hover:           150ms ease-in-out
Focus:           200ms ease-in-out
Modal:           300ms ease-in-out
Dropdown:        200ms ease-in
Loading Spinner: 1s linear infinite
Progress Bar:    300ms ease-in-out
```

---

This visual guide shows the complete UI structure and design system of the Advanced Data Table component.
