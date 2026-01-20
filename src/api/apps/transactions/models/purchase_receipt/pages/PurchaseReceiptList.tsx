import PageBreadcrumb from "../../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../../components/common/ComponentCard";
import AdvancedDataTable from "../../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { deleteAction } from "../../../../../userProfile";
import { fetchPurchaseReceipts } from "../services/purchaseReceiptApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import PurchaseReceiptDetail from "./PurchaseReceiptDetail";

export default function PurchaseReceiptList() {
  const dispatch = useDispatch();
  const [data, setData] = useState<any[]>([]);
  const [selectedPurchaseReceipt, setSelectedPurchaseReceipt] = useState<any | null>(null);
  const [selectedPurchaseReceipts, setSelectedPurchaseReceipts] = useState<any[]>([]);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const getPurchaseReceiptData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchPurchaseReceipts();
      if (res.status === 200) {
        setData(res.data.items || []);
      } else {
        dispatch(showToast({ message: "Failed to fetch purchase receipts", type: "error" }));
      }
    } catch (error) {
      console.error("Failed to fetch purchase receipts", error);
      dispatch(showToast({ message: "Failed to fetch purchase receipts", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getPurchaseReceiptData();
  }, [getPurchaseReceiptData]);

  const handleView = useCallback((row: any) => {
    setSelectedPurchaseReceipt(row);
    setFormMode("view");
  }, []);

  const handleEdit = useCallback((row: any) => {
    setSelectedPurchaseReceipt(row);
    setFormMode("edit");
  }, []);

  const handleAdd = () => {
    setSelectedPurchaseReceipt(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getPurchaseReceiptData();
    setFormMode(null);
    setSelectedPurchaseReceipt(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedPurchaseReceipt(null);
  };

  const handleDelete = useCallback(async (row: any) => {
    if (!window.confirm(`Delete purchase receipt ${row.id}?`)) return;
    
    try {
      await deleteAction(row.id);
      dispatch(showToast({ message: "Purchase receipt deleted successfully", type: "success" }));
      getPurchaseReceiptData();
      if (selectedPurchaseReceipt && selectedPurchaseReceipt.id === row.id) {
        setFormMode(null);
        setSelectedPurchaseReceipt(null);
      }
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete purchase receipt", type: "error" }));
    }
  }, [dispatch, getPurchaseReceiptData, selectedPurchaseReceipt]);

  const handleBulkDelete = useCallback(async () => {
    if (!selectedPurchaseReceipts.length) return;
    if (!window.confirm(`Delete ${selectedPurchaseReceipts.length} purchase receipt(s)?`)) return;

    try {
      await Promise.all(selectedPurchaseReceipts.map((r) => deleteAction(r.id)));
      dispatch(showToast({ message: `${selectedPurchaseReceipts.length} purchase receipt(s) deleted`, type: "success" }));
      getPurchaseReceiptData();
      setSelectedPurchaseReceipts([]);
    } catch (error) {
      dispatch(showToast({ message: "Failed to delete some purchase receipts", type: "error" }));
    }
  }, [selectedPurchaseReceipts, dispatch, getPurchaseReceiptData]);

  const columns: TableColumn<any>[] = useMemo(() => [
    { id: "id", name: "ID", selector: (row) => row.id, sortable: true, width: "80px" },
    { id: "purchase_order_id", name: "Purchase Order ID", selector: (row) => row.purchase_order_id || "--", sortable: true, width: "15%" },
    { id: "receipt_date", name: "Receipt Date", selector: (row) => row.receipt_date || "--", sortable: true, width: "18%" },
    { id: "received_by", name: "Received By", selector: (row) => row.received_by || "--", sortable: true, width: "18%" },
    { id: "notes", name: "Notes", selector: (row) => row.notes || "--", sortable: true, width: "20%" },
    {
      id: "actions",
      name: "Actions",
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
      width: "100px",
    },
  ], [handleDelete, handleEdit, handleView]);

  return (
    <>
      <PageBreadcrumb pageTitle="Purchase Receipt List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={columns}
              title="Purchase Receipts"
              loading={loading}
              storageKey="purchase-receipt-list"
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedPurchaseReceipts}
              exportFileName="purchase_receipts_export"
              onRowActivate={handleEdit}
              searchPlaceholder="Search purchase receipts..."
              noDataMessage="No purchase receipts found"
              customActions={
                <div className="flex gap-2">
                  {selectedPurchaseReceipts.length > 0 && (
                    <button
                      onClick={handleBulkDelete}
                      className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                    >
                      <FaTrash className="w-4 h-4" />
                      Delete ({selectedPurchaseReceipts.length})
                    </button>
                  )}
                  <button
                    onClick={handleAdd}
                    className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <FaPlus className="w-4 h-4" />
                    Add Purchase Receipt
                  </button>
                </div>
              }
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <PurchaseReceiptDetail
              inline
              modeProp={formMode}
              dataProp={selectedPurchaseReceipt}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
