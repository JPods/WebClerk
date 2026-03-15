/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * ApplyPayments - Bulk Payment Application Page
 * 
 * Mirrors WC2's ApplyPayments form with:
 * - Customer search/filter
 * - Invoice list (unpaid invoices)
 * - Payment list (available payments)
 * - Apply payment to selected invoice(s)
 * - Auto-apply to oldest invoices
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useDispatch } from 'react-redux';
import { FaSearch, FaCheck, FaSync, FaTimes, FaSpinner, FaPlus } from 'react-icons/fa';
import PageBreadcrumb from '@/components/common/PageBreadCrumb';
import ComponentCard from '@/components/common/ComponentCard';
import { getRecords } from '@/api/wcapi';
import { showToast } from '@/store/slices/toastSlice';
import usePaymentApplication, { PaymentRecord, InvoiceRecord } from '../hooks/usePaymentApplication';
import PaymentDialog from '../components/PaymentDialog';

// Org search result type
interface OrgSearchResult {
  id: number;
  display_name: string;
  ida?: string;
  email?: string | null;
  phone?: string | null;
}

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

  // State
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedOrg, setSelectedOrg] = useState<OrgSearchResult | null>(null);
  const [orgResults, setOrgResults] = useState<OrgSearchResult[]>([]);
  const [searchingOrgs, setSearchingOrgs] = useState(false);
  const [showAllInvoices, setShowAllInvoices] = useState(false);

  const [invoices, setInvoices] = useState<InvoiceRecord[]>([]);
  const [payments, setPayments] = useState<PaymentRecord[]>([]);
  const [loadingData, setLoadingData] = useState(false);

  const [selectedInvoices, setSelectedInvoices] = useState<Set<number>>(new Set());
  const [selectedPayment, setSelectedPayment] = useState<PaymentRecord | null>(null);
  const [applyAmount, setApplyAmount] = useState<string>('');
  const [applying, setApplying] = useState(false);
  const [showPaymentDialog, setShowPaymentDialog] = useState(false);

  // Search for customers/orgs
  const searchOrgs = useCallback(async (query: string) => {
    if (!query || query.length < 2) {
      setOrgResults([]);
      return;
    }

    setSearchingOrgs(true);
    try {
      const trimmed = query.trim();
      const result = await getRecords('customer', {
        limit: 20,
        is_active: true,
        // Be generous with search params; different deployments may key off different names
        search: trimmed,
        q: trimmed,
        keywords: trimmed,
        display_name: trimmed,
      });

      const records: any[] = result?.results || result?.items || [];
      setOrgResults(
        records.map((r: any) => ({
          id: r.id,
          display_name: r.display_name || r.company || r.name || `#${r.id}`,
          ida: r.ida,
          email: r.email,
          phone: r.phone,
        })),
      );
    } catch (err) {
      console.error('Failed to search orgs:', err);
      setOrgResults([]);
    } finally {
      setSearchingOrgs(false);
    }
  }, []);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchQuery && !selectedOrg) {
        searchOrgs(searchQuery);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery, selectedOrg, searchOrgs]);

  // Load invoices and payments when org selected
  useEffect(() => {
    if (selectedOrg) {
      loadCustomerData(String(selectedOrg.id));
    } else {
      setInvoices([]);
      setPayments([]);
      setSelectedInvoices(new Set());
      setSelectedPayment(null);
    }
  }, [selectedOrg]);

  const loadCustomerData = useCallback(async (orgId: string) => {
    setLoadingData(true);
    try {
      const [invoiceData, paymentData] = await Promise.all([
        getUnpaidInvoices(orgId),
        getAvailablePayments(orgId)
      ]);
      setInvoices(invoiceData);
      setPayments(paymentData);
    } finally {
      setLoadingData(false);
    }
  }, [getUnpaidInvoices, getAvailablePayments]);

  // Handle org selection
  const handleSelectOrg = (org: OrgSearchResult) => {
    setSelectedOrg(org);
    setSearchQuery(org.display_name);
    setOrgResults([]);
  };

  // Handle clearing org selection
  const handleClearOrg = () => {
    setSelectedOrg(null);
    setSearchQuery('');
    setOrgResults([]);
  };

  // Toggle invoice selection
  const toggleInvoiceSelection = (invoiceId: number) => {
    setSelectedInvoices(prev => {
      const next = new Set(prev);
      if (next.has(invoiceId)) {
        next.delete(invoiceId);
      } else {
        next.add(invoiceId);
      }
      return next;
    });
  };

  // Select all invoices
  const selectAllInvoices = () => {
    setSelectedInvoices(new Set(invoices.map(inv => inv.id)));
  };

  // Clear invoice selection
  const clearInvoiceSelection = () => {
    setSelectedInvoices(new Set());
  };

  // Calculate totals
  const selectedInvoiceTotal = useMemo(() => {
    return invoices
      .filter(inv => selectedInvoices.has(inv.id))
      .reduce((sum, inv) => sum + getInvoiceBalance(inv), 0);
  }, [invoices, selectedInvoices, getInvoiceBalance]);

  const paymentAvailable = selectedPayment ? getPaymentAvailable(selectedPayment) : 0;

  // Update apply amount when selection changes
  useEffect(() => {
    if (selectedPayment && selectedInvoices.size > 0) {
      const maxApply = Math.min(paymentAvailable, selectedInvoiceTotal);
      setApplyAmount(maxApply.toFixed(2));
    } else {
      setApplyAmount('');
    }
  }, [selectedPayment, selectedInvoices, paymentAvailable, selectedInvoiceTotal]);

  // Apply payment to selected invoices
  const handleApplyToSelected = useCallback(async () => {
    if (!selectedPayment || selectedInvoices.size === 0) return;

    setApplying(true);
    try {
      let remainingAmount = parseFloat(applyAmount) || paymentAvailable;
      const sortedInvoices = invoices
        .filter(inv => selectedInvoices.has(inv.id))
        .sort((a, b) => new Date(a.dt_created || 0).getTime() - new Date(b.dt_created || 0).getTime());

      let appliedCount = 0;
      for (const invoice of sortedInvoices) {
        if (remainingAmount <= 0) break;

        const balance = getInvoiceBalance(invoice);
        const toApply = Math.min(remainingAmount, balance);

        if (toApply > 0) {
          const result = await applyPaymentToInvoice(invoice.id, selectedPayment.id, toApply);
          if (result.success) {
            remainingAmount -= result.amount_applied;
            appliedCount++;
          }
        }
      }

      if (appliedCount > 0) {
        dispatch(showToast({
          message: `Applied payment to ${appliedCount} invoice(s)`,
          type: 'success'
        }));
        // Refresh data
        if (selectedOrg) {
          await loadCustomerData(selectedOrg.id);
        }
        setSelectedInvoices(new Set());
        setSelectedPayment(null);
      }
    } finally {
      setApplying(false);
    }
  }, [selectedPayment, selectedInvoices, applyAmount, paymentAvailable, invoices, getInvoiceBalance, applyPaymentToInvoice, dispatch, selectedOrg, loadCustomerData]);

  // Auto-apply to oldest invoices
  const handleAutoApply = useCallback(async () => {
    if (!selectedPayment) return;

    setApplying(true);
    try {
      let remainingAmount = paymentAvailable;
      const sortedInvoices = [...invoices].sort(
        (a, b) => new Date(a.dt_created || 0).getTime() - new Date(b.dt_created || 0).getTime()
      );

      let appliedCount = 0;
      for (const invoice of sortedInvoices) {
        if (remainingAmount <= 0) break;

        const balance = getInvoiceBalance(invoice);
        const toApply = Math.min(remainingAmount, balance);

        if (toApply > 0) {
          const result = await applyPaymentToInvoice(invoice.id, selectedPayment.id, toApply);
          if (result.success) {
            remainingAmount -= result.amount_applied;
            appliedCount++;
          }
        }
      }

      if (appliedCount > 0) {
        dispatch(showToast({
          message: `Auto-applied to ${appliedCount} oldest invoice(s)`,
          type: 'success'
        }));
        // Refresh data
        if (selectedOrg) {
          await loadCustomerData(selectedOrg.id);
        }
        setSelectedPayment(null);
      }
    } finally {
      setApplying(false);
    }
  }, [selectedPayment, paymentAvailable, invoices, getInvoiceBalance, applyPaymentToInvoice, dispatch, selectedOrg, loadCustomerData]);

  // Format helpers
  const formatCurrency = (value: number | undefined | null): string => {
    if (value == null) return '$0.00';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
  };

  const formatDate = (dateStr?: string | null): string => {
    if (!dateStr) return '--';
    return new Date(dateStr).toLocaleDateString();
  };

  return (
    <div className="p-4 space-y-4">
      <PageBreadcrumb pageTitle="Apply Payments" />

      {/* Customer Search */}
      <ComponentCard title="Customer Selection">
        <div className="p-4">
          <div className="flex items-center gap-4">
            <div className="relative flex-1 max-w-md">
              <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search customer by name, ID, or phone..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  if (selectedOrg) setSelectedOrg(null);
                }}
                className="w-full pl-10 pr-10 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              />
              {selectedOrg && (
                <button
                  onClick={handleClearOrg}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  <FaTimes />
                </button>
              )}

              {/* Search Results Dropdown */}
              {orgResults.length > 0 && !selectedOrg && (
                <div className="absolute z-50 w-full mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                  {orgResults.map((org) => (
                    <div
                      key={org.id}
                      onClick={() => handleSelectOrg(org)}
                      className="px-4 py-2 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700 border-b border-slate-100 dark:border-slate-700 last:border-b-0"
                    >
                      <div className="font-medium text-slate-900 dark:text-white">
                        {org.display_name}
                      </div>
                      <div className="text-xs text-slate-500 dark:text-slate-400">
                        {org.ida && <span className="mr-3">ID: {org.ida}</span>}
                        {org.phone && <span className="mr-3">{org.phone}</span>}
                        {org.email && <span>{org.email}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {searchingOrgs && <FaSpinner className="animate-spin text-slate-400" />}

            {selectedOrg && (
              <div className="flex items-center gap-2 px-3 py-1 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                <span className="text-sm font-medium text-blue-700 dark:text-blue-300">
                  {selectedOrg.display_name}
                </span>
                {selectedOrg.ida && (
                  <span className="text-xs text-blue-600 dark:text-blue-400">
                    ({selectedOrg.ida})
                  </span>
                )}
              </div>
            )}

            <label className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
              <input
                type="checkbox"
                checked={showAllInvoices}
                onChange={(e) => setShowAllInvoices(e.target.checked)}
                className="rounded"
              />
              Show All (include paid)
            </label>
          </div>
        </div>
      </ComponentCard>

      {selectedOrg && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Invoices Panel */}
          <ComponentCard title={`Unpaid Invoices (${invoices.length})`}>
            <div className="p-2">
              {/* Invoice Actions */}
              <div className="flex items-center gap-2 mb-2 pb-2 border-b border-slate-200 dark:border-slate-700">
                <button
                  onClick={selectAllInvoices}
                  className="text-xs px-2 py-1 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded"
                >
                  Select All
                </button>
                <button
                  onClick={clearInvoiceSelection}
                  className="text-xs px-2 py-1 text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 rounded"
                >
                  Clear
                </button>
                {selectedInvoices.size > 0 && (
                  <span className="text-xs text-slate-500 dark:text-slate-400">
                    {selectedInvoices.size} selected = {formatCurrency(selectedInvoiceTotal)}
                  </span>
                )}
              </div>

              {/* Invoice List */}
              {loadingData ? (
                <div className="flex items-center justify-center py-8 text-slate-400">
                  <FaSpinner className="animate-spin mr-2" />
                  Loading invoices...
                </div>
              ) : invoices.length === 0 ? (
                <div className="text-center py-8 text-slate-400">
                  No unpaid invoices
                </div>
              ) : (
                <div className="overflow-x-auto max-h-80 overflow-y-auto">
                  <table className="w-full text-xs">
                    <thead className="bg-slate-100 dark:bg-slate-800 sticky top-0">
                      <tr>
                        <th className="w-8 p-1"></th>
                        <th className="p-1 text-left font-medium">Invoice</th>
                        <th className="p-1 text-right font-medium">Balance</th>
                        <th className="p-1 text-right font-medium">Total</th>
                        <th className="p-1 text-center font-medium">Days</th>
                        <th className="p-1 text-left font-medium">Terms</th>
                        <th className="p-1 text-left font-medium">Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {invoices.map((invoice) => {
                        const isSelected = selectedInvoices.has(invoice.id);
                        const balance = getInvoiceBalance(invoice);
                        const daysPastDue = calculateDaysPastDue(invoice);
                        
                        return (
                          <tr
                            key={invoice.id}
                            onClick={() => toggleInvoiceSelection(invoice.id)}
                            className={`cursor-pointer border-t border-slate-200 dark:border-slate-700 ${
                              isSelected ? 'bg-blue-50 dark:bg-blue-900/20' : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'
                            }`}
                          >
                            <td className="p-1 text-center">
                              <input
                                type="checkbox"
                                checked={isSelected}
                                onChange={() => toggleInvoiceSelection(invoice.id)}
                                className="w-3 h-3"
                              />
                            </td>
                            <td className="p-1 font-mono">
                              {invoice.ida || invoice.invoice_no || `#${invoice.id}`}
                            </td>
                            <td className="p-1 text-right font-mono font-medium text-amber-600 dark:text-amber-400">
                              {formatCurrency(balance)}
                            </td>
                            <td className="p-1 text-right font-mono text-slate-600 dark:text-slate-400">
                              {formatCurrency(invoice.totals?.total)}
                            </td>
                            <td className="p-1 text-center">
                              <span className={`px-1 rounded ${
                                daysPastDue > 60 ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' :
                                daysPastDue > 30 ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400' :
                                daysPastDue > 0 ? 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400' :
                                'text-slate-600 dark:text-slate-400'
                              }`}>
                                {daysPastDue}
                              </span>
                            </td>
                            <td className="p-1 text-slate-600 dark:text-slate-400">
                              {invoice.terms || '--'}
                            </td>
                            <td className="p-1 text-slate-600 dark:text-slate-400">
                              {formatDate(invoice.dt || invoice.dt_created)}
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

          {/* Payments Panel */}
          <ComponentCard title={`Available Payments (${payments.length})`}>
            <div className="p-2">
              {/* Refresh button */}
              <div className="flex items-center gap-2 mb-2 pb-2 border-b border-slate-200 dark:border-slate-700">
                <button
                  onClick={() => selectedOrg && loadCustomerData(selectedOrg.id)}
                  disabled={loadingData}
                  className="text-xs px-2 py-1 text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 rounded flex items-center gap-1"
                >
                  <FaSync className={loadingData ? 'animate-spin' : ''} />
                  Refresh
                </button>
                <button
                  onClick={() => setShowPaymentDialog(true)}
                  className="text-xs px-2 py-1 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/30 rounded flex items-center gap-1"
                >
                  <FaPlus />
                  Make Payment
                </button>
                {selectedPayment && (
                  <span className="text-xs text-green-600 dark:text-green-400">
                    Selected: {formatCurrency(paymentAvailable)} available
                  </span>
                )}
              </div>

              {/* Payment List */}
              {loadingData ? (
                <div className="flex items-center justify-center py-8 text-slate-400">
                  <FaSpinner className="animate-spin mr-2" />
                  Loading payments...
                </div>
              ) : payments.length === 0 ? (
                <div className="text-center py-8 text-slate-400">
                  No available payments
                </div>
              ) : (
                <div className="overflow-x-auto max-h-80 overflow-y-auto">
                  <table className="w-full text-xs">
                    <thead className="bg-slate-100 dark:bg-slate-800 sticky top-0">
                      <tr>
                        <th className="w-8 p-1"></th>
                        <th className="p-1 text-left font-medium">Reference</th>
                        <th className="p-1 text-right font-medium">Available</th>
                        <th className="p-1 text-right font-medium">Original</th>
                        <th className="p-1 text-left font-medium">Date</th>
                        <th className="p-1 text-left font-medium">Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      {payments.map((payment) => {
                        const isSelected = selectedPayment?.id === payment.id;
                        const available = getPaymentAvailable(payment);
                        
                        return (
                          <tr
                            key={payment.id}
                            onClick={() => setSelectedPayment(payment)}
                            className={`cursor-pointer border-t border-slate-200 dark:border-slate-700 ${
                              isSelected ? 'bg-green-50 dark:bg-green-900/20' : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'
                            }`}
                          >
                            <td className="p-1 text-center">
                              <input
                                type="radio"
                                checked={isSelected}
                                onChange={() => setSelectedPayment(payment)}
                                className="w-3 h-3"
                              />
                            </td>
                            <td className="p-1 font-mono">
                              {payment.reference_number || payment.ida || `PAY-${payment.id}`}
                            </td>
                            <td className="p-1 text-right font-mono font-medium text-green-600 dark:text-green-400">
                              {formatCurrency(available)}
                            </td>
                            <td className="p-1 text-right font-mono text-slate-600 dark:text-slate-400">
                              {formatCurrency(payment.amount)}
                            </td>
                            <td className="p-1 text-slate-600 dark:text-slate-400">
                              {formatDate(payment.dt_payment || payment.dt_created)}
                            </td>
                            <td className="p-1 text-slate-600 dark:text-slate-400">
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
        </div>
      )}

      {/* Apply Actions */}
      {selectedOrg && (
        <ComponentCard title="Apply Payment">
          <div className="p-4">
            <div className="flex flex-wrap items-center gap-4">
              {/* Amount Input */}
              <div className="flex items-center gap-2">
                <label className="text-sm text-slate-600 dark:text-slate-400">Amount:</label>
                <div className="relative">
                  <span className="absolute left-2 top-1/2 -translate-y-1/2 text-slate-400">$</span>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={applyAmount}
                    onChange={(e) => setApplyAmount(e.target.value)}
                    disabled={!selectedPayment}
                    className="w-32 pl-6 pr-2 py-1 border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 text-slate-900 dark:text-white font-mono text-sm disabled:bg-slate-100 dark:disabled:bg-slate-800"
                  />
                </div>
              </div>

              {/* Summary */}
              <div className="text-sm text-slate-600 dark:text-slate-400">
                Invoice(s): {formatCurrency(selectedInvoiceTotal)} |
                Payment: {formatCurrency(paymentAvailable)}
              </div>

              {/* Actions */}
              <div className="flex gap-2 ml-auto">
                <button
                  onClick={handleApplyToSelected}
                  disabled={!selectedPayment || selectedInvoices.size === 0 || applying}
                  className="px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:bg-slate-400 disabled:cursor-not-allowed rounded-lg transition-colors flex items-center gap-2"
                >
                  {applying ? <FaSpinner className="animate-spin" /> : <FaCheck />}
                  Apply to Selected
                </button>

                <button
                  onClick={handleAutoApply}
                  disabled={!selectedPayment || invoices.length === 0 || applying}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 disabled:cursor-not-allowed rounded-lg transition-colors flex items-center gap-2"
                >
                  {applying ? <FaSpinner className="animate-spin" /> : <FaSync />}
                  Auto-Apply Oldest
                </button>
              </div>
            </div>
          </div>
        </ComponentCard>
      )}
      
      {/* Make Payment Dialog */}
      <PaymentDialog
        isOpen={showPaymentDialog}
        onClose={() => setShowPaymentDialog(false)}
        customer_id={selectedOrg?.id}
        customer_name={selectedOrg?.display_name}
        onPaymentAdded={() => {
          if (selectedOrg) loadCustomerData(String(selectedOrg.id));
        }}
      />
    </div>
  );
};

export default ApplyPayments;
