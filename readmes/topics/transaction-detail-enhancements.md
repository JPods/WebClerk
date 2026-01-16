# Transaction Detail Page Enhancements

This document describes the enhanced features implemented for transaction detail pages (Sales Orders, Purchase Orders, etc.) in the React2025 frontend.

## Overview

The transaction detail pages have been significantly enhanced with improved user experience, better data visibility, and streamlined workflows. These enhancements apply to all transaction types through the shared `TransactionDetailBase` component.

---

## Core UI Enhancements

### 1. Tab Badges with Counts

Dynamic badge indicators on tabs showing relevant counts:

- **Lines Tab**: Shows total line item count
- **Contacts Tab**: Shows number of linked contacts
- **Comments Tab**: Shows comment count
- **Actions Tab**: Shows count of pending actions

```tsx
// Example: Tab with badge
<Tab badge={lines.length}>Lines</Tab>
```

### 2. Unsaved Changes Warning

Prevents accidental loss of work by:

- Detecting when form data has been modified
- Showing browser confirmation dialog on navigation attempts
- Visual indicator in the toolbar when changes are pending

```tsx
// Uses beforeunload event
useEffect(() => {
  const handleBeforeUnload = (e: BeforeUnloadEvent) => {
    if (hasUnsavedChanges) {
      e.preventDefault();
      e.returnValue = '';
    }
  };
  window.addEventListener('beforeunload', handleBeforeUnload);
  return () => window.removeEventListener('beforeunload', handleBeforeUnload);
}, [hasUnsavedChanges]);
```

### 3. Toast Notifications

User feedback for all major actions:

- **Success**: Save, clone, delete operations
- **Error**: Validation failures, API errors
- **Info**: Status updates, confirmations

Integrated with existing Redux `toastSlice` for consistent messaging across the app.

### 4. Sticky Toolbar

The transaction toolbar remains visible when scrolling:

- Sticky positioning at top of viewport
- Backdrop blur effect for visual separation
- All action buttons always accessible

```tsx
<div className="sticky top-0 z-10 backdrop-blur-sm bg-white/90 dark:bg-slate-900/90">
  <TransactionToolbar ... />
</div>
```

---

## Line Item Features

### 5. Line Item Notes Expansion

Expandable rows reveal line-specific notes:

- **Public Notes** (amber): Visible to customers
- **Internal Notes** (blue): Internal use only
- **Warehouse Notes** (green): Shipping/fulfillment instructions

Click the expand icon to toggle note visibility for each line.

### 6. Bulk Line Actions

Select and operate on multiple lines at once:

- Checkbox selection per line
- "Select All" checkbox in header
- Bulk delete with confirmation
- Selection count indicator

```tsx
// Bulk actions bar appears when items selected
{selectedLineIds.size > 0 && (
  <div className="bg-blue-50 px-4 py-2">
    {selectedLineIds.size} lines selected
    <button onClick={handleBulkDelete}>Delete Selected</button>
  </div>
)}
```

### 7. Duplicate Line Button

One-click line duplication:

- Copies all line data including notes
- Appears in actions column
- Only visible in edit mode

### 8. Line Details Modal

Full-screen modal for comprehensive line editing:

**Location**: `src/apps/transactions/components/LineDetailsModal.tsx`

**Three Sections:**

1. **Details Tab**
   - Item code and description
   - Quantity and unit of measure
   - Warehouse assignment

2. **Pricing Tab**
   - Unit price with override capability
   - Unit cost display
   - Margin calculation
   - Extended price

3. **Notes Tab**
   - Public notes (customer-visible)
   - Internal notes (staff only)
   - Warehouse notes (fulfillment)

### 9. Open Item in New Window

Quick access to item details:

- External link icon in actions column
- Opens item record in new browser window
- Configurable window size (1000x800)

```tsx
const handleOpenItem = (itemIdOrCode: number | string) => {
  const path = typeof itemIdOrCode === 'number' 
    ? `/products/items/${itemIdOrCode}`
    : `/products/items/code/${itemIdOrCode}`;
  window.open(path, '_blank', 'width=1000,height=800');
};
```

### 10. Drag-and-Drop Line Reorder

Reorder lines by dragging:

**Location**: `src/apps/transactions/hooks/useDragAndDrop.ts`

- HTML5 Drag and Drop API
- Visual feedback during drag
- Drop indicators between rows

```tsx
const { getDragProps, getDragClasses } = useDragAndDrop({
  items: lines,
  onReorder: handleReorderLines,
});
```

### 11. Split Line Feature

Divide a line item across multiple shipments/allocations:

**Location**: `src/apps/transactions/components/SplitLineModal.tsx`

**Features:**
- Split quantity across 2+ allocations
- Assign different warehouses per split
- Set individual ship dates
- Add allocation-specific notes
- "Distribute Evenly" quick action
- Validation ensures all quantity allocated

---

## New Tab Components

### 12. Activity/Audit Log Tab

Timeline view of transaction history:

**Location**: `src/apps/transactions/components/ActivityLogTab.tsx`

**Activity Types:**
- Document created/updated
- Lines added/removed/modified
- Status changes
- Print/email events
- Shipments
- Payments

**Features:**
- Filter by activity type
- Grouped by date
- Expandable details for changes
- Shows old → new values for modifications

### 13. Attachments Tab

File management for transaction documents:

**Location**: `src/apps/transactions/components/AttachmentsTab.tsx`

**Features:**
- Drag-and-drop file upload
- File type icons (PDF, Word, Excel, Image)
- Image preview modal
- Download functionality
- Delete with confirmation
- File size display
- Upload progress indicator

**Supported Files:** PDF, Word, Excel, Images (up to 10MB)

---

## Additional Features

### 14. Print Preview Modal

Preview documents before printing:

**Location**: `src/apps/transactions/components/PrintPreviewModal.tsx`

**Print Options:**
- Show/hide prices
- Show/hide costs
- Show/hide notes
- Show/hide terms
- Number of copies
- Paper size (Letter/A4)

**Actions:**
- Print directly
- Download as PDF
- Email document
- Fullscreen preview

### 15. Quick Add Recent Items

Fast access to frequently used items:

**Location**: `src/apps/transactions/components/QuickAddRecent.tsx`

**Sections:**
- **Recent Items**: Items added in recent orders
- **Favorites**: User-marked favorite items

**Features:**
- Shows last quantity and price used
- Click to add with previous quantity
- Collapsible sections

---

## Component Exports

All new components are exported from the barrel file:

```tsx
// src/apps/transactions/components/index.ts

export { default as LineDetailsModal } from './LineDetailsModal';
export { default as SplitLineModal } from './SplitLineModal';
export { default as ActivityLogTab } from './ActivityLogTab';
export { default as PrintPreviewModal } from './PrintPreviewModal';
export { default as AttachmentsTab } from './AttachmentsTab';
export { default as QuickAddRecent } from './QuickAddRecent';
```

---

## Integration Example

Here's how these features integrate into a transaction detail page:

```tsx
// In SalesOrderDetail.tsx

import {
  LineDetailsModal,
  SplitLineModal,
  ActivityLogTab,
  AttachmentsTab,
} from '../../components';
import { useDragAndDrop } from '../../hooks/useDragAndDrop';

// State for modals
const [showLineModal, setShowLineModal] = useState(false);
const [selectedLine, setSelectedLine] = useState<TransactionLine | null>(null);
const [selectedLineIds, setSelectedLineIds] = useState<Set<number>>(new Set());
const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());

// Drag and drop
const { getDragProps, getDragClasses } = useDragAndDrop({
  items: lines,
  onReorder: (newLines) => updateFormData({ lines: newLines }),
});

// Render lines with all features
{lines.map((line, idx) => (
  <tr 
    key={line.id} 
    {...getDragProps(idx)}
    className={getDragClasses(idx)}
  >
    <td><input type="checkbox" checked={selectedLineIds.has(line.id)} /></td>
    <td><button onClick={() => toggleRowExpansion(line.id)}>▶</button></td>
    {/* ... line data cells ... */}
    <td>
      <button onClick={() => handleOpenLineDetails(line)}>Edit</button>
      <button onClick={() => handleOpenItem(line.item_code)}>Open Item</button>
      <button onClick={() => handleDuplicateLine(line.id)}>Duplicate</button>
    </td>
  </tr>
))}

// Modals
<LineDetailsModal
  line={selectedLine}
  isOpen={showLineModal}
  isEditing={isEditing}
  onClose={() => setShowLineModal(false)}
  onSave={handleLineModalSave}
  onOpenItem={handleOpenItem}
/>
```

---

## Related Documentation

- [QuickQuote Feature Specification](./quick-quote-specification.md) - Planned rapid quoting interface
- [Architecture Overview](../01-architecture.md) - System architecture
- [API Integration](../03-api-integration.md) - Backend API details

---

## Future Enhancements

Potential future improvements:

1. **Keyboard shortcuts** for common actions
2. **Line templates** for frequently ordered item groups
3. **Real-time collaboration** indicators
4. **Undo/redo** for line edits
5. **Advanced line search** within document
6. **Line grouping** by category or custom criteria
