import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import ComponentCard from "@/components/common/ComponentCard";
import DataTable, { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { getRecords } from "@/api/wcapi";
import { FaEye, FaEdit, FaPlus, FaTrashAlt } from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "@/context/ThemeContext";
import { deleteRecord } from "@/api/wcapi";
import ServiceDisplay from "./ServiceDisplay";

export default function ServiceList() {
  const { theme } = useTheme();
  const [data, setData] = useState<any[]>([]);
  const [selectedService, setSelectedService] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const getServiceData = useCallback(async () => {
    try {
      setLoading(true);
      const list = await getRecords('service');
      const recs = Array.isArray(list?.results) ? list.results : Array.isArray(list) ? list : [];
      setData(recs);
    } catch (error) {
      console.error("Failed to fetch services", error);
      dispatch(showToast({ message: "Failed to fetch services", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getServiceData();
  }, [getServiceData]);

  const handleView = (row: any) => {
    setSelectedService(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedService(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedService(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getServiceData();
    setFormMode(null);
    setSelectedService(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedService(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete service ${row.id}?`)) {
      try {
        await deleteRecord('service', row.id);
        dispatch(showToast({ message: "Service deleted successfully", type: "success" }));
        getServiceData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete service", type: "error" }));
      }
    }
  };

  // Hardcoded columns: id and common fields
  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "10%" },
    { name: "Name", selector: (row) => row.name || "--", sortable: true, width: "40%" },
    { name: "Type", selector: (row) => row.type || "--", sortable: true, width: "30%" },
    { name: "Price", selector: (row) => row.price || "--", sortable: true, width: "20%" },
  ];

  userColumns.push({
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
  });

  return (
    <>
      <PageBreadcrumb pageTitle="Service List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Service
              </button>
            </div>
            <div className="overflow-x-auto bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-400 rounded-md">
              <DataTable
                columns={userColumns.map((col) => ({
                  ...col,
                  name: typeof col.name === "string" ? col.name.toUpperCase() : col.name,
                }))}
                data={data}
                pagination
                theme={theme === "dark" ? "tailwindDark" : "default"}
                highlightOnHover
                pointerOnHover
                progressPending={loading}
                progressComponent={<div className="p-8 text-center">Loading services...</div>}
                onRowClicked={(row) => handleView(row)}
              />
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <ServiceDisplay
              inline
              modeProp={formMode}
              dataProp={selectedService}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}