/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import DataGrid from "@/components/common/DataGrid";
import type { ColumnFilter } from "@/components/common/ButtonToolbar";
import ComponentCard from "../../../../../components/common/ComponentCard";
import { useEffect, useState, useCallback, useMemo, useRef} from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchPurchases, fetchPurchaseDetail } from "../services/purchaseApi";
import {
  buildSearchPresetParams,
  type SearchPresetInputValue,
  type SearchPresetRecord,
} from "@/api/wcapi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import PurchaseDetail from "./PurchaseDetail";
import { sanitizeRecord, formatDateTimeValue } from "../../common/valueNormalization";
import ButtonToolbar from "@/components/common/ButtonToolbar";
import { useColumnContextMenu } from "@/hooks/useColumnContextMenu";

const numericPurchaseKeys = ["dt_created", "id_vendor"]; 

export default function PurchaseList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedPurchases, setSelectedPurchases] = useState<any[]>([]);
  const [selectedPurchase, setSelectedPurchase] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>([]);
  const tableRef = useRef<any>(null);
  const columnBtnRef = useRef<HTMLButtonElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  const dispatch = useDispatch();

  const getPurchaseData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchPurchases();
      if (res.status === 200) {
        const sanitizedItems = Array.isArray(res.data.items)
          ? res.data.items.map((item: any) => sanitizeRecord(item, numericPurchaseKeys))
          : [];
        setData(sanitizedItems);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch purchases", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch purchases", error);
      dispatch(showToast({ message: "Failed to fetch purchases", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getPurchaseData();
  }, [getPurchaseData]);

  // Auto-refresh when another window saves/transfers a transaction.
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent)?.detail as any;
      const model = String(detail?.model || "");
      if (
        ["order", "invoice", "proposal", "purchase", "workorder"].includes(model)
      ) {
        getPurchaseData();
      }
    };
    window.addEventListener("wcapi:modelChanged", handler as any);
    return () => window.removeEventListener("wcapi:modelChanged", handler as any);
  }, [getPurchaseData]);

  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const searchQuery = terms.join(",");
      const res = await fetchPurchases({ search: searchQuery });
      if (res.status === 200) {
        const sanitizedItems = Array.isArray(res.data.items)
          ? res.data.items.map((item: any) => sanitizeRecord(item, numericPurchaseKeys))
          : [];
        setData(sanitizedItems);
      }
    } catch (error) {
      console.error("Database search failed:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleApplySearchPreset = useCallback(
    async (
      preset: SearchPresetRecord,
      values: Record<string, SearchPresetInputValue> = {},
    ) => {
      try {
        setLoading(true);
        setSearchDatabase(true);
        setSearchTerm("");
        const res = await fetchPurchases(
          buildSearchPresetParams(preset, {
            values,
            params: { limit: 500 },
          }),
        );
        if (res.status === 200) {
          const sanitizedItems = Array.isArray(res.data.items)
            ? res.data.items.map((item: any) => sanitizeRecord(item, numericPurchaseKeys))
            : [];
          setData(sanitizedItems);
        } else {
          dispatch(
            showToast({ message: "Failed to run saved search", type: "error" }),
          );
        }
      } catch (error) {
        console.error("Saved search failed:", error);
        dispatch(
          showToast({ message: "Failed to run saved search", type: "error" }),
        );
      } finally {
        setLoading(false);
      }
    },
    [dispatch],
  );

  const openPurchase = useCallback(
    async (row: any, modeToSet: "view" | "edit") => {
      const purchaseId = row?.id;
      if (!purchaseId) {
        dispatch(
          showToast({ message: "Purchase id missing", type: "error" })
        );
        return;
      }

      setFormMode(modeToSet);
      setDetailLoading(true);
      setSelectedPurchase(null);

      try {
        const response = await fetchPurchaseDetail(purchaseId);
        const detail = response ?? {};
        const hasDetail = detail && Object.keys(detail).length > 0;
        if (!hasDetail) {
          throw new Error("Purchase not found");
        }
        const sanitizedRow = sanitizeRecord(row, numericPurchaseKeys);
        const sanitizedDetail = sanitizeRecord(detail, numericPurchaseKeys);
        setSelectedPurchase({ ...sanitizedRow, ...sanitizedDetail });
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Failed to load purchase";
        dispatch(showToast({ message, type: "error" }));
        setFormMode(null);
        setSelectedPurchase(null);
      } finally {
        setDetailLoading(false);
      }
    },
    [dispatch]
  );

  const handleView = useCallback(
    (row: any) => {
      openPurchase(row, "view");
    },
    [openPurchase]
  );

  const handleEdit = useCallback(
    (row: any) => {
      openPurchase(row, "edit");
    },
    [openPurchase]
  );

  const handleAdd = () => {
    setSelectedPurchase(null);
    setFormMode("add");
    setDetailLoading(false);
  };

  const handleFormSaved = () => {
    getPurchaseData();
    setFormMode(null);
    setSelectedPurchase(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedPurchase(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete purchase ${row.purchase_no}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(showToast({ message: "Purchase deleted successfully", type: "success" }));
        getPurchaseData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete purchase", type: "error" }));
      }
    }
  };

  const userColumns: any[] = useMemo(() => [
    { 
      name: "ID", 
      selector: (row) => row.id, 
      sortable: true, 
      width: "80px",
      cell: (row) => (
        <div 
          onClick={(e) => {
            e.stopPropagation();
            handleEdit(row);
          }}
          className="text-xs font-mono text-blue-600 dark:text-blue-400 cursor-pointer hover:underline"
        >
          {row.id}
        </div>
      ),
    },
    {
      name: "Purchase No",
      selector: (row) => row.purchase_no || "--",
      sortable: true,
      width: "30%",
    },
    {
      name: "Created",
      selector: (row) => row.dt_created || 0,
      sortable: true,
      width: "25%",
      cell: (row) => {
        const formatted = formatDateTimeValue(row.dt_created);
        return formatted || "--";
      },
    },
    {
      name: "Action",
      width: "140px",
      cell: (row) => (
        <div className="flex gap-2">
          <button 
            onClick={(e) => { e.stopPropagation(); handleView(row); }} 
            title="View"
            className="p-2 text-blue-600 hover:bg-blue-50 rounded dark:hover:bg-blue-900/20 transition-colors"
          >
            <FaEye className="w-4 h-4" />
          </button>
          <button 
            onClick={(e) => { e.stopPropagation(); handleEdit(row); }} 
            title="Edit"
            className="p-2 text-green-600 hover:bg-green-50 rounded dark:hover:bg-green-900/20 transition-colors"
          >
            <FaEdit className="w-4 h-4" />
          </button>
          <button 
            onClick={(e) => { e.stopPropagation(); handleDelete(row); }} 
            title="Delete"
            className="p-2 text-red-600 hover:bg-red-50 rounded dark:hover:bg-red-900/20 transition-colors"
          >
            <FaTrash className="w-4 h-4" />
          </button>
        </div>
      ),
    },
  ], [handleView, handleEdit, handleDelete]);

  // Filters configuration
  const filters: ColumnFilter[] = useMemo(() => [
    {
      key: "purchase_no",
      label: "PO Number",
      type: "text",
    },
  ], []);

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
    if (columnVisibility.length === 0) return userColumns;
    return userColumns.filter((_: any, index: number) => columnVisibility[index] !== false);
  }, [userColumns, columnVisibility]);

  const columnCtx = useColumnContextMenu("purchase-list", userColumns);
  return (
    <>
      <ButtonToolbar
        pageTitle="Purchase List"
        title="Purchase"
        modelKey="purchase"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        selectedRows={selectedPurchases}
        selectedCount={selectedPurchases.length}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={getPurchaseData}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={userColumns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="purchase-list"
        filters={filters}
        filterValues={filterValues}
        onFilterValuesChange={setFilterValues}
        filtersOpen={filtersOpen}
        onFiltersOpenChange={setFiltersOpen}
        onApplySearchPreset={handleApplySearchPreset}
      />
<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <DataGrid
              ref={tableRef}
              data={filteredData}
              columns={userColumns}
              title="Purchases"
              loading={loading}
              filters={filters}
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedPurchases}
              exportFileName="purchases"
              searchPlaceholder="Search purchases..."
              noDataMessage="No purchases found"
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
              customActions={
                <button
                  onClick={handleAdd}
                  className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <FaPlus className="w-4 h-4" 
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              hideHeader={true}/>
                  Add Purchase
                </button>
              }
              onRowClicked={handleEdit}
              allFields={columnCtx.allFields}
              namedViews={columnCtx.namedViews}
              onDeleteColumn={columnCtx.onDeleteColumn}
              onAddColumn={columnCtx.onAddColumn}
              onSaveLayout={columnCtx.onSaveLayout}
              onSaveLayoutAs={columnCtx.onSaveLayoutAs}
              onLoadView={columnCtx.onLoadView}
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            {formMode !== "add" && (detailLoading || !selectedPurchase) ? (
              <ComponentCard>
                <div className="p-8 text-center text-sm text-gray-500 dark:text-gray-400">
                  Loading purchase...
                </div>
              </ComponentCard>
            ) : (
              <PurchaseDetail
                inline
                modeProp={formMode}
                dataProp={formMode === "add" ? null : selectedPurchase}
                onSaved={handleFormSaved}
                onCancelInline={handleFormCancel}
              />
            )}
          </div>
        )}
      </div>
    </>
  );
}