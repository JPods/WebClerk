import ComponentCard from "../../../../../components/common/ComponentCard";
import AdvancedDataTable, {
  ColumnFilter,
  type AdvancedDataTableHandle,
} from "../../../../../components/common/AdvancedDataTable";
import { TableColumn } from "react-data-table-component";
import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { deleteAction } from "../../../../../api/userProfile";
import { fetchInvoices } from "../services/invoiceApi";
import { FaEye, FaEdit, FaPlus, FaTrash } from "react-icons/fa";
import { showToast } from "../../../../../store/slices/toastSlice";
import { useDispatch } from "react-redux";
import { PageRoutes } from "@/routes/Routes";
import ButtonToolbar from "@/components/common/ButtonToolbar";

// Invoice row type for the data table
interface InvoiceRow {
  id: number;
  invoice_no?: string;
  status?: string;
  customer_name?: string;
  customer_id?: number;
  vendor_name?: string;
  vendor_id?: number;
  total?: number;
  total_amount?: number;
  margin_percentage?: number;
  margin_amount?: number;
  line_count?: number;
  lines?: unknown[];
  dt_created?: string | number;
}

export default function InvoiceList() {
  const [data, setData] = useState<InvoiceRow[]>([]);
  const [selectedInvoices, setSelectedInvoices] = useState<InvoiceRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>([]);
  const tableRef = useRef<AdvancedDataTableHandle<any>>(null);
  const columnBtnRef = useRef<HTMLButtonElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  const dispatch = useDispatch();
  const navigate = useNavigate();

  const getInvoiceData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetchInvoices();
      if (res.status === 200) {
        setData(res.data.items);
      } else {
        dispatch(
          showToast({ message: "Failed to fetch invoices", type: "error" }),
        );
      }
    } catch (error) {
      console.error("Failed to fetch invoices", error);
      dispatch(
        showToast({ message: "Failed to fetch invoices", type: "error" }),
      );
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  // Database search handler for comma-separated terms (AND logic)
  const handleDatabaseSearch = useCallback(async (terms: string[]) => {
    try {
      setLoading(true);
      const searchQuery = terms.join(",");
      const res = await fetchInvoices({ search: searchQuery });
      if (res.status === 200) {
        setData(res.data.items);
      }
    } catch (error) {
      console.error("Database search failed:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    getInvoiceData();
  }, [getInvoiceData]);

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
        getInvoiceData();
      }
    };
    window.addEventListener("wcapi:modelChanged", handler as any);
    return () =>
      window.removeEventListener("wcapi:modelChanged", handler as any);
  }, [getInvoiceData]);

  const handleView = useCallback(
    (row: InvoiceRow) => {
      const invoiceId = row?.id;
      if (!invoiceId) {
        dispatch(showToast({ message: "Invoice id missing", type: "error" }));
        return;
      }
      navigate(
        PageRoutes.transactionsInvoiceDetail.replace(":id?", String(invoiceId)),
        { state: { mode: "view" } },
      );
    },
    [dispatch, navigate],
  );

  const handleEdit = useCallback(
    (row: InvoiceRow) => {
      const invoiceId = row?.id;
      if (!invoiceId) {
        dispatch(showToast({ message: "Invoice id missing", type: "error" }));
        return;
      }
      navigate(
        PageRoutes.transactionsInvoiceDetail.replace(":id?", String(invoiceId)),
        { state: { mode: "edit" } },
      );
    },
    [dispatch, navigate],
  );

  const handleAdd = () => {
    navigate(PageRoutes.transactionsInvoiceDetail.replace(":id?", ""), {
      state: { mode: "add" },
    });
  };

  const handleDelete = async (row: InvoiceRow) => {
    if (window.confirm(`Delete invoice ${row.invoice_no}?`)) {
      try {
        await deleteAction(row.id);
        dispatch(
          showToast({
            message: "Invoice deleted successfully",
            type: "success",
          }),
        );
        getInvoiceData(); // Refresh data
      } catch (error) {
        dispatch(
          showToast({ message: "Failed to delete invoice", type: "error" }),
        );
      }
    }
  };

  const handleBulkDelete = useCallback(async () => {
    if (!selectedInvoices.length) return;
    if (!window.confirm(`Delete ${selectedInvoices.length} invoices?`)) return;

    try {
      await Promise.all(selectedInvoices.map((row) => deleteAction(row.id)));
      dispatch(
        showToast({
          message: "Invoices deleted successfully",
          type: "success",
        }),
      );
      setSelectedInvoices([]);
      getInvoiceData();
    } catch (error) {
      dispatch(
        showToast({
          message: "Failed to delete invoices",
          type: "error",
        }),
      );
    }
  }, [selectedInvoices, dispatch, getInvoiceData]);

  const userColumns: TableColumn<InvoiceRow>[] = useMemo(
    () => [
      {
        name: "ID",
        selector: (row: InvoiceRow) => row.id,
        sortable: true,
        width: "80px",
        cell: (row: InvoiceRow) => (
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
        selector: (row: InvoiceRow) => row.invoice_no || "--",
        sortable: true,
        width: "14%",
      },
      {
        name: "Status",
        selector: (row: InvoiceRow) => row.status || "--",
        sortable: true,
        width: "12%",
        cell: (row: InvoiceRow) => (
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
        selector: (row: InvoiceRow) =>
          row.customer_name || row.customer_id || "--",
        sortable: true,
        width: "12%",
      },
      {
        name: "Vendor",
        selector: (row: InvoiceRow) => row.vendor_name || row.vendor_id || "--",
        sortable: true,
        width: "12%",
      },
      {
        name: "Total Amount",
        selector: (row: InvoiceRow) => row.total || row.total_amount || 0,
        sortable: true,
        width: "10%",
        cell: (row: InvoiceRow) => (
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
        selector: (row: InvoiceRow) => row.margin_percentage || 0,
        sortable: true,
        width: "8%",
        cell: (row: InvoiceRow) => (
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
        selector: (row: InvoiceRow) =>
          row.line_count || (row.lines ? row.lines.length : 0),
        sortable: true,
        width: "6%",
        cell: (row: InvoiceRow) => (
          <span className="text-center bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
            {row.line_count || (row.lines ? row.lines.length : 0)}
          </span>
        ),
      },
      {
        name: "Created",
        selector: (row: InvoiceRow) =>
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
        cell: (row: InvoiceRow) => (
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
    [handleView, handleEdit, handleDelete],
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
    [],
  );

  // Calculate summary statistics (commented out - for future summary cards)
  // const totalInvoices = data.length;
  // const totalValue = data.reduce(
  //   (sum, invoice) => sum + (invoice.total || invoice.total_amount || 0),
  //   0
  // );
  // const totalMargin = data.reduce(
  //   (sum, invoice) => sum + (invoice.margin_amount || 0),
  //   0
  // );
  // const avgMargin = totalInvoices > 0 ? (totalMargin / totalValue) * 100 : 0;
  // const statusCounts = data.reduce((acc, invoice) => {
  //   acc[invoice.status || "unknown"] =
  //     (acc[invoice.status || "unknown"] || 0) + 1;
  //   return acc;
  // }, {} as Record<string, number>);

  // Filter data based on filterValues from ButtonToolbar
  const filteredData = useMemo(() => {
    if (Object.keys(filterValues).length === 0) return data;
    return data.filter((row: any) => {
      return Object.entries(filterValues).every(([key, value]) => {
        if (!value) return true;
        const rowValue = String(row[key] || "").toLowerCase();
        return rowValue.includes(value.toLowerCase());
      });
    });
  }, [data, filterValues]);

  // Filter columns based on visibility from ButtonToolbar
  const visibleColumns = useMemo(() => {
    if (columnVisibility.length === 0) return userColumns;
    return userColumns.filter(
      (_: any, index: number) => columnVisibility[index] !== false,
    );
  }, [userColumns, columnVisibility]);
  return (
    <>
      <ButtonToolbar
        pageTitle="Invoice List"
        title="Invoice"
        modelKey="invoice"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        handleBulkDelete={handleBulkDelete}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        selectedRows={selectedInvoices}
        selectedCount={selectedInvoices.length}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={getInvoiceData}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={userColumns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="invoice-list"
        filters={filters}
        filterValues={filterValues}
        onFilterValuesChange={setFilterValues}
        filtersOpen={filtersOpen}
        onFiltersOpenChange={setFiltersOpen}
      />
      {/* Summary Cards */}
      {/* <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <ComponentCard>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {totalInvoices}
            </div>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              Total Invoices
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
      </div> */}

      <div>
        <ComponentCard>
          <AdvancedDataTable
            ref={tableRef}
            data={filteredData}
            columns={userColumns}
            title="Invoices"
            loading={loading}
            filters={filters}
            enableExport={true}
            enableSelection={true}
            onSelectionChange={setSelectedInvoices}
            onDeleteSelected={handleBulkDelete}
            exportFileName="invoices"
            searchPlaceholder="Search invoices, customers, vendors..."
            noDataMessage="No invoices found"
            enableDatabaseSearch={true}
            searchDatabase={searchDatabase}
            onSearchModeChange={setSearchDatabase}
            onDatabaseSearch={handleDatabaseSearch}
            externalSearchTerm={searchTerm}
            onExternalSearchTermChange={setSearchTerm}
            filtersOpen={filtersOpen}
            onFiltersOpenChange={setFiltersOpen}
            hideHeader={true}
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
    </>
  );
}
