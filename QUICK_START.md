# 🚀 Quick Integration Guide

## Step-by-Step Setup

### 1. ✅ Packages Already Installed

The following packages have been installed:
```bash
✓ xlsx
✓ jspdf-autotable
```

### 2. 📁 Files Created

All files are ready in your project:
```
src/
├── components/
│   └── common/
│       └── AdvancedDataTable.tsx  ✅ Main component
│
└── apps/
    └── utils/
        ├── actions/
        │   ├── ActionListPage.tsx  ✅ Complete example
        │   ├── index.ts           ✅ Exports
        │   └── README.md          ✅ Documentation
        │
        └── examples/
            └── ContactListExample.tsx ✅ Usage example
```

### 3. 🔗 Add Route (Required)

Open your router configuration file and add:

**Option A: Using React Router v6**
```tsx
// In your routes file (e.g., src/routes/Routes.tsx)
import ActionListPage from "@/apps/utils/actions/ActionListPage";

// Add to your routes array:
{
  path: "/actions",
  element: <ActionListPage />,
}
```

**Option B: In App.tsx directly**
```tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import ActionListPage from "./apps/utils/actions/ActionListPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* ... other routes ... */}
        <Route path="/actions" element={<ActionListPage />} />
      </Routes>
    </BrowserRouter>
  );
}
```

### 4. 🔗 Add to Navigation (Optional)

Add a menu item to access the page:

```tsx
// In your sidebar/navigation component
<Link to="/actions">
  <FaList /> Actions List
</Link>
```

### 5. 🎯 Test It!

1. **Start your dev server** (if not running):
   ```bash
   npm run dev
   ```

2. **Navigate to**: `http://localhost:5173/actions`

3. **Try these features**:
   - ✅ Type in search box
   - ✅ Click "Filters" button
   - ✅ Select a filter option
   - ✅ Click column headers to sort
   - ✅ Select checkboxes
   - ✅ Hover over "Export" and select Excel
   - ✅ Check your Downloads folder!

---

## 🎨 Use in Your Own Pages

### Basic Example

```tsx
import AdvancedDataTable from "@/components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";

// 1. Define your data type
interface Product {
  id: number;
  name: string;
  price: number;
  category: string;
  inStock: boolean;
}

// 2. Create your component
export default function ProductList() {
  const [data, setData] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);

  // 3. Fetch data
  useEffect(() => {
    setLoading(true);
    fetchProducts().then(products => {
      setData(products);
      setLoading(false);
    });
  }, []);

  // 4. Define columns
  const columns: TableColumn<Product>[] = [
    {
      name: "Product Name",
      selector: (row) => row.name,
      sortable: true,
    },
    {
      name: "Price",
      selector: (row) => row.price,
      sortable: true,
      cell: (row) => `$${row.price.toFixed(2)}`,
    },
    {
      name: "Category",
      selector: (row) => row.category,
      sortable: true,
    },
    {
      name: "In Stock",
      selector: (row) => row.inStock,
      cell: (row) => (
        <span className={row.inStock ? "text-green-600" : "text-red-600"}>
          {row.inStock ? "Yes" : "No"}
        </span>
      ),
    },
  ];

  // 5. Define filters (optional)
  const filters = [
    {
      key: "category",
      label: "Category",
      type: "select" as const,
      options: [
        { value: "electronics", label: "Electronics" },
        { value: "clothing", label: "Clothing" },
        { value: "books", label: "Books" },
      ],
    },
    {
      key: "inStock",
      label: "Availability",
      type: "select" as const,
      options: [
        { value: "true", label: "In Stock" },
        { value: "false", label: "Out of Stock" },
      ],
    },
  ];

  // 6. Render
  return (
    <AdvancedDataTable
      data={data}
      columns={columns}
      loading={loading}
      filters={filters}
      enableExport={true}
      enableSelection={true}
      exportFileName="products"
      searchPlaceholder="Search products..."
    />
  );
}
```

---

## 🔧 Common Customizations

### Add Custom Action Buttons

```tsx
<AdvancedDataTable
  data={data}
  columns={columns}
  customActions={
    <>
      <button
        onClick={handleRefresh}
        className="px-4 py-2 bg-gray-600 text-white rounded-lg"
      >
        Refresh
      </button>
      <button
        onClick={handleAdd}
        className="px-4 py-2 bg-blue-600 text-white rounded-lg"
      >
        Add New
      </button>
    </>
  }
/>
```

### Handle Row Click

```tsx
<AdvancedDataTable
  data={data}
  columns={columns}
  onRowClicked={(row) => {
    navigate(`/products/${row.id}`);
  }}
/>
```

### Handle Selection Changes

```tsx
const [selected, setSelected] = useState([]);

<AdvancedDataTable
  data={data}
  columns={columns}
  enableSelection={true}
  onSelectionChange={setSelected}
/>

// Use selected array for bulk operations
<button onClick={() => bulkDelete(selected)}>
  Delete {selected.length} items
</button>
```

### Customize Empty State

```tsx
<AdvancedDataTable
  data={data}
  columns={columns}
  noDataMessage="No products found. Add your first product!"
/>
```

### Custom Cell Rendering

```tsx
const columns = [
  {
    name: "Avatar",
    cell: (row) => (
      <img
        src={row.avatar}
        alt={row.name}
        className="w-10 h-10 rounded-full"
      />
    ),
  },
  {
    name: "Status",
    cell: (row) => (
      <span className={`px-2 py-1 rounded-full text-xs ${
        row.active ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
      }`}>
        {row.active ? "Active" : "Inactive"}
      </span>
    ),
  },
];
```

---

## 📊 Real-World Integration Examples

### With Redux

```tsx
import { useSelector, useDispatch } from "react-redux";
import { fetchProducts, deleteProduct } from "@/store/productsSlice";

export default function ProductList() {
  const dispatch = useDispatch();
  const { products, loading } = useSelector((state) => state.products);

  useEffect(() => {
    dispatch(fetchProducts());
  }, [dispatch]);

  const handleDelete = async (id) => {
    await dispatch(deleteProduct(id));
    dispatch(fetchProducts()); // Refresh
  };

  return (
    <AdvancedDataTable
      data={products}
      columns={columns}
      loading={loading}
    />
  );
}
```

### With React Query

```tsx
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

export default function ProductList() {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["products"],
    queryFn: fetchProducts,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteProduct,
    onSuccess: () => {
      queryClient.invalidateQueries(["products"]);
    },
  });

  return (
    <AdvancedDataTable
      data={data || []}
      columns={columns}
      loading={isLoading}
    />
  );
}
```

### With Axios

```tsx
import axios from "axios";

export default function ProductList() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await axios.get("/api/products");
      setData(response.data);
    } catch (error) {
      console.error("Error fetching products:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  return (
    <AdvancedDataTable
      data={data}
      columns={columns}
      loading={loading}
    />
  );
}
```

---

## 🎯 API Data Transformation

### Transform Nested API Data

```tsx
// API returns nested data
const apiResponse = {
  status: "success",
  data: {
    results: [
      {
        id: 1,
        attributes: {
          name: "Product 1",
          price: { amount: 100, currency: "USD" },
        },
      },
    ],
  },
};

// Transform for table
const transformedData = apiResponse.data.results.map((item) => ({
  id: item.id,
  name: item.attributes.name,
  price: item.attributes.price.amount,
  currency: item.attributes.price.currency,
}));

<AdvancedDataTable data={transformedData} columns={columns} />
```

### Handle Pagination from API

```tsx
const [page, setPage] = useState(1);
const [data, setData] = useState([]);

useEffect(() => {
  fetch(`/api/products?page=${page}&limit=50`)
    .then(res => res.json())
    .then(json => {
      // Combine all pages or use server-side pagination
      setData(json.results);
    });
}, [page]);

// Table handles client-side pagination automatically
<AdvancedDataTable data={data} columns={columns} />
```

---

## 🎨 Styling Customization

### Override Colors

```tsx
// In your CSS or Tailwind config
.custom-table {
  --primary-color: #8B5CF6; /* Purple */
  --success-color: #10B981; /* Green */
}

<div className="custom-table">
  <AdvancedDataTable data={data} columns={columns} />
</div>
```

### Custom Badge Component

```tsx
// Create reusable badge
const StatusBadge = ({ status }) => {
  const colors = {
    active: "bg-green-100 text-green-800",
    pending: "bg-yellow-100 text-yellow-800",
    inactive: "bg-red-100 text-red-800",
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs ${colors[status]}`}>
      {status}
    </span>
  );
};

// Use in columns
{
  name: "Status",
  cell: (row) => <StatusBadge status={row.status} />,
}
```

---

## 🐛 Troubleshooting

### Problem: Table not showing

**Check:**
1. Is data an array? `console.log(Array.isArray(data))`
2. Is data empty? `console.log(data.length)`
3. Are columns defined correctly?
4. Check browser console for errors

**Solution:**
```tsx
// Add debug logging
console.log("Data:", data);
console.log("Columns:", columns);
console.log("Loading:", loading);
```

### Problem: Export not working

**Check:**
1. Packages installed? `npm list xlsx jspdf-autotable`
2. Browser blocking downloads?
3. Check browser console for errors

**Solution:**
```bash
# Reinstall packages
npm install xlsx jspdf-autotable --save
```

### Problem: Filters not showing

**Check:**
1. Is `filters` prop passed?
2. Is filters an array?
3. Do filters have correct structure?

**Solution:**
```tsx
// Debug filters
console.log("Filters:", filters);

// Ensure correct structure
const filters = [
  {
    key: "status",        // ✓ Correct
    label: "Status",      // ✓ Correct
    type: "select",       // ✓ Correct
    options: [...]        // ✓ Correct
  }
];
```

### Problem: Dark mode not working

**Check:**
1. ThemeContext provider wrapping app?
2. Theme toggle working?

**Solution:**
```tsx
// Ensure provider is in place
import { ThemeProvider } from "@/context/ThemeContext";

<ThemeProvider>
  <App />
</ThemeProvider>
```

---

## 📝 Checklist

Before deploying:

- [ ] ✅ Packages installed (`xlsx`, `jspdf-autotable`)
- [ ] ✅ Route added to router
- [ ] ✅ Navigation link added (optional)
- [ ] ✅ Test search functionality
- [ ] ✅ Test filter functionality
- [ ] ✅ Test sorting
- [ ] ✅ Test selection
- [ ] ✅ Test Excel export
- [ ] ✅ Test PDF export
- [ ] ✅ Test pagination
- [ ] ✅ Test on mobile device
- [ ] ✅ Test dark mode
- [ ] ✅ Test with empty data
- [ ] ✅ Test with loading state

---

## 🎉 You're Done!

The Advanced Data Table is now integrated and ready to use throughout your application.

### Quick Links:
- 📖 [Full Documentation](./src/apps/utils/actions/README.md)
- 🎨 [Visual Guide](./VISUAL_GUIDE.md)
- 📋 [Implementation Summary](./IMPLEMENTATION_SUMMARY.md)
- 💡 [Example Code](./src/apps/utils/examples/ContactListExample.tsx)

### Need Help?
- Check the README.md for detailed documentation
- Review the example files for usage patterns
- Look at ActionListPage.tsx for advanced features

Enjoy building beautiful data tables! 🚀
