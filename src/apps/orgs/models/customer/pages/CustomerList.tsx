import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import DataTable, { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { fetchCustomers, deleteCustomer } from "../services/customerApi";
import {
  FaEye,
  FaEdit,
  FaTrash,
  FaPlus,
  FaCheck,
  FaTimes,
} from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "../../../../../context/ThemeContext";
import CustomerDetail from "./CustomerDisplay";
import { dynamicData } from "../../../../../model/dynamicData";
import CustomerListMob from "./CustomerListMob";
export default function CustomerList() {
  const { theme } = useTheme();
  const [data, setData] = useState<any[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    null
  );
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const getLocationData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchCustomers();
      if (res.status === 200) {
        setData(res.data.data.results);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch locations", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch locations", error);
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getLocationData();
  }, [getLocationData]);

  const handleView = (row: any) => {
    setSelectedCustomer(row);
    setFormMode("view");
  };

  const handleEdit = async (row: dynamicData) => {
    const res = await fetchCustomers(row.id);
    console.log("res.", res);
    if (res.status === 200) setSelectedCustomer(res.data.data.record);
    else setSelectedCustomer(row);
    setFormMode("edit");
    console.log("res", res);
  };

  const handleAdd = () => {
    setSelectedCustomer(null);
    setFormMode("add");
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete location ${row.name}?`)) {
      try {
        await deleteCustomer(row.id);
        dispatch(
          showToast({
            message: "Location deleted successfully",
            type: "success",
          })
        );
        getLocationData(); // Refresh data
        if (selectedCustomer && selectedCustomer.id === row.id) {
          setFormMode(null);
          setSelectedCustomer(null);
        }
      } catch (error) {
        dispatch(
          showToast({
            message: "Failed to delete location",
            type: "error",
          })
        );
      }
    }
  };

  const handleFormSaved = () => {
    getLocationData();
    setFormMode(null);
    setSelectedCustomer(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedCustomer(null);
  };

  const userColumns: TableColumn<any>[] = [
    { name: "id", selector: (row) => row.id, sortable: true, width: "5%" },

    {
      name: "display_name",
      selector: (row) => row.display_name || "--",
      sortable: true,
      width: "25%",
    },
    {
      name: "org_type",
      selector: (row) => row.org_type || "--",
      sortable: true,
      width: "10%",
    },
    {
      name: "status",
      selector: (row) => row.status || "--",
      sortable: true,
      width: "30%",
    },

    {
      name: "is_active",
      selector: (row) => (row.is_active ? "yes" : "no"),
      cell: (row) => (
        <>
          {row.is_active ? (
            <FaCheck className="text-success-600 hover:scale-110 transition" />
          ) : (
            <FaTimes className="text-warning-600 hover:scale-110 transition" />
          )}
        </>
      ),
      sortable: true,
      width: "10%",
    },
    {
      name: "version",
      selector: (row) => row.version || "--",
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
      <PageBreadcrumb pageTitle="Customer List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-2">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Customer
              </button>
            </div>
            <div className="w-full overflow-x-auto rounded-md cus-bg-purple-light dark:bg-gray-900 h-[calc(100vh-265px)]">
              {formMode ? (
                <div className="flex flex-col">
                  <CustomerListMob
                    dataProp={data}
                    handleView={handleView}
                    handleEdit={handleEdit}
                  />
                </div>
              ) : (
                <DataTable
                  columns={userColumns.map((col) => ({
                    ...col,
                    name: typeof col.name === "string" && col.name,
                  }))}
                  data={data}
                  pagination
                  theme={theme === "dark" ? "tailwindDark" : "default"}
                  highlightOnHover
                  pointerOnHover
                  progressPending={loading}
                  progressComponent={
                    <div className="p-8 text-center text-gray-500">
                      Loading locations...
                    </div>
                  }
                  onRowClicked={(row) => handleView(row)}
                  keyField="id"
                />
              )}
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <CustomerDetail
              inline
              modeProp={formMode}
              dataProp={selectedCustomer}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
