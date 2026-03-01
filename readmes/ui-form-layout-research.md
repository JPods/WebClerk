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

| Layout         | Best For                                                              |
| -------------- | --------------------------------------------------------------------- |
| **Horizontal** | ✅ Best for daily enterprise use - scannable, professional, efficient |
| **Compact**    | ✅ Great for power users who value density                            |
| **Grid**       | Good for occasional users or onboarding                               |
| **Two-Column** | Good for complex forms with logical groupings                         |
| **Dense**      | Niche - data entry specialists, 4D-style apps                         |

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

| Value        | Label      | Description                                        |
| ------------ | ---------- | -------------------------------------------------- |
| `grid`       | Grid       | 3-column grid layout with labels above inputs      |
| `compact`    | Compact    | Dense 3-column with tighter spacing                |
| `dense`      | Dense      | Ultra-compact with inline labels - maximum density |
| `horizontal` | Horizontal | 2-column with label to the left of entry area      |
| `two-column` | Two Column | Card-based two-column layout                       |

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
- `src/apps/communications/models/email/pages/EmailDetail.tsx` - Email detail with horizontal layout, tri-modal support

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

| Element               | Behavior                             | Rationale                                        |
| --------------------- | ------------------------------------ | ------------------------------------------------ |
| **Basic Information** | Persistent, between toolbar and tabs | Users always need quick reference to core fields |
| **Financial Summary** | Below tabs, collapsed by default     | Important but secondary; expand when needed      |
| **Tab Content**       | Scrollable                           | Keeps navigation fixed while browsing data       |

### Component Placement

- **BasicInformationPanel** - Displays read-only scalar fields (display_name, email, phone, etc.)
- **Financial Summary** - Collapsible panel inside tab content area
- **Tab panels** - JSON aspect data (contacts, addresses, documents, etc.)

---

## CustomerDisplay.tsx Implementation

### Layout Choices

| Setting             | Value            | Rationale                                 |
| ------------------- | ---------------- | ----------------------------------------- |
| **Layout**          | Horizontal       | Label-left for enterprise power users     |
| **Default Columns** | 3                | More density, less scrolling              |
| **Label Width**     | `w-20` (5rem)    | Compact but readable                      |
| **Column Selector** | 2 or 3           | Persisted to localStorage for team review |
| **Default Mode**    | View (read-only) | Edit button to switch to edit mode        |

### Key Components

- **HorizontalField** - Reusable label-left field wrapper
- **Column Selector** - Toggle buttons (2/3) in tab bar, persisted to `customerDetail_columnCount`
- **Edit Button** - Local `isEditing` state for inline view→edit switching

### Grid Classes

```tsx
// Dynamic column layout
className={`grid grid-cols-1 ${columnCount === 3 ? 'lg:grid-cols-3' : 'lg:grid-cols-2'} gap-x-6 gap-y-1`}
```

---

## EmailDetail.tsx Implementation

### Layout Choices

| Setting             | Value         | Rationale                                                           |
| ------------------- | ------------- | ------------------------------------------------------------------- |
| **Layout**          | Horizontal    | Label-left using `HorizontalField` component                        |
| **Default Columns** | 3             | More density, less scrolling                                        |
| **Column Selector** | Yes           | Persisted to `emailDetail_columnCount`                              |
| **Default Mode**    | add/edit/view | Tri-modal: add for new, view for read-only, edit for inline editing |
| **Inline Support**  | Yes           | Can be embedded in other pages via `inline` prop                    |

### Key Components

- **HorizontalField** - Reusable label-left field wrapper with icon support
- **ColumnSelector** - Toggle buttons (2/3) in form header, uses `useColumnCount` hook
- **SimpleDetailHeader** - Standard header with entity name, record ID/name, mode, back URL
- **SimpleDetailToolbar** - Save/Cancel/Edit buttons based on mode
- **DetailTabs** - Tab navigation below persistent overview

### Form Fields

| Field         | Type          | Icon        | Notes                                                       |
| ------------- | ------------- | ----------- | ----------------------------------------------------------- |
| `email`       | Input (email) | Mail        | Required, validated                                         |
| `name`        | Input (text)  | Type        | Display name                                                |
| `attention`   | Input (text)  | User        | Attention line                                              |
| `opt_out`     | DropDown      | BellOff     | Status: active, opted_out, bounced, invalid, spam_complaint |
| `is_primary`  | Checkbox      | Star        | Boolean via Controller                                      |
| `is_verified` | Checkbox      | CheckCircle | Boolean via Controller                                      |

### Tab Panels

| Tab       | Component         | Content            |
| --------- | ----------------- | ------------------ |
| contacts  | ContactLinksPanel | Linked contacts    |
| comments  | CommentsPanel     | User comments      |
| actions   | ActionsPanel      | Action items       |
| documents | DocumentsPanel    | Attached documents |
| raw       | `<pre>`           | JSON data dump     |

### Grid Classes

```tsx
// Uses shared utility function
className={getGridClassName(columnCount)}
```

### Storage Key

```tsx
const STORAGE_KEY = "emailDetail_columnCount";
```

---

## Detail Feature Checklist Badge

### Purpose

Every `model_nameDetail.tsx` page surfaces a small dev-only badge listing which
standard behaviours are implemented on that page. The badge is gated by the same
`VITE_DEBUG_BADGES='true'` env-var that controls `DevBadge`.

### Component

`src/components/common/DetailFeatureBadge.tsx`

```tsx
import { DetailFeatureBadge } from "@/components/common/DetailFeatureBadge";

<DetailFeatureBadge
  features={{
    autoSave: true,
    bgSaveChildren: true,
    print: false,
    clone: false,
    transactions: false,
  }}
/>
```

### Feature Flags

| Key              | Label         | Description                                                      |
| ---------------- | ------------- | ---------------------------------------------------------------- |
| `autoSave`       | Auto-Save     | Parent record auto-saves when user creates the first child       |
| `bgSaveChildren` | BG Children   | Child/related records save in background; close waits for them   |
| `print`          | Print         | Print / PDF export wired                                         |
| `clone`          | Clone         | Clone / duplicate record action available                        |
| `transactions`   | Txn Flow      | Transaction flow support (proposal → order → invoice chain)      |

### Integration Points

The badge is rendered automatically by two shared wrapper components:

| Component              | File                                                | How to enable                                      |
| ---------------------- | --------------------------------------------------- | -------------------------------------------------- |
| `SimpleDetailHeader`   | `src/components/common/SimpleDetailHeader.tsx`       | Pass `features={{}}` prop                          |
| `DetailShell`          | `src/components/common/DetailShell.tsx`              | Pass `features={{}}` prop                          |

Pages that build their own header (e.g. the three `ContactDetail` variants)
import and render `<DetailFeatureBadge>` directly next to `<DevBadge>`.

### Current Status

| Page                  | autoSave | bgSaveChildren | print | clone | transactions |
| --------------------- | :------: | :------------: | :---: | :---: | :----------: |
| `ContactDetail.tsx`   |    ✅    |       ✅       |       |       |              |
| `ContactDetail2.tsx`  |    ✅    |       ✅       |       |       |              |
| `ContactDetail3.tsx`  |    ✅    |       ✅       |       |       |              |
| All other Detail pages|          |                |       |       |              |

---

## Auto-Save & Background Children Pattern

### Problem

When a user opens a **new** record (add mode), the record has no ID yet. But
child records (communications, actions, documents, comments) need the parent's
ID as a foreign key. Previously, the user had to save first before linking any
children — a confusing chicken-and-egg UX.

### Solution — save-as-you-go

Two hooks work together:

| Hook                 | File                                                    | Responsibility                              |
| -------------------- | ------------------------------------------------------- | ------------------------------------------- |
| `useAutoSaveContact` | `src/apps/core/models/contact/hooks/useAutoSaveContact.ts` | `ensureContactId()` — returns existing ID or auto-saves the parent first |
| `useInflightSaves`   | `src/hooks/useInflightSaves.ts`                         | Tracks background save promises; `waitForAll()` for close guard |

### Flow

```
User clicks "Search Email" on an unsaved contact
  → openCommSelect() calls ensureContactId()
    → No ID exists → auto-save contact with required fields filled
      → Password auto-generated via crypto.randomUUID()
      → onContactCreated callback fires:
          • setFetchedData (transitions add → edit)
          • broadcasts "contact-saved" event
          • links to parent org via refs.links
    → Returns new contact ID
  → Comm search dialog opens with valid contactId
```

### Close Guard

`handleClose` is async. If `inflightCount > 0`, it calls `waitForAll()` before
closing the window, ensuring no background saves are silently dropped.

### Header Indicators

When auto-save or background saves are in progress, a blue spinner badge
appears in the header next to "Unsaved changes":

```tsx
{(autoSaveInProgress || inflightCount > 0) && (
  <span className="... text-blue-700 ...">
    <FaSpinner className="animate-spin" size={10} />
    {autoSaveInProgress ? "Auto-saving…" : `${inflightCount} saving…`}
  </span>
)}
```

### Unsaved Placeholder

When there is no `activeContactId`, the tab section renders a placeholder
instead of tabs:

```
Fill in the required fields above. Tabs & related records will appear
once the contact is saved — or use the search buttons to auto-save and
link records.
```
