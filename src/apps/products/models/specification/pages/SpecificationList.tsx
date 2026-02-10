import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import { TableColumn } from "react-data-table-component";
import AdvancedDataTable from "../../../../../components/common/AdvancedDataTable";
import { useEffect, useState, useCallback } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchSpecifications } from "../services/specificationApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "../../../../../context/ThemeContext";
import SpecificationDetail from "./SpecificationDetail";

export default function SpecificationList() {
  const { theme } = useTheme();
  const [data, setData] = useState<any[]>([]);
  const [selectedSpecification, setSelectedSpecification] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const getSpecificationData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchSpecifications();
      if (res.status === 200) {
        setData(res.data.items || []);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch specifications", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch specifications", error);
      dispatch(showToast({ message: "Failed to fetch specifications", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getSpecificationData();
  }, [getSpecificationData]);

  const handleView = (row: any) => {
    setSelectedSpecification(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedSpecification(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedSpecification(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getSpecificationData();
    setFormMode(null);
    setSelectedSpecification(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedSpecification(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete specification ${row.name}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(showToast({ message: "Specification deleted successfully", type: "success" }));
        getSpecificationData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete specification", type: "error" }));
      }
    }
  };

  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },
    {
      name: "Name",
      selector: (row) => row.name || "--",
      sortable: true,
      width: "25%",
    },
    {
      name: "Description",
      selector: (row) => row.description || "--",
      sortable: true,
      width: "30%",
    },
    {
      name: "Version",
      selector: (row) => row.version || "--",
      sortable: true,
      width: "15%",
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

  return (
    <>
      <PageBreadcrumb pageTitle="Specification List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Specification
              </button>
            </div>
            <div className="overflow-x-auto bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-400 rounded-md">
              <AdvancedDataTable
                columns={userColumns.map((col) => ({
                  ...col,
                  name: typeof col.name === "string" ? col.name.toUpperCase() : col.name,
                }))}
                data={data}
                storageKey="specification_list"
                onRowActivate={handleEdit}
                loading={loading}
              />
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <SpecificationDetail
              inline
              modeProp={formMode}
              dataProp={selectedSpecification}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}