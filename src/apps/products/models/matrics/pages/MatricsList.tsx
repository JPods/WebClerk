import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchMatricss } from "../services/matricsApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import MatricsDetail from "./MatricsDetail";

export default function MatricsList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedMatrics, setSelectedMatrics] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const getMatricsData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchMatricss();
      if (res.status === 200) {
        setData(res.data.items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch matrics", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch matrics", error);
      dispatch(showToast({ message: "Failed to fetch matrics", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getMatricsData();
  }, [getMatricsData]);

  const handleView = (row: any) => {
    setSelectedMatrics(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedMatrics(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedMatrics(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getMatricsData();
    setFormMode(null);
    setSelectedMatrics(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedMatrics(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete matrics ${row.name}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(showToast({ message: "Matrics deleted successfully", type: "success" }));
        getMatricsData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete matrics", type: "error" }));
      }
    }
  };

  const userColumns: TableColumn<any>[] = useMemo(() => [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },
    {
      name: "Name",
      selector: (row) => row.name || "--",
      sortable: true,
      width: "25%",
    },
    {
      name: "Value",
      selector: (row) => row.value || "--",
      sortable: true,
      width: "20%",
    },
    {
      name: "Unit",
      selector: (row) => row.unit || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Description",
      selector: (row) => row.description || "--",
      sortable: true,
      width: "25%",
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
  ], []);

  return (
    <>
      <PageBreadcrumb pageTitle="Matrics List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Matrics
              </button>
            </div>
            <AdvancedDataTable
              columns={userColumns}
              data={data}
              loading={loading}
              storageKey="matrics_list"
              onRowActivate={handleEdit}
              title="Matrics"
              exportFileName="matrics"
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <MatricsDetail
              inline
              modeProp={formMode}
              dataProp={selectedMatrics}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
