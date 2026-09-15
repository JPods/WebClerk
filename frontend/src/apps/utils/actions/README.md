# Advanced Data Table and Action List Implementation

## 🎯 Overview

This implementation provides a beautiful, feature-rich data table component and an action list page with advanced capabilities including:

- ✅ **Sorting** - Click column headers to sort
- ✅ **Search** - Global search across all columns
- ✅ **Filtering** - Dynamic filters based on API data
- ✅ **Pagination** - Customizable rows per page
- ✅ **Selection** - Individual or select-all checkboxes
- ✅ **Export** - Download as Excel or PDF (all data or selected rows)
- ✅ **Responsive** - Mobile-friendly design
- ✅ **Dark Mode** - Full dark mode support
- ✅ **Reusable** - Can be used anywhere in the app

## 📁 Files Created

### 1. `src/components/common/AdvancedDataTable.tsx`
A fully-featured, reusable data table component with:
- Search bar with clear button
- Dynamic filter panel
- Export dropdown (Excel/PDF for all data or selected rows)
- Selection with count display
- Stats bar showing total, filtered, and selected counts
- Beautiful loading and no-data states
- Responsive design with dark mode support

### 2. `src/apps/utils/actions/ActionListPage.tsx`
Action list page demonstrating all table features:
- Fetches actions from API
- Displays action data with translated content
- Filters: Status, Project, Column, Priority
- Bulk delete functionality
- Individual action operations (View/Edit/Delete)
- Beautiful badges and progress bars
- Assignee pills with overflow handling

## 📦 Required Packages

Install these packages for full functionality:

```bash
npm install xlsx jspdf-autotable
```

### Package Details:
- **xlsx** (^0.18.5): Excel export functionality
- **jspdf-autotable** (^3.8.4): PDF table generation
- **jspdf**: Already installed ✅
- **react-data-table-component**: Already installed ✅

## 🚀 Usage

### Basic Usage

```tsx
import AdvancedDataTable from "@/components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";

const MyPage = () => {
  const columns: TableColumn<MyDataType>[] = [
    {
      name: "Name",
      selector: (row) => row.name,
      sortable: true,
    },
    {
      name: "Email",
      selector: (row) => row.email,
      sortable: true,
    },
  ];

  return (
    <AdvancedDataTable
      data={myData}
      columns={columns}
      loading={isLoading}
      enableExport={true}
      enableSelection={true}
    />
  );
};
```

### With Filters

```tsx
const filters = [
  {
    key: "status",
    label: "Status",
    type: "select",
    options: [
      { value: "active", label: "Active" },
      { value: "inactive", label: "Inactive" },
    ],
  },
  {
    key: "category",
    label: "Category",
    type: "text",
  },
];

<AdvancedDataTable
  data={data}
  columns={columns}
  filters={filters}
  enableExport={true}
/>
```

### With Selection and Custom Actions

```tsx
const [selectedRows, setSelectedRows] = useState([]);

<AdvancedDataTable
  data={data}
  columns={columns}
  enableSelection={true}
  onSelectionChange={setSelectedRows}
  customActions={
    <>
      <button onClick={handleBulkAction}>
        Bulk Action ({selectedRows.length})
      </button>
      <button onClick={handleAdd}>
        Add New
      </button>
    </>
  }
/>
```

## 🎨 Component Props

### AdvancedDataTable Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `data` | `T[]` | Required | Array of data objects |
| `columns` | `TableColumn<T>[]` | Required | Column definitions |
| `title` | `string` | "Data Table" | Table title |
| `loading` | `boolean` | `false` | Show loading spinner |
| `filters` | `ColumnFilter[]` | `[]` | Filter configurations |
| `enableExport` | `boolean` | `true` | Enable export buttons |
| `enableSelection` | `boolean` | `false` | Enable row selection |
| `onSelectionChange` | `(rows: T[]) => void` | - | Selection callback |
| `customActions` | `ReactNode` | - | Custom action buttons |
| `exportFileName` | `string` | "export" | Export file name prefix |
| `onRowClicked` | `(row: T) => void` | - | Row click handler |
| `searchPlaceholder` | `string` | "Search..." | Search input placeholder |
| `noDataMessage` | `string` | "No data available" | Empty state message |

### ColumnFilter Interface

```tsx
interface ColumnFilter {
  key: string;                          // Field key in data
  label: string;                        // Display label
  options?: Array<{                     // For select type
    value: string;
    label: string;
  }>;
  type?: "select" | "text" | "date";   // Filter input type
}
```

## 🎯 Features in Detail

### 1. Search
- Global search across all data fields
- Case-insensitive matching
- Clear button when text is entered
- Real-time filtering

### 2. Filters
- Toggle filter panel with button
- Active filter count badge
- Support for select dropdowns and text inputs
- Clear all filters button
- Filters persist until cleared

### 3. Export
- **Excel Export**:
  - Auto-sized columns
  - Preserves data types
  - Includes column headers
  - Date-stamped filename
  
- **PDF Export**:
  - Title and export date
  - Grid theme with alternating rows
  - Auto-pagination for large datasets
  - Responsive column widths

### 4. Selection
- Individual row selection
- Select all checkbox
- Selected count display
- Export selected rows only
- Bulk operations support

### 5. Stats Bar
- Total record count
- Filtered count (when filters applied)
- Selected count (when selection enabled)
- Real-time updates

## 🎨 Styling

The component uses Tailwind CSS with full dark mode support:
- Gray scale for light mode
- Dark gray scale for dark mode
- Blue accents for primary actions
- Semantic colors (green for export, red for delete, etc.)
- Smooth transitions and hover effects

## 📱 Responsive Design

- Mobile-friendly search and filters
- Collapsible filter panel on small screens
- Horizontal scroll for wide tables
- Touch-friendly buttons and interactions
- Adaptive layout for different screen sizes

## 🔗 Action List Page Routes

Add these routes to your router:

```tsx
// In your routes configuration
{
  path: "/actions",
  element: <ActionListPage />,
},
{
  path: "/actions/:id",
  element: <ActionDetailPage />,
},
{
  path: "/actions/:id/edit",
  element: <ActionEditPage />,
},
{
  path: "/actions/new",
  element: <ActionCreatePage />,
}
```

## 🎯 Action List Features

The Action List Page demonstrates all table capabilities with:

### Data Display
- **Action Title & Description**: Multi-line with translation support
- **Project Badge**: Color-coded project tags
- **Status Badge**: Active/inactive with semantic colors
- **Priority Badge**: Low/Medium/High/Critical with color coding
- **Progress Bar**: Visual progress indicator with percentage
- **Assignees**: Pills showing assigned staff (max 2 visible)
- **Due Date**: Formatted date display

### Filters
- Status dropdown
- Project dropdown
- Column dropdown
- Priority dropdown
- All dynamically populated from API data

### Actions
- **View**: Navigate to detail page
- **Edit**: Navigate to edit page
- **Delete**: Single action delete with confirmation
- **Bulk Delete**: Delete multiple selected actions

### Export
- Export all actions to Excel/PDF
- Export selected actions only
- Filename includes date stamp

## 🐛 Troubleshooting

### Missing Export Libraries

If export buttons don't work, install:
```bash
npm install xlsx jspdf-autotable
```

### TypeScript Errors

Add type declarations if needed:
```bash
npm install --save-dev @types/jspdf-autotable
```

### Dark Mode Not Working

Ensure ThemeContext is properly wrapped around your app:
```tsx
<ThemeProvider>
  <App />
</ThemeProvider>
```

## 🚀 Next Steps

1. **Install Dependencies**:
   ```bash
   npm install xlsx jspdf-autotable
   ```

2. **Add Routes**: Include action routes in your router

3. **Test the Page**: Navigate to `/actions` to see the table

4. **Customize**: Adapt the component for other data models

5. **Create Detail Pages**: Build ActionDetailPage and ActionEditPage

## 💡 Tips

- Use `useMemo` for column definitions to avoid re-renders
- Pre-process data before passing to the table for better performance
- Use the `customActions` prop to add page-specific buttons
- Leverage the `onRowClicked` handler for quick navigation
- Keep filter options updated based on current data

## 🎨 Design Philosophy

This implementation follows modern design principles:
- **Clean & Minimal**: No visual clutter
- **Intuitive**: Self-explanatory UI
- **Responsive**: Works on all devices
- **Accessible**: Keyboard navigation and screen reader support
- **Performant**: Optimized rendering with React best practices
- **Themeable**: Respects user's theme preference

## 📝 License

This component is part of the WebClerk React project.

---

**Created**: January 2026  
**Author**: AI Assistant  
**Version**: 1.0.0
