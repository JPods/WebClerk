/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import DataGrid from "@/components/common/DataGrid";
import ComponentCard from "../../../../../components/common/ComponentCard";
import { useEffect, useState, useCallback, useMemo, useRef} from "react";
import { fetchReceipts, deleteReceipt } from "../services/purchaseReceiptApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import ReceiptDetail from "./ReceiptDetail";
import ButtonToolbar from "@/components/common/ButtonToolbar";

export default function ReceiptList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedReceipt, setSelectedReceipt] = useState<any | null>(null);
  const [selectedReceipts, setSelectedReceipts] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>([]);
  const tableRef = useRef<any>(null);
  const columnBtnRef = useRef<HTMLButtonElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  const getReceiptData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchReceipts();
      if (res.status === 200) {
        setData(res.data.items || []);
      } else {
        dispatch(showToast({ message: "Failed to fetch receipts", type: "error" }));
      }
    } catch (error) {
      console.error("Failed to fetch receipts", error);
      dispatch(showToast({ message: "Failed to fetch receipts", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getReceiptData();
  }, [getReceiptData]);

  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const searchQuery = terms.join(",");
      const res = await fetchReceipts({ search: searchQuery });
      if (res.status === 200) {
        setData(res.data.items || []);
      }
    } catch (error) {
      console.error("Database search failed:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleView = useCallback((row: any) => {
    setSelectedReceipt(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback((row: any) => {
    setSelectedReceipt(row);
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedReceipt(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getReceiptData();
    setFormMode(null);
    setSelectedReceipt(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedReceipt(null);
  };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete receipt ${row.id}?`)) return;
    
    try {
      await deleteReceipt(row.id);
      dispatch(showToast({ message: "Receipt deleted successfully", type: "success" }));
      getReceiptData();
      if (selectedReceipt && selectedReceipt.id === row.id) {
        setFormMode(null);
        setSelectedReceipt(null);
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete receipt", type: "error" }));
    }
  }, [dispatch, getReceiptData, selectedReceipt]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedReceipts.length) return;
    if (!window.confirm(`Delete ${selectedReceipts.length} receipt(s)?`)) return;

    try {
      await Promise.all(selectedReceipts.map((r) => deleteReceipt(r.id)));
      dispatch(showToast({ message: `${selectedReceipts.length} receipt(s) deleted`, type: "success" }));
      getReceiptData();
      setSelectedReceipts([]);
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete some receipts", type: "error" }));
    }
  }, [selectedReceipts, dispatch, getReceiptData]);

  const columns: any[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "ida", name: "Receipt No", selector: (row) => row.ida || "--", sortable: true, width: "15%" },
    { id: "source_type", name: "Source", selector: (row) => row.source_type?.replace('_', ' ') || "--", sortable: true, width: "15%" },
    { id: "dt_received", name: "Date Received", selector: (row) => row.dt_received ? new Date(row.dt_received).toLocaleString() : "--", sortable: true, width: "18%" },
    { id: "status", name: "Status", selector: (row) => row.status || "--", sortable: true, width: "12%" },
    { id: "notes", name: "Notes", selector: (row) => row.notes || "--", sortable: true, width: "20%" },
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
          <button onClick={() => handleDelete(row)} title="Delete">
            <FaTrash className="text-red-600 hover:scale-110 transition" />
          </button>
        </div>
      ),
      ignoreRowClick: true,
      allowOverflow: true,
      button: true,
      width: "100px",
    },
  ], [handleDelete, handleEdit, handleView]);

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
        pageTitle="Receipt List"
        title="Receipt"
        modelKey="receipt"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        handleBulkDelete={handleBulkDelete}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        selectedRows={selectedReceipts}
        selectedCount={selectedReceipts.length}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={getReceiptData}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={columns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="receipt-list"
        filterValues={filterValues}
        onFilterValuesChange={setFilterValues}
        filtersOpen={filtersOpen}
        onFiltersOpenChange={setFiltersOpen}
      />
<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <DataGrid
              ref={tableRef}
              data={filteredData}
              columns={visibleColumns}
              title="Receipts"
              loading={loading}
              storageKey="receipt-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedReceipts}
              exportFileName="receipts_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search receipts..."
              noDataMessage="No receipts found"
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
              customActions={
                <div className="flex gap-2">
                  {selectedReceipts.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" 
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              hideHeader={true}/>
                      Delete ({selectedReceipts.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Receipt
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <ReceiptDetail
              inline
              modeProp={formMode}
              dataProp={selectedReceipt}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
