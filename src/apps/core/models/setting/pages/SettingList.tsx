import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import DataTable, { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { fetchSettings, deleteSetting } from "../services/settingApi";
import { FaEye, FaEdit, FaPlus, FaTrashAlt } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "../../../../../context/ThemeContext";
import SettingDetail from "./SettingDetail";
import Badge from "../../../../../components/ui/badge/Badge";

export default function SettingList() {
  const { theme } = useTheme();
  const [data, setData] = useState<any[]>([]);
  const [selectedSetting, setSelectedSetting] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const getSettingData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchSettings();
      if (res.status === 200) {
        setData(res.data.items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch settings", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch settings", error);
      dispatch(showToast({ message: "Failed to fetch settings", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getSettingData();
  }, [getSettingData]);

  const handleView = (row: any) => {
    setSelectedSetting(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedSetting(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedSetting(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getSettingData();
    setFormMode(null);
    setSelectedSetting(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedSetting(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete setting ${row.name}?`)) {
      try {
        await deleteSetting(row.id);
        dispatch(showToast({ message: "Setting deleted successfully", type: "success" }));
        getSettingData(); // Refresh data
      } catch {
        dispatch(showToast({ message: "Failed to delete setting", type: "error" }));
      }
    }
  };

  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },
    {
      name: "Name",
      selector: (row) => row.name || "--",
      sortable: true,
      width: "20%",
    },
    {
      name: "Purpose",
      selector: (row) => row.purpose || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Role",
      selector: (row) => row.role || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Model Target",
      selector: (row) => row.model_target || "--",
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

  return (
    <>
      <PageBreadcrumb pageTitle="Setting List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Setting
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
                progressComponent={<div className="p-8 text-center">Loading settings...</div>}
                onRowClicked={(row) => handleView(row)}
              />
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <SettingDetail
              inline
              modeProp={formMode}
              dataProp={selectedSetting}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}