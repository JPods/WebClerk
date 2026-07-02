/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * PaymentListPage — Data-table list of all payments.
 *
 * Mirrors the InvoiceList / OrderList pattern:
 *   ButtonToolbar → AdvancedDataTable inside ComponentCard.
 *
 * Legacy wc2 reference: Table 28 Output form columns:
 *   CustomerID, TypePay, Invoice#, DateReceived, Amount,
 *   AmountAvailable, NameOnAcct, Company, Comment, etc.
 */
import DataGrid from "@/components/common/DataGrid";
import type { ColumnFilter } from "@/components/common/ButtonToolbar";
import ComponentCard from '@/components/common/ComponentCard';
import ButtonToolbar from '@/components/common/ButtonToolbar';
import { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchPayments } from '../services/paymentApi';
import { FaEye, FaEdit, FaPlus, FaTrash } from 'react-icons/fa';
import { showToast } from '@/store/slices/toastSlice';
import { useDispatch } from 'react-redux';
import { deleteRecord } from '@/api/wcapi';
import { PageRoutes } from '@/routes/Routes';
import type { Payment } from '../types/Payment';

const STATUS_STYLES: Record<string, string> = {
  completed:
    'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  pending:
    'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  processing:
    'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  cancelled: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
  refunded:
    'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  partially_refunded:
    'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
};

const formatCurrency = (v: number | undefined | null) => {
  if (v == null) return '$0.00';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(v);
};

const formatDate = (d?: string | number | null) => {
  if (!d) return '--';
  const date = typeof d === 'string' ? new Date(d) : new Date(d * 1000);
  return date.toLocaleDateString();
};

export default function PaymentListPage() {
  const [data, setData] = useState<Payment[]>([]);
  const [selectedRows, setSelectedRows] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchDatabase, setSearchDatabase] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [columnVisibility, setColumnVisibility] = useState<boolean[]>([]);
  const tableRef = useRef<any>(null);
  const columnBtnRef = useRef<HTMLButtonElement>(null);
  const importInputRef = useRef<HTMLInputElement>(null);

  const dispatch = useDispatch();
  const navigate = useNavigate();

  const getPaymentData = useCallback(
    async (params?: Record<string, unknown>) => {
      try {
        setLoading(true);
        const res = await fetchPayments(params);
        if (res.status === 200) {
          setData(res.data.items);
        } else {
          dispatch(
            showToast({ message: 'Failed to fetch payments', type: 'error' }),
          );
        }
      } catch (error) {
        console.error('Failed to fetch payments', error);
        dispatch(
          showToast({ message: 'Failed to fetch payments', type: 'error' }),
        );
      } finally {
        setLoading(false);
      }
    },
    [dispatch],
  );

  const handleDatabaseSearch = useCallback(
    async (terms: string[]) => {
      try {
        setLoading(true);
        const res = await fetchPayments({ search: terms.join(',') });
        if (res.status === 200) {
          setData(res.data.items);
        }
      } catch (error) {
        console.error('Database search failed:', error);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    getPaymentData();
  }, [getPaymentData]);

  // Listen for model changes (e.g. payment created from another window)
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent)?.detail as any;
      if (String(detail?.model || '') === 'payment') {
        getPaymentData();
      }
    };
    window.addEventListener('wcapi:modelChanged', handler as any);
    return () =>
      window.removeEventListener('wcapi:modelChanged', handler as any);
  }, [getPaymentData]);

  // Navigation handlers
  const handleView = useCallback(
    (row: Payment) => {
      navigate(
        PageRoutes.transactionsPaymentDetail.replace(':id?', String(row.id)),
        { state: { mode: 'view' } },
      );
    },
    [navigate],
  );

  const handleEdit = useCallback(
    (row: Payment) => {
      navigate(
        PageRoutes.transactionsPaymentDetail.replace(':id?', String(row.id)),
        { state: { mode: 'edit' } },
      );
    },
    [navigate],
  );

  const handleAdd = () => {
    navigate(
      PageRoutes.transactionsPaymentDetail.replace(':id?', ''),
      { state: { mode: 'add' } },
    );
  };

  const handleDelete = useCallback(
    async (row: Payment) => {
      if (!window.confirm(`Delete payment #${row.id}?`)) return;
      try {
        await deleteRecord('payment', row.id);
        dispatch(
          showToast({ message: 'Payment deleted', type: 'success' }),
        );
        getPaymentData();
      } catch {
        dispatch(
          showToast({ message: 'Failed to delete payment', type: 'error' }),
        );
      }
    },
    [dispatch, getPaymentData],
  );

  const handleBulkDelete = useCallback(async () => {
    if (!selectedRows.length) return;
    if (!window.confirm(`Delete ${selectedRows.length} payments?`)) return;
    try {
      await Promise.all(
        selectedRows.map((r) => deleteRecord('payment', r.id)),
      );
      dispatch(
        showToast({ message: 'Payments deleted', type: 'success' }),
      );
      setSelectedRows([]);
      getPaymentData();
    } catch {
      dispatch(
        showToast({ message: 'Failed to delete payments', type: 'error' }),
      );
    }
  }, [selectedRows, dispatch, getPaymentData]);

  // Columns
  const userColumns: any[] = useMemo(
    () => [
      {
        name: 'ID',
        selector: (row: Payment) => row.id,
        sortable: true,
        width: '70px',
        cell: (row: Payment) => (
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
        name: 'status',
        selector: (row: Payment) => row.status || '--',
        sortable: true,
        width: '120px',
        cell: (row: Payment) => (
          <span
            className={`px-2 py-1 rounded-full text-xs font-medium ${
              STATUS_STYLES[row.status] || STATUS_STYLES.pending
            }`}
          >
            {row.status || 'Unknown'}
          </span>
        ),
      },
      {
        name: 'amount',
        selector: (row: Payment) => row.amount ?? 0,
        sortable: true,
        width: '110px',
        cell: (row: Payment) => (
          <span className="font-medium text-green-600 dark:text-green-400">
            {formatCurrency(row.amount)}
          </span>
        ),
      },
      {
        name: 'amount_available',
        selector: (row: Payment) => row.amount_available ?? 0,
        sortable: true,
        width: '130px',
        cell: (row: Payment) => (
          <span className="text-slate-700 dark:text-slate-300">
            {formatCurrency(row.amount_available)}
          </span>
        ),
      },
      {
        name: 'customer_name',
        selector: (row: Payment) => row.customer_name || '--',
        sortable: true,
        width: '14%',
      },
      {
        name: 'payment_method_name',
        selector: (row: Payment) => row.payment_method_name || row.gateway || '--',
        sortable: true,
        width: '12%',
      },
      {
        name: 'reference_number',
        selector: (row: Payment) => row.reference_number || '--',
        sortable: true,
        width: '12%',
      },
      {
        name: 'invoice_number',
        selector: (row: Payment) => row.invoice_number || '--',
        sortable: true,
        width: '10%',
      },
      {
        name: 'dt_payment',
        selector: (row: Payment) => row.dt_payment || '--',
        sortable: true,
        width: '10%',
        cell: (row: Payment) => <span>{formatDate(row.dt_payment)}</span>,
      },
      {
        name: 'dt_created',
        selector: (row: Payment) => row.dt_created || '--',
        sortable: true,
        width: '10%',
        cell: (row: Payment) => <span>{formatDate(row.dt_created)}</span>,
      },
      {
        name: 'Actions',
        width: '140px',
        cell: (row: Payment) => (
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

  const filters: ColumnFilter[] = useMemo(
    () => [
      {
        key: 'status',
        label: 'Status',
        type: 'select',
        options: [
          { value: 'pending', label: 'Pending' },
          { value: 'completed', label: 'Completed' },
          { value: 'failed', label: 'Failed' },
          { value: 'cancelled', label: 'Cancelled' },
          { value: 'refunded', label: 'Refunded' },
        ],
      },
      {
        key: 'customer_name',
        label: 'Customer',
        type: 'text',
      },
      {
        key: 'gateway',
        label: 'Gateway',
        type: 'select',
        options: [
          { value: 'manual', label: 'Manual' },
          { value: 'stripe', label: 'Stripe' },
          { value: 'paypal', label: 'PayPal' },
        ],
      },
    ],
    [],
  );

  const filteredData = useMemo(() => {
    if (Object.keys(filterValues).length === 0) return data;
    return data.filter((row: any) =>
      Object.entries(filterValues).every(([key, value]) => {
        if (!value) return true;
        return String(row[key] || '')
          .toLowerCase()
          .includes(value.toLowerCase());
      }),
    );
  }, [data, filterValues]);

  return (
    <>
      <ButtonToolbar
        pageTitle="Payment List"
        title="Payment"
        modelKey="payment"
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        handleAddInline={handleAdd}
        handleBulkDelete={handleBulkDelete}
        tableRef={tableRef}
        columnBtnRef={columnBtnRef}
        importInputRef={importInputRef}
        selectedRows={selectedRows}
        selectedCount={selectedRows.length}
        totalCount={data.length}
        filteredCount={filteredData.length}
        onRefresh={() => getPaymentData()}
        loading={loading}
        enableDatabaseSearch
        searchDatabase={searchDatabase}
        onSearchModeChange={setSearchDatabase}
        columns={userColumns}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
        storageKey="payment-list"
        filters={filters}
        filterValues={filterValues}
        onFilterValuesChange={setFilterValues}
        filtersOpen={filtersOpen}
        onFiltersOpenChange={setFiltersOpen}
      />
      <div>
        <ComponentCard>
          <DataGrid
            ref={tableRef}
            data={filteredData}
            columns={userColumns}
            title="Payments"
            loading={loading}
            filters={filters}
            enableExport
            enableSelection
            onSelectionChange={setSelectedRows}
            onDeleteSelected={handleBulkDelete}
            exportFileName="payments"
            searchPlaceholder="Search payments..."
            noDataMessage="No payments found"
            enableDatabaseSearch
            searchDatabase={searchDatabase}
            onSearchModeChange={setSearchDatabase}
            onDatabaseSearch={handleDatabaseSearch}
            externalSearchTerm={searchTerm}
            onExternalSearchTermChange={setSearchTerm}
            filtersOpen={filtersOpen}
            onFiltersOpenChange={setFiltersOpen}
            hideHeader
            customActions={
              <button
                onClick={handleAdd}
                className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
              >
                <FaPlus className="w-4 h-4" />
                Add Payment
              </button>
            }
            onRowClicked={handleEdit}
          />
        </ComponentCard>
      </div>
    </>
  );
}
