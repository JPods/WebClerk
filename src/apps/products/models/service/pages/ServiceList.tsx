/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import DataGrid from "@/components/common/DataGrid";
import ComponentCard from "../../../../../components/common/ComponentCard";
import { useEffect, useState, useCallback, useMemo, useRef} from "react";
import { fetchServices, deleteService } from "../services/serviceApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import ServiceDetail from "./ServiceDetail";
import ButtonToolbar from "@/components/common/ButtonToolbar";

export default function ServiceList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedService, setSelectedService] = useState<any | null>(null);
  const [selectedItems, setSelectedItems] = useState<any[]>([]);
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

  const getData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchServices();
      if (res.status === 200) {
        setData(res.data?.items || res.data?.data?.results || []);
      } else {
        dispatch(showToast({ message: "Failed to fetch services", type: "error" }));
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to fetch services", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => { getData(); }, [getData]);

  const handleView = useCallback((row: any) => { setSelectedService(row); setFormMode("view"); }, []);
  const handleEdit = useCallback((row: any) => { setSelectedService(row); setFormMode("edit"); }, []);
  const handleAdd = () => { setSelectedService(null); setFormMode("add"); };
  const handleFormSaved = () => { getData(); setFormMode(null); setSelectedService(null); };
  const handleFormCancel = () => { setFormMode(null); setSelectedService(null); };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete service ${row.name || row.id}?`)) return;
    try {
      await deleteService(row.id);
      dispatch(showToast({ message: "Service deleted successfully", type: "success" }));
      getData();
    } catch { dispatch(showToast({ message: "Failed to delete service", type: "error" })); }
  }, [dispatch, getData]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedItems.length || !window.confirm(`Delete ${selectedItems.length} service(s)?`)) return;
    try {
      await Promise.all(selectedItems.map((item) => deleteService(item.id)));
      dispatch(showToast({ message: `${selectedItems.length} service(s) deleted`, type: "success" }));
      getData(); setSelectedItems([]);
    } catch { dispatch(showToast({ message: "Failed to delete some services", type: "error" })); }
  }, [selectedItems, dispatch, getData]);

  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const searchQuery = terms.join(",");
      const res = await fetchServices({ search: searchQuery });
      if (res.status === 200) {
        setData(res.data?.items || res.data?.data?.results || []);
      }
    } catch (error) {
      console.error("Database search failed:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const columns: any[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "name", name: "Name", selector: (row) => row.name || "--", sortable: true },
    { id: "description", name: "Description", selector: (row) => row.description || "--", sortable: true },
    { id: "cost", name: "Cost", selector: (row) => row.cost || "--", sortable: true, width: "120px" },
    { id: "date", name: "Date", selector: (row) => row.date || "--", sortable: true, width: "120px" },
    {
      id: "actions",
      name: "Actions",
      cell: (row) => (
        <div className="flex gap-2">
          <button onClick={() => handleView(row)} title="View"><FaEye className="text-blue-600 hover:scale-110 transition" /></button>
          <button onClick={() => handleEdit(row)} title="Edit"><FaEdit className="text-green-600 hover:scale-110 transition" /></button>
          <button onClick={() => handleDelete(row)} title="Delete"><FaTrash className="text-red-600 hover:scale-110 transition" /></button>
        </div>
      ),
      ignoreRowClick: true, allowOverflow: true, button: true, width: "100px",
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
        pageTitle="Service List"
        title="Service"
        modelKey="service"
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
        storageKey="service-list"
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
              title="Services"
              loading={loading}
              storageKey="service-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedItems}
              exportFileName="service_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search services..."
              noDataMessage="No services found"
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
              customActions={
                <div className="flex gap-2">
                  {selectedItems.length > 0 && (
                    <button onClick={handleBulkDelete} className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors">
                      <FaTrash className="w-4 h-4" 
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              hideHeader={true}/> Delete ({selectedItems.length})
                    </button>
                  )}
                  <button onClick={handleAdd} className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors">
                    <FaPlus className="w-4 h-4" /> Add Service
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <ServiceDetail inline modeProp={formMode} dataProp={selectedService} onSaved={handleFormSaved} onCancelInline={handleFormCancel} />
          </div>
        )}
      </div>
    </>
  );
}