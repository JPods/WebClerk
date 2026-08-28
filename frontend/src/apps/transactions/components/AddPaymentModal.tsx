/* LastChecked: 2026-08-21 | WhereUsed: TransactionDetail toolbar | WhoCreated: Claude */
/**
 * PaymentCard — Enter a new payment or apply an existing one.
 *
 * Top:    Payment entry fields (amount, method, reference, date, notes)
 * Bottom: Panel of available payments from this customer — click to apply
 *
 * From an Order: enter payment → amount = available (not yet applied to invoice)
 * From an Invoice: enter new OR pick existing → applies via PendingPaymentApplication
 */
import React, { useState, useEffect, useCallback } from 'react';
import { FaTimes, FaDollarSign, FaCheck, FaSpinner } from 'react-icons/fa';
import { useDispatch } from 'react-redux';
import { getRecords, saveRecord, manageAction } from '@/api/wcapi';
import { showToast } from '@/store/slices/toastSlice';
import { formatDt } from '@/utils/fieldFormatters';
import { withDevIdentifier } from '@/components/common/DevIdentifier';
import { formatCurrency } from '@/utils/stringUtils';

interface PaymentMethod {
  id: number;
  name: string;
  is_active: boolean;
}

interface AvailablePayment {
  id: number;
  ida?: string;
  amount: number;
  available?: number;
  reference_number?: string;
  status?: string;
  method?: string;
  dt_created?: string;
  dt_payment?: string;
  parent_id?: number;
  parent_model?: string;
}

interface AddPaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
  order_id?: number;
  invoice_id?: number;
  customer_id?: number | null;
  contact_id?: number | null;
  customer_name?: string;
  orderTotal?: number;
  onPaymentAdded?: () => void;
  /** Default type — 'received' from invoice/order, 'expense' from dashboard */
  defaultType?: 'received' | 'expense';
}


const AddPaymentModal: React.FC<AddPaymentModalProps> = ({
  isOpen,
  onClose,
  order_id,
  invoice_id,
  customer_id,
  contact_id,
  customer_name,
  orderTotal,
  onPaymentAdded,
}) => {
  const dispatch = useDispatch();

  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [availablePayments, setAvailablePayments] = useState<AvailablePayment[]>([]);
  const [loadingPayments, setLoadingPayments] = useState(false);
  const [saving, setSaving] = useState(false);

  // New payment form state
  const [amount, setAmount] = useState('');
  const [paymentMethodId, setPaymentMethodId] = useState<number | null>(null);
  const [referenceNumber, setReferenceNumber] = useState('');
  const [notes, setNotes] = useState('');
  const [paymentDate, setPaymentDate] = useState(() =>
    new Date().toISOString().split('T')[0]
  );

  // Apply existing payment state
  const [selectedPayment, setSelectedPayment] = useState<AvailablePayment | null>(null);
  const [applyAmount, setApplyAmount] = useState('');

  // Adjustment controls
  const [discountPct, setDiscountPct] = useState('');
  const [discountAmt, setDiscountAmt] = useState('');
  const [dismissBalance, setDismissBalance] = useState(false);

  // Load payment methods + available payments when modal opens
  useEffect(() => {
    if (!isOpen) return;

    getRecords('paymentmethod', { is_active: true, limit: 50 })
      .then((response) => {
        const methods = response?.results || response || [];
        setPaymentMethods(methods);
        if (methods.length > 0 && !paymentMethodId) {
          setPaymentMethodId(methods[0].id);
        }
      })
      .catch(console.error);

    // Load available payments for this customer (invoice or order context)
    if ((invoice_id || order_id) && customer_id) {
      setLoadingPayments(true);
      getRecords('payment', {
        customer_id: customer_id,
        status: 'completed',
        limit: 50,
      })
        .then((response) => {
          const payments = (response?.results || response || []) as AvailablePayment[];
          // Filter to payments with available balance != 0
          const withBalance = payments.filter((p) => {
            const avail = p.available ?? p.amount ?? 0;
            return avail !== 0;
          });
          setAvailablePayments(withBalance);
        })
        .catch(console.error)
        .finally(() => setLoadingPayments(false));
    }
  }, [isOpen, customer_id, invoice_id, order_id]);

  // Reset form when modal closes
  useEffect(() => {
    if (!isOpen) {
      setAmount('');
      setReferenceNumber('');
      setNotes('');
      setPaymentDate(new Date().toISOString().split('T')[0]);
      setSelectedPayment(null);
      setApplyAmount('');
      setDiscountPct('');
      setDiscountAmt('');
      setDismissBalance(false);
    }
  }, [isOpen]);

  // Load prior payments for this order/invoice and compute received total
  const [priorReceived, setPriorReceived] = useState(0);
  useEffect(() => {
    if (!isOpen) { setPriorReceived(0); return; }
    // json.path.value — read totals.received from the transaction envelope
    const fetchPrior = async () => {
      try {
        const model = invoice_id ? 'invoice' : order_id ? 'order' : null;
        const id = invoice_id || order_id;
        if (model && id) {
          const res = await getRecords(model, { id, limit: 1 });
          const record = (res?.results || [])[0];
          const received = record?.totals?.received ?? 0;
          setPriorReceived(Number(received));
        }
      } catch { /* ignore */ }
    };
    fetchPrior();
  }, [isOpen, order_id, invoice_id]);

  // Effective balance: for invoices, orderTotal is already the balance (passed as
  // totals.balance from TransactionDetail). For orders, it's the full total.
  const effectiveBalance = invoice_id
    ? (orderTotal ?? 0)                    // already net of received
    : (orderTotal ?? 0) - priorReceived;   // full total minus what's been paid

  // Default amount = balance due. Update whenever priorReceived changes (async load).
  const [amountTouched, setAmountTouched] = useState(false);
  useEffect(() => {
    if (!isOpen) { setAmountTouched(false); return; }
    if (!amountTouched && effectiveBalance > 0) {
      setAmount(effectiveBalance.toFixed(2));
    }
  }, [isOpen, effectiveBalance, amountTouched]);

  // When selecting an existing payment, default apply amount to min(available, balance)
  useEffect(() => {
    if (selectedPayment) {
      const avail = selectedPayment.available ?? selectedPayment.amount ?? 0;
      const balance = orderTotal ?? 0;
      setApplyAmount(Math.min(avail, balance).toFixed(2));
    }
  }, [selectedPayment, orderTotal]);

  // ── Save new payment ──────────────────────────────────────────────
  const handleSaveNew = useCallback(async () => {
    if (!amount || parseFloat(amount) <= 0) {
      dispatch(showToast({ message: 'Enter a valid amount', type: 'error' }));
      return;
    }

    setSaving(true);
    try {
      // parent_id/parent_model = where this payment was entered
      const parentModel = invoice_id ? 'invoice' : order_id ? 'order' : customer_id ? 'customer' : '';
      const parentId = invoice_id || order_id || customer_id || null;

      const paymentData: Record<string, unknown> = {
        amount: parseFloat(amount),
        contact_id,
        customer_id: customer_id || null,
        dt_payment: new Date(paymentDate).toISOString(),
        paymentmethod_id: paymentMethodId,
        reference_number: referenceNumber,
        notes,
        status: 'completed',
        gateway: 'manual',
        parent_id: parentId,
        parent_model: parentModel,
        refs: {
          order_ids: order_id ? [order_id] : [],
          invoice_ids: invoice_id ? [invoice_id] : [],
          customer_id: customer_id || null,
          contact_id: contact_id || null,
          source: { type: parentModel, id: parentId },
        },
      };
      if (invoice_id) paymentData.invoice_id = invoice_id;

      const saved = await saveRecord('payment', paymentData) as any;
      const newPaymentId = saved?.record?.id || saved?.id;

      // If from an invoice, apply the payment immediately (with adjustments)
      if (invoice_id && newPaymentId) {
        const applyParams: Record<string, unknown> = {
          payment_id: newPaymentId,
          invoice_id: invoice_id,
          amount: parseFloat(amount),
        };
        if (dismissBalance) {
          applyParams.dismiss_balance = true;
        }
        await manageAction('apply_payment_to_invoice', applyParams);

        const parts = [`Payment of ${formatCurrency(parseFloat(amount))} applied`];
        if (dismissBalance) parts.push('balance dismissed (write-off payment)');
        dispatch(showToast({
          message: parts.join(' + '),
          type: 'success',
        }));
      } else if (order_id) {
        // Update order totals.received and balance
        try {
          const payAmt = parseFloat(amount);
          await manageAction('recalculate_totals', {
            transaction_id: order_id,
            model_name: 'order',
          });
        } catch { /* best effort */ }
        dispatch(showToast({
          message: `Payment of ${formatCurrency(parseFloat(amount))} recorded against order`,
          type: 'success',
        }));
      } else {
        dispatch(showToast({
          message: `Payment of ${formatCurrency(parseFloat(amount))} recorded`,
          type: 'success',
        }));
      }
      onPaymentAdded?.();
      onClose();
    } catch (error: any) {
      const msg = error.response?.data?.detail || error.response?.data?.message || 'Failed to create payment';
      dispatch(showToast({ message: msg, type: 'error' }));
    } finally {
      setSaving(false);
    }
  }, [amount, contact_id, customer_id, paymentDate, paymentMethodId, referenceNumber, notes, order_id, invoice_id, dispatch, onPaymentAdded, onClose]);

  // ── Apply existing payment ────────────────────────────────────────
  const handleApplyExisting = useCallback(async () => {
    if (!selectedPayment || !invoice_id) return;
    const amt = parseFloat(applyAmount);
    if (isNaN(amt) || amt <= 0) return;

    setSaving(true);
    try {
      await manageAction('apply_payment_to_invoice', {
        payment_id: selectedPayment.id,
        invoice_id: invoice_id,
        amount: amt,
      });
      dispatch(showToast({
        message: `Applied ${formatCurrency(amt)} from ${selectedPayment.reference_number || selectedPayment.ida || `#${selectedPayment.id}`}`,
        type: 'success',
      }));
      onPaymentAdded?.();
      onClose();
    } catch (error: any) {
      const msg = error.response?.data?.error || error.message || 'Failed to apply payment';
      dispatch(showToast({ message: msg, type: 'error' }));
    } finally {
      setSaving(false);
    }
  }, [selectedPayment, invoice_id, applyAmount, dispatch, onPaymentAdded, onClose]);

  if (!isOpen) return null;

  const applyAmountNum = parseFloat(applyAmount) || 0;
  const selectedAvail = selectedPayment
    ? (selectedPayment.available ?? 0)
    : 0;
  const isValidApply = selectedPayment && applyAmountNum > 0
    && applyAmountNum <= selectedAvail
    && applyAmountNum <= (orderTotal ?? Infinity);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      <div className="relative bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[calc(100vh-4rem)] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <FaDollarSign className="text-green-500" />
            Enter Payment
          </h2>
          <div className="flex items-center gap-3">
            {customer_name && (
              <span className="text-sm text-slate-500 dark:text-slate-400">{customer_name}</span>
            )}
            {orderTotal != null && (
              <span className="text-sm font-mono text-slate-600 dark:text-slate-300">
                {formatCurrency(effectiveBalance)}
              </span>
            )}
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700"
            >
              <FaTimes size={18} />
            </button>
          </div>
        </div>

        {/* Text fields — top */}
        <div className="px-6 py-3 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            {/* Payment Method */}
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Method</label>
              <select data-wc="select"
                value={paymentMethodId || ''}
                onChange={(e) => setPaymentMethodId(e.target.value ? parseInt(e.target.value) : null)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              >
                <option value="">Select...</option>
                {paymentMethods.map((m) => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
            </div>

            {/* Date */}
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Date</label>
              <input
                type="date" value={paymentDate}
                onChange={(e) => setPaymentDate(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              />
            </div>

            {/* Reference */}
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Reference / Check #</label>
              <input
                type="text" value={referenceNumber}
                onChange={(e) => setReferenceNumber(e.target.value)}
                placeholder="Check #, trans ID..."
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              />
            </div>

            {/* Notes */}
            <div>
              <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Notes</label>
              <input
                type="text" value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Optional..."
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
              />
            </div>
          </div>
        </div>

        {/* Numbers block — amount, dismiss, summary, button */}
        <div className="px-6 pb-4 space-y-2">
          {(() => {
            const invoiceDue = effectiveBalance;
            const payAmt = parseFloat(amount) || 0;
            const remainder = invoiceDue - payAmt;
            const finalBal = dismissBalance ? 0 : Math.max(0, remainder);

            return (
              <>
                {/* Bal Due + Amount — side by side */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Balance Due</label>
                    <div className={`px-3 py-2 rounded-lg border text-sm font-medium font-mono ${
                      invoiceDue > 0
                        ? 'border-red-300 text-red-600 bg-red-50 dark:border-red-700 dark:text-red-400 dark:bg-red-900/20'
                        : 'border-green-300 text-green-600 bg-green-50 dark:border-green-700 dark:text-green-400 dark:bg-green-900/20'
                    }`}>
                      {formatCurrency(invoiceDue)}
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">Amount</label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">$</span>
                      <input
                        type="number" step="0.01" min="0"
                        value={amount}
                        onChange={(e) => { setAmount(e.target.value); setAmountTouched(true); setSelectedPayment(null); }}
                        placeholder="0.00"
                        className="w-full pl-7 pr-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                      />
                    </div>
                  </div>
                </div>

                {/* Dismiss row */}
                <label className="flex items-center gap-1.5 cursor-pointer" title="Creates a write-off payment for the remaining balance">
                  <input
                    type="checkbox"
                    checked={dismissBalance}
                    onChange={(e) => setDismissBalance(e.target.checked)}
                    className="w-4 h-4 rounded border-slate-300 text-amber-600 focus:ring-amber-500"
                  />
                  <span className="text-xs text-slate-500 dark:text-slate-400">Dismiss balance — too little value to chase</span>
                </label>

                {/* Live summary — immediately below the numbers */}
                {(invoice_id || order_id) && (
                  <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 p-3 text-sm font-mono space-y-1">
                    {priorReceived > 0 && (
                      <>
                        <div className="flex justify-between">
                          <span className="text-slate-500">{invoice_id ? 'Invoice' : 'Order'} total</span>
                          <span className="text-slate-900 dark:text-white">{formatCurrency(orderTotal)}</span>
                        </div>
                        <div className="flex justify-between text-green-600">
                          <span>Received</span>
                          <span>-{formatCurrency(priorReceived)}</span>
                        </div>
                      </>
                    )}
                    <div className="flex justify-between">
                      <span className="text-slate-500">{priorReceived > 0 ? 'Balance due' : (invoice_id ? 'Invoice due' : 'Order due')}</span>
                      <span className="text-slate-900 dark:text-white">{formatCurrency(invoiceDue)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Payment</span>
                      <span className="text-slate-900 dark:text-white">-{formatCurrency(payAmt)}</span>
                    </div>
                    {remainder > 0 && dismissBalance && (
                      <div className="flex justify-between text-amber-600">
                        <span>Write-off — separate payment</span>
                        <span>-{formatCurrency(remainder)}</span>
                      </div>
                    )}
                    <div className="flex justify-between border-t border-slate-300 dark:border-slate-600 pt-1 font-semibold">
                      <span className={finalBal === 0 ? 'text-green-700' : 'text-red-600'}>
                        {finalBal === 0 ? 'Paid in full' : 'Remaining'}
                      </span>
                      <span className={finalBal === 0 ? 'text-green-700' : 'text-red-600'}>
                        {formatCurrency(finalBal)}
                      </span>
                    </div>
                  </div>
                )}

                {/* Button — right after the numbers */}
                <button
                  onClick={handleSaveNew}
                  disabled={saving || !amount || parseFloat(amount) <= 0 || !!selectedPayment}
                  className="w-full px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 disabled:bg-slate-400 disabled:cursor-not-allowed rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  {saving && !selectedPayment ? (
                    <><FaSpinner className="animate-spin" size={14} /> Saving...</>
                  ) : (
                    <><FaCheck size={14} /> Enter Payment {amount ? formatCurrency(parseFloat(amount)) : ''}</>
                  )}
                </button>
              </>
            );
          })()}
        </div>

        {/* Available payments panel — invoice context only */}
        {(invoice_id || order_id) && (
          <div className="border-t border-slate-200 dark:border-slate-700">
            <div className="px-6 py-3">
              <h3 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Available Payments from {customer_name || 'Customer'}
              </h3>
            </div>

            {loadingPayments ? (
              <div className="flex items-center justify-center py-6 text-slate-400 text-sm">
                <FaSpinner className="animate-spin mr-2" /> Loading...
              </div>
            ) : availablePayments.length === 0 ? (
              <div className="text-center py-6 text-slate-400 text-sm">
                No available payments
              </div>
            ) : (
              <div className="px-6 pb-2">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-xs text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">
                      <th className="py-1 text-left font-medium">Reference</th>
                      <th className="py-1 text-left font-medium">Source</th>
                      <th className="py-1 text-right font-medium">Available</th>
                      <th className="py-1 text-right font-medium">Original</th>
                      <th className="py-1 text-left font-medium">Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {availablePayments.map((p) => {
                      const avail = p.available ?? p.amount ?? 0;
                      const isSelected = selectedPayment?.id === p.id;
                      const pm = p.parent_model || '';
                      const pid = p.parent_id || '';
                      // Highlight if this payment was entered on the current document
                      const isThisDoc = (pm === 'order' && pid === order_id) || (pm === 'invoice' && pid === invoice_id);
                      const sourceLabel = pm === 'customer' ? 'Customer'
                        : pm === 'order' ? `Order #${pid}`
                        : pm === 'invoice' ? `Inv #${pid}`
                        : pm ? `${pm} #${pid}` : '—';
                      return (
                        <tr
                          key={p.id}
                          onClick={() => {
                            setSelectedPayment(isSelected ? null : p);
                            if (isSelected) setApplyAmount('');
                          }}
                          className={`cursor-pointer border-b border-slate-100 dark:border-slate-700/50 transition-colors ${
                            isSelected
                              ? 'bg-blue-50 dark:bg-blue-900/20'
                              : isThisDoc
                                ? 'bg-green-50/50 dark:bg-green-900/10'
                                : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'
                          }`}
                        >
                          <td className="py-1.5 font-mono text-slate-900 dark:text-white">
                            {p.reference_number || p.ida || `#${p.id}`}
                          </td>
                          <td className={`py-1.5 text-xs ${isThisDoc ? 'text-green-600 dark:text-green-400 font-medium' : 'text-slate-400 dark:text-slate-500'}`}>
                            {sourceLabel}
                          </td>
                          <td className="py-1.5 text-right font-mono text-green-600 dark:text-green-400 font-medium">
                            {formatCurrency(avail)}
                          </td>
                          <td className="py-1.5 text-right font-mono text-slate-500 dark:text-slate-400">
                            {formatCurrency(p.amount)}
                          </td>
                          <td className="py-1.5 text-slate-500 dark:text-slate-400">
                            {formatDt(p.dt_payment || p.dt_created, 'date')}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>

                {/* Apply selected payment */}
                {selectedPayment && (
                  <div className="mt-3 flex items-center gap-3">
                    <div className="flex-1">
                      <label className="block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1">
                        Apply amount
                      </label>
                      <div className="relative">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">$</span>
                        <input
                          type="number" step="0.01" min="0.01"
                          max={Math.min(selectedAvail, orderTotal ?? Infinity)}
                          value={applyAmount}
                          onChange={(e) => setApplyAmount(e.target.value)}
                          className="w-full pl-7 pr-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white font-mono focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                        />
                      </div>
                    </div>
                    <button
                      onClick={handleApplyExisting}
                      disabled={saving || !isValidApply}
                      className="mt-5 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 disabled:cursor-not-allowed rounded-lg transition-colors flex items-center gap-2"
                    >
                      {saving && selectedPayment ? (
                        <><FaSpinner className="animate-spin" size={14} /> Applying...</>
                      ) : (
                        <><FaCheck size={14} /> Apply</>
                      )}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default withDevIdentifier(AddPaymentModal, 'AddPaymentModal', 'rose', 'apps/transactions/components/AddPaymentModal.tsx');
