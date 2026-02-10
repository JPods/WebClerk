import PageBreadcrumb from "../../../../../components/common/PageBreadcrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter } from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchPurchaseOrders, fetchPurchaseOrderDetail } from "../services/purchaseOrderApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import PurchaseDetail from "./PurchaseDetail";
import { sanitizeRecord, formatDateTimeValue } from "../../common/valueNormalization";

const numericPurchaseOrderKeys = ["dt_created", "id_vendor"]; 

export default function PurchaseList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedPurchaseOrders, setSelectedPurchaseOrders] = useState<any[]>([]);
  const [selectedPurchaseOrder, setSelectedPurchaseOrder] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);

  const dispatch = useDispatch();

  const getPurchaseOrderData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchPurchaseOrders();
      if (res.status === 200) {
        const sanitizedItems = Array.isArray(res.data.items)
          ? res.data.items.map((item: any) => sanitizeRecord(item, numericPurchaseOrderKeys))
          : [];
        setData(sanitizedItems);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch purchase orders", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch purchase orders", error);
      dispatch(showToast({ message: "Failed to fetch purchase orders", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getPurchaseOrderData();
  }, [getPurchaseOrderData]);

  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const searchQuery = terms.join(",");
      const res = await fetchPurchaseOrders({ search: searchQuery });
      if (res.status === 200) {
        const sanitizedItems = Array.isArray(res.data.items)
          ? res.data.items.map((item: any) => sanitizeRecord(item, numericPurchaseOrderKeys))
          : [];
        setData(sanitizedItems);
      }
    } catch (error) {
      console.error("Database search failed:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  const openPurchaseOrder = useCallback(
    async (row: any, modeToSet: "view" | "edit") => {
      const purchaseOrderId = row?.id;
      if (!purchaseOrderId) {
        dispatch(
          showToast({ message: "Purchase order id missing", type: "error" })
        );
        return;
      }

      setFormMode(modeToSet);
      setDetailLoading(true);
      setSelectedPurchaseOrder(null);

      try {
        const response = await fetchPurchaseOrderDetail(purchaseOrderId);
        const detail = response ?? {};
        const hasDetail = detail && Object.keys(detail).length > 0;
        if (!hasDetail) {
          throw new Error("Purchase order not found");
        }
        const sanitizedRow = sanitizeRecord(row, numericPurchaseOrderKeys);
        const sanitizedDetail = sanitizeRecord(detail, numericPurchaseOrderKeys);
        setSelectedPurchaseOrder({ ...sanitizedRow, ...sanitizedDetail });
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Failed to load purchase order";
        dispatch(showToast({ message, type: "error" }));
        setFormMode(null);
        setSelectedPurchaseOrder(null);
      } finally {
        setDetailLoading(false);
      }
    },
    [dispatch]
  );

  const handleView = useCallback(
    (row: any) => {
      openPurchaseOrder(row, "view");
    },
    [openPurchaseOrder]
  );

  const handleEdit = useCallback(
    (row: any) => {
      openPurchaseOrder(row, "edit");
    },
    [openPurchaseOrder]
  );

  const handleAdd = () => {
    setSelectedPurchaseOrder(null);
    setFormMode("add");
    setDetailLoading(false);
  };

  const handleFormSaved = () => {
    getPurchaseOrderData();
    setFormMode(null);
    setSelectedPurchaseOrder(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedPurchaseOrder(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete purchase order ${row.purchase_order_no}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(showToast({ message: "Purchase order deleted successfully", type: "success" }));
        getPurchaseOrderData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete purchase order", type: "error" }));
      }
    }
  };

  const userColumns: TableColumn<any>[] = useMemo(() => [
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
      name: "Purchase Order No",
      selector: (row) => row.purchase_order_no || "--",
      sortable: true,
      width: "30%",
    },
    {
      name: "Created",
      selector: (row) => row.dt_created || 0,
      sortable: true,
      width: "25%",
      cell: (row) => {
        const formatted = formatDateTimeValue(row.dt_created);
        return formatted || "--";
      },
    },
    {
      name: "Action",
      width: "140px",
      cell: (row) => (
        <div className="flex gap-2">
          <button 
            onClick={(e) => { e.stopPropagation(); handleView(row); }} 
            title="View"
            className="p-2 text-blue-600 hover:bg-blue-50 rounded dark:hover:bg-blue-900/20 transition-colors"
          >
            <FaEye className="w-4 h-4" />
          </button>
          <button 
            onClick={(e) => { e.stopPropagation(); handleEdit(row); }} 
            title="Edit"
            className="p-2 text-green-600 hover:bg-green-50 rounded dark:hover:bg-green-900/20 transition-colors"
          >
            <FaEdit className="w-4 h-4" />
          </button>
          <button 
            onClick={(e) => { e.stopPropagation(); handleDelete(row); }} 
            title="Delete"
            className="p-2 text-red-600 hover:bg-red-50 rounded dark:hover:bg-red-900/20 transition-colors"
          >
            <FaTrash className="w-4 h-4" />
          </button>
        </div>
      ),
    },
  ], [handleView, handleEdit, handleDelete]);

  // Filters configuration
  const filters: ColumnFilter[] = useMemo(() => [
    {
      key: "purchase_order_no",
      label: "PO Number",
      type: "text",
    },
  ], []);

  return (
    <>
      <PageBreadcrumb pageTitle="Purchase Order List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={userColumns}
              title="Purchase Orders"
              loading={loading}
              filters={filters}
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedPurchaseOrders}
              exportFileName="purchase_orders"
              searchPlaceholder="Search purchase orders..."
              noDataMessage="No purchase orders found"
              enableDatabaseSearch={true}
              searchDatabase={searchDatabase}
              onSearchModeChange={setSearchDatabase}
              onDatabaseSearch={handleDatabaseSearch}
              customActions={
                <button
                  onClick={handleAdd}
                  className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <FaPlus className="w-4 h-4" />
                  Add Purchase Order
                </button>
              }
              onRowClicked={handleEdit}
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            {formMode !== "add" && (detailLoading || !selectedPurchaseOrder) ? (
              <ComponentCard>
                <div className="p-8 text-center text-sm text-gray-500 dark:text-gray-400">
                  Loading purchase order...
                </div>
              </ComponentCard>
            ) : (
              <PurchaseDetail
                inline
                modeProp={formMode}
                dataProp={formMode === "add" ? null : selectedPurchaseOrder}
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