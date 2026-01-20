import PageBreadcrumb from "../../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../../components/common/ComponentCard";
import AdvancedDataTable from "../../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { deleteAction } from "../../../../../userProfile";
import { fetchRequisitions } from "../services/requisitionApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import RequisitionDetail from "./RequisitionDetail";

export default function RequisitionList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedRequisition, setSelectedRequisition] = useState<any | null>(null);
  const [selectedRequisitions, setSelectedRequisitions] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const getRequisitionData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchRequisitions();
      if (res.status === 200) {
        setData(res.data.items || []);
      } else {
        dispatch(showToast({ message: "Failed to fetch requisitions", type: "error" }));
      }
    } catch (error) {
      console.error("Failed to fetch requisitions", error);
      dispatch(showToast({ message: "Failed to fetch requisitions", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getRequisitionData();
  }, [getRequisitionData]);

  const handleView = useCallback((row: any) => {
    setSelectedRequisition(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback((row: any) => {
    setSelectedRequisition(row);
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedRequisition(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getRequisitionData();
    setFormMode(null);
    setSelectedRequisition(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedRequisition(null);
  };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete requisition ${row.requisition_no}?`)) return;
    
    try {
      await deleteAction(row.id);
      dispatch(showToast({ message: "Requisition deleted successfully", type: "success" }));
      getRequisitionData();
      if (selectedRequisition && selectedRequisition.id === row.id) {
        setFormMode(null);
        setSelectedRequisition(null);
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete requisition", type: "error" }));
    }
  }, [dispatch, getRequisitionData, selectedRequisition]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedRequisitions.length) return;
    if (!window.confirm(`Delete ${selectedRequisitions.length} requisition(s)?`)) return;

    try {
      await Promise.all(selectedRequisitions.map((r) => deleteAction(r.id)));
      dispatch(showToast({ message: `${selectedRequisitions.length} requisition(s) deleted`, type: "success" }));
      getRequisitionData();
      setSelectedRequisitions([]);
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete some requisitions", type: "error" }));
    }
  }, [selectedRequisitions, dispatch, getRequisitionData]);

  const columns: TableColumn<any>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "requisition_no", name: "Requisition No", selector: (row) => row.requisition_no || "--", sortable: true, width: "30%" },
    { id: "dt_created", name: "Created", selector: (row) => row.dt_created ? new Date(row.dt_created * 1000).toLocaleDateString() : "--", sortable: true, width: "25%" },
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
      <PageBreadcrumb pageTitle="Requisition List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="Requisitions"
              loading={loading}
              storageKey="requisition-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedRequisitions}
              exportFileName="requisitions_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search requisitions..."
              noDataMessage="No requisitions found"
              customActions={
                <div className="flex gap-2">
                  {selectedRequisitions.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" />
                      Delete ({selectedRequisitions.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Requisition
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <RequisitionDetail
              inline
              modeProp={formMode}
              dataProp={selectedRequisition}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
