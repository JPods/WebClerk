import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter } from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { fetchReps, deleteRep } from "../services/repApi";
import { FaEye, FaEdit, FaTrash, FaPlus, FaCheck, FaTimes } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import RepDetail from "./RepDisplay";
import { dynamicData } from "../../../../../model/dynamicData";

export default function RepList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<dynamicData[]>([]);
  const [selectedRep, setSelectedRep] = useState<dynamicData | null>(null);
  const [selectedReps, setSelectedReps] = useState<dynamicData[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const getRepData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchReps();
      setData(res.data.data.results || []);
    } catch (error) {
      console.error("Failed to fetch reps", error);
      dispatch(showToast({ message: "Failed to fetch reps", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getRepData();
  }, [getRepData]);

  const handleView = useCallback((row: dynamicData) => {
    setSelectedRep(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback(async (row: dynamicData) => {
    try {
      const res = await fetchReps(row.id);
      if (res.status === 200) {
        setSelectedRep(res.data.data.record);
      } else {
        setSelectedRep(row);
      }
    } catch {
      setSelectedRep(row);
    }
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedRep(null);
    setFormMode("add");
  };

  const handleDelete = useCallback(async (row: dynamicData) => {
    if (!window.confirm(`Delete rep ${row.display_name || row.name}?`)) return;
    
    try {
      await deleteRep(row.id);
      dispatch(showToast({ message: "Rep deleted successfully", type: "success" }));
      getRepData();
      if (selectedRep && selectedRep.id === row.id) {
        setFormMode(null);
        setSelectedRep(null);
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete rep", type: "error" }));
    }
  }, [dispatch, getRepData, selectedRep]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedReps.length) return;
    if (!window.confirm(`Delete ${selectedReps.length} rep(s)?`)) return;

    try {
      await Promise.all(selectedReps.map((r) => deleteRep(r.id)));
      dispatch(showToast({ message: `${selectedReps.length} rep(s) deleted`, type: "success" }));
      getRepData();
      setSelectedReps([]);
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete some reps", type: "error" }));
    }
  }, [selectedReps, dispatch, getRepData]);

  const handleFormSaved = () => {
    getRepData();
    setFormMode(null);
    setSelectedRep(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedRep(null);
  };

  const filters: ColumnFilter[] = useMemo(() => [
    { key: "org_type", label: "Org Type", type: "text" },
    { key: "status", label: "Status", type: "text" },
    { key: "is_active", label: "Active", type: "select", options: [
      { value: "true", label: "Active" },
      { value: "false", label: "Inactive" },
    ]},
  ], []);

  const columns: TableColumn<dynamicData>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "display_name", name: "Display Name", selector: (row) => row.display_name || "--", sortable: true, width: "25%" },
    { id: "org_type", name: "Org Type", selector: (row) => row.org_type || "--", sortable: true, width: "12%" },
    { id: "status", name: "Status", selector: (row) => row.status || "--", sortable: true, width: "15%" },
    {
      id: "is_active",
      name: "Active",
      selector: (row) => (row.is_active ? "yes" : "no"),
      cell: (row) => (
        row.is_active 
          ? <FaCheck className="text-green-600" /> 
          : <FaTimes className="text-yellow-600" />
      ),
      sortable: true,
      width: "10%",
    },
    { id: "version", name: "Version", selector: (row) => row.version || "--", sortable: true, width: "10%" },
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
      <PageBreadcrumb pageTitle="Rep List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="Reps"
              loading={loading}
              filters={filters}
              storageKey="rep-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedReps}
              exportFileName="reps_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search reps..."
              noDataMessage="No reps found"
              customActions={
                <div className="flex gap-2">
                  {selectedReps.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" />
                      Delete ({selectedReps.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Rep
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <RepDetail
              inline
              modeProp={formMode}
              dataProp={selectedRep}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
