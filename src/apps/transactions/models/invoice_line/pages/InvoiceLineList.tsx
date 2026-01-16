import PageBreadcrumb from "../../../../../components/common/PageBreadCrumb";
import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback } from "react";
import { deleteInvoiceLine, fetchInvoiceLines } from "../services/invoiceLineApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import InvoiceLineDetail from "./InvoiceLineDetail";
import type { InvoiceLine } from "../types/invoiceLineType";

export default function InvoiceLineList() {
  const [data, setData] = useState<InvoiceLine[]>([]);
  const [selectedInvoiceLine, setSelectedInvoiceLine] = useState<InvoiceLine | null>(null);
  const [formMode, setFormMode] = useState<"add" | "edit" | "view" | null>(null);
  const [loading, setLoading] = useState(false);

  const dispatch = useDispatch();

  const getInvoiceLineData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchInvoiceLines();
      if (res.status === 200) {
        setData(res.data.items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch invoice lines", type: "error" })
        );
      }
    } catch (error) {
      console.error("Failed to fetch invoice lines", error);
      dispatch(showToast({ message: "Failed to fetch invoice lines", type: "error" }));
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    getInvoiceLineData();
  }, [getInvoiceLineData]);

  const handleView = (row: InvoiceLine) => {
    setSelectedInvoiceLine(row);
    setFormMode("view");
  };

  const handleEdit = (row: InvoiceLine) => {
    setSelectedInvoiceLine(row);
    setFormMode("edit");
  };

  const handleAdd = () => {
    setSelectedInvoiceLine(null);
    setFormMode("add");
  };

  const handleFormSaved = () => {
    getInvoiceLineData();
    setFormMode(null);
    setSelectedInvoiceLine(null);
  };

  const handleFormCancel = () => {
    setFormMode(null);
    setSelectedInvoiceLine(null);
  };

  const handleDelete = async (row: InvoiceLine) => {
    if (window.confirm(`Delete invoice line ${row.id}?`)) {
      try {
        await deleteInvoiceLine(row.id!);
        dispatch(showToast({ message: "Invoice line deleted successfully", type: "success" }));
        getInvoiceLineData(); // Refresh data
      } catch (error) {
        dispatch(showToast({ message: "Failed to delete invoice line", type: "error" }));
      }
    }
  };

  const userColumns: TableColumn<InvoiceLine>[] = [
    { name: "ID", selector: (row: InvoiceLine) => row.id || 0, sortable: true, width: "80px" },
    {
      name: "Invoice ID",
      selector: (row: InvoiceLine) => row.parent || "--",
      sortable: true,
      width: "120px",
    },
    {
      name: "Item",
      selector: (row: InvoiceLine) => row.item_name || "--",
      sortable: true,
      width: "150px",
    },
    {
      name: "Description",
      selector: (row: InvoiceLine) => row.description || "--",
      sortable: true,
      grow: 2,
    },
    {
      name: "Quantity",
      selector: (row: InvoiceLine) => row.quantity || 0,
      sortable: true,
      width: "100px",
      right: true,
    },
    {
      name: "Unit Price",
      selector: (row: InvoiceLine) => row.price?.sell || 0,
      sortable: true,
      width: "120px",
      right: true,
      format: (row: InvoiceLine) => `$${(row.price?.sell || 0).toFixed(2)}`,
    },
    {
      name: "Extended",
      selector: (row: InvoiceLine) => row.extended_price || 0,
      sortable: true,
      width: "120px",
      right: true,
      format: (row: InvoiceLine) => `$${(row.extended_price || 0).toFixed(2)}`,
    },
    {
      name: "Action",
      cell: (row: InvoiceLine) => (
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
      <PageBreadcrumb pageTitle="Invoice Line List" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={formMode ? "lg:col-span-1" : "lg:col-span-3"}>
          <ComponentCard>
            <div className="flex justify-end mb-4">
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2 text-white bg-blue-500 rounded-md hover:bg-blue-600 disabled:opacity-50"
              >
                <FaPlus />
                Add Invoice Line
              </button>
            </div>
            <div className="overflow-x-auto bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-400 rounded-md">
              <AdvancedDataTable
                columns={userColumns.map((col) => ({
                  ...col,
                  name: typeof col.name === "string" ? col.name.toUpperCase() : col.name,
                }))}
                data={data}
                storageKey="invoice_line_list"
                onRowActivate={handleEdit}
                loading={loading}
              />
            </div>
          </ComponentCard>
        </div>
        {formMode && (
          <div className="lg:col-span-2">
            <InvoiceLineDetail
              inline
              modeProp={formMode}
              dataProp={selectedInvoiceLine}
              onSaved={handleFormSaved}
              onCancelInline={handleFormCancel}
            />
          </div>
        )}
      </div>
    </>
  );
}
