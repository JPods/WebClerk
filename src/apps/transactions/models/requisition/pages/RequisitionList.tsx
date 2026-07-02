/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import DataGrid from "@/components/common/DataGrid";
import type { ColumnFilter } from "@/components/common/ButtonToolbar";
import ComponentCard from "../../../../../components/common/ComponentCard";
import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchRequisitions } from "../services/requisitionApi";
import {
  buildSearchPresetParams,
  type SearchPresetInputValue,
  type SearchPresetRecord,
} from "@/api/wcapi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import RequisitionDetail from "./RequisitionDetail";
import ButtonToolbar from "@/components/common/ButtonToolbar";

export default function RequisitionList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedRequisition, setSelectedRequisition] = useState<any | null>(
    null,
  );
  const [selectedRequisitions, setSelectedRequisitions] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>([]);
  const tableRef = useRef<any>(null);
  const columnBtnRef = useRef<HTMLButtonElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  const getRequisitionData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchRequisitions();
      if (res.status === 200) {
        setData(res.data.items || []);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch requisitions", type: "error" }),
        );
      }
    } catch (error) {
      console.error("Failed to fetch requisitions", error);
      dispatch(
        showToast({ message: "Failed to fetch requisitions", type: "error" }),
      );
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getRequisitionData();
  }, [getRequisitionData]);

  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const searchQuery = terms.join(",");
      const res = await fetchRequisitions({ search: searchQuery });
      if (res.status === 200) {
        setData(res.data.items || []);
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
        const res = await fetchRequisitions(
          buildSearchPresetParams(preset, {
            values,
            params: { limit: 500 },
          }),
        );
        if (res.status === 200) {
          setData(res.data.items || []);
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

  const handleView = useCallback((row: any) => {
    setSelectedRequisition(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback((row: any) => {
    setSelectedRequisition(row);
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedRequisition(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getRequisitionData();
    setFormMode(null);
    setSelectedRequisition(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedRequisition(null);
  };

  const handleDelete = useCallback(
    async (row: any) => {
      if (!window.confirm(`Delete requisition ${row.requisition_no}?`)) return;

      try {
        await deleteAction(row.id);
        dispatch(
          showToast({
            message: "Requisition deleted successfully",
            type: "success",
          }),
        );
        getRequisitionData();
        if (selectedRequisition && selectedRequisition.id === row.id) {
          setFormMode(null);
          setSelectedRequisition(null);
        }
      } catch (error) {
        dispatch(
          showToast({ message: "Failed to delete requisition", type: "error" }),
        );
      }
    },
    [dispatch, getRequisitionData, selectedRequisition],
  );

  const handleBulkDelete = useCallback(async () => {
    if (!selectedRequisitions.length) return;
    if (
      !window.confirm(`Delete ${selectedRequisitions.length} requisition(s)?`)
    )
      return;

    try {
      await Promise.all(selectedRequisitions.map((r) => deleteAction(r.id)));
      dispatch(
        showToast({
          message: `${selectedRequisitions.length} requisition(s) deleted`,
          type: "success",
        }),
      );
      getRequisitionData();
      setSelectedRequisitions([]);
    } catch (error) {
      dispatch(
        showToast({
          message: "Failed to delete some requisitions",
          type: "error",
        }),
      );
    }
  }, [selectedRequisitions, dispatch, getRequisitionData]);

  const columns: any[] = useMemo(
    () => [
      {
        id: "id",
        name: "ID",
        selector: (row) => row.id,
        sortable: true,
        width: "80px",
      },
      {
        id: "requisition_no",
        name: "Requisition No",
        selector: (row) => row.requisition_no || "--",
        sortable: true,
        width: "30%",
      },
      {
        id: "dt_created",
        name: "Created",
        selector: (row) =>
          row.dt_created
            ? new Date(row.dt_created * 1000).toLocaleDateString()
            : "--",
        sortable: true,
        width: "25%",
      },
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
    ],
    [handleDelete, handleEdit, handleView],
  );

  // Define filters for the table
  const filters: ColumnFilter[] = useMemo(
    () => [
      { key: "id", label: "ID", type: "text" },
      { key: "requisition_no", label: "Requisition No", type: "text" },
    ],
    [],
  );

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
    return columns.filter(
      (_: any, index: number) => columnVisibility[index] !== false,
    );
  }, [columns, columnVisibility]);
  return (
    <>
      <ButtonToolbar
        pageTitle="Requisition List"
        title="Requisition"
        modelKey="requisition"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        handleBulkDelete={handleBulkDelete}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        selectedRows={selectedRequisitions}
        selectedCount={selectedRequisitions.length}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={getRequisitionData}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        onApplySearchPreset={handleApplySearchPreset}
        columns={columns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="requisition-list"
        filters={filters}
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
              title="Requisitions"
              loading={loading}
              filters={filters}
              storageKey="requisition-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedRequisitions}
              onDeleteSelected={handleBulkDelete}
              exportFileName="requisitions_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search requisitions..."
              noDataMessage="No requisitions found"
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              filtersOpen={filtersOpen}
              onFiltersOpenChange={setFiltersOpen}
              hideHeader={true}
              customActions={
                <div className="flex gap-2">
                  {selectedRequisitions.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" />
                      Delete ({selectedRequisitions.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Requisition
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <RequisitionDetail
              inline
              modeProp={formMode}
              dataProp={selectedRequisition}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
