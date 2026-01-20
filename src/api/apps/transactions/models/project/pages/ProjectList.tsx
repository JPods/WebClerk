import PageBreadcrumb from "../../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../../components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter } from "../../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { deleteAction } from "../../../../../userProfile";
import { fetchProjects } from "../services/projectApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import ProjectDetail from "./ProjectDetail";

export default function ProjectList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedProject, setSelectedProject] = useState<any | null>(null);
  const [selectedProjects, setSelectedProjects] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

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

  return (
    <>
      <PageBreadcrumb pageTitle="Project List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
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
              customActions={
                <div className="flex gap-2">
                  {selectedProjects.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" />
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
