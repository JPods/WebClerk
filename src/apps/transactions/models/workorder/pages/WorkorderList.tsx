import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, { type AdvancedDataTableHandle } from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo, useRef} from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchWorkorders, fetchWorkorderDetail } from "../services/workorderApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import WorkorderDetail from "./WorkorderDetail";
import ButtonToolbar from "@/components/common/ButtonToolbar";

export default function WorkorderList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedWorkorder, setSelectedWorkorder] = useState<any | null>(null);
  const [selectedWorkorders, setSelectedWorkorders] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>([]);
  const tableRef = useRef<AdvancedDataTableHandle<any>>(null);
  const columnBtnRef = useRef<HTMLButtonElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  const getWorkorderData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchWorkorders();
      if (res.status === 200) {
        setData(res.data.items || []);
      } else {
        dispatch(showToast({ message: "Failed to fetch workorders", type: "error" }));
      }
    } catch (error) {
      console.error("Failed to fetch workorders", error);
      dispatch(showToast({ message: "Failed to fetch workorders", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getWorkorderData();
  }, [getWorkorderData]);

  // Auto-refresh when another window saves/transfers a transaction.
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent)?.detail as any;
      const model = String(detail?.model || "");
      if (
        ["order", "invoice", "proposal", "purchase", "workorder"].includes(model)
      ) {
        getWorkorderData();
      }
    };
    window.addEventListener("wcapi:modelChanged", handler as any);
    return () => window.removeEventListener("wcapi:modelChanged", handler as any);
  }, [getWorkorderData]);

  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const searchQuery = terms.join(",");
      const res = await fetchWorkorders({ search: searchQuery });
      if (res.status === 200) {
        setData(res.data.items || []);
      }
    } catch (error) {
      console.error("Database search failed:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const openWorkorder = useCallback(
    async (row: any, modeToSet: "view" | "edit") => {
      const workorderId = row?.id;
      if (!workorderId) {
        dispatch(showToast({ message: "Workorder id missing", type: "error" }));
        return;
      }

      setFormMode(modeToSet);
      setDetailLoading(true);
      setSelectedWorkorder(null);

      try {
        const detail = await fetchWorkorderDetail(workorderId);
        const hasDetail = detail && Object.keys(detail).length > 0;
        if (!hasDetail) {
          throw new Error("Workorder not found");
        }
        setSelectedWorkorder({ ...row, ...detail });
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Failed to load workorder";
        dispatch(showToast({ message, type: "error" }));
        setFormMode(null);
        setSelectedWorkorder(null);
      } finally {
        setDetailLoading(false);
      }
    },
    [dispatch]
  );

  const handleView = useCallback((row: any) => {
    openWorkorder(row, "view");
  }, [openWorkorder]);

  const handleEdit = useCallback((row: any) => {
    openWorkorder(row, "edit");
  }, [openWorkorder]);

  const handleAdd = () => {
    setSelectedWorkorder(null);
    setFormMode("add");
    setDetailLoading(false);
  };

  const handleFormSaved = () => {
    getWorkorderData();
    setFormMode(null);
    setSelectedWorkorder(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedWorkorder(null);
  };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete workorder ${row.workorder_no}?`)) return;
    
    try {
      await deleteAction(row.id);
      dispatch(showToast({ message: "Workorder deleted successfully", type: "success" }));
      getWorkorderData();
      if (selectedWorkorder && selectedWorkorder.id === row.id) {
        setFormMode(null);
        setSelectedWorkorder(null);
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete workorder", type: "error" }));
    }
  }, [dispatch, getWorkorderData, selectedWorkorder]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedWorkorders.length) return;
    if (!window.confirm(`Delete ${selectedWorkorders.length} workorder(s)?`)) return;

    try {
      await Promise.all(selectedWorkorders.map((w) => deleteAction(w.id)));
      dispatch(showToast({ message: `${selectedWorkorders.length} workorder(s) deleted`, type: "success" }));
      getWorkorderData();
      setSelectedWorkorders([]);
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete some workorders", type: "error" }));
    }
  }, [selectedWorkorders, dispatch, getWorkorderData]);

  const columns: TableColumn<any>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "workorder_no", name: "Workorder No", selector: (row) => row.workorder_no || "--", sortable: true, width: "30%" },
    { id: "dt_created", name: "Created", selector: (row) => row.dt_created ? new Date(row.dt_created * 1000).toLocaleDateString() : "--", sortable: true, width: "25%" },
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
        pageTitle="Workorder List"
        title="Workorder"
        modelKey="workorder"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        handleBulkDelete={handleBulkDelete}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        selectedRows={selectedWorkorders}
        selectedCount={selectedWorkorders.length}
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
        storageKey="workorder-list"
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
              data={filteredData}
              columns={visibleColumns}
              title="Workorders"
              loading={loading}
              storageKey="workorder-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedWorkorders}
              exportFileName="workorders_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search workorders..."
              noDataMessage="No workorders found"
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
              customActions={
                <div className="flex gap-2">
                  {selectedWorkorders.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" 
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              hideHeader={true}/>
                      Delete ({selectedWorkorders.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Workorder
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            {formMode !== "add" && (detailLoading || !selectedWorkorder) ? (
              <ComponentCard>
                <div className="p-8 text-center text-sm text-gray-500 dark:text-gray-400">
                  Loading workorder...
                </div>
              </ComponentCard>
            ) : (
              <WorkorderDetail
                inline
                modeProp={formMode}
                dataProp={formMode === "add" ? null : selectedWorkorder}
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
