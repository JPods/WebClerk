import ComponentCard from "@/components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter, type AdvancedDataTableHandle } from "@/components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo, useRef} from "react";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { fetchGLJournals, deleteGLJournal } from "../services/glJournalApi";
import GLJournalDetail from "./GLJournalDetail";
import ButtonToolbar from "@/components/common/ButtonToolbar";

export default function GLJournalList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedGLJournal, setSelectedGLJournal] = useState<any | null>(null);
  const [selectedGLJournals, setSelectedGLJournals] = useState<any[]>([]);
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

  const getGLJournalData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchGLJournals();
      if (res.status === 200) {
        setData(res.data.items || []);
      } else {
        dispatch(showToast({ message: "Failed to fetch gl journals", type: "error" }));
      }
    } catch (error) {
      console.error("Failed to fetch gl journals", error);
      dispatch(showToast({ message: "Failed to fetch gl journals", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getGLJournalData();
  }, [getGLJournalData]);

  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const searchQuery = terms.join(",");
      const res = await fetchGLJournals({ search: searchQuery });
      if (res.status === 200) {
        setData(res.data.items || res.data || []);
      }
    } catch (error) {
      console.error("Database search failed:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleView = useCallback((row: any) => {
    setSelectedGLJournal(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback((row: any) => {
    setSelectedGLJournal(row);
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedGLJournal(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getGLJournalData();
    setFormMode(null);
    setSelectedGLJournal(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedGLJournal(null);
  };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete gl journal ${row.id}?`)) return;
    
    try {
      await deleteGLJournal(row.id);
      dispatch(showToast({ message: "GL Journal deleted successfully", type: "success" }));
      getGLJournalData();
      if (selectedGLJournal && selectedGLJournal.id === row.id) {
        setFormMode(null);
        setSelectedGLJournal(null);
      }
    } catch {
      dispatch(showToast({ message: "Failed to delete gl journal", type: "error" }));
    }
  }, [dispatch, getGLJournalData, selectedGLJournal]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedGLJournals.length) return;
    if (!window.confirm(`Delete ${selectedGLJournals.length} gl journal(s)?`)) return;

    try {
      await Promise.all(selectedGLJournals.map((j) => deleteGLJournal(j.id)));
      dispatch(showToast({ message: `${selectedGLJournals.length} gl journal(s) deleted`, type: "success" }));
      getGLJournalData();
      setSelectedGLJournals([]);
    } catch {
      dispatch(showToast({ message: "Failed to delete some gl journals", type: "error" }));
    }
  }, [selectedGLJournals, dispatch, getGLJournalData]);

  const filters: ColumnFilter[] = useMemo(() => [
    { key: "type", label: "Type", type: "text" },
  ], []);

  const columns: TableColumn<any>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "date", name: "Date", selector: (row) => row.date || "--", sortable: true, width: "15%" },
    { id: "description", name: "Description", selector: (row) => row.description || "--", sortable: true, width: "30%" },
    { id: "amount", name: "Amount", selector: (row) => row.amount || "--", sortable: true, width: "15%" },
    { id: "type", name: "Type", selector: (row) => row.type || "--", sortable: true, width: "12%" },
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
        pageTitle="GL Journal List"
        title="GL Journal"
        modelKey="gl_journal"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        handleBulkDelete={handleBulkDelete}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        selectedRows={selectedGLJournals}
        selectedCount={selectedGLJournals.length}
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
        storageKey="gl_journal-list"
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
              title="GL Journals"
              loading={loading}
              filters={filters}
              storageKey="gl-journal-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedGLJournals}
              exportFileName="gl_journals_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search gl journals..."
              noDataMessage="No gl journals found"
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
              customActions={
                <div className="flex gap-2">
                  {selectedGLJournals.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" 
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              hideHeader={true}/>
                      Delete ({selectedGLJournals.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add GL Journal
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <GLJournalDetail
              inline
              modeProp={formMode}
              dataProp={selectedGLJournal}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
