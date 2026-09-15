/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * ApplyPaymentModal - Modal for applying a payment to an invoice
 * 
 * Used from InvoiceDetail to apply available payments to the current invoice
 */
import React, { useState, useEffect, useCallback } from 'react';
import { FaTimes, FaDollarSign, FaCheck, FaSpinner } from 'react-icons/fa';
import usePaymentApplication, { PaymentRecord, InvoiceRecord } from '../hooks/usePaymentApplication';
import { withDevIdentifier } from '@/components/common/DevIdentifier';
import { formatDt } from '@/utils/fieldFormatters';
import { formatCurrency } from '@/utils/stringUtils';

interface ApplyPaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
  invoice: InvoiceRecord;
  onPaymentApplied?: () => void;
}

const ApplyPaymentModal: React.FC<ApplyPaymentModalProps> = ({
  isOpen,
  onClose,
  invoice,
  onPaymentApplied
}) => {
  const {
    getAvailablePayments,
    applyPaymentToInvoice,
    getInvoiceBalance,
    getPaymentAvailable
  } = usePaymentApplication();

  const [payments, setPayments] = useState<PaymentRecord[]>([]);
  const [selectedPayment, setSelectedPayment] = useState<PaymentRecord | null>(null);
  const [applyAmount, setApplyAmount] = useState<string>('');
  const [applying, setApplying] = useState(false);
  const [loadingPayments, setLoadingPayments] = useState(false);

  // Get org_id from invoice
  const orgId = invoice.org_id || 
    invoice.refs?.links?.customer?.[0]?.id || 
    '';

  // Load available payments when modal opens
  useEffect(() => {
    if (isOpen && orgId) {
      setLoadingPayments(true);
      getAvailablePayments(orgId)
        .then(setPayments)
        .finally(() => setLoadingPayments(false));
    }
  }, [isOpen, orgId, getAvailablePayments]);

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setSelectedPayment(null);
      setApplyAmount('');
    }
  }, [isOpen]);

  // Calculate invoice balance
  const invoiceBalance = getInvoiceBalance(invoice);

  // Set default apply amount when payment selected
  useEffect(() => {
    if (selectedPayment) {
      const paymentAvailable = getPaymentAvailable(selectedPayment);
      const maxApply = Math.min(paymentAvailable, invoiceBalance);
      setApplyAmount(maxApply.toFixed(2));
    }
  }, [selectedPayment, invoiceBalance, getPaymentAvailable]);

  const handleApply = useCallback(async () => {
    if (!selectedPayment) return;

    const amount = parseFloat(applyAmount);
    if (isNaN(amount) || amount <= 0) {
      return;
    }

    setApplying(true);
    try {
      const result = await applyPaymentToInvoice(invoice.id, selectedPayment.id, amount);
      
      if (result.success) {
        onPaymentApplied?.();
        onClose();
      }
    } finally {
      setApplying(false);
    }
  }, [selectedPayment, applyAmount, invoice.id, applyPaymentToInvoice, onPaymentApplied, onClose]);


  // Format date
  const formatDate = (dateStr?: string | null): string => {
    if (!dateStr) return '--';
    return formatDt(dateStr, 'date');
  };

  if (!isOpen) return null;

  const paymentAvailable = selectedPayment ? getPaymentAvailable(selectedPayment) : 0;
  const applyAmountNum = parseFloat(applyAmount) || 0;
  const isValidAmount = applyAmountNum > 0 && 
    applyAmountNum <= paymentAvailable && 
    applyAmountNum <= invoiceBalance;

  return (
    <div className="fixed inset-0 z-[200000] flex items-center justify-center bg-black/30 px-4 py-6 backdrop-blur-sm">
      <div className="w-full max-w-2xl max-h-[calc(100vh-4rem)] overflow-y-auto rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-2">
            <FaDollarSign className="text-green-500" size={20} />
            <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
              Apply Payment to Invoice
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-full text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            disabled={applying}
          >
            <FaTimes size={16} />
          </button>
        </div>

        {/* Invoice Info */}
        <div className="p-4 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-slate-500 dark:text-slate-400">Invoice:</span>
              <span className="ml-2 font-mono font-medium text-slate-900 dark:text-white">
                {invoice.ida || invoice.invoice_no || `#${invoice.id}`}
              </span>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400">Total:</span>
              <span className="ml-2 font-mono text-slate-900 dark:text-white">
                {formatCurrency(invoice.totals?.total)}
              </span>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400">Paid:</span>
              <span className="ml-2 font-mono text-green-600 dark:text-green-400">
                {formatCurrency(invoice.amount_paid || invoice.totals?.received)}
              </span>
            </div>
            <div>
              <span className="text-slate-500 dark:text-slate-400">Balance:</span>
              <span className="ml-2 font-mono font-bold text-amber-600 dark:text-amber-400">
                {formatCurrency(invoiceBalance)}
              </span>
            </div>
          </div>
        </div>

        {/* Available Payments */}
        <div className="p-4">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300 mb-3">
            Available Payments
          </h3>
          
          {loadingPayments ? (
            <div className="flex items-center justify-center py-8 text-slate-400">
              <FaSpinner className="animate-spin mr-2" />
              Loading payments...
            </div>
          ) : payments.length === 0 ? (
            <div className="text-center py-8 text-slate-400">
              No available payments for this customer
            </div>
          ) : (
            <div className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-slate-100 dark:bg-slate-800">
                  <tr>
                    <th className="w-10 p-2"></th>
                    <th className="p-2 text-left font-medium text-slate-600 dark:text-slate-300">Reference</th>
                    <th className="p-2 text-right font-medium text-slate-600 dark:text-slate-300">Available</th>
                    <th className="p-2 text-right font-medium text-slate-600 dark:text-slate-300">Original</th>
                    <th className="p-2 text-left font-medium text-slate-600 dark:text-slate-300">Date</th>
                    <th className="p-2 text-left font-medium text-slate-600 dark:text-slate-300">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {payments.map((payment) => {
                    const available = getPaymentAvailable(payment);
                    const isSelected = selectedPayment?.id === payment.id;
                    
                    return (
                      <tr 
                        key={payment.id}
                        onClick={() => setSelectedPayment(payment)}
                        className={`cursor-pointer border-t border-slate-200 dark:border-slate-700 transition-colors ${
                          isSelected 
                            ? 'bg-blue-50 dark:bg-blue-900/20' 
                            : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'
                        }`}
                      >
                        <td className="p-2 text-center">
                          <input
                            type="radio"
                            checked={isSelected}
                            onChange={() => setSelectedPayment(payment)}
                            className="w-4 h-4 text-blue-600"
                          />
                        </td>
                        <td className="p-2 font-mono text-slate-900 dark:text-white">
                          {payment.reference_number || payment.ida || `PAY-${payment.id}`}
                        </td>
                        <td className="p-2 text-right font-mono font-medium text-green-600 dark:text-green-400">
                          {formatCurrency(available)}
                        </td>
                        <td className="p-2 text-right font-mono text-slate-600 dark:text-slate-400">
                          {formatCurrency(payment.amount)}
                        </td>
                        <td className="p-2 text-slate-600 dark:text-slate-400">
                          {formatDate(payment.dt_payment || payment.dt_created)}
                        </td>
                        <td className="p-2">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            payment.status === 'completed' 
                              ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                              : 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400'
                          }`}>
                            {payment.status || 'pending'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Apply Amount Input */}
        {selectedPayment && (
          <div className="p-4 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Amount to Apply
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">$</span>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    max={Math.min(paymentAvailable, invoiceBalance)}
                    value={applyAmount}
                    onChange={(e) => setApplyAmount(e.target.value)}
                    className="w-full pl-7 pr-4 py-2 border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-slate-900 dark:text-white font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                  Max: {formatCurrency(Math.min(paymentAvailable, invoiceBalance))}
                </div>
              </div>
              
              <div className="text-sm text-slate-600 dark:text-slate-400">
                <div>After apply:</div>
                <div className="font-mono">
                  Invoice: {formatCurrency(invoiceBalance - applyAmountNum)}
                </div>
                <div className="font-mono">
                  Payment: {formatCurrency(paymentAvailable - applyAmountNum)}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-3 p-4 border-t border-slate-200 dark:border-slate-700">
          <button
            onClick={onClose}
            disabled={applying}
            className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleApply}
            disabled={!selectedPayment || !isValidAmount || applying}
            className="px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:bg-slate-400 disabled:cursor-not-allowed rounded-lg transition-colors flex items-center gap-2"
          >
            {applying ? (
              <>
                <FaSpinner className="animate-spin" />
                Applying...
              </>
            ) : (
              <>
                <FaCheck />
                Apply {applyAmount ? formatCurrency(parseFloat(applyAmount)) : 'Payment'}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default withDevIdentifier(ApplyPaymentModal, 'ApplyPaymentModal', 'rose', 'apps/transactions/components/ApplyPaymentModal.tsx');