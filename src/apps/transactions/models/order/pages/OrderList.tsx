import ComponentCard from "@/components/common/ComponentCard";
import AdvancedDataTable, {
  ColumnFilter,
} from "@/components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { deleteAction } from "@/api/userProfile";
import { fetchOrders, fetchOrderDetail } from "../services/orderApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import OrderDetail from "./OrderDetail";

// Define the possible order statuses for type safety
type OrderStatus =
  | "draft"
  | "confirmed"
  | "shipped"
  | "delivered"
  | "cancelled";

type OrderRow = {
  id: number | string;
  ida?: string;
  status?: string;
  customer_name?: string;
  id_customer?: string | number;
  vendor_name?: string;
  id_vendor?: string | number;
  total?: number;
  total_amount?: number;
  margin_percentage?: number;
  margin_amount?: number;
  line_count?: number;
  lines?: any[];
  dt_created?: string | number;
  [key: string]: any;
};

export default function OrderList() {
  const [data, setData] = useState<OrderRow[]>([]);
  const [selectedOrder, setSelectedOrder] = useState<OrderRow | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);

  const dispatch = useDispatch();

  const getOrderData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchOrders();
      if (res.status === 200) {
        setData(res.data.items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch orders", type: "error" }),
        );
      }
    } catch (error) {
      console.error("Failed to fetch orders", error);
      dispatch(showToast({ message: "Failed to fetch orders", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getOrderData();
  }, [getOrderData]);

  // Database search handler for comma-separated terms (AND logic)
  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const searchQuery = terms.join(",");
      const res = await fetchOrders({ search: searchQuery });
      if (res.status === 200) {
        setData(res.data.items);
      }
    } catch (error) {
      console.error("Database search failed:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const openOrder = useCallback(
    async (row: any, modeToSet: "view" | "edit") => {
      const order_id = row?.id;
      console.log("[openOrder] row:", row);
      console.log("[openOrder] order_id:", order_id);
      console.log("[openOrder] modeToSet:", modeToSet);
      if (!order_id) {
        dispatch(showToast({ message: "Order id missing", type: "error" }));
        return;
      }

      setFormMode(modeToSet);
      console.log("[openOrder] formMode set to:", modeToSet);
      setDetailLoading(true);
      setSelectedOrder(null);

      try {
        const detail = await fetchOrderDetail(order_id);
        console.log("[openOrder] detail from API:", detail);
        console.log("[openOrder] detail.lines:", detail?.lines);
        console.log("[openOrder] detail.lines count:", detail?.lines?.length);
        const hasDetail = detail && Object.keys(detail).length > 0;
        if (!hasDetail) {
          throw new Error("Order not found");
        }
        const merged = { ...row, ...detail };
        console.log("[openOrder] merged:", merged);
        console.log("[openOrder] merged.lines:", merged?.lines);
        console.log("[openOrder] merged.lines count:", merged?.lines?.length);
        setSelectedOrder(merged);
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Failed to load order";
        dispatch(showToast({ message, type: "error" }));
        setFormMode(null);
        setSelectedOrder(null);
      } finally {
        setDetailLoading(false);
      }
    },
    [dispatch],
  );

  const handleView = useCallback(
    (row: any) => {
      console.log("[OrderList] handleView called");
      openOrder(row, "view");
    },
    [openOrder],
  );

  const handleEdit = useCallback(
    (row: any) => {
      openOrder(row, "edit");
    },
    [openOrder],
  );

  const handleAdd = () => {
    setSelectedOrder(null);
    setFormMode("add");
    setDetailLoading(false);
  };

  const handleFormSaved = () => {
    getOrderData();
    setFormMode(null);
    setSelectedOrder(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedOrder(null);
  };

  const handle_delete = useCallback(
    async (row: any) => {
      if (window.confirm(`Delete order ${row.ida}?`)) {
        try {
          await deleteAction(row.id);
          dispatch(
            showToast({
              message: "Order deleted successfully",
              type: "success",
            }),
          );
          getOrderData(); // Refresh data
        } catch (error) {
          dispatch(
            showToast({
              message: "Failed to delete order",
              type: "error",
            }),
          );
        }
      }
    },
    [dispatch, getOrderData],
  );

  const userColumns: TableColumn<OrderRow>[] = useMemo(
    () => [
      {
        name: "ID",
        selector: (row: OrderRow) => row.id,
        sortable: true,
        width: "80px",
        cell: (row: OrderRow) => (
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
        name: "Order No",
        selector: (row: OrderRow) => row.ida || "--",
        sortable: true,
        width: "10%",
      },
      {
        name: "Status",
        selector: (row: OrderRow) => row.status || "--",
        sortable: true,
        width: "12%",
        cell: (row: OrderRow) => (
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
        selector: (row: OrderRow) =>
          row.refs?.links?.customer?.attention ||
          row.refs?.links?.customer?.email ||
          "--",
        sortable: true,
        width: "20%",
      },
      {
        name: "Vendor",
        selector: (row: OrderRow) => row.vendor?.display_name || "--",
        sortable: true,
        width: "20%",
      },
      {
        name: "Total Amount",
        selector: (row: OrderRow) => row.total || row.total_amount || 0,
        sortable: true,
        width: "10%",
        cell: (row: OrderRow) => (
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
        selector: (row: OrderRow) => row.margin_percentage || 0,
        sortable: true,
        width: "8%",
        cell: (row: OrderRow) => (
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
        selector: (row: OrderRow) =>
          row.line_count || (row.lines ? row.lines.length : 0),
        sortable: true,
        width: "6%",
        cell: (row: OrderRow) => (
          <span className="text-center bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
            {row.line_count || (row.lines ? row.lines.length : 0)}
          </span>
        ),
      },
      {
        name: "Created",
        selector: (row: OrderRow) =>
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
        cell: (row: OrderRow) => (
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
                handle_delete(row);
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
    [handleView, handleEdit, handle_delete],
  );

  // Filters configuration
  const filters: ColumnFilter[] = useMemo(
    () => [
      {
        key: "status",
        name: "status",
        field: "status",
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
        name: "customer_name",
        field: "customer_name",
        label: "Customer",
        type: "text",
      },
      {
        key: "vendor_name",
        name: "vendor_name",
        field: "vendor_name",
        label: "Vendor",
        type: "text",
      },
    ],
    [],
  );

  // Calculate summary statistics
  const totalOrders = data.length;
  const totalValue = data.reduce(
    (sum, order) => sum + (order.total || order.total_amount || 0),
    0,
  );
  const totalMargin = data.reduce(
    (sum, order) => sum + (order.margin_amount || 0),
    0,
  );
  const avgMargin = totalOrders > 0 ? (totalMargin / totalValue) * 100 : 0;
  const statusCounts = data.reduce((acc, order) => {
    acc[order.status || "unknown"] = (acc[order.status || "unknown"] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <>
      <div className="mb-4">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold text-slate-700">
            Sales Order List
          </div>
          <div className="text-sm text-slate-500">
            Total Orders: {totalOrders} • Total Value: ${totalValue.toFixed(2)}{" "}
            • Avg Margin: {avgMargin.toFixed(1)}% • Delivered:{" "}
            {statusCounts.delivered || 0}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={userColumns}
              title="Orders"
              loading={loading}
              filters={filters}
              enableExport={true}
              enableSelection={true}
              exportFileName="orders"
              searchPlaceholder="Search orders, customers, vendors..."
              noDataMessage="No orders found"
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
              customActions={
                <button
                  onClick={handleAdd}
                  className="flex items-center gap-2 px-3 py-2 text-xs font-medium disabled:opacity-50 text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <FaPlus className="w-4 h-4" />
                  Add Order
                </button>
              }
              onRowClicked={handleView}
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            {formMode !== "add" && (detailLoading || !selectedOrder) ? (
              <ComponentCard>
                <div className="p-8 text-center text-sm text-gray-500 dark:text-gray-400">
                  Loading order...
                </div>
              </ComponentCard>
            ) : (
              <OrderDetail
                key={`${selectedOrder?.id ?? "new"}-${formMode}`}
                inline
                modeProp={formMode}
                dataProp={
                  formMode === "add"
                    ? null
                    : selectedOrder
                    ? {
                        ...selectedOrder,
                        id:
                          typeof selectedOrder.id === "string"
                            ? Number(selectedOrder.id)
                            : selectedOrder.id,
                        customer_id:
                          selectedOrder.customer_id ??
                          selectedOrder.id_customer ??
                          "",
                        vendor_id:
                          selectedOrder.vendor_id ??
                          selectedOrder.id_vendor ??
                          "",
                        manufacturer_id: selectedOrder.manufacturer_id ?? "",
                        status: (selectedOrder.status ?? "draft") as any, // Cast to 'any' to satisfy TransactionStatus
                      }
                    : null
                }
                onSaved={handleFormSaved}
              />
            )}
          </div>
        )}
      </div>
    </>
  );
}
