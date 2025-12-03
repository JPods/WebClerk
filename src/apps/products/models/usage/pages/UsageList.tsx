import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import DataTable, { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchUsages } from "../services/usageApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "../../../../../context/ThemeContext";
import UsageDetail from "./UsageDetail";

export default function UsageList() {
  const { theme } = useTheme();
  const [data, setData] = useState<any[]>([]);
  const [selectedUsage, setSelectedUsage] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const getUsageData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchUsages();
      if (res.status === 200) {
        setData(res.data.items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch usages", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch usages", error);
      dispatch(showToast({ message: "Failed to fetch usages", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getUsageData();
  }, [getUsageData]);

  const handleView = (row: any) => {
    setSelectedUsage(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedUsage(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedUsage(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getUsageData();
    setFormMode(null);
    setSelectedUsage(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedUsage(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete usage ${row.id}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(showToast({ message: "Usage deleted successfully", type: "success" }));
        getUsageData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete usage", type: "error" }));
      }
    }
  };

  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },
    {
      name: "Item ID",
      selector: (row) => row.item_id || "--",
      sortable: true,
      width: "20%",
    },
    {
      name: "Quantity Used",
      selector: (row) => row.quantity_used || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Date Used",
      selector: (row) => row.date_used || "--",
      sortable: true,
      width: "20%",
    },
    {
      name: "User ID",
      selector: (row) => row.user_id || "--",
      sortable: true,
      width: "20%",
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
      <PageBreadcrumb pageTitle="Usage List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Usage
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
                progressComponent={<div className="p-8 text-center">Loading usages...</div>}
                onRowClicked={(row) => handleView(row)}
              />
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <UsageDetail
              inline
              modeProp={formMode}
              dataProp={selectedUsage}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}