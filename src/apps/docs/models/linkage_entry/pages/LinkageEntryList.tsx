/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import DataGrid from "@/components/common/DataGrid";
import ComponentCard from "@/components/common/ComponentCard";
import { useEffect, useState, useCallback, useMemo, useRef} from "react";
import { getRecords } from "@/api/wcapi";
import { FaEye, FaEdit, FaPlus, FaTrashAlt } from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { deleteRecord } from "@/api/wcapi";
import LinkageEntryDisplay from "./LinkageEntryDisplay";
import ButtonToolbar from "@/components/common/ButtonToolbar";
import { useColumnContextMenu } from "@/hooks/useColumnContextMenu";

export default function LinkageEntryList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedEntry, setSelectedEntry] = useState<any | null>(null);
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

  const dispatch = useDispatch();

  const getLinkageEntryData = useCallback(async () => {
    try {
      setLoading(true);
      const list = await getRecords('linkage_entry');
      const recs = Array.isArray(list?.results) ? list.results : Array.isArray(list) ? list : [];
      setData(recs);
    } catch (error) {
      console.error("Failed to fetch linkage entries", error);
      dispatch(showToast({ message: "Failed to fetch linkage entries", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getLinkageEntryData();
  }, [getLinkageEntryData]);

  // Handle database search
  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    const query = terms.join(' ');
    setLoading(true);
    try {
      const list = await getRecords('linkage_entry', { search: query });
      const recs = Array.isArray(list?.results) ? list.results : Array.isArray(list) ? list : [];
      setData(recs);
    } catch (error) {
      console.error("Database search error:", error);
      dispatch(showToast({ message: "Search failed", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  const handleView = (row: any) => {
    setSelectedEntry(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedEntry(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedEntry(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getLinkageEntryData();
    setFormMode(null);
    setSelectedEntry(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedEntry(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete linkage entry ${row.id}?`)) {
      try {
        await deleteRecord('linkage_entry', row.id);
        dispatch(showToast({ message: "Linkage Entry deleted successfully", type: "success" }));
        getLinkageEntryData();
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete linkage entry", type: "error" }));
      }
    }
  };

  const userColumns: any[] = [
    { name: "ID", selector: (row: any) => row.id, sortable: true, width: "80px" },
    { name: "Group", selector: (row: any) => row.group_id, sortable: true, width: "100px" },
    { name: "Model", selector: (row: any) => row.model_name || "--", sortable: true, width: "120px" },
    { name: "Record ID", selector: (row: any) => row.record_id, sortable: true, width: "100px" },
    { name: "Purpose", selector: (row: any) => row.purpose || "--", sortable: true, width: "120px" },
    { name: "Role", selector: (row: any) => row.role || "--", sortable: true, width: "100px" },
    { name: "Name", selector: (row: any) => row.name || "--", sortable: true },
  ];

  userColumns.push({
    name: "Action",
    cell: (row: any) => (
      <div className="flex gap-2">
        <button onClick={() => handleView(row)} title="View">
          <FaEye className="text-blue-600 hover:scale-110 transition" />
        </button>
        <button onClick={() => handleEdit(row)} title="Edit">
          <FaEdit className="text-green-600 hover:scale-110 transition" />
        </button>
        <button onClick={() => handleDelete(row)} title="Delete">
          <FaTrashAlt className="text-red-600 hover:scale-110 transition" />
        </button>
      </div>
    ),
    ignoreRowClick: true,
    allowOverflow: true,
    button: true,
  });

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

  const columnCtx = useColumnContextMenu("linkage_entry_list", userColumns);
  return (
    <>
      <ButtonToolbar
        pageTitle="Linkage Entries"
        title="Linkage Entries"
        modelKey="linkage_entries"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={getLinkageEntryData}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={userColumns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="linkage_entries-list"
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
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Linkage Entry
              </button>
            </div>
            <DataGrid
              ref={tableRef}
              columns={userColumns}
              data={filteredData}
              storageKey="linkage_entry_list"
              loading={loading}
              onRowActivate={handleEdit}
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
            
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              allFields={columnCtx.allFields}
              namedViews={columnCtx.namedViews}
              onDeleteColumn={columnCtx.onDeleteColumn}
              onAddColumn={columnCtx.onAddColumn}
              onSaveLayout={columnCtx.onSaveLayout}
              onSaveLayoutAs={columnCtx.onSaveLayoutAs}
              onLoadView={columnCtx.onLoadView}
              hideHeader={true}/>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <LinkageEntryDisplay
              inline
              modeProp={formMode}
              dataProp={selectedEntry}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
