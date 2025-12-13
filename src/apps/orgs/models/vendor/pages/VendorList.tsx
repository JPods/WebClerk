import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import DataTable, { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchVendors } from "../services/vendorApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "../../../../../context/ThemeContext";
import VendorDetail from "./VendorDetail";

export default function VendorList() {
  const { theme } = useTheme();
  const [data, setData] = useState<any[]>([]);
  const [selectedVendor, setSelectedVendor] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const getVendorData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchVendors();
      if (res.status === 200) {
        setData(res.data.items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch vendors", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch vendors", error);
      dispatch(showToast({ message: "Failed to fetch vendors", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getVendorData();
  }, [getVendorData]);

  const handleView = (row: any) => {
    setSelectedVendor(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedVendor(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedVendor(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getVendorData();
    setFormMode(null);
    setSelectedVendor(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedVendor(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete vendor ${row.name}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(showToast({ message: "Vendor deleted successfully", type: "success" }));
        getVendorData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete vendor", type: "error" }));
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
      name: "Phone",
      selector: (row) => row.phone || "--",
      sortable: true,
      width: "20%",
    },
    {
      name: "Email",
      selector: (row) => row.email || "--",
      sortable: true,
      width: "25%",
    },
    {
      name: "Vendor Number",
      selector: (row) => row.vendor_number || "--",
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
      <PageBreadcrumb pageTitle="Vendor List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Vendor
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
                progressComponent={<div className="p-8 text-center">Loading vendors...</div>}
                onRowClicked={(row) => handleView(row)}
              />
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <VendorDetail
              inline
              modeProp={formMode}
              dataProp={selectedVendor}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}