import PageBreadcrumb from "../../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../../components/common/ComponentCard";
import AdvancedDataTable from "../../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { deleteAction } from "../../../../../userProfile";
import { fetchPurchaseOrderLines } from "../services/purchaseOrderLineApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import PurchaseOrderLineDetail from "./PurchaseOrderLineDetail";

export default function PurchaseOrderLineList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedPurchaseOrderLine, setSelectedPurchaseOrderLine] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const getPurchaseOrderLineData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchPurchaseOrderLines();
      if (res.status === 200) {
        setData(res.data.items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch purchase order lines", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch purchase order lines", error);
      dispatch(showToast({ message: "Failed to fetch purchase order lines", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getPurchaseOrderLineData();
  }, [getPurchaseOrderLineData]);

  const handleView = (row: any) => {
    setSelectedPurchaseOrderLine(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedPurchaseOrderLine(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedPurchaseOrderLine(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getPurchaseOrderLineData();
    setFormMode(null);
    setSelectedPurchaseOrderLine(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedPurchaseOrderLine(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete purchase order line ${row.id}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(showToast({ message: "Purchase order line deleted successfully", type: "success" }));
        getPurchaseOrderLineData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete purchase order line", type: "error" }));
      }
    }
  };

  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "5%" },
    {
      name: "Purchase Order ID",
      selector: (row) => row.purchase_order_id || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Item ID",
      selector: (row) => row.item_id || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Quantity",
      selector: (row) => row.quantity || "--",
      sortable: true,
      width: "10%",
    },
    {
      name: "Unit Price",
      selector: (row) => row.unit_price || "--",
      sortable: true,
      width: "15%",
    },
    {
      name: "Line Total",
      selector: (row) => row.line_total || "--",
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
      <PageBreadcrumb pageTitle="Purchase Order Line List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Purchase Order Line
              </button>
            </div>
            <div className="overflow-x-auto bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-400 rounded-md">
              <AdvancedDataTable
                columns={userColumns.map((col) => ({
                  ...col,
                  name: typeof col.name === "string" ? col.name.toUpperCase() : col.name,
                }))}
                data={data}
                storageKey="purchase_order_line_list"
                onRowActivate={handleEdit}
                loading={loading}
              />
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <PurchaseOrderLineDetail
              inline
              modeProp={formMode}
              dataProp={selectedPurchaseOrderLine}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}