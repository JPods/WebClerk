# List Table Styling & Double-Click Navigation

## Overview

This document describes the consistent table styling system for all `model_nameList.tsx` components and the double-click navigation pattern for opening detail views.

## Features

### 1. Double-Click to Open Detail View

All list components support double-clicking a row to open the corresponding detail view.

**Implementation Pattern:**

```tsx
// In your List component
const handleDoubleClick = useCallback((row: any) => {
  setSelectedItem(row);
  setFormMode("view");
}, []);

// In AdvancedDataTable
<AdvancedDataTable
  data={items}
  columns={columns}
  onRowDoubleClicked={handleDoubleClick}
  // ... other props
/>
```

**Behavior:**
- Double-click opens the detail panel in "view" mode
- Single-click can still be used for row selection
- Action buttons remain available for edit/delete operations

### 2. Consistent Table Styling

All list tables use shared CSS classes defined in `src/index.css` that provide:

- Clean, modern appearance matching `LineDetailsModal.tsx` styling
- Light and dark mode support
- Hover states with visual feedback
- Alternating row colors for readability
- Proper spacing and typography

## CSS Classes Reference

### Core Table Styles

The following `react-data-table-component` classes are styled automatically:

| Class | Description |
|-------|-------------|
| `.rdt_TableHead` | Header row background (slate-50/slate-900) |
| `.rdt_TableHeadRow` | Header row border and height |
| `.rdt_TableCol` | Column header text (uppercase, tracking) |
| `.rdt_TableBody .rdt_TableRow` | Data rows with hover effects |
| `.rdt_TableCell` | Cell padding and typography |
| `.rdt_Pagination` | Pagination controls styling |

### Custom Utility Classes

Use these classes in your list components for consistent styling:

#### Action Buttons
```tsx
<div className="model-list-actions">
  <button onClick={() => handleView(row)} title="View">
    <FaEye className="text-blue-600" />
  </button>
  <button onClick={() => handleEdit(row)} title="Edit">
    <FaEdit className="text-green-600" />
  </button>
</div>
```

#### Status Badges
```tsx
// Success (green)
<span className="model-list-badge model-list-badge--success">Active</span>

// Warning (amber)
<span className="model-list-badge model-list-badge--warning">Pending</span>

// Error (red)
<span className="model-list-badge model-list-badge--error">Failed</span>

// Info (blue)
<span className="model-list-badge model-list-badge--info">New</span>

// Neutral (gray)
<span className="model-list-badge model-list-badge--neutral">Draft</span>
```

#### Currency/Price Formatting
```tsx
<span className="model-list-currency">
  ${price.toFixed(2)}
</span>
```

#### ID/Code Display
```tsx
<span className="model-list-code">
  {item.sku}
</span>
```

## Visual Design

### Light Mode
- Background: White with slate-50 alternating rows
- Headers: slate-50 background, slate-600 text
- Hover: blue-50 background with blue border
- Selected: blue-100 background

### Dark Mode
- Background: slate-800/900
- Headers: slate-900 background, slate-400 text
- Hover: blue-900/10 background
- Selected: blue-900/30 background

## Implementation Checklist

When creating a new list component:

- [ ] Import `AdvancedDataTable` from `@/components/common/AdvancedDataTable`
- [ ] Add `handleDoubleClick` callback for row double-click
- [ ] Pass `onRowDoubleClicked={handleDoubleClick}` to AdvancedDataTable
- [ ] Use `model-list-actions` class for action button containers
- [ ] Use `model-list-badge--*` classes for status indicators
- [ ] Use `model-list-currency` class for price/currency cells
- [ ] Use `model-list-code` class for IDs, SKUs, codes

## Example: ItemList.tsx

```tsx
import AdvancedDataTable from "@/components/common/AdvancedDataTable";
import ItemDetail from "./ItemDetail";

export default function ItemList() {
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [selectedItem, setSelectedItem] = useState<any | null>(null);

  // Double-click opens detail view
  const handleDoubleClick = useCallback((row: any) => {
    setSelectedItem(row);
    setFormMode("view");
  }, []);

  const columns = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id },
    { id: "name", name: "Name", selector: (row) => row.name },
    {
      id: "price",
      name: "Price",
      cell: (row) => (
        <span className="model-list-currency">
          ${row.price.toFixed(2)}
        </span>
      ),
    },
    {
      id: "status",
      name: "Status",
      cell: (row) => (
        <span className={`model-list-badge model-list-badge--${row.active ? 'success' : 'neutral'}`}>
          {row.active ? 'Active' : 'Inactive'}
        </span>
      ),
    },
    {
      id: "actions",
      name: "Actions",
      cell: (row) => (
        <div className="model-list-actions">
          <button onClick={() => handleView(row)}><FaEye /></button>
          <button onClick={() => handleEdit(row)}><FaEdit /></button>
        </div>
      ),
    },
  ], []);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
        <AdvancedDataTable
          data={items}
          columns={columns}
          onRowDoubleClicked={handleDoubleClick}
          // ... other props
        />
      </div>
      {formMode && (
        <div className="lg:col-span-2">
          <ItemDetail
            inline
            modeProp={formMode}
            dataProp={selectedItem}
          />
        </div>
      )}
    </div>
  );
}
```

## Related Files

- [src/index.css](../../../src/index.css) - CSS styles (search for "Model List Table Styles")
- [src/components/common/AdvancedDataTable.tsx](../../../src/components/common/AdvancedDataTable.tsx) - Base table component
- [src/apps/transactions/components/LineDetailsModal.tsx](../../../src/apps/transactions/components/LineDetailsModal.tsx) - Design reference
- [src/apps/products/models/item/pages/ItemList.tsx](../../../src/apps/products/models/item/pages/ItemList.tsx) - Reference implementation

## Changelog

| Date | Change |
|------|--------|
| 2026-01-30 | Initial implementation with double-click navigation and consistent CSS styling |
