/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, { type AdvancedDataTableHandle } from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo, useRef} from "react";
import { getRecords, deleteRecord } from "../../../../../api/wcapi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import TermDisplay from "./TermDisplay";
import ButtonToolbar from "@/components/common/ButtonToolbar";

export default function TermList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedTerm, setSelectedTerm] = useState<any | null>(null);
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

  const dispatch = useDispatch();

  const getTermData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await getRecords('term');
      setData(res.results || []);
    } catch (error) {
      console.error("Failed to fetch terms", error);
      dispatch(showToast({ message: "Failed to fetch terms", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getTermData();
  }, [getTermData]);

  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const searchQuery = terms.join(",");
      const res = await getRecords('term', { search: searchQuery });
      setData(res.results || []);
    } catch (error) {
      console.error("Database search failed:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleView = (row: any) => {
    setSelectedTerm(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedTerm(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedTerm(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getTermData();
    setFormMode(null);
    setSelectedTerm(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedTerm(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete term ${row.name}?`)) {
      try {
        await deleteRecord('term', row.id);
        dispatch(showToast({ message: "Term deleted successfully", type: "success" }));
        getTermData();
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete term", type: "error" }));
      }
    }
  };

  const userColumns: TableColumn<any>[] = useMemo(() => [
    { name: "ID", selector: (row: any) => row.id, sortable: true, width: "80px" },
    { name: "Name", selector: (row: any) => row.name || "--", sortable: true },
    { name: "Description", selector: (row: any) => row.description || "--", sortable: true },
    { name: "Duration", selector: (row: any) => row.duration || "--", sortable: true },
    {
      name: "Actions",
      cell: (row: any) => (
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
      button: true,
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
  return (
    <>
      <ButtonToolbar
        pageTitle="Terms"
        title="Terms"
        modelKey="terms"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={getTermData}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={userColumns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="terms-list"
        filterValues={filterValues}
        onFilterValuesChange={setFilterValues}
        filtersOpen={filtersOpen}
        onFiltersOpenChange={setFiltersOpen}
      />
<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600"
              >
                <FaPlus />
                Add Term
              </button>
            </div>
            <AdvancedDataTable
              ref={tableRef}
              columns={userColumns}
              data={filteredData}
              loading={loading}
              storageKey="term_list"
              onRowActivate={handleEdit}
              title="Terms"
              exportFileName="terms"
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
            
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              hideHeader={true}/>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <TermDisplay
              inline
              modeProp={formMode}
              dataProp={selectedTerm}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
