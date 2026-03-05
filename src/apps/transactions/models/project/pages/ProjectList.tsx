import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter, type AdvancedDataTableHandle } from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo, useRef} from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchProjects } from "../services/projectApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import ProjectDetail from "./ProjectDetail";
import ButtonToolbar from "@/components/common/ButtonToolbar";

export default function ProjectList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedProject, setSelectedProject] = useState<any | null>(null);
  const [selectedProjects, setSelectedProjects] = useState<any[]>([]);
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

  const getProjectData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchProjects();
      if (res.status === 200) {
        setData(res.data.items || []);
      } else {
        dispatch(showToast({ message: "Failed to fetch projects", type: "error" }));
      }
    } catch (error) {
      console.error("Failed to fetch projects", error);
      dispatch(showToast({ message: "Failed to fetch projects", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getProjectData();
  }, [getProjectData]);

  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const searchQuery = terms.join(",");
      const res = await fetchProjects({ search: searchQuery });
      if (res.status === 200) {
        setData(res.data.items || []);
      }
    } catch (error) {
      console.error("Database search failed:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleView = useCallback((row: any) => {
    setSelectedProject(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback((row: any) => {
    setSelectedProject(row);
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedProject(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getProjectData();
    setFormMode(null);
    setSelectedProject(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedProject(null);
  };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete project ${row.name}?`)) return;
    
    try {
      await deleteAction(row.id);
      dispatch(showToast({ message: "Project deleted successfully", type: "success" }));
      getProjectData();
      if (selectedProject && selectedProject.id === row.id) {
        setFormMode(null);
        setSelectedProject(null);
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete project", type: "error" }));
    }
  }, [dispatch, getProjectData, selectedProject]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedProjects.length) return;
    if (!window.confirm(`Delete ${selectedProjects.length} project(s)?`)) return;

    try {
      await Promise.all(selectedProjects.map((p) => deleteAction(p.id)));
      dispatch(showToast({ message: `${selectedProjects.length} project(s) deleted`, type: "success" }));
      getProjectData();
      setSelectedProjects([]);
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete some projects", type: "error" }));
    }
  }, [selectedProjects, dispatch, getProjectData]);

  const filters: ColumnFilter[] = useMemo(() => [
    { key: "status", label: "Status", type: "text" },
  ], []);

  const columns: TableColumn<any>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "name", name: "Name", selector: (row) => row.name || "--", sortable: true, width: "20%" },
    { id: "description", name: "Description", selector: (row) => row.description || "--", sortable: true, width: "25%" },
    { id: "status", name: "Status", selector: (row) => row.status || "--", sortable: true, width: "12%" },
    { id: "start_date", name: "Start Date", selector: (row) => row.start_date || "--", sortable: true, width: "12%" },
    { id: "end_date", name: "End Date", selector: (row) => row.end_date || "--", sortable: true, width: "12%" },
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
        pageTitle="Project List"
        title="Project"
        modelKey="project"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        handleBulkDelete={handleBulkDelete}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        selectedRows={selectedProjects}
        selectedCount={selectedProjects.length}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={getProjectData}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={columns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="project-list"
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
              title="Projects"
              loading={loading}
              filters={filters}
              storageKey="project-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedProjects}
              exportFileName="projects_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search projects..."
              noDataMessage="No projects found"
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
              customActions={
                <div className="flex gap-2">
                  {selectedProjects.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" 
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              hideHeader={true}/>
                      Delete ({selectedProjects.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Project
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <ProjectDetail
              inline
              modeProp={formMode}
              dataProp={selectedProject}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
