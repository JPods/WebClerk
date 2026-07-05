/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import DataGrid from "@/components/common/DataGrid";
import ComponentCard from "../../../../../components/common/ComponentCard";
import { useEffect, useState, useCallback, useMemo, useRef} from "react";
import { fetchAudits, deleteAudit } from "../services/auditApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import AuditDetail from "./AuditDetail";
import ButtonToolbar from "@/components/common/ButtonToolbar";
import { useColumnContextMenu } from "@/hooks/useColumnContextMenu";

export default function AuditList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedAudit, setSelectedAudit] = useState<any | null>(null);
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

  const getAuditData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchAudits();
      if (res.status === 200) {
        setData(res.data.items);
      } else {
        dispatch(showToast({ message: "Failed to fetch audits", type: "error" }));
      }
    } catch (error) {
      console.error("Failed to fetch audits", error);
      dispatch(showToast({ message: "Failed to fetch audits", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getAuditData();
  }, [getAuditData]);

  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const searchQuery = terms.join(",");
      const res = await fetchAudits({ search: searchQuery });
      if (res.status === 200) {
        setData(res.data.items || res.data || []);
      }
    } catch (error) {
      console.error("Database search failed:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleView = (row: any) => {
    setSelectedAudit(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedAudit(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedAudit(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getAuditData();
    setFormMode(null);
    setSelectedAudit(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedAudit(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete audit ${row.id}?`)) {
      try {
        await deleteAudit(row.id);
        dispatch(showToast({ message: "Audit deleted successfully", type: "success" }));
        getAuditData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete audit", type: "error" }));
      }
    }
  };

  const userColumns: any[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },
    {
      name: "Date",
      selector: (row) => row.date || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Action",
      selector: (row) => row.action || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "User",
      selector: (row) => row.user || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Description",
      selector: (row) => row.description || "--",
      sortable: true,
      width: "35%",
    },
    {
      name: "Action",
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
    },
  ];

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

  const columnCtx = useColumnContextMenu("audit_list", userColumns);
  return (
    <>
      <ButtonToolbar
        pageTitle="Audit List"
        title="Audit"
        modelKey="audit"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={getAuditData}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={userColumns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="audit-list"
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
                Add Audit
              </button>
            </div>
            <div className="overflow-x-auto bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-400 rounded-md">
              <DataGrid
              ref={tableRef}
                columns={userColumns.map((col) => ({
                  ...col,
                  name: typeof col.name === "string" ? col.name.toUpperCase() : col.name,
                }))}
                data={filteredData}
                storageKey="audit_list"
                loading={loading}
                onRowActivate={handleEdit}
                enableDatabaseSearch={true}
                searchDatabase={searchDatabase}
                onSearchModeChange={setSearchDatabase}
                onDatabaseSearch={handleDatabaseSearch}
                rowKeyField="id"
              
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
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <AuditDetail
              inline
              modeProp={formMode}
              dataProp={selectedAudit}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}