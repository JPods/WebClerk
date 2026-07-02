/* LastChecked: 2026-06-30 | WhereUsed: /transactions/apply-payments | WhoCreated: Claude */
/**
 * ApplyPayments — Full payment application workflow.
 *
 * Two-pane layout:
 *   Left:  Unapplied payments (balance > 0). Click one to select.
 *   Right: Open invoices for that payment's customer. Per-invoice apply amount.
 *
 * Workflow: Select payment -> see invoices -> enter amounts (or Auto Apply) ->
 *           review summary -> Submit -> backend creates PendingPaymentApplication
 *           records via apply_payment_to_invoice.
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useDispatch } from 'react-redux';
import {
  FaSearch,
  FaCheck,
  FaSync,
  FaSpinner,
  FaEraser,
  FaMagic,
  FaPlus,
} from 'react-icons/fa';
import PageBreadcrumb from '@/components/common/PageBreadCrumb';
import ComponentCard from '@/components/common/ComponentCard';
import { getRecords, GetListPayload } from '@/api/wcapi';
import { showToast } from '@/store/slices/toastSlice';
import usePaymentApplication, {
  PaymentRecord,
  InvoiceRecord,
} from '../hooks/usePaymentApplication';
import PaymentDialog from '../components/PaymentDialog';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

/** Per-invoice amount the user wants to apply from the selected payment. */
interface InvoiceApplication {
  invoiceId: number;
  amount: number; // 0 = not applied
}

type SearchPayload = Pick<GetListPayload, 'results'> & { items?: unknown[] };

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const formatCurrency = (value: number | undefined | null): string => {
  if (value == null) return '$0.00';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(value);
};

const formatDate = (dateStr?: string | null): string => {
  if (!dateStr) return '--';
  return new Date(dateStr).toLocaleDateString();
};

/** Return CSS classes for invoice aging color bands. */
const agingColor = (days: number): string => {
  if (days >= 90)
    return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
  if (days >= 60)
    return 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400';
  if (days >= 30)
    return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400';
  return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
};

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

const ApplyPayments: React.FC = () => {
  const dispatch = useDispatch();
  const {
    getAvailablePayments,
    getUnpaidInvoices,
    applyPaymentToInvoice,
    calculateDaysPastDue,
    getInvoiceBalance,
    getPaymentAvailable,
  } = usePaymentApplication();

  /* ---------- payments state ---------- */
  const [payments, setPayments] = useState<PaymentRecord[]>([]);
  const [loadingPayments, setLoadingPayments] = useState(false);
  const [selectedPayment, setSelectedPayment] = useState<PaymentRecord | null>(null);

  /* ---------- payment filters ---------- */
  const [paymentSearch, setPaymentSearch] = useState('');
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');

  /* ---------- invoices state ---------- */
  const [invoices, setInvoices] = useState<InvoiceRecord[]>([]);
  const [loadingInvoices, setLoadingInvoices] = useState(false);

  /* ---------- application amounts ---------- */
  const [applications, setApplications] = useState<Map<number, number>>(new Map());

  /* ---------- submit state ---------- */
  const [submitting, setSubmitting] = useState(false);
  const [showPaymentDialog, setShowPaymentDialog] = useState(false);

  /* ---------------------------------------------------------------- */
  /*  Load all unapplied payments                                      */
  /* ---------------------------------------------------------------- */

  const loadPayments = useCallback(async () => {
    setLoadingPayments(true);
    try {
      const params: Record<string, unknown> = {
        status: 'completed',
        limit: 200,
        ordering: '-dt_created',
      };
      if (filterDateFrom) params.dt_created__gte = filterDateFrom;
      if (filterDateTo) params.dt_created__lte = filterDateTo;

      const result = (await getRecords('payment', params)) as SearchPayload;
      const records: PaymentRecord[] = Array.isArray(result?.results)
        ? result.results
        : Array.isArray(result?.items)
          ? (result.items as PaymentRecord[])
          : [];

      // Keep only payments with remaining balance > 0
      const unapplied = records.filter((p) => {
        const avail = p.amount_available ?? p.amount;
        return avail > 0.005; // tolerance for floating point
      });
      setPayments(unapplied);
    } catch (err) {
      console.error('Failed to load payments:', err);
      dispatch(showToast({ message: 'Failed to load payments', type: 'error' }));
    } finally {
      setLoadingPayments(false);
    }
  }, [filterDateFrom, filterDateTo, dispatch]);

  // Initial load
  useEffect(() => {
    loadPayments();
  }, [loadPayments]);

  /* ---------------------------------------------------------------- */
  /*  Filter payments client-side by search text                       */
  /* ---------------------------------------------------------------- */

  const filteredPayments = useMemo(() => {
    if (!paymentSearch.trim()) return payments;
    const q = paymentSearch.toLowerCase();
    return payments.filter((p) => {
      const ref = (p.reference_number || p.ida || `PAY-${p.id}`).toLowerCase();
      const org =
        p.refs?.links?.org?.[0]?.display_name?.toLowerCase() || '';
      return ref.includes(q) || org.includes(q) || String(p.id).includes(q);
    });
  }, [payments, paymentSearch]);

  /* ---------------------------------------------------------------- */
  /*  When a payment is selected, load invoices for its customer       */
  /* ---------------------------------------------------------------- */

  const loadInvoicesForPayment = useCallback(
    async (payment: PaymentRecord) => {
      const orgId = payment.org_id || payment.refs?.links?.org?.[0]?.id;
      if (!orgId) {
        setInvoices([]);
        dispatch(
          showToast({ message: 'Payment has no linked customer', type: 'warning' }),
        );
        return;
      }
      setLoadingInvoices(true);
      try {
        const inv = await getUnpaidInvoices(String(orgId));
        setInvoices(inv);
      } finally {
        setLoadingInvoices(false);
      }
    },
    [getUnpaidInvoices, dispatch],
  );

  const handleSelectPayment = useCallback(
    (payment: PaymentRecord) => {
      setSelectedPayment(payment);
      setApplications(new Map());
      loadInvoicesForPayment(payment);
    },
    [loadInvoicesForPayment],
  );

  /* ---------------------------------------------------------------- */
  /*  Application amount helpers                                       */
  /* ---------------------------------------------------------------- */

  const setApplyAmount = useCallback((invoiceId: number, amount: number) => {
    setApplications((prev) => {
      const next = new Map(prev);
      if (amount <= 0) {
        next.delete(invoiceId);
      } else {
        next.set(invoiceId, amount);
      }
      return next;
    });
  }, []);

  const totalApplied = useMemo(() => {
    let sum = 0;
    applications.forEach((amt) => {
      sum += amt;
    });
    return sum;
  }, [applications]);

  const paymentAvailable = selectedPayment
    ? getPaymentAvailable(selectedPayment)
    : 0;

  const remaining = paymentAvailable - totalApplied;

  /* ---------------------------------------------------------------- */
  /*  Auto Apply — FIFO oldest first                                   */
  /* ---------------------------------------------------------------- */

  const handleAutoApply = useCallback(() => {
    if (!selectedPayment) return;

    const sorted = [...invoices].sort(
      (a, b) =>
        new Date(a.dt || a.dt_created || 0).getTime() -
        new Date(b.dt || b.dt_created || 0).getTime(),
    );

    let budget = paymentAvailable;
    const next = new Map<number, number>();

    for (const inv of sorted) {
      if (budget <= 0.005) break;
      const balance = getInvoiceBalance(inv);
      const toApply = Math.min(budget, balance);
      if (toApply > 0.005) {
        next.set(inv.id, parseFloat(toApply.toFixed(2)));
        budget -= toApply;
      }
    }

    setApplications(next);
  }, [selectedPayment, invoices, paymentAvailable, getInvoiceBalance]);

  const handleClearAmounts = useCallback(() => {
    setApplications(new Map());
  }, []);

  /* ---------------------------------------------------------------- */
  /*  Submit — create PendingPaymentApplication for each line          */
  /* ---------------------------------------------------------------- */

  const handleSubmit = useCallback(async () => {
    if (!selectedPayment || applications.size === 0) return;

    // Validate total does not exceed available
    if (totalApplied > paymentAvailable + 0.005) {
      dispatch(
        showToast({
          message: `Applied total ($${totalApplied.toFixed(2)}) exceeds available ($${paymentAvailable.toFixed(2)})`,
          type: 'error',
        }),
      );
      return;
    }

    setSubmitting(true);
    let successCount = 0;
    let failCount = 0;

    try {
      // Apply each invoice sequentially (backend locks rows)
      for (const [invoiceId, amount] of applications.entries()) {
        if (amount <= 0) continue;
        const result = await applyPaymentToInvoice(invoiceId, selectedPayment.id, amount);
        if (result.success) {
          successCount++;
        } else {
          failCount++;
        }
      }

      if (successCount > 0) {
        dispatch(
          showToast({
            message: `Applied payment to ${successCount} invoice(s)${failCount > 0 ? ` (${failCount} failed)` : ''}`,
            type: failCount > 0 ? 'warning' : 'success',
          }),
        );
      } else if (failCount > 0) {
        dispatch(
          showToast({ message: `All ${failCount} applications failed`, type: 'error' }),
        );
      }

      // Refresh both panes
      setApplications(new Map());
      await loadPayments();

      // If payment still exists and still has balance, reload invoices
      const refreshedPayments = payments; // will be stale; re-select will reload
      setSelectedPayment(null);
      setInvoices([]);
    } finally {
      setSubmitting(false);
    }
  }, [
    selectedPayment,
    applications,
    totalApplied,
    paymentAvailable,
    applyPaymentToInvoice,
    dispatch,
    loadPayments,
    payments,
  ]);

  /* ---------------------------------------------------------------- */
  /*  Customer name for selected payment                               */
  /* ---------------------------------------------------------------- */

  const selectedCustomerName = useMemo(() => {
    if (!selectedPayment) return '';
    return (
      selectedPayment.refs?.links?.org?.[0]?.display_name ||
      `Customer #${selectedPayment.org_id || '?'}`
    );
  }, [selectedPayment]);

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div data-wc="apply-payments" className="p-4 space-y-4">
      <PageBreadcrumb pageTitle="Apply Payments" />

      {/* ---- Summary bar (visible when a payment is selected) ---- */}
      {selectedPayment && (
        <div
          data-wc="apply-payments-summary"
          className="flex flex-wrap items-center gap-6 px-4 py-3 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700"
        >
          <div className="text-sm">
            <span className="text-slate-500 dark:text-slate-400">Payment:</span>{' '}
            <span className="font-mono font-medium text-slate-900 dark:text-white">
              {formatCurrency(paymentAvailable)}
            </span>
          </div>
          <div className="text-sm">
            <span className="text-slate-500 dark:text-slate-400">Applied:</span>{' '}
            <span className="font-mono font-medium text-green-600 dark:text-green-400">
              {formatCurrency(totalApplied)}
            </span>
          </div>
          <div className="text-sm">
            <span className="text-slate-500 dark:text-slate-400">Remaining:</span>{' '}
            <span
              className={`font-mono font-medium ${
                remaining < -0.005
                  ? 'text-red-600 dark:text-red-400'
                  : 'text-slate-900 dark:text-white'
              }`}
            >
              {formatCurrency(remaining)}
            </span>
          </div>
          <div className="text-sm">
            <span className="text-slate-500 dark:text-slate-400">Customer:</span>{' '}
            <span className="font-medium text-slate-900 dark:text-white">
              {selectedCustomerName}
            </span>
          </div>
        </div>
      )}

      {/* ---- Two-pane layout ---- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* ============================================================ */}
        {/*  LEFT PANE — Unapplied Payments                              */}
        {/* ============================================================ */}
        <ComponentCard
          title={`Unapplied Payments (${filteredPayments.length})`}
        >
          <div data-wc="apply-payments-left" className="p-2">
            {/* Filters */}
            <div className="flex flex-wrap items-center gap-2 mb-2 pb-2 border-b border-slate-200 dark:border-slate-700">
              <div className="relative flex-1 min-w-[140px]">
                <FaSearch className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 text-xs" />
                <input
                  data-wc="apply-payments-search"
                  type="text"
                  placeholder="Search ref / customer..."
                  value={paymentSearch}
                  onChange={(e) => setPaymentSearch(e.target.value)}
                  className="w-full pl-7 pr-2 py-1 text-xs border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <input
                type="date"
                value={filterDateFrom}
                onChange={(e) => setFilterDateFrom(e.target.value)}
                className="text-xs px-1 py-1 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                title="From date"
              />
              <input
                type="date"
                value={filterDateTo}
                onChange={(e) => setFilterDateTo(e.target.value)}
                className="text-xs px-1 py-1 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                title="To date"
              />
              <button
                onClick={loadPayments}
                disabled={loadingPayments}
                className="text-xs px-2 py-1 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded flex items-center gap-1"
                title="Refresh"
              >
                <FaSync className={loadingPayments ? 'animate-spin' : ''} />
              </button>
              <button
                onClick={() => setShowPaymentDialog(true)}
                className="text-xs px-2 py-1 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/30 rounded flex items-center gap-1"
                title="Record new payment"
              >
                <FaPlus /> New
              </button>
            </div>

            {/* Payment list */}
            {loadingPayments ? (
              <div className="flex items-center justify-center py-8 text-slate-400">
                <FaSpinner className="animate-spin mr-2" /> Loading payments...
              </div>
            ) : filteredPayments.length === 0 ? (
              <div className="text-center py-8 text-slate-400 text-sm">
                No unapplied payments found
              </div>
            ) : (
              <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                <table className="w-full text-xs">
                  <thead className="bg-slate-100 dark:bg-slate-800 sticky top-0 z-10">
                    <tr>
                      <th className="p-1.5 text-left font-medium text-slate-600 dark:text-slate-300">
                        Reference
                      </th>
                      <th className="p-1.5 text-left font-medium text-slate-600 dark:text-slate-300">
                        Customer
                      </th>
                      <th className="p-1.5 text-right font-medium text-slate-600 dark:text-slate-300">
                        Available
                      </th>
                      <th className="p-1.5 text-right font-medium text-slate-600 dark:text-slate-300">
                        Original
                      </th>
                      <th className="p-1.5 text-left font-medium text-slate-600 dark:text-slate-300">
                        Date
                      </th>
                      <th className="p-1.5 text-left font-medium text-slate-600 dark:text-slate-300">
                        Type
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredPayments.map((payment) => {
                      const isSelected = selectedPayment?.id === payment.id;
                      const available = getPaymentAvailable(payment);
                      const custName =
                        payment.refs?.links?.org?.[0]?.display_name || '--';

                      return (
                        <tr
                          key={payment.id}
                          data-wc="apply-payments-row"
                          onClick={() => handleSelectPayment(payment)}
                          className={`cursor-pointer border-t border-slate-200 dark:border-slate-700 transition-colors ${
                            isSelected
                              ? 'bg-blue-50 dark:bg-blue-900/20 ring-1 ring-blue-300 dark:ring-blue-700'
                              : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'
                          }`}
                        >
                          <td className="p-1.5 font-mono">
                            {payment.reference_number ||
                              payment.ida ||
                              `PAY-${payment.id}`}
                          </td>
                          <td className="p-1.5 text-slate-600 dark:text-slate-400 truncate max-w-[120px]">
                            {custName}
                          </td>
                          <td className="p-1.5 text-right font-mono font-medium text-green-600 dark:text-green-400">
                            {formatCurrency(available)}
                          </td>
                          <td className="p-1.5 text-right font-mono text-slate-500 dark:text-slate-500">
                            {formatCurrency(payment.amount)}
                          </td>
                          <td className="p-1.5 text-slate-600 dark:text-slate-400">
                            {formatDate(
                              payment.dt_payment || payment.dt_created,
                            )}
                          </td>
                          <td className="p-1.5 text-slate-600 dark:text-slate-400">
                            {payment.gateway || 'manual'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </ComponentCard>

        {/* ============================================================ */}
        {/*  RIGHT PANE — Open Invoices for selected payment's customer   */}
        {/* ============================================================ */}
        <ComponentCard
          title={
            selectedPayment
              ? `Open Invoices — ${selectedCustomerName} (${invoices.length})`
              : 'Open Invoices'
          }
        >
          <div data-wc="apply-payments-right" className="p-2">
            {!selectedPayment ? (
              <div className="text-center py-12 text-slate-400 text-sm">
                Select a payment on the left to see open invoices
              </div>
            ) : (
              <>
                {/* Action bar */}
                <div className="flex flex-wrap items-center gap-2 mb-2 pb-2 border-b border-slate-200 dark:border-slate-700">
                  <button
                    onClick={handleAutoApply}
                    disabled={invoices.length === 0}
                    className="text-xs px-2 py-1 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 disabled:text-slate-400 disabled:hover:bg-transparent rounded flex items-center gap-1"
                    title="Apply to oldest invoices first until payment is exhausted"
                  >
                    <FaMagic /> Auto Apply (FIFO)
                  </button>
                  <button
                    onClick={handleClearAmounts}
                    disabled={applications.size === 0}
                    className="text-xs px-2 py-1 text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:text-slate-400 disabled:hover:bg-transparent rounded flex items-center gap-1"
                  >
                    <FaEraser /> Clear
                  </button>
                  <div className="ml-auto flex items-center gap-3">
                    {applications.size > 0 && (
                      <span className="text-xs text-slate-500 dark:text-slate-400">
                        {applications.size} invoice(s) ={' '}
                        {formatCurrency(totalApplied)}
                      </span>
                    )}
                    <button
                      data-wc="apply-payments-submit"
                      onClick={handleSubmit}
                      disabled={
                        submitting ||
                        applications.size === 0 ||
                        remaining < -0.005
                      }
                      className="px-3 py-1.5 text-xs font-medium text-white bg-green-600 hover:bg-green-700 disabled:bg-slate-400 disabled:cursor-not-allowed rounded-lg transition-colors flex items-center gap-1"
                    >
                      {submitting ? (
                        <FaSpinner className="animate-spin" />
                      ) : (
                        <FaCheck />
                      )}
                      Submit
                    </button>
                  </div>
                </div>

                {/* Invoice list */}
                {loadingInvoices ? (
                  <div className="flex items-center justify-center py-8 text-slate-400">
                    <FaSpinner className="animate-spin mr-2" /> Loading
                    invoices...
                  </div>
                ) : invoices.length === 0 ? (
                  <div className="text-center py-8 text-slate-400 text-sm">
                    No open invoices for this customer
                  </div>
                ) : (
                  <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                    <table className="w-full text-xs">
                      <thead className="bg-slate-100 dark:bg-slate-800 sticky top-0 z-10">
                        <tr>
                          <th className="p-1.5 text-left font-medium text-slate-600 dark:text-slate-300">
                            Invoice
                          </th>
                          <th className="p-1.5 text-left font-medium text-slate-600 dark:text-slate-300">
                            Date
                          </th>
                          <th className="p-1.5 text-right font-medium text-slate-600 dark:text-slate-300">
                            Total
                          </th>
                          <th className="p-1.5 text-right font-medium text-slate-600 dark:text-slate-300">
                            Balance
                          </th>
                          <th className="p-1.5 text-center font-medium text-slate-600 dark:text-slate-300">
                            Age
                          </th>
                          <th className="p-1.5 text-right font-medium text-slate-600 dark:text-slate-300">
                            Apply
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {invoices.map((invoice) => {
                          const balance = getInvoiceBalance(invoice);
                          const days = calculateDaysPastDue(invoice);
                          const currentAmt = applications.get(invoice.id) ?? 0;

                          return (
                            <tr
                              key={invoice.id}
                              data-wc="apply-payments-invoice-row"
                              className={`border-t border-slate-200 dark:border-slate-700 ${
                                currentAmt > 0
                                  ? 'bg-green-50 dark:bg-green-900/10'
                                  : ''
                              }`}
                            >
                              <td className="p-1.5 font-mono">
                                {invoice.ida ||
                                  invoice.invoice_no ||
                                  `#${invoice.id}`}
                              </td>
                              <td className="p-1.5 text-slate-600 dark:text-slate-400">
                                {formatDate(invoice.dt || invoice.dt_created)}
                              </td>
                              <td className="p-1.5 text-right font-mono text-slate-600 dark:text-slate-400">
                                {formatCurrency(invoice.totals?.total)}
                              </td>
                              <td className="p-1.5 text-right font-mono font-medium text-amber-600 dark:text-amber-400">
                                {formatCurrency(balance)}
                              </td>
                              <td className="p-1.5 text-center">
                                <span
                                  className={`inline-block min-w-[28px] px-1 rounded text-xs font-medium ${agingColor(days)}`}
                                >
                                  {days}
                                </span>
                              </td>
                              <td className="p-1.5 text-right">
                                <div className="relative inline-block">
                                  <span className="absolute left-1.5 top-1/2 -translate-y-1/2 text-slate-400 text-[10px]">
                                    $
                                  </span>
                                  <input
                                    data-wc="apply-payments-amount"
                                    type="number"
                                    step="0.01"
                                    min="0"
                                    max={balance}
                                    value={currentAmt > 0 ? currentAmt : ''}
                                    placeholder="0.00"
                                    onChange={(e) => {
                                      const val = parseFloat(e.target.value);
                                      if (isNaN(val) || val <= 0) {
                                        setApplyAmount(invoice.id, 0);
                                      } else {
                                        // Cap at invoice balance
                                        setApplyAmount(
                                          invoice.id,
                                          parseFloat(
                                            Math.min(val, balance).toFixed(2),
                                          ),
                                        );
                                      }
                                    }}
                                    className="w-20 pl-4 pr-1 py-0.5 text-xs text-right font-mono border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-1 focus:ring-green-500 focus:border-green-500"
                                  />
                                </div>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                      {/* Totals row */}
                      <tfoot>
                        <tr className="border-t-2 border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-800/50">
                          <td
                            colSpan={3}
                            className="p-1.5 text-right text-xs font-medium text-slate-500 dark:text-slate-400"
                          >
                            Totals
                          </td>
                          <td className="p-1.5 text-right font-mono font-medium text-amber-600 dark:text-amber-400 text-xs">
                            {formatCurrency(
                              invoices.reduce(
                                (s, inv) => s + getInvoiceBalance(inv),
                                0,
                              ),
                            )}
                          </td>
                          <td />
                          <td className="p-1.5 text-right font-mono font-medium text-green-600 dark:text-green-400 text-xs">
                            {formatCurrency(totalApplied)}
                          </td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                )}
              </>
            )}
          </div>
        </ComponentCard>
      </div>

      {/* ---- Make Payment Dialog ---- */}
      <PaymentDialog
        isOpen={showPaymentDialog}
        onClose={() => setShowPaymentDialog(false)}
        onPaymentAdded={() => {
          loadPayments();
        }}
      />
    </div>
  );
};

export default ApplyPayments;
