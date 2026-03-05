import ComponentCard from "@/components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter, type AdvancedDataTableHandle } from "@/components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo, useRef} from "react";
import { getRecords, deleteRecord } from "@/api/wcapi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import TaxJurisdictionDisplay from "./TaxJurisdictionDisplay";
import ButtonToolbar from "@/components/common/ButtonToolbar";

export default function TaxJurisdictionList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedTaxJurisdiction, setSelectedTaxJurisdiction] = useState<any | null>(null);
  const [selectedTaxJurisdictions, setSelectedTaxJurisdictions] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>([]);
  const tableRef = useRef<AdvancedDataTableHandle<any>>(null);
  const columnBtnRef = useRef<HTMLButtonElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  const getTaxJurisdictionData = useCallback(async () => {
    try {
      setLoading(true);
      const list = await getRecords('tax_jurisdiction');
      const recs = Array.isArray(list?.results) ? list.results : Array.isArray(list) ? list : [];
      setData(recs);
    } catch (error) {
      console.error("Failed to fetch tax jurisdictions", error);
      dispatch(showToast({ message: "Failed to fetch tax jurisdictions", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getTaxJurisdictionData();
  }, [getTaxJurisdictionData]);

  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const searchQuery = terms.join(",");
      const list = await getRecords('tax_jurisdiction', { search: searchQuery });
      const recs = Array.isArray(list?.results) ? list.results : Array.isArray(list) ? list : [];
      setData(recs);
    } catch (error) {
      console.error("Database search failed:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleView = useCallback((row: any) => {
    setSelectedTaxJurisdiction(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback((row: any) => {
    setSelectedTaxJurisdiction(row);
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedTaxJurisdiction(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getTaxJurisdictionData();
    setFormMode(null);
    setSelectedTaxJurisdiction(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedTaxJurisdiction(null);
  };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete tax jurisdiction ${row.name || row.id}?`)) return;
    
    try {
      await deleteRecord('tax_jurisdiction', row.id);
      dispatch(showToast({ message: "Tax Jurisdiction deleted successfully", type: "success" }));
      getTaxJurisdictionData();
      if (selectedTaxJurisdiction && selectedTaxJurisdiction.id === row.id) {
        setFormMode(null);
        setSelectedTaxJurisdiction(null);
      }
    } catch {
      dispatch(showToast({ message: "Failed to delete tax jurisdiction", type: "error" }));
    }
  }, [dispatch, getTaxJurisdictionData, selectedTaxJurisdiction]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedTaxJurisdictions.length) return;
    if (!window.confirm(`Delete ${selectedTaxJurisdictions.length} tax jurisdiction(s)?`)) return;

    try {
      await Promise.all(selectedTaxJurisdictions.map((t) => deleteRecord('tax_jurisdiction', t.id)));
      dispatch(showToast({ message: `${selectedTaxJurisdictions.length} tax jurisdiction(s) deleted`, type: "success" }));
      getTaxJurisdictionData();
      setSelectedTaxJurisdictions([]);
    } catch {
      dispatch(showToast({ message: "Failed to delete some tax jurisdictions", type: "error" }));
    }
  }, [selectedTaxJurisdictions, dispatch, getTaxJurisdictionData]);

  const filters: ColumnFilter[] = useMemo(() => [
    { key: "code", label: "Code", type: "text" },
  ], []);

  const columns: TableColumn<any>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "name", name: "Name", selector: (row) => row.name || "--", sortable: true, width: "30%" },
    { id: "code", name: "Code", selector: (row) => row.code || "--", sortable: true, width: "20%" },
    { id: "rate", name: "Rate", selector: (row) => row.rate || "--", sortable: true, width: "20%" },
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
        pageTitle="Tax Jurisdiction List"
        title="Tax Jurisdiction"
        modelKey="tax_jurisdiction"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        handleBulkDelete={handleBulkDelete}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        selectedRows={selectedTaxJurisdictions}
        selectedCount={selectedTaxJurisdictions.length}
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
        storageKey="tax_jurisdiction-list"
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
              data={filteredData}
              columns={visibleColumns}
              title="Tax Jurisdictions"
              loading={loading}
              filters={filters}
              storageKey="tax-jurisdiction-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedTaxJurisdictions}
              exportFileName="tax_jurisdictions_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search tax jurisdictions..."
              noDataMessage="No tax jurisdictions found"
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
              customActions={
                <div className="flex gap-2">
                  {selectedTaxJurisdictions.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" 
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              hideHeader={true}/>
                      Delete ({selectedTaxJurisdictions.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Tax Jurisdiction
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <TaxJurisdictionDisplay
              inline
              modeProp={formMode}
              dataProp={selectedTaxJurisdiction}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
