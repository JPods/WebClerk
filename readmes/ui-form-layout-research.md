# Form Layout Research for Enterprise Software

## Overview

This document summarizes UX research on form layouts for enterprise applications where users interact with the software daily.

---

## Key Research Findings

### 1. Label Placement Studies (Luke Wroblewski / UXMatters)

- **Labels above fields** (Grid layout) have the fastest completion times in eye-tracking studies because users scan in a single vertical path
- **Labels to the left** (Horizontal layout) are preferred for **data-dense enterprise apps** where users become experts - it's more scannable once learned

### 2. Enterprise Software Specific Research

The Nielsen Norman Group recommends for **heavy daily use**:

- **Horizontal/inline labels** - Power users prefer density over ease of first-use
- **Consistent field widths** - Reduces cognitive load when scanning
- **Grouping related fields** - Card-based layouts support logical organization

### 3. Density vs. Usability Tradeoff

Research from Baymard Institute shows:

- **Novice users**: Prefer more whitespace (Grid, Two-Column)
- **Expert users** (daily enterprise): Prefer **compact/dense layouts** - they want to see more data without scrolling

---

## Layout Recommendations

| Layout | Best For |
|--------|----------|
| **Horizontal** | ✅ Best for daily enterprise use - scannable, professional, efficient |
| **Compact** | ✅ Great for power users who value density |
| **Grid** | Good for occasional users or onboarding |
| **Two-Column** | Good for complex forms with logical groupings |
| **Dense** | Niche - data entry specialists, 4D-style apps |

---

## Why Horizontal (Label-Left) is the Enterprise Standard

**Horizontal layout** is generally considered the gold standard for enterprise software because:

1. **Muscle memory** - Users develop spatial memory for field locations
2. **Scannable labels** - Labels align cleanly in a column, easy to scan vertically
3. **Industry standard** - Used by SAP, Salesforce, Oracle, and most ERP systems
4. **Reduced scrolling** - Horizontal layouts are typically more vertically compact than label-above layouts

---

## Our Implementation

Contact Detail pages support 5 layout options:

| Value | Label | Description |
|-------|-------|-------------|
| `grid` | Grid | 3-column grid layout with labels above inputs |
| `compact` | Compact | Dense 3-column with tighter spacing |
| `dense` | Dense | Ultra-compact with inline labels - maximum density |
| `horizontal` | Horizontal | 2-column with label to the left of entry area |
| `two-column` | Two Column | Card-based two-column layout |

Users can select their preferred layout via the layout selector, and their choice is persisted to localStorage.

---

## References

- Luke Wroblewski - "Web Form Design: Filling in the Blanks" (2008)
- Nielsen Norman Group - "Form Design Guidelines" 
- UXMatters - "Label Placement in Forms"
- Baymard Institute - "Form Usability" research

---

## Related Files

- `src/apps/core/models/contact/pages/ContactDetail.tsx` - Main contact detail with layout selector
- `src/apps/core/models/contact/pages/ContactDetailHorizontal.tsx` - Horizontal layout component
- `src/apps/core/models/contact/pages/ContactDetailTwoColumn.tsx` - Two-column layout component
- `src/apps/orgs/models/customer/pages/CustomerDisplay.tsx` - Customer detail with horizontal layout

---

## Detail Page Layout Pattern

The standard layout for model Detail pages follows this vertical structure:

```
┌────────────────────────────────────────┐
│  Header (Title, ID, Nav Arrows)        │
├────────────────────────────────────────┤
│  Toolbar (Save, Cancel, Edit, Delete)  │
├────────────────────────────────────────┤
│  Basic Information Panel (PERSISTENT)  │  ← Always visible, read-only in view mode
│  - Core scalar fields                  │     Editable form in edit/add mode
├────────────────────────────────────────┤
│  Tab Navigation                        │
├────────────────────────────────────────┤
│  Tab Content (scrollable)              │
│  - Financial Summary (collapsed)       │  ← Collapsed by default, expand on demand
│  - Tab-specific data panels            │
└────────────────────────────────────────┘
```

### Key Principles

| Element | Behavior | Rationale |
|---------|----------|-----------|
| **Basic Information** | Persistent, between toolbar and tabs | Users always need quick reference to core fields |
| **Financial Summary** | Below tabs, collapsed by default | Important but secondary; expand when needed |
| **Tab Content** | Scrollable | Keeps navigation fixed while browsing data |

### Component Placement

- **BasicInformationPanel** - Displays read-only scalar fields (display_name, email, phone, etc.)
- **Financial Summary** - Collapsible panel inside tab content area
- **Tab panels** - JSON aspect data (contacts, addresses, documents, etc.)

---

## CustomerDisplay.tsx Implementation

### Layout Choices

| Setting | Value | Rationale |
|---------|-------|----------|
| **Layout** | Horizontal | Label-left for enterprise power users |
| **Default Columns** | 3 | More density, less scrolling |
| **Label Width** | `w-20` (5rem) | Compact but readable |
| **Column Selector** | 2 or 3 | Persisted to localStorage for team review |
| **Default Mode** | View (read-only) | Edit button to switch to edit mode |

### Key Components

- **HorizontalField** - Reusable label-left field wrapper
- **Column Selector** - Toggle buttons (2/3) in tab bar, persisted to `customerDetail_columnCount`
- **Edit Button** - Local `isEditing` state for inline view→edit switching

### Grid Classes

```tsx
// Dynamic column layout
className={`grid grid-cols-1 ${columnCount === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-2'} gap-x-6 gap-y-1`}
```
