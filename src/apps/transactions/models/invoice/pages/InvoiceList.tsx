import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import DataTable, { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchInvoices } from "../services/invoiceApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { useTheme } from "../../../../../context/ThemeContext";
import InvoiceDetail from "./InvoiceDetail";

export default function InvoiceList() {
  const { theme } = useTheme();
  const [data, setData] = useState<any[]>([]);
  const [selectedInvoice, setSelectedInvoice] = useState<any | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const getInvoiceData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchInvoices();
      if (res.status === 200) {
        setData(res.data.items);
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

  const handleView = (row: any) => {
    setSelectedInvoice(row);
    setFormMode("view");
  };

  const handleEdit = (row: any) => {
    setSelectedInvoice(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedInvoice(null);
    setFormMode("add");
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

  const userColumns: TableColumn<any>[] = [
    { name: "ID", selector: (row) => row.id, sortable: true, width: "6%" },
    {
      name: "Invoice No",
      selector: (row) => row.invoice_no || "--",
      sortable: true,
      width: "12%",
    },
    {
      name: "Status",
      selector: (row) => row.status || "--",
      sortable: true,
      width: "10%",
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
      name: "Due Date",
      selector: (row) => row.due_date ? new Date(row.due_date).toLocaleDateString() : "--",
      sortable: true,
      width: "10%",
      cell: (row) => {
        const dueDate = row.due_date ? new Date(row.due_date) : null;
        const isOverdue = dueDate && dueDate < new Date() && row.status !== 'paid';
        return (
          <span className={isOverdue ? 'text-red-600 dark:text-red-400 font-medium' : ''}>
            {dueDate ? dueDate.toLocaleDateString() : "--"}
          </span>
        );
      },
    },
    {
      name: "Actions",
      cell: (row) => (
        <div className="flex gap-1">
          <button onClick={() => handleView(row)} title="View" className="p-1 hover:bg-gray-100 dark:hover:bg-gray-600 rounded transition-colors">
            <FaEye className="text-blue-600 dark:text-blue-400 text-sm" />
          </button>
          <button onClick={() => handleEdit(row)} title="Edit" className="p-1 hover:bg-gray-100 dark:hover:bg-gray-600 rounded transition-colors">
            <FaEdit className="text-green-600 dark:text-green-400 text-sm" />
          </button>
          <button onClick={() => handleDelete(row)} title="Delete" className="p-1 hover:bg-gray-100 dark:hover:bg-gray-600 rounded transition-colors">
            <FaTrash className="text-red-600 dark:text-red-400 text-sm" />
          </button>
        </div>
      ),
      ignoreRowClick: true,
      allowOverflow: true,
      button: true,
      width: "10%",
    },
  ];

  // Calculate summary statistics
  const totalInvoices = data.length;
  const totalValue = data.reduce((sum, invoice) => sum + (invoice.total_amount || 0), 0);
  const totalPaid = data.reduce((sum, invoice) => sum + (invoice.paid_amount || 0), 0);
  const overdueCount = data.filter(invoice => invoice.status === 'overdue').length;

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
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">${totalPaid.toFixed(2)}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Total Paid</div>
          </div>
        </ComponentCard>
        <ComponentCard>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">{overdueCount}</div>
            <div className="text-sm text-gray-600 dark:text-gray-400">Overdue</div>
          </div>
        </ComponentCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Invoice
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
                progressComponent={<div className="p-8 text-center">Loading invoices...</div>}
                onRowClicked={(row) => handleView(row)}
              />
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <InvoiceDetail
              inline
              modeProp={formMode}
              dataProp={selectedInvoice}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}