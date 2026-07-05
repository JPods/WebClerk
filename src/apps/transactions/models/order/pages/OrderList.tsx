/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import DataGrid from "@/components/common/DataGrid";
import type { ColumnFilter } from "@/components/common/ButtonToolbar";
import ComponentCard from "@/components/common/ComponentCard";
import ButtonToolbar from "@/components/common/ButtonToolbar";
import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { deleteAction } from "@/api/userProfile";
import { fetchOrders, fetchOrderDetail } from "../services/orderApi";
import {
  buildSearchPresetParams,
  type SearchPresetInputValue,
  type SearchPresetRecord,
} from "@/api/wcapi";
import { FaEye, FaEdit, FaTrash } from "react-icons/fa";
import { showToast } from "@/store/slices/toastSlice";
import { useDispatch } from "react-redux";
import OrderDetail from "./OrderDetail";
import type { QuickFilterItem } from "@/components/common/PrintReportDropdown";
import { useColumnContextMenu } from "@/hooks/useColumnContextMenu";

// Quick-filter presets
type QuickFilter = "all" | "open" | "last30" | "last60";

const QUICK_FILTER_LABELS: Record<QuickFilter, string> = {
  all: "All",
  open: "Open Orders",
  last30: "Last 30 Days",
  last60: "Last 60 Days",
};

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
  const [selectedOrders, setSelectedOrders] = useState<OrderRow[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [quickFilter, setQuickFilter] = useState<QuickFilter>("all");
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>([]);

  const tableRef = useRef<any>(null);
  const columnBtnRef = useRef<HTMLButtonElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  const dispatch = useDispatch();

  const getOrderData = useCallback(
    async (filter?: QuickFilter) => {
      const activeFilter = filter ?? quickFilter;
      try {
        setLoading(true);

        // Build params based on quick filter
        const params: Record<string, any> = {};
        if (activeFilter === "open") {
          params.status = "draft,confirmed,shipped";
        } else if (activeFilter === "last30" || activeFilter === "last60") {
          const days = activeFilter === "last30" ? 30 : 60;
          const since = new Date();
          since.setDate(since.getDate() - days);
          params.dt_created__gte = since.toISOString().split("T")[0];
        }

        const res = await fetchOrders(params);
        if (res.status === 200) {
          setData(res.data.items);
        } else {
          dispatch(
            showToast({ message: "Failed to fetch orders", type: "error" }),
          );
        }
      } catch (error) {
        console.error("Failed to fetch orders", error);
        dispatch(
          showToast({ message: "Failed to fetch orders", type: "error" }),
        );
      } finally {
        setLoading(false);
      }
    },
    [dispatch, quickFilter],
  );

  useEffect(() => {
    getOrderData();
  }, [getOrderData]);

  const handleQuickFilter = useCallback(
    (filter: QuickFilter) => {
      setQuickFilter(filter);
      getOrderData(filter);
    },
    [getOrderData],
  );

  const handleApplySearchPreset = useCallback(
    async (
      preset: SearchPresetRecord,
      values: Record<string, SearchPresetInputValue> = {},
    ) => {
      try {
        setLoading(true);
        setQuickFilter("all");
        setSearchDatabase(true);
        setSearchTerm("");
        const res = await fetchOrders(
          buildSearchPresetParams(preset, {
            values,
            params: { limit: 500 },
          }),
        );
        if (res.status === 200) {
          setData(res.data.items);
        } else {
          dispatch(
            showToast({ message: "Failed to run saved search", type: "error" }),
          );
        }
      } catch (error) {
        console.error("Saved search failed:", error);
        dispatch(
          showToast({ message: "Failed to run saved search", type: "error" }),
        );
      } finally {
        setLoading(false);
      }
    },
    [dispatch],
  );

  // Auto-refresh when another window saves/transfers a transaction.
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent)?.detail as any;
      const model = String(detail?.model || "");
      if (
        ["order", "invoice", "proposal", "purchase", "workorder"].includes(
          model,
        )
      ) {
        getOrderData();
      }
    };
    window.addEventListener("wcapi:modelChanged", handler as any);
    return () =>
      window.removeEventListener("wcapi:modelChanged", handler as any);
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

  const handleBulkDelete = useCallback(async () => {
    if (selectedOrders.length === 0) return;
    if (!window.confirm(`Delete ${selectedOrders.length} selected order(s)?`))
      return;

    try {
      for (const order of selectedOrders) {
        await deleteAction(order.id);
      }
      dispatch(
        showToast({
          message: `${selectedOrders.length} order(s) deleted successfully`,
          type: "success",
        }),
      );
      setSelectedOrders([]);
      getOrderData();
    } catch (error) {
      dispatch(
        showToast({
          message: "Failed to delete some orders",
          type: "error",
        }),
      );
    }
  }, [dispatch, getOrderData, selectedOrders]);

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

  const userColumns: any[] = useMemo(
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
        name: "display_name",
        selector: (row: OrderRow) =>
          row.refs?.links?.customer?.display_name || "-fix-",
        sortable: true,
        width: "20%",
      },
      {
        name: "attention",
        selector: (row: OrderRow) =>
          row.refs?.links?.customer?.attention || "-fix-",
        sortable: true,
        width: "20%",
      },
      {
        name: "email",
        selector: (row: OrderRow) =>
          row.refs?.links?.customer?.email || "-fix-",
        sortable: true,
        width: "20%",
      },
      {
        name: "phone",
        selector: (row: OrderRow) =>
          row.refs?.links?.customer?.phone || "-fix-",
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

  const quickFilters: QuickFilterItem[] = useMemo(
    () =>
      (Object.keys(QUICK_FILTER_LABELS) as QuickFilter[]).map((key) => ({
        key,
        label: QUICK_FILTER_LABELS[key],
        active: quickFilter === key,
      })),
    [quickFilter],
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


  const columnCtx = useColumnContextMenu("order-list", userColumns);
  return (
    <>
      <ButtonToolbar
        pageTitle="Sales Order List"
        title="Order"
        modelKey="order"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        handleBulkDelete={handleBulkDelete}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        selectedRows={selectedOrders}
        selectedCount={selectedOrders.length}
        totalCount={data.length}
        filteredCount={data.length}
        onRefresh={() => getOrderData()}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={userColumns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="order-list"
        filters={filters}
        filterValues={filterValues}
        onFilterValuesChange={setFilterValues}
        filtersOpen={filtersOpen}
        onFiltersOpenChange={setFiltersOpen}
        quickFilters={quickFilters}
        onQuickFilter={(key) => handleQuickFilter(key as QuickFilter)}
        summaryContent={
          <span className="text-xs text-slate-500">
            Value: ${totalValue.toFixed(2)} • Avg Margin: {avgMargin.toFixed(1)}
            % • Delivered: {statusCounts.delivered || 0}
          </span>
        }
        onApplySearchPreset={handleApplySearchPreset}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <DataGrid
              ref={tableRef}
              data={data}
              columns={userColumns}
              title="Orders"
              loading={loading}
              filters={filters}
              storageKey="order-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedOrders}
              onDeleteSelected={handleBulkDelete}
              exportFileName="orders"
              externalSearchTerm={searchTerm}
              onExternalSearchTermChange={setSearchTerm}
              searchPlaceholder="Search orders, customers, vendors..."
              noDataMessage="No orders found"
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
              onRowClicked={handleView}
              filtersOpen={filtersOpen}
              onFiltersOpenChange={setFiltersOpen}
              hideHeader={true}
              allFields={columnCtx.allFields}
              namedViews={columnCtx.namedViews}
              onDeleteColumn={columnCtx.onDeleteColumn}
              onAddColumn={columnCtx.onAddColumn}
              onSaveLayout={columnCtx.onSaveLayout}
              onSaveLayoutAs={columnCtx.onSaveLayoutAs}
              onLoadView={columnCtx.onLoadView}
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
                        status: (selectedOrder.status ?? "draft") as any,
                        dt_created:
                          typeof selectedOrder.dt_created === "number"
                            ? String(selectedOrder.dt_created)
                            : selectedOrder.dt_created,
                      }
                    : null
                }
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
