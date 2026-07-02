/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import DataGrid from "@/components/common/DataGrid";
import type { ColumnFilter } from "@/components/common/ButtonToolbar";
import ComponentCard from "@/components/common/ComponentCard";
import { useEffect, useState, useCallback, useMemo, useRef} from "react";
import { getRecords, deleteRecord } from "@/api/wcapi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import BaseOrgModelDisplay from "./BaseOrgModelDisplay";
import ButtonToolbar from "@/components/common/ButtonToolbar";

export default function BaseOrgModelList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedBaseOrgModel, setSelectedBaseOrgModel] = useState<any | null>(null);
  const [selectedBaseOrgModels, setSelectedBaseOrgModels] = useState<any[]>([]);
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

  const getBaseOrgModelData = useCallback(async () => {
    try {
      setLoading(true);
      const list = await getRecords('base_org_model');
      const recs = Array.isArray(list?.results) ? list.results : Array.isArray(list) ? list : [];
      setData(recs);
    } catch (error) {
      console.error("Failed to fetch base org models", error);
      dispatch(showToast({ message: "Failed to fetch base org models", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getBaseOrgModelData();
  }, [getBaseOrgModelData]);

  // Handle database search
  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    const query = terms.join(' ');
    setLoading(true);
    try {
      const list = await getRecords('base_org_model', { search: query });
      const recs = Array.isArray(list?.results) ? list.results : Array.isArray(list) ? list : [];
      setData(recs);
    } catch (error) {
      console.error("Database search error:", error);
      dispatch(showToast({ message: "Search failed", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  const handleView = useCallback((row: any) => {
    setSelectedBaseOrgModel(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback((row: any) => {
    setSelectedBaseOrgModel(row);
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedBaseOrgModel(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getBaseOrgModelData();
    setFormMode(null);
    setSelectedBaseOrgModel(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedBaseOrgModel(null);
  };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete base org model ${row.name || row.id}?`)) return;
    
    try {
      await deleteRecord('base_org_model', row.id);
      dispatch(showToast({ message: "Base Org Model deleted successfully", type: "success" }));
      getBaseOrgModelData();
      if (selectedBaseOrgModel && selectedBaseOrgModel.id === row.id) {
        setFormMode(null);
        setSelectedBaseOrgModel(null);
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete base org model", type: "error" }));
    }
  }, [dispatch, getBaseOrgModelData, selectedBaseOrgModel]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedBaseOrgModels.length) return;
    if (!window.confirm(`Delete ${selectedBaseOrgModels.length} base org model(s)?`)) return;

    try {
      await Promise.all(selectedBaseOrgModels.map((m) => deleteRecord('base_org_model', m.id)));
      dispatch(showToast({ message: `${selectedBaseOrgModels.length} base org model(s) deleted`, type: "success" }));
      getBaseOrgModelData();
      setSelectedBaseOrgModels([]);
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete some base org models", type: "error" }));
    }
  }, [selectedBaseOrgModels, dispatch, getBaseOrgModelData]);

  const filters: ColumnFilter[] = useMemo(() => [
    { key: "type", label: "Type", type: "text" },
    { key: "status", label: "Status", type: "text" },
  ], []);

  const columns: any[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "name", name: "Name", selector: (row) => row.name || "--", sortable: true, width: "40%" },
    { id: "type", name: "Type", selector: (row) => row.type || "--", sortable: true, width: "25%" },
    { id: "status", name: "Status", selector: (row) => row.status || "--", sortable: true, width: "15%" },
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
        pageTitle="Base Org Model List"
        title="Base Org Model"
        modelKey="base_org_model"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        handleBulkDelete={handleBulkDelete}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        selectedRows={selectedBaseOrgModels}
        selectedCount={selectedBaseOrgModels.length}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={getBaseOrgModelData}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={columns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="base_org_model-list"
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
              title="Base Org Models"
              loading={loading}
              filters={filters}
              storageKey="base-org-model-list"
              enableExport={true}
              enableSelection={true}
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
              onSelectionChange={setSelectedBaseOrgModels}
              exportFileName="base_org_models_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search base org models..."
              noDataMessage="No base org models found"
              customActions={
                <div className="flex gap-2">
                  {selectedBaseOrgModels.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" 
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              hideHeader={true}/>
                      Delete ({selectedBaseOrgModels.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Base Org Model
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <BaseOrgModelDisplay
              inline
              modeProp={formMode}
              dataProp={selectedBaseOrgModel}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
