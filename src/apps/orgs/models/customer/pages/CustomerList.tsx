import { useState, useEffect, useMemo, useCallback } from "react";
import { TableColumn } from "react-data-table-component";
import { FaPlus, FaEye, FaEdit, FaTrash } from "react-icons/fa";
import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, {
  ColumnFilter,
} from "../../../../../components/common/AdvancedDataTable";
import { fetchCustomers } from "../services/customerApi";
import { useNavigate } from "react-router";
import { useDispatch } from "react-redux";
import { showToast } from "../../../../../store/slices/toastSlice";
import CustomerDetail from "./CustomerDetail";
import CustomerListMob from "./CustomerListMob";
import { deleteRecord, getRecord } from "../../../../../api/wcapi";
import { useAppSelector } from "../../../../../store/hooks";
import { CustomerApiTask } from "../types/customerType";

export default function CustomerList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedCustomers, setSelectedCustomers] = useState<any[]>([]);
  const [selectedCustomer, setSelectedCustomer] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    null,
  );
  const [searchDatabase, setSearchDatabase] = useState(false);

  // Fetch actions
  const fetchActions = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetchCustomers();
      if (response.status === 200) {
        const apiData = Array.isArray(response?.data?.items)
          ? response.data.items
          : [];
        setData(apiData);
      } else {
        throw new Error("Failed to fetch customers");
      }
    } catch (error) {
      console.error("Error fetching customers:", error);
      dispatch(
        showToast({
          message: "Failed to load customers. Please try again.",
          type: "error",
        }),
      );
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    fetchActions();
  }, [fetchActions]);

  // Database search handler
  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    setLoading(true);
    const searchQuery = terms.join(",");
    try {
      const res = await fetchCustomers({ search: searchQuery });
      if (res.status === 200) {
        setData(res.data.items || []);
      }
    } catch (error) {
      console.error("Database search failed:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Action handlers
  const handleView = useCallback((row: any) => {
    setSelectedCustomer(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback(async (row: any) => {
    setSelectedCustomer(row);
    setFormMode("edit");
    // Optionally fetch fresh data here if needed
  }, []);

  const handleDelete = useCallback(
    async (row: any) => {
      if (!window.confirm(`Delete customer #${row.id}?`)) return;
      setLoading(true);
      try {
        await deleteRecord("customer", row.id);
        setData((prev) => prev.filter((c) => c.id !== row.id));
        setSelectedCustomers((prev) => prev.filter((c) => c.id !== row.id));
        if (selectedCustomer?.id === row.id) {
          setSelectedCustomer(null);
          setFormMode(null);
        }
        dispatch(showToast({ message: "Customer deleted", type: "success" }));
      } catch (error) {
        console.error("Delete failed:", error);
        dispatch(
          showToast({ message: "Failed to delete customer", type: "error" }),
        );
      } finally {
        setLoading(false);
      }
    },
    [dispatch, selectedCustomer],
  );

  // Add new handler
  const handleAdd = () => {
    setSelectedCustomer(null);
    setFormMode("add");
  };

  // Form saved handler
  const handleFormSaved = () => {
    fetchActions();
    setFormMode(null);
    setSelectedCustomer(null);
  };

  // Form cancel handler
  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedCustomer(null);
  };

  // Columns
  const useCustomerColumns = (
    handleEdit: any,
    handleView: any,
    handleDelete: any,
  ) =>
    useMemo(
      () => [
        {
          name: "ID",
          selector: (row: any) => row.id,
          sortable: true,
          width: "80px",
          cell: (row: any) => (
            <div
              onClick={(e) => {
                e.stopPropagation();
                handleEdit(row);
              }}
              className="text-xs font-mono text-blue-600 dark:text-blue-400 cursor-pointer hover:underline"
            >
              {row.id}
            </div>
          ),
        },
        {
          name: "Display Name",
          selector: (row: any) => row.display_name || "--",
          sortable: true,
          width: "20%",
          cell: (row: any) => (
            <div className="font-medium text-gray-900 dark:text-white">
              {row.display_name || "--"}
            </div>
          ),
        },
        {
          name: "Org Type",
          selector: (row: any) => row.org_type || "--",
          sortable: true,
          width: "12%",
        },
        {
          name: "Status",
          selector: (row: any) => row.status || "--",
          sortable: true,
          width: "15%",
          cell: (row: any) => (
            <span
              className={`px-2 py-1 rounded-full text-xs font-medium ${
                row.status === "active"
                  ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                  : row.status === "pending"
                  ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
                  : row.status === "suspended"
                  ? "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
                  : "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200"
              }`}
            >
              {row.status || "Unknown"}
            </span>
          ),
        },
        {
          name: "Active",
          selector: (row: any) => (row.is_active ? "yes" : "no"),
          sortable: true,
          width: "10%",
          cell: (row: any) => (
            <span
              className={`px-2 py-1 rounded-full text-xs font-medium ${
                row.is_active
                  ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200"
                  : "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400"
              }`}
            >
              {row.is_active ? "Yes" : "No"}
            </span>
          ),
        },
        {
          name: "Version",
          selector: (row: any) => row.version || "--",
          sortable: true,
          width: "10%",
        },
        {
          name: "Actions",
          width: "140px",
          cell: (row: any) => (
            <div className="flex gap-2">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleView(row);
                }}
                title="View"
                className="p-2 text-blue-600 text-xs hover:bg-blue-50 rounded dark:hover:bg-blue-900/20 transition-colors"
              >
                <FaEye className="w-4 h-4" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleEdit(row);
                }}
                title="Edit"
                className="p-2 text-green-600 text-xs hover:bg-green-50 rounded dark:hover:bg-green-900/20 transition-colors"
              >
                <FaEdit className="w-4 h-4" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(row);
                }}
                title="Delete"
                className="p-2 text-red-600 text-xs hover:bg-red-50 rounded dark:hover:bg-red-900/20 transition-colors"
              >
                <FaTrash className="w-4 h-4" />
              </button>
            </div>
          ),
        },
      ],
      [handleEdit, handleView, handleDelete],
    );

  const columns = useCustomerColumns(handleEdit, handleView, handleDelete);

  const filters: ColumnFilter[] = [
    {
      key: "status",
      name: "status",
      field: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "active", label: "Active" },
        { value: "inactive", label: "Inactive" },
        { value: "pending", label: "Pending" },
        { value: "suspended", label: "Suspended" },
        { value: "archived", label: "Archived" },
      ],
    },
    {
      key: "is_active",
      name: "is_active",
      field: "is_active",
      label: "Active Status",
      type: "select",
      options: [
        { value: "true", label: "Active" },
        { value: "false", label: "Inactive" },
      ],
    },
    {
      key: "org_type",
      name: "org_type",
      field: "org_type",
      label: "Organization Type",
      type: "select",
      options: [
        { value: "customer", label: "Customer" },
        { value: "vendor", label: "Vendor" },
        { value: "partner", label: "Partner" },
        { value: "internal", label: "Internal" },
      ],
    },
    {
      key: "display_name",
      name: "display_name",
      field: "display_name",
      label: "Name",
      type: "text",
    },
  ];

  return (
    <>
      <PageBreadcrumb pageTitle="Customer List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard className="cus-bg-purple-light rounded-md">
            {formMode ? (
              <div className="flex flex-col">
                <CustomerListMob
                  dataProp={data}
                  selectedCustomer={selectedCustomer}
                  handleView={handleView}
                  handleEdit={handleEdit}
                  emptyMessage="No customer found."
                />
              </div>
            ) : (
              <AdvancedDataTable
                data={data}
                columns={columns}
                title="Customer"
                loading={loading}
                filters={filters}
                enableExport={true}
                enableSelection={true}
                enableDatabaseSearch={true}
                searchDatabase={searchDatabase}
                onSearchModeChange={setSearchDatabase}
                onDatabaseSearch={handleDatabaseSearch}
                onSelectionChange={setSelectedCustomers}
                exportFileName="customer_export"
                searchPlaceholder="Search customer, display_name, org_type..."
                noDataMessage="No customer found"
                customActions={
                  <div className="flex gap-2">
                    <button
                      onClick={handleAdd}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                    >
                      <FaPlus className="w-4 h-4" />
                      New Customer
                    </button>
                  </div>
                }
                onRowClicked={handleView}
              />
            )}
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
