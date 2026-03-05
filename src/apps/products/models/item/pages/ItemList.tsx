import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter, type AdvancedDataTableHandle } from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useCallback, useEffect, useMemo, useState, useRef} from "react";
import { FaEdit, FaEye, FaPlus, FaTrash, FaTachometerAlt } from "react-icons/fa";
import { useNavigate } from "react-router-dom";
import { PageRoutes } from "../../../../../routes/Routes";
import { useDispatch } from "react-redux";
import { deleteAction } from "../../../../../api/userProfile";
import { showToast } from "../../../../../store/slices/toastSlice";
import { fetchItems } from "../services/itemApi";
import ItemDetail from "./ItemDetail";
import ButtonToolbar from "@/components/common/ButtonToolbar";

type ItemListMode = "add" | "edit" | "view" | null;

const valueFrom = (row: any, keys: string[], fallback: any = undefined) => {
  for (const key of keys) {
    const value = row?.[key];
    if (value !== undefined && value !== null && value !== "") {
      return value;
    }
  }
  return fallback;
};

// Normalizes differing API payload shapes into a flat array of items.
const extractItems = (payload: any): any[] => {
  if (!payload) return [];

  const directCandidates = [
    payload?.data?.items,
    payload?.data?.results,
    payload?.data?.data?.items,
    payload?.data?.data?.results,
    payload?.items,
    payload?.results,
  ];

  for (const candidate of directCandidates) {
    if (Array.isArray(candidate)) return candidate;
  }

  const objectCandidates = [payload?.data?.data, payload?.data, payload];
  for (const obj of objectCandidates) {
    if (obj && typeof obj === "object" && !Array.isArray(obj)) {
      const values = Object.values(obj);
      for (const value of values) {
        if (Array.isArray(value)) return value;
      }
    }
  }

  return [];
};

export default function ItemList() {
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [formMode, setFormMode] = useState<ItemListMode>(null);
  const [selectedItem, setSelectedItem] = useState<any | null>(null);
  const [selectedItems, setSelectedItems] = useState<any[]>([]);
  const [searchDatabase, setSearchDatabase] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>([]);
  const tableRef = useRef<AdvancedDataTableHandle<any>>(null);
  const columnBtnRef = useRef<HTMLButtonElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  const getItemId = useCallback((row: any) => {
    return valueFrom(row, ["id", "item_id", "uuid", "item_number", "sku"], null) ?? null;
  }, []);

  const getItemLabel = useCallback((row: any) => {
    return valueFrom(row, ["name", "item_name", "title", "sku", "item_number"], "Item") || "Item";
  }, []);

  const getItems = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchItems();
      if (res.status === 200) {
        const normalized = extractItems(res);
        // Limit to first 10 records to reduce initial load time
        setItems(normalized.slice(0, 10));
        if (!normalized.length) {
          dispatch(showToast({ message: "Item response contained no rows", type: "warning" }));
        }
      } else {
        dispatch(showToast({ message: "Failed to fetch items", type: "error" }));
      }
    } catch (error) {
      console.error("Failed to fetch items", error);
      dispatch(showToast({ message: "Failed to fetch items", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getItems();
  }, [getItems]);

  const handleView = useCallback((row: any) => {
    setSelectedItem(row);
    setFormMode("view");
  }, []);

  // Double-click opens the detail view
  const handleDoubleClick = useCallback((row: any) => {
    setSelectedItem(row);
    setFormMode("view");
  }, []);

  const handleDashboard = useCallback((row: any) => {
    const id = getItemId(row);
    console.log('Dashboard button clicked, id:', id);
    if (id) {
      navigate(PageRoutes.productsItemDashboard.replace(":id", String(id)));
    }
  }, [navigate, getItemId]);

  const handleEdit = useCallback((row: any) => {
    setSelectedItem(row);
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedItem(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getItems();
    setFormMode(null);
    setSelectedItem(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedItem(null);
  };

  const handleDelete = useCallback(
    async (row: any) => {
      const id = getItemId(row);
      if (!id) {
        dispatch(showToast({ message: "Item id missing", type: "error" }));
        return;
      }

      const label = getItemLabel(row);
      if (!window.confirm(`Delete item ${label}?`)) return;

      try {
        await deleteAction(id);
        dispatch(showToast({ message: "Item deleted successfully", type: "success" }));
        getItems();
      } catch (error) {
        console.error("Failed to delete item", error);
        dispatch(showToast({ message: "Failed to delete item", type: "error" }));
      }
    },
    [dispatch, getItemId, getItemLabel, getItems]
  );

  const handleBulkDelete = useCallback(async () => {
    if (!selectedItems.length) return;
    if (!window.confirm(`Delete ${selectedItems.length} item(s)?`)) return;

    try {
      await Promise.all(selectedItems.map((item) => deleteAction(getItemId(item))));
      dispatch(showToast({ message: `${selectedItems.length} item(s) deleted`, type: "success" }));
      getItems();
      setSelectedItems([]);
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete some items", type: "error" }));
    }
  }, [selectedItems, dispatch, getItemId, getItems]);

  // Database search handler for comma-separated terms (AND logic)
  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const searchQuery = terms.join(",");
      const res = await fetchItems({ search: searchQuery });
      if (res.status === 200) {
        const normalized = extractItems(res);
        setItems(normalized);
      }
    } catch (error) {
      console.error("Database search failed:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const filters: ColumnFilter[] = useMemo(() => [
    { key: "category", label: "Category", type: "text" },
    { key: "kind", label: "Kind", type: "select", options: [
      { value: "physical", label: "Physical" },
      { value: "service", label: "Service" },
      { value: "bundle", label: "Bundle" },
    ]},
  ], []);

  const columns: TableColumn<any>[] = useMemo(() => {
    const idSelector = (row: any) => valueFrom(row, ["id", "item_id", "item_number", "sku", "uuid"], "--");
    const nameSelector = (row: any) => valueFrom(row, ["name", "item_name", "title", "description"], "--");
    const skuSelector = (row: any) => valueFrom(row, ["sku", "item_code", "item_number", "external_id"], "--");
    const categorySelector = (row: any) => valueFrom(row, ["category", "category_name", "segment", "group"], "--");
    const retailSelector = (row: any) => {
      const val = Number(row?.price?.retail);
      return Number.isFinite(val) ? val : 0;
    };
    const distributorSelector = (row: any) => {
      const val = Number(row?.price?.distributor);
      return Number.isFinite(val) ? val : 0;
    };
    const descriptionSelector = (row: any) =>
      valueFrom(row, ["description", "long_description", "short_description", "change_reason"], "--");

    return [
      { id: "id", name: "ID", selector: idSelector, sortable: true, width: "80px" },
      { id: "name", name: "Name", selector: nameSelector, sortable: true, wrap: true, width: "20%" },
      { id: "sku", name: "SKU", selector: skuSelector, sortable: true, wrap: true, width: "15%" },
      { id: "category", name: "Category", selector: categorySelector, sortable: true, wrap: true, width: "15%" },
      {
        id: "retail",
        name: "Retail",
        selector: retailSelector,
        sortable: true,
        width: "10%",
        cell: (row) => (
          <span className="font-medium text-green-600 dark:text-green-400">
            ${retailSelector(row).toFixed(2)}
          </span>
        ),
      },
      {
        id: "distributor",
        name: "Distributor",
        selector: distributorSelector,
        sortable: true,
        width: "10%",
        cell: (row) => (
          <span className="font-medium text-blue-600 dark:text-blue-400">
            ${distributorSelector(row).toFixed(2)}
          </span>
        ),
      },
      { id: "description", name: "Description", selector: descriptionSelector, sortable: false, wrap: true, width: "20%" },
      {
        id: "actions",
        name: "Actions",
        cell: (row) => (
          <div className="flex gap-2">
            <button onClick={() => handleView(row)} title="View">
              <FaEye className="text-blue-600 hover:scale-110 transition" />
            </button>
            <button onClick={() => handleEdit(row)} title="Edit">
              <FaEdit className="text-green-600 hover:scale-110 transition" />
            </button>
            <button onClick={() => handleDashboard(row)} title="Dashboard">
              <FaTachometerAlt className="text-purple-600 hover:scale-110 transition" />
            </button>
            <button onClick={() => handleDelete(row)} title="Delete">
              <FaTrash className="text-red-600 hover:scale-110 transition" />
            </button>
          </div>
        ),
        ignoreRowClick: true,
        allowOverflow: true,
        button: true,
        width: "120px",
      },
    ];
  }, [handleDelete, handleEdit, handleView]);

  // Filter data based on filterValues from ButtonToolbar
  const filteredData = useMemo(() => {
    if (Object.keys(filterValues).length === 0) return data;
    return data.filter((row: any) => {
      return Object.entries(filterValues).every(([key, value]) => {
        if (!value) return true;
        const rowValue = String(row[key] || "").toLowerCase();
        return rowValue.includes(value.toLowerCase());
      });
    });
  }, [data, filterValues]);

  // Filter columns based on visibility from ButtonToolbar
  const visibleColumns = useMemo(() => {
    if (columnVisibility.length === 0) return columns;
    return columns.filter((_: any, index: number) => columnVisibility[index] !== false);
  }, [columns, columnVisibility]);
  return (
    <>
      <ButtonToolbar
        pageTitle="Item List"
        title="Item"
        modelKey="item"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        handleBulkDelete={handleBulkDelete}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        selectedRows={selectedItems}
        selectedCount={selectedItems.length}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={getData}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={columns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="item-list"
        filters={filters}
        filterValues={filterValues}
        onFilterValuesChange={setFilterValues}
        filtersOpen={filtersOpen}
        onFiltersOpenChange={setFiltersOpen}
      />
<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              ref={tableRef}
              data={items}
              columns={visibleColumns}
              title="Items"
              loading={loading}
              filters={filters}
              storageKey="item-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedItems}
              exportFileName="items_export"
              onRowDoubleClicked={handleDoubleClick}
              searchPlaceholder="Search items..."
              noDataMessage="No items found"
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
              customActions={
                <div className="flex gap-2">
                  {selectedItems.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" 
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              hideHeader={true}/>
                      Delete ({selectedItems.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Item
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <ItemDetail
              inline
              modeProp={formMode}
              dataProp={selectedItem}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
