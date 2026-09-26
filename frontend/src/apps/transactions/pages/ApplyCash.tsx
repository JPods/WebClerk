/* LastChecked: 2026-06-30 | WhereUsed: /transactions/apply-cash | WhoCreated: Claude */
/**
 * ApplyCash — Full cash application workflow.
 *
 * Two-pane layout:
 *   Left:  Unapplied cash (balance > 0). Click one to select.
 *   Right: Open invoices for that cash's customer. Per-invoice apply amount.
 *
 * Workflow: Select cash -> see invoices -> enter amounts (or Auto Apply) ->
 *           review summary -> Submit -> backend creates a Pending application record
 *           records via apply_cash_to_invoice.
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
import { formatDt } from '@/utils/fieldFormatters';
import ComponentCard from '@/components/common/ComponentCard';
import { getRecords, GetListPayload } from '@/api/wcapi';
import { showToast } from '@/store/slices/toastSlice';
import useCashApplication, {
  CashRecord,
  InvoiceRecord,
} from '../hooks/useCashApplication';
import CashDialog from '../components/CashDialog';
import { formatCurrency } from '@/utils/stringUtils';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type SearchPayload = Pick<GetListPayload, 'results'> & { items?: unknown[] };

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */


const formatDate = (dateStr?: string | null): string => {
  if (!dateStr) return '--';
  return formatDt(dateStr, 'date');
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

const ApplyCash: React.FC = () => {
  const dispatch = useDispatch();
  const {
    getUnpaidInvoices,
    applyCashToInvoice,
    calculateDaysPastDue,
    getInvoiceBalance,
    getCashAvailable,
  } = useCashApplication();

  /* ---------- cashEntries state ---------- */
  const [cashEntries, setCashEntries] = useState<CashRecord[]>([]);
  const [loadingCashEntries, setLoadingCashEntries] = useState(false);
  const [selectedCash, setSelectedCash] = useState<CashRecord | null>(null);

  /* ---------- cash filters ---------- */
  const [cashSearch, setCashSearch] = useState('');
  const [filterDateFrom, setFilterDateFrom] = useState('');
  const [filterDateTo, setFilterDateTo] = useState('');

  /* ---------- invoices state ---------- */
  const [invoices, setInvoices] = useState<InvoiceRecord[]>([]);
  const [loadingInvoices, setLoadingInvoices] = useState(false);

  /* ---------- application amounts ---------- */
  const [applications, setApplications] = useState<Map<number, number>>(new Map());

  /* ---------- submit state ---------- */
  const [submitting, setSubmitting] = useState(false);
  const [showCashDialog, setShowCashDialog] = useState(false);

  /* ---------------------------------------------------------------- */
  /*  Load all unapplied cash                                      */
  /* ---------------------------------------------------------------- */

  const loadCashEntries = useCallback(async () => {
    setLoadingCashEntries(true);
    try {
      const params: Record<string, unknown> = {
        status: 'completed',
        limit: 200,
        ordering: '-dt_created',
      };
      if (filterDateFrom) params.dt_created__gte = filterDateFrom;
      if (filterDateTo) params.dt_created__lte = filterDateTo;

      const result = (await getRecords('cash', params)) as SearchPayload;
      const records: CashRecord[] = Array.isArray(result?.results)
        ? result.results
        : Array.isArray(result?.items)
          ? (result.items as CashRecord[])
          : [];

      // Keep only cash with remaining balance > 0
      const unapplied = records.filter((p) => {
        return p.available > 0.005; // tolerance for floating point
      });
      setCashEntries(unapplied);
    } catch (err) {
      console.error('Failed to load cash:', err);
      dispatch(showToast({ message: 'Failed to load cash', type: 'error' }));
    } finally {
      setLoadingCashEntries(false);
    }
  }, [filterDateFrom, filterDateTo, dispatch]);

  // Initial load
  useEffect(() => {
    loadCashEntries();
  }, [loadCashEntries]);

  /* ---------------------------------------------------------------- */
  /*  Filter cash client-side by search text                       */
  /* ---------------------------------------------------------------- */

  const filteredCashEntries = useMemo(() => {
    if (!cashSearch.trim()) return cashEntries;
    const q = cashSearch.toLowerCase();
    return cashEntries.filter((p) => {
      const ref = (p.reference_number || p.ida || `PAY-${p.id}`).toLowerCase();
      const org =
        p.refs?.links?.org?.[0]?.display_name?.toLowerCase() || '';
      return ref.includes(q) || org.includes(q) || String(p.id).includes(q);
    });
  }, [cashEntries, cashSearch]);

  /* ---------------------------------------------------------------- */
  /*  When a cash entry is selected, load invoices for its customer       */
  /* ---------------------------------------------------------------- */

  const loadInvoicesForCash = useCallback(
    async (cash: CashRecord) => {
      const orgId = cash.org_id || cash.refs?.links?.org?.[0]?.id;
      if (!orgId) {
        setInvoices([]);
        dispatch(
          showToast({ message: 'Cash has no linked customer', type: 'warning' }),
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

  const handleSelectCash = useCallback(
    (cash: CashRecord) => {
      setSelectedCash(cash);
      setApplications(new Map());
      loadInvoicesForCash(cash);
    },
    [loadInvoicesForCash],
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

  const cashAvailable = selectedCash
    ? getCashAvailable(selectedCash)
    : 0;

  const remaining = cashAvailable - totalApplied;

  /* ---------------------------------------------------------------- */
  /*  Auto Apply — FIFO oldest first                                   */
  /* ---------------------------------------------------------------- */

  const handleAutoApply = useCallback(() => {
    if (!selectedCash) return;

    const sorted = [...invoices].sort(
      (a, b) =>
        new Date(a.dt || a.dt_created || 0).getTime() -
        new Date(b.dt || b.dt_created || 0).getTime(),
    );

    let budget = cashAvailable;
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
  }, [selectedCash, invoices, cashAvailable, getInvoiceBalance]);

  const handleClearAmounts = useCallback(() => {
    setApplications(new Map());
  }, []);

  /* ---------------------------------------------------------------- */
  /*  Submit — create a Pending application for each line            */
  /* ---------------------------------------------------------------- */

  const handleSubmit = useCallback(async () => {
    if (!selectedCash || applications.size === 0) return;

    // Validate total does not exceed available
    if (totalApplied > cashAvailable + 0.005) {
      dispatch(
        showToast({
          message: `Applied total (${formatCurrency(totalApplied)}) exceeds available (${formatCurrency(cashAvailable)})`,
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
        const result = await applyCashToInvoice(invoiceId, selectedCash.id, amount);
        if (result.success) {
          successCount++;
        } else {
          failCount++;
        }
      }

      if (successCount > 0) {
        dispatch(
          showToast({
            message: `Applied cash to ${successCount} invoice(s)${failCount > 0 ? ` (${failCount} failed)` : ''}`,
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
      await loadCashEntries();

      // If cash still exists and still has balance, reload invoices
      // cashEntries will be stale; re-select will reload
      setSelectedCash(null);
      setInvoices([]);
    } finally {
      setSubmitting(false);
    }
  }, [
    selectedCash,
    applications,
    totalApplied,
    cashAvailable,
    applyCashToInvoice,
    dispatch,
    loadCashEntries,
    cashEntries,
  ]);

  /* ---------------------------------------------------------------- */
  /*  Customer name for selected cash                               */
  /* ---------------------------------------------------------------- */

  const selectedCustomerName = useMemo(() => {
    if (!selectedCash) return '';
    return (
      selectedCash.refs?.links?.org?.[0]?.display_name ||
      `Customer #${selectedCash.org_id || '?'}`
    );
  }, [selectedCash]);

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div data-wc="apply-cash" className="p-4 space-y-4">
      <PageBreadcrumb pageTitle="Apply Cash" />

      {/* ---- Summary bar (visible when a cash entry is selected) ---- */}
      {selectedCash && (
        <div
          data-wc="apply-cash-summary"
          className="flex flex-wrap items-center gap-6 px-4 py-3 rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700"
        >
          <div className="text-sm">
            <span className="text-slate-500 dark:text-slate-400">Cash:</span>{' '}
            <span className="font-mono font-medium text-slate-900 dark:text-white">
              {formatCurrency(cashAvailable)}
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
        {/*  LEFT PANE — Unapplied Cash                              */}
        {/* ============================================================ */}
        <ComponentCard
          title={`Unapplied Cash (${filteredCashEntries.length})`}
        >
          <div data-wc="apply-cash-left" className="p-2">
            {/* Filters */}
            <div className="flex flex-wrap items-center gap-2 mb-2 pb-2 border-b border-slate-200 dark:border-slate-700">
              <div className="relative flex-1 min-w-[140px]">
                <FaSearch className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400 text-xs" />
                <input
                  data-wc="apply-cash-search"
                  type="text"
                  placeholder="Search ref / customer..."
                  value={cashSearch}
                  onChange={(e) => setCashSearch(e.target.value)}
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
                onClick={loadCashEntries}
                disabled={loadingCashEntries}
                className="text-xs px-2 py-1 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700 rounded flex items-center gap-1"
                title="Refresh"
              >
                <FaSync className={loadingCashEntries ? 'animate-spin' : ''} />
              </button>
              <button
                onClick={() => setShowCashDialog(true)}
                className="text-xs px-2 py-1 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/30 rounded flex items-center gap-1"
                title="Record new cash"
              >
                <FaPlus /> New
              </button>
            </div>

            {/* Cash list */}
            {loadingCashEntries ? (
              <div className="flex items-center justify-center py-8 text-slate-400">
                <FaSpinner className="animate-spin mr-2" /> Loading cashEntries...
              </div>
            ) : filteredCashEntries.length === 0 ? (
              <div className="text-center py-8 text-slate-400 text-sm">
                No unapplied cash found
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
                    {filteredCashEntries.map((cash) => {
                      const isSelected = selectedCash?.id === cash.id;
                      const available = getCashAvailable(cash);
                      const custName =
                        cash.refs?.links?.org?.[0]?.display_name || '--';

                      return (
                        <tr
                          key={cash.id}
                          data-wc="apply-cash-row"
                          onClick={() => handleSelectCash(cash)}
                          className={`cursor-pointer border-t border-slate-200 dark:border-slate-700 transition-colors ${
                            isSelected
                              ? 'bg-blue-50 dark:bg-blue-900/20 ring-1 ring-blue-300 dark:ring-blue-700'
                              : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'
                          }`}
                        >
                          <td className="p-1.5 font-mono">
                            {cash.reference_number ||
                              cash.ida ||
                              `PAY-${cash.id}`}
                          </td>
                          <td className="p-1.5 text-slate-600 dark:text-slate-400 truncate max-w-[120px]">
                            {custName}
                          </td>
                          <td className="p-1.5 text-right font-mono font-medium text-green-600 dark:text-green-400">
                            {formatCurrency(available)}
                          </td>
                          <td className="p-1.5 text-right font-mono text-slate-500 dark:text-slate-500">
                            {formatCurrency(cash.amount)}
                          </td>
                          <td className="p-1.5 text-slate-600 dark:text-slate-400">
                            {formatDate(
                              cash.dt_cash || cash.dt_created,
                            )}
                          </td>
                          <td className="p-1.5 text-slate-600 dark:text-slate-400">
                            {cash.gateway || 'manual'}
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
        {/*  RIGHT PANE — Open Invoices for selected cash's customer   */}
        {/* ============================================================ */}
        <ComponentCard
          title={
            selectedCash
              ? `Open Invoices — ${selectedCustomerName} (${invoices.length})`
              : 'Open Invoices'
          }
        >
          <div data-wc="apply-cash-right" className="p-2">
            {!selectedCash ? (
              <div className="text-center py-12 text-slate-400 text-sm">
                Select a cash entry on the left to see open invoices
              </div>
            ) : (
              <>
                {/* Action bar */}
                <div className="flex flex-wrap items-center gap-2 mb-2 pb-2 border-b border-slate-200 dark:border-slate-700">
                  <button
                    onClick={handleAutoApply}
                    disabled={invoices.length === 0}
                    className="text-xs px-2 py-1 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 disabled:text-slate-400 disabled:hover:bg-transparent rounded flex items-center gap-1"
                    title="Apply to oldest invoices first until cash is exhausted"
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
                      data-wc="apply-cash-submit"
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
                              data-wc="apply-cash-invoice-row"
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
                                    data-wc="apply-cash-amount"
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
                          {/* Aggregate of server-provided invoice balances — no server-side aggregate available */}
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

      {/* ---- Make Cash Dialog ---- */}
      <CashDialog
        isOpen={showCashDialog}
        onClose={() => setShowCashDialog(false)}
        onCashAdded={() => {
          loadCashEntries();
        }}
      />
    </div>
  );
};

export default ApplyCash;
