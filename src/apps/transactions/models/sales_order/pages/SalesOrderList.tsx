import PageBreadcrumb from "../../../../../components/common/PageBreadcrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, {
  ColumnFilter,
} from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import {
  fetchSalesOrders,
  fetchSalesOrderDetail,
} from "../services/salesOrderApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import SalesOrderDetail from "./SalesOrderDetail";

export default function SalesOrderList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedSalesOrders, setSelectedSalesOrders] = useState<any[]>([]);
  const [selectedSalesOrder, setSelectedSalesOrder] = useState<any | null>(
    null
  );
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    null
  );
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);

  const dispatch = useDispatch();

  const getSalesOrderData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchSalesOrders();
      if (res.status === 200) {
        setData(res.data.items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch sales orders", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch sales orders", error);
      dispatch(
        showToast({ message: "Failed to fetch sales orders", type: "error" })
      );
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getSalesOrderData();
  }, [getSalesOrderData]);

  const openSalesOrder = useCallback(
    async (row: any, modeToSet: "view" | "edit") => {
      const salesOrderId = row?.id;
      console.log('[openSalesOrder] row:', row);
      console.log('[openSalesOrder] salesOrderId:', salesOrderId);
      if (!salesOrderId) {
        dispatch(
          showToast({ message: "Sales order id missing", type: "error" })
        );
        return;
      }

      setFormMode(modeToSet);
      setDetailLoading(true);
      setSelectedSalesOrder(null);

      try {
        const detail = await fetchSalesOrderDetail(salesOrderId);
        console.log('[openSalesOrder] detail from API:', detail);
        console.log('[openSalesOrder] detail.lines:', detail?.lines);
        console.log('[openSalesOrder] detail.lines count:', detail?.lines?.length);
        const hasDetail = detail && Object.keys(detail).length > 0;
        if (!hasDetail) {
          throw new Error("Sales order not found");
        }
        const merged = { ...row, ...detail };
        console.log('[openSalesOrder] merged:', merged);
        console.log('[openSalesOrder] merged.lines:', merged?.lines);
        console.log('[openSalesOrder] merged.lines count:', merged?.lines?.length);
        setSelectedSalesOrder(merged);
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Failed to load sales order";
        dispatch(showToast({ message, type: "error" }));
        setFormMode(null);
        setSelectedSalesOrder(null);
      } finally {
        setDetailLoading(false);
      }
    },
    [dispatch]
  );

  const handleView = useCallback(
    (row: any) => {
      openSalesOrder(row, "view");
    },
    [openSalesOrder]
  );

  const handleEdit = useCallback(
    (row: any) => {
      openSalesOrder(row, "edit");
    },
    [openSalesOrder]
  );

  const handleAdd = () => {
    setSelectedSalesOrder(null);
    setFormMode("add");
    setDetailLoading(false);
  };

  const handleFormSaved = () => {
    getSalesOrderData();
    setFormMode(null);
    setSelectedSalesOrder(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedSalesOrder(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete sales order ${row.sales_order_no}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(
          showToast({
            message: "Sales order deleted successfully",
            type: "success",
          })
        );
        getSalesOrderData(); // Refresh data
      } catch (error) {
        dispatch(
          showToast({ message: "Failed to delete sales order", type: "error" })
        );
      }
    }
  };

  const userColumns: TableColumn<any>[] = useMemo(
    () => [
      {
        name: "ID",
        selector: (row) => row.id,
        sortable: true,
        width: "80px",
        cell: (row) => (
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
        name: "Sales Order No",
        selector: (row) => row.sales_order_no || "--",
        sortable: true,
        width: "14%",
      },
      {
        name: "Status",
        selector: (row) => row.status || "--",
        sortable: true,
        width: "12%",
        cell: (row) => (
          <span
            className={`px-2 py-1 rounded-full text-xs font-medium ${
              row.status === "delivered"
                ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                : row.status === "shipped"
                ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                : row.status === "confirmed"
                ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
                : row.status === "draft"
                ? "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200"
                : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
            }`}
          >
            {row.status || "Unknown"}
          </span>
        ),
      },
      {
        name: "Customer",
        selector: (row) => row.customer_name || row.id_customer || "--",
        sortable: true,
        width: "12%",
      },
      {
        name: "Vendor",
        selector: (row) => row.vendor_name || row.id_vendor || "--",
        sortable: true,
        width: "12%",
      },
      {
        name: "Total Amount",
        selector: (row) => row.total || row.total_amount || 0,
        sortable: true,
        width: "10%",
        cell: (row) => (
          <span className="font-medium text-green-600 dark:text-green-400">
            $
            {row.total
              ? Number(row.total).toFixed(2)
              : row.total_amount
              ? Number(row.total_amount).toFixed(2)
              : "0.00"}
          </span>
        ),
      },
      {
        name: "Margin",
        selector: (row) => row.margin_percentage || 0,
        sortable: true,
        width: "8%",
        cell: (row) => (
          <span
            className={`text-center px-2 py-1 rounded text-xs font-medium ${
              (row.margin_percentage || 0) >= 20
                ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                : (row.margin_percentage || 0) >= 10
                ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200"
                : "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
            }`}
          >
            {row.margin_percentage
              ? Number(row.margin_percentage).toFixed(1)
              : "0.0"}
            %
          </span>
        ),
      },
      {
        name: "Lines",
        selector: (row) => row.line_count || (row.lines ? row.lines.length : 0),
        sortable: true,
        width: "6%",
        cell: (row) => (
          <span className="text-center bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
            {row.line_count || (row.lines ? row.lines.length : 0)}
          </span>
        ),
      },
      {
        name: "Created",
        selector: (row) =>
          row.dt_created
            ? typeof row.dt_created === "string"
              ? new Date(row.dt_created).toLocaleDateString()
              : new Date(row.dt_created * 1000).toLocaleDateString()
            : "--",
        sortable: true,
        width: "10%",
      },
      {
        name: "Actions",
        width: "140px",
        cell: (row) => (
          <div className="flex gap-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleView(row);
              }}
              title="View"
              className="p-2 text-blue-600 hover:bg-blue-50 rounded dark:hover:bg-blue-900/20 transition-colors"
            >
              <FaEye className="w-4 h-4" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleEdit(row);
              }}
              title="Edit"
              className="p-2 text-green-600 hover:bg-green-50 rounded dark:hover:bg-green-900/20 transition-colors"
            >
              <FaEdit className="w-4 h-4" />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleDelete(row);
              }}
              title="Delete"
              className="p-2 text-red-600 hover:bg-red-50 rounded dark:hover:bg-red-900/20 transition-colors"
            >
              <FaTrash className="w-4 h-4" />
            </button>
          </div>
        ),
      },
    ],
    [handleView, handleEdit, handleDelete]
  );

  // Filters configuration
  const filters: ColumnFilter[] = useMemo(
    () => [
      {
        key: "status",
        label: "Status",
        type: "select",
        options: [
          { value: "draft", label: "Draft" },
          { value: "confirmed", label: "Confirmed" },
          { value: "shipped", label: "Shipped" },
          { value: "delivered", label: "Delivered" },
          { value: "cancelled", label: "Cancelled" },
        ],
      },
      {
        key: "customer_name",
        label: "Customer",
        type: "text",
      },
      {
        key: "vendor_name",
        label: "Vendor",
        type: "text",
      },
    ],
    []
  );

  // Calculate summary statistics
  const totalOrders = data.length;
  const totalValue = data.reduce(
    (sum, order) => sum + (order.total || order.total_amount || 0),
    0
  );
  const totalMargin = data.reduce(
    (sum, order) => sum + (order.margin_amount || 0),
    0
  );
  const avgMargin = totalOrders > 0 ? (totalMargin / totalValue) * 100 : 0;
  const statusCounts = data.reduce((acc, order) => {
    acc[order.status || "unknown"] = (acc[order.status || "unknown"] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <>
      <PageBreadcrumb pageTitle="Sales Order List" />

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <ComponentCard>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {totalOrders}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Total Orders
            </div>
          </div>
        </ComponentCard>
        <ComponentCard>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              ${totalValue.toFixed(2)}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Total Value
            </div>
          </div>
        </ComponentCard>
        <ComponentCard>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
              {avgMargin.toFixed(1)}%
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Avg Margin
            </div>
          </div>
        </ComponentCard>
        <ComponentCard>
          <div className="text-center">
            <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
              {statusCounts.delivered || 0}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Delivered
            </div>
          </div>
        </ComponentCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={userColumns}
              title="Sales Orders"
              loading={loading}
              filters={filters}
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedSalesOrders}
              exportFileName="sales_orders"
              searchPlaceholder="Search orders, customers, vendors..."
              noDataMessage="No sales orders found"
              customActions={
                <button
                  onClick={handleAdd}
                  className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <FaPlus className="w-4 h-4" />
                  Add Sales Order
                </button>
              }
              onRowClicked={handleEdit}
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            {formMode !== "add" && (detailLoading || !selectedSalesOrder) ? (
              <ComponentCard>
                <div className="p-8 text-center text-sm text-gray-500 dark:text-gray-400">
                  Loading sales order...
                </div>
              </ComponentCard>
            ) : (
              <SalesOrderDetail
                inline
                modeProp={formMode}
                dataProp={formMode === "add" ? null : selectedSalesOrder}
                onSaved={handleFormSaved}
                onCancelInline={handleFormCancel}
              />
            )}
          </div>
        )}
      </div>
    </>
  );
}
