import PageBreadcrumb from "../../../../../components/common/PageBreadcrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, { ColumnFilter } from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchInvoices, fetchInvoiceDetail } from "../services/invoiceApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import InvoiceDetail from "./InvoiceDetail";
import { sanitizeRecord, formatDateTimeValue } from "../../common/valueNormalization";

const numericInvoiceKeys = [
  "total_amount",
  "margin_percentage",
  "margin_amount",
  "paid_amount",
  "line_count",
  "balance_due",
];

export default function InvoiceList() {
  const [data, setData] = useState<any[]>([]);
  const [selectedInvoices, setSelectedInvoices] = useState<any[]>([]);
  const [selectedInvoice, setSelectedInvoice] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);

  const dispatch = useDispatch();

  const getInvoiceData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchInvoices();
      if (res.status === 200) {
        const sanitizedItems = Array.isArray(res.data.items)
          ? res.data.items.map((item: any) => sanitizeRecord(item, numericInvoiceKeys))
          : [];
        setData(sanitizedItems);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch invoices", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch invoices", error);
      dispatch(showToast({ message: "Failed to fetch invoices", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getInvoiceData();
  }, [getInvoiceData]);

  const openInvoice = useCallback(
    async (row: any, modeToSet: "view" | "edit") => {
      const invoiceId = row?.id;
      if (!invoiceId) {
        dispatch(showToast({ message: "Invoice id missing", type: "error" }));
        return;
      }

      setFormMode(modeToSet);
      setDetailLoading(true);
      setSelectedInvoice(null);

      try {
        const detail = await fetchInvoiceDetail(invoiceId);
        const hasDetail = detail && Object.keys(detail).length > 0;
        if (!hasDetail) {
          throw new Error("Invoice not found");
        }
        const sanitizedRow = sanitizeRecord(row, numericInvoiceKeys);
        const sanitizedDetail = sanitizeRecord(detail, numericInvoiceKeys);
        setSelectedInvoice({ ...sanitizedRow, ...sanitizedDetail });
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Failed to load invoice";
        dispatch(showToast({ message, type: "error" }));
        setFormMode(null);
        setSelectedInvoice(null);
      } finally {
        setDetailLoading(false);
      }
    },
    [dispatch]
  );

  const handleView = useCallback(
    (row: any) => {
      openInvoice(row, "view");
    },
    [openInvoice]
  );

  const handleEdit = useCallback(
    (row: any) => {
      openInvoice(row, "edit");
    },
    [openInvoice]
  );

  const handleAdd = () => {
    setSelectedInvoice(null);
    setFormMode("add");
    setDetailLoading(false);
  };

  const handleFormSaved = () => {
    getInvoiceData();
    setFormMode(null);
    setSelectedInvoice(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedInvoice(null);
  };

  const handleDelete = async (row: any) => {
    if (window.confirm(`Delete invoice ${row.invoice_no}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(showToast({ message: "Invoice deleted successfully", type: "success" }));
        getInvoiceData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete invoice", type: "error" }));
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
      name: "Invoice No",
      selector: (row) => row.invoice_no || "--",
      sortable: true,
      width: "14%",
    },
    {
      name: "Status",
      selector: (row) => row.status || "--",
      sortable: true,
      width: "12%",
      cell: (row) => (
        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
          row.status === 'paid' ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
          row.status === 'sent' ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' :
          row.status === 'overdue' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' :
          row.status === 'draft' ? 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200' :
          'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
        }`}>
          {row.status || 'Unknown'}
        </span>
      ),
    },
    {
      name: "Customer",
      selector: (row) => row.customer_name || row.customer_id || "--",
      sortable: true,
      width: "12%",
    },
    {
      name: "Vendor",
      selector: (row) => row.vendor_name || row.vendor_id || "--",
      sortable: true,
      width: "12%",
    },
    {
      name: "Total Amount",
      selector: (row) => row.total_amount || 0,
      sortable: true,
      width: "10%",
      cell: (row) => (
        <span className="font-medium text-green-600 dark:text-green-400">
          ${Number(row.total_amount || 0).toFixed(2)}
        </span>
      ),
    },
    {
      name: "Margin",
      selector: (row) => row.margin_percentage || 0,
      sortable: true,
      width: "8%",
      cell: (row) => (
        <span className={`text-center px-2 py-1 rounded text-xs font-medium ${
          (row.margin_percentage || 0) >= 20 ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
          (row.margin_percentage || 0) >= 10 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
          'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
        }`}>
          {row.margin_percentage ? Number(row.margin_percentage).toFixed(1) : '0.0'}%
        </span>
      ),
    },
    {
      name: "Lines",
      selector: (row) => row.line_count || (row.line_items ? row.line_items.length : 0),
      sortable: true,
      width: "6%",
      cell: (row) => (
        <span className="text-center bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
          {row.line_count || (row.line_items ? row.line_items.length : 0)}
        </span>
      ),
    },
    {
      name: "Paid Amount",
      selector: (row) => row.paid_amount || 0,
      sortable: true,
      width: "10%",
      cell: (row) => (
        <span className="font-medium text-blue-600 dark:text-blue-400">
          ${Number(row.paid_amount || 0).toFixed(2)}
        </span>
      ),
    },
    {
      name: "Balance",
      selector: (row) => (row.total_amount || 0) - (row.paid_amount || 0),
      sortable: true,
      width: "10%",
      cell: (row) => {
        const balance = (row.total_amount || 0) - (row.paid_amount || 0);
        return (
          <span className={`font-medium ${balance > 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'}`}>
            ${balance.toFixed(2)}
          </span>
        );
      },
    },
    {
      name: "Created",
      selector: (row) => row.dt_created || "--",
      sortable: true,
      width: "10%",
      cell: (row) => formatDateTimeValue(row.dt_created) || "--",
    },
    {
      name: "Actions",
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
      key: "status",
      label: "Status",
      type: "select",
      options: [
        { value: "draft", label: "Draft" },
        { value: "sent", label: "Sent" },
        { value: "paid", label: "Paid" },
        { value: "overdue", label: "Overdue" },
        { value: "cancelled", label: "Cancelled" },
      ],
    },
    {
      key: "customer_name",
      label: "Customer",
      type: "text",
    },
  ], []);

  // Calculate summary statistics
  const totalInvoices = data.length;
  const totalValue = data.reduce((sum, invoice) => sum + (invoice.total_amount || 0), 0);
  const totalMargin = data.reduce((sum, invoice) => sum + (invoice.margin_amount || 0), 0);
  const avgMargin = totalInvoices > 0 ? (totalMargin / totalValue) * 100 : 0;
  const statusCounts = data.reduce((acc, invoice) => {
    acc[invoice.status || 'unknown'] = (acc[invoice.status || 'unknown'] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <>
      <PageBreadcrumb pageTitle="Invoice List" />

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <ComponentCard>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">{totalInvoices}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Total Invoices</div>
          </div>
        </ComponentCard>
        <ComponentCard>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">${totalValue.toFixed(2)}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Total Value</div>
          </div>
        </ComponentCard>
        <ComponentCard>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">{avgMargin.toFixed(1)}%</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Avg Margin</div>
          </div>
        </ComponentCard>
        <ComponentCard>
          <div className="text-center">
            <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">{statusCounts.paid || 0}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Paid</div>
          </div>
        </ComponentCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <AdvancedDataTable
              data={data}
              columns={userColumns}
              title="Invoices"
              loading={loading}
              filters={filters}
              enableExport={true}
              enableSelection={true}
              onSelectionChange={setSelectedInvoices}
              exportFileName="invoices"
              searchPlaceholder="Search invoices, customers..."
              noDataMessage="No invoices found"
              customActions={
                <button
                  onClick={handleAdd}
                  className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <FaPlus className="w-4 h-4" />
                  Add Invoice
                </button>
              }
              onRowClicked={handleEdit}
            />
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            {formMode !== "add" && (detailLoading || !selectedInvoice) ? (
              <ComponentCard>
                <div className="p-8 text-center text-sm text-gray-500 dark:text-gray-400">
                  Loading invoice...
                </div>
              </ComponentCard>
            ) : (
              <InvoiceDetail
                inline
                modeProp={formMode}
                dataProp={formMode === "add" ? null : selectedInvoice}
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