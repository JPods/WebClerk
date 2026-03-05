import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, { type AdvancedDataTableHandle } from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useRef} from "react";
import { fetchTemplates, deleteTemplate } from "../services/templateApi";
import { FaEye, FaEdit, FaPlus, FaTrashAlt } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import TemplateDetail from "./TemplateDetail";
import Badge from "../../../../../components/ui/badge/Badge";
import ButtonToolbar from "@/components/common/ButtonToolbar";

export default function TemplateList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<any | null>(null);
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

  const getTemplateData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchTemplates();
      if (res.status === 200) {
        setData(res.data.items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch templates", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch templates", error);
      dispatch(showToast({ message: "Failed to fetch templates", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getTemplateData();
  }, [getTemplateData]);

  // Handle database search
  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    const query = terms.join(' ');
    setLoading(true);
    try {
      const res = await fetchTemplates({ search: query });
      if (res.status === 200) {
        setData(res.data.items);
      }
    } catch (error) {
      console.error("Database search error:", error);
      dispatch(showToast({ message: "Search failed", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  const handleView = (row: any) => {
    setSelectedTemplate(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedTemplate(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedTemplate(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getTemplateData();
    setFormMode(null);
    setSelectedTemplate(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedTemplate(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete template ${row.name}?`)) {
      try {
        await deleteTemplate(row.id);
        dispatch(showToast({ message: "Template deleted successfully", type: "success" }));
        getTemplateData(); // Refresh data
      } catch {
        dispatch(showToast({ message: "Failed to delete template", type: "error" }));
      }
    }
  };

  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },
    {
      name: "Purpose",
      selector: (row) => row.purpose || "--",
      sortable: true,
      width: "20%",
    },
    {
      name: "Name",
      selector: (row) => row.name || "--",
      sortable: true,
      width: "25%",
    },
    {
      name: "DT Processed",
      selector: (row) => row.dt_processed || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Is Active",
      selector: (row) => (row.is_active ? "Active" : "Inactive"),
      cell: (row) => (
        <>
          <Badge size="sm" color={row.is_active ? "success" : "warning"}>
            {row.is_active ? "Active" : "Inactive"}
          </Badge>
        </>
      ),
      sortable: true,
      width: "10%",
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
            <FaTrashAlt className="text-red-600 hover:scale-110 transition" />
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
    if (columnVisibility.length === 0) return columns;
    return columns.filter((_: any, index: number) => columnVisibility[index] !== false);
  }, [columns, columnVisibility]);
  return (
    <>
      <ButtonToolbar
        pageTitle="Template List"
        title="Template"
        modelKey="template"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
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
        storageKey="template-list"
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
                Add Template
              </button>
            </div>
            <AdvancedDataTable
              ref={tableRef}
              columns={userColumns}
              data={filteredData}
              storageKey="template_list"
              loading={loading}
              onRowActivate={handleEdit}
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
            <TemplateDetail
              inline
              modeProp={formMode}
              dataProp={selectedTemplate}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}