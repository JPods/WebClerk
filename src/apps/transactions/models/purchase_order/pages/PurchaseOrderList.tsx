import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import DataTable, { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchPurchaseOrders, fetchPurchaseOrderDetail } from "../services/purchaseOrderApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "../../../../../context/ThemeContext";
import PurchaseOrderDetail from "./PurchaseOrderDetail";

export default function PurchaseOrderList() {
  const { theme } = useTheme();
  const [data, setData] = useState<any[]>([]);
  const [selectedPurchaseOrder, setSelectedPurchaseOrder] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);

  const dispatch = useDispatch();

  const getPurchaseOrderData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchPurchaseOrders();
      if (res.status === 200) {
        setData(res.data.items);
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
        setSelectedPurchaseOrder({ ...row, ...detail });
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

  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "10%" },
    {
      name: "Purchase Order No",
      selector: (row) => row.purchase_order_no || "--",
      sortable: true,
      width: "30%",
    },
    {
      name: "Created",
      selector: (row) => new Date(row.dt_created * 1000).toLocaleDateString() || "--",
      sortable: true,
      width: "25%",
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
      <PageBreadcrumb pageTitle="Purchase Order List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Purchase Order
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
                progressComponent={<div className="p-8 text-center">Loading purchase orders...</div>}
                onRowClicked={handleView}
              />
            </div>
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
              <PurchaseOrderDetail
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