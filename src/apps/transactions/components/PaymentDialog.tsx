/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * PaymentDialog — Full-featured payment creation/edit dialog.
 *
 * Enhanced version of AddPaymentModal with fields from the legacy wc2
 * diaMakePay dialog:
 *   • Payment type selection (auto-detected from card number)
 *   • Total / Payment / Difference auto-calculation
 *   • Credit card fields (number, expiry, CVV, approval)
 *   • Check fields (check number, bank)
 *   • Billing address (for AVS verification)
 *   • Reference info, dates, and notes
 *
 * Can be used standalone or to replace AddPaymentModal where a richer
 * dialog is needed.
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  FaTimes,
  FaDollarSign,
  FaCheck,
  FaSpinner,
  FaCreditCard,
  FaMoneyCheck,
  FaLock,
} from 'react-icons/fa';
import { useDispatch } from 'react-redux';
import apiClient from '@/api/axios';
import { getRecords } from '@/api/wcapi';
import { showToast } from '@/store/slices/toastSlice';
import { withDevIdentifier } from '@/components/common/DevIdentifier';
import SpreedlyCardForm from './SpreedlyCardForm';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PaymentMethodOption {
  id: number;
  name: string;
  is_active: boolean;
}

interface PaymentDialogProps {
  isOpen: boolean;
  onClose: () => void;
  // Context
  order_id?: number;
  invoice_id?: number;
  customer_id?: number | null;
  contact_id?: number | null;
  customer_name?: string;
  /** Total due on the parent transaction */
  total?: number;
  /** Amount already received */
  received?: number;
  /** Callback after successful save */
  onPaymentAdded?: () => void;
}

// Card type auto-detection from first digit (legacy wc2 logic)
const detectCardType = (num: string): string | null => {
  if (!num) return null;
  const first = num[0];
  switch (first) {
    case '3': return 'Amex';
    case '4': return 'Visa';
    case '5': return 'Mastercard';
    case '6': return 'Discover';
    default: return null;
  }
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const PaymentDialog: React.FC<PaymentDialogProps> = ({
  isOpen,
  onClose,
  order_id,
  invoice_id,
  customer_id,
  contact_id,
  customer_name,
  total,
  received = 0,
  onPaymentAdded,
}) => {
  const dispatch = useDispatch();

  // Payment mode: 'manual' (check/wire/ACH) or 'card' (Spreedly hosted fields)
  const [paymentMode, setPaymentMode] = useState<'manual' | 'card'>('manual');

  // Options
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethodOption[]>([]);
  const [saving, setSaving] = useState(false);

  // Core fields
  const [amount, setAmount] = useState('');
  const [paymentMethodId, setPaymentMethodId] = useState<number | null>(null);
  const [referenceNumber, setReferenceNumber] = useState('');
  const [notes, setNotes] = useState('');
  const [paymentDate, setPaymentDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [isCredit, setIsCredit] = useState(false);

  // Expanded (credit card / check / address)
  const [showCC, setShowCC] = useState(false);
  const [showCheck, setShowCheck] = useState(false);
  const [showAddress, setShowAddress] = useState(false);

  // Credit card fields
  const [cardNumber, setCardNumber] = useState('');
  const [cardExpiry, setCardExpiry] = useState('');
  const [cardCvv, setCardCvv] = useState('');
  const [cardApproval, setCardApproval] = useState('');

  // Check fields
  const [checkNumber, setCheckNumber] = useState('');
  const [bankName, setBankName] = useState('');

  // Address (AVS)
  const [address1, setAddress1] = useState('');
  const [address2, setAddress2] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [zip, setZip] = useState('');

  // Auto-calculated
  const balanceDue = useMemo(() => {
    if (total == null) return null;
    return total - received;
  }, [total, received]);

  const difference = useMemo(() => {
    if (balanceDue == null) return null;
    const pay = parseFloat(amount) || 0;
    return balanceDue - pay;
  }, [balanceDue, amount]);

  const detectedCardType = useMemo(() => detectCardType(cardNumber), [cardNumber]);

  // Load payment methods
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
  }, [isOpen]);

  // Reset form on close
  useEffect(() => {
    if (isOpen) return;
    setAmount('');
    setReferenceNumber('');
    setNotes('');
    setPaymentDate(new Date().toISOString().split('T')[0]);
    setIsCredit(false);
    setShowCC(false);
    setShowCheck(false);
    setShowAddress(false);
    setCardNumber('');
    setCardExpiry('');
    setCardCvv('');
    setCardApproval('');
    setCheckNumber('');
    setBankName('');
    setAddress1('');
    setAddress2('');
    setCity('');
    setState('');
    setZip('');
    setPaymentMode('manual');
  }, [isOpen]);

  // Default amount to balance due
  useEffect(() => {
    if (isOpen && balanceDue != null && balanceDue > 0 && !amount) {
      setAmount(balanceDue.toFixed(2));
    }
  }, [isOpen, balanceDue]);

  // Save
  const handleSave = useCallback(async () => {
    const parsedAmount = parseFloat(amount);
    if (!parsedAmount || parsedAmount <= 0) {
      dispatch(showToast({ message: 'Enter a valid amount', type: 'error' }));
      return;
    }
    if (!contact_id) {
      dispatch(showToast({ message: 'Contact is required to record a payment', type: 'error' }));
      return;
    }

    setSaving(true);
    try {
      const paymentData: Record<string, unknown> = {
        amount: isCredit ? -parsedAmount : parsedAmount,
        contact_id,
        dt_payment: new Date(paymentDate).toISOString(),
        paymentmethod_id: paymentMethodId,
        reference_number: referenceNumber || checkNumber || undefined,
        notes,
        status: 'completed',
        gateway: 'manual',
        refs: {
          order_ids: order_id ? [order_id] : [],
          invoice_ids: invoice_id ? [invoice_id] : [],
          customer_id: customer_id || null,
          contact_id: contact_id || null,
          source: order_id
            ? { type: 'order', id: order_id }
            : invoice_id
              ? { type: 'invoice', id: invoice_id }
              : undefined,
        },
        metadata: {
          ...(cardApproval ? { card_approval: cardApproval } : {}),
          ...(detectedCardType ? { card_type: detectedCardType } : {}),
          ...(cardNumber ? { card_last4: cardNumber.slice(-4) } : {}),
          ...(bankName ? { bank: bankName } : {}),
          ...(address1
            ? {
                billing_address: {
                  address1,
                  address2,
                  city,
                  state,
                  zip,
                },
              }
            : {}),
        },
      };
      if (invoice_id) {
        paymentData.invoice_id = invoice_id;
      }

      const response = await apiClient.post('/api/transactions/payments/', paymentData);

      if (response.data) {
        const displayAmount = isCredit ? -parsedAmount : parsedAmount;
        dispatch(
          showToast({
            message: `Payment of $${Math.abs(displayAmount).toFixed(2)} recorded`,
            type: 'success',
          }),
        );
        onPaymentAdded?.();
        onClose();
      }
    } catch (error: any) {
      const msg =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        'Failed to create payment';
      dispatch(showToast({ message: msg, type: 'error' }));
    } finally {
      setSaving(false);
    }
  }, [
    amount, isCredit, contact_id, paymentDate, paymentMethodId,
    referenceNumber, notes, order_id, invoice_id, customer_id,
    checkNumber, cardApproval, detectedCardType, cardNumber,
    bankName, address1, address2, city, state, zip,
    dispatch, onPaymentAdded, onClose,
  ]);

  if (!isOpen) return null;

  const formatCurrency = (v?: number | null) => {
    if (v == null) return '--';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(v);
  };

  const inputClass =
    'w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm';
  const labelClass =
    'block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Dialog */}
      <div className="relative bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700 shrink-0">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <FaDollarSign className="text-green-500" />
            {isCredit ? 'Credit Payment' : 'Make Payment'}
          </h2>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700"
          >
            <FaTimes size={18} />
          </button>
        </div>

        {/* Scrollable body */}
        <div className="px-6 py-4 space-y-4 overflow-y-auto flex-1">
          {/* Context info */}
          <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 text-sm space-y-1">
            {customer_name && (
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Customer:</span>
                <span className="font-medium text-slate-900 dark:text-white">{customer_name}</span>
              </div>
            )}
            {total != null && (
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">
                  {invoice_id ? 'Invoice Total:' : 'Order Total:'}
                </span>
                <span className="font-medium text-slate-900 dark:text-white">
                  {formatCurrency(total)}
                </span>
              </div>
            )}
            {received > 0 && (
              <div className="flex justify-between">
                <span className="text-slate-500 dark:text-slate-400">Received:</span>
                <span className="text-green-600 dark:text-green-400">{formatCurrency(received)}</span>
              </div>
            )}
            {balanceDue != null && (
              <div className="flex justify-between font-medium">
                <span className="text-slate-500 dark:text-slate-400">Balance Due:</span>
                <span
                  className={
                    balanceDue > 0
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-green-600 dark:text-green-400'
                  }
                >
                  {formatCurrency(balanceDue)}
                </span>
              </div>
            )}
          </div>

          {/* Payment mode toggle */}
          {invoice_id && (
            <div className="flex rounded-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
              <button
                type="button"
                onClick={() => setPaymentMode('manual')}
                className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium transition ${
                  paymentMode === 'manual'
                    ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                    : 'text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700'
                }`}
              >
                <FaMoneyCheck size={12} />
                Manual (Check / Wire / ACH)
              </button>
              <button
                type="button"
                onClick={() => setPaymentMode('card')}
                className={`flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium transition ${
                  paymentMode === 'card'
                    ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                    : 'text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700'
                }`}
              >
                <FaLock size={12} />
                Pay by Card
              </button>
            </div>
          )}

          {/* Card payment via Spreedly hosted fields */}
          {paymentMode === 'card' && invoice_id ? (
            <SpreedlyCardForm
              invoiceId={invoice_id}
              amount={balanceDue != null && balanceDue > 0 ? balanceDue : parseFloat(amount) || 0}
              customerName={customer_name}
              onSuccess={(paymentId) => {
                onPaymentAdded?.();
                onClose();
              }}
              onCancel={() => setPaymentMode('manual')}
            />
          ) : (
          <>
          {/* Amount + Difference row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Amount *</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">$</span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0.00"
                  className={`${inputClass} pl-7`}
                />
              </div>
            </div>
            <div>
              <label className={labelClass}>Difference</label>
              <div
                className={`px-3 py-2 rounded-lg border text-sm font-medium ${
                  difference != null && difference < 0
                    ? 'border-red-300 text-red-600 bg-red-50 dark:border-red-700 dark:text-red-400 dark:bg-red-900/20'
                    : difference === 0
                      ? 'border-green-300 text-green-600 bg-green-50 dark:border-green-700 dark:text-green-400 dark:bg-green-900/20'
                      : 'border-slate-300 text-slate-900 bg-slate-50 dark:border-slate-600 dark:text-white dark:bg-slate-700'
                }`}
              >
                {difference != null ? formatCurrency(difference) : '--'}
              </div>
            </div>
          </div>

          {/* Credit toggle */}
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            <input
              type="checkbox"
              checked={isCredit}
              onChange={(e) => setIsCredit(e.target.checked)}
              className="rounded"
            />
            Credit (refund/credit memo)
          </label>

          {/* Payment Method + Date */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClass}>Payment Method</label>
              <select
                value={paymentMethodId ?? ''}
                onChange={(e) =>
                  setPaymentMethodId(e.target.value ? parseInt(e.target.value) : null)
                }
                className={inputClass}
              >
                <option value="">Select method...</option>
                {paymentMethods.map((m) => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className={labelClass}>Payment Date</label>
              <input
                type="date"
                value={paymentDate}
                onChange={(e) => setPaymentDate(e.target.value)}
                className={inputClass}
              />
            </div>
          </div>

          {/* Reference Number */}
          <div>
            <label className={labelClass}>Reference / Check #</label>
            <input
              type="text"
              value={referenceNumber}
              onChange={(e) => setReferenceNumber(e.target.value)}
              placeholder="Check number, transaction ID, etc."
              className={inputClass}
            />
          </div>

          {/* Expandable Sections */}
          <div className="space-y-2 pt-2">
            {/* Credit Card section */}
            <button
              type="button"
              onClick={() => setShowCC((v) => !v)}
              className="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400 hover:underline"
            >
              <FaCreditCard size={12} />
              {showCC ? 'Hide' : 'Show'} Credit Card Fields
            </button>
            {showCC && (
              <div className="pl-4 space-y-3 border-l-2 border-blue-200 dark:border-blue-800">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className={labelClass}>Card Number</label>
                    <input
                      type="text"
                      value={cardNumber}
                      onChange={(e) =>
                        setCardNumber(e.target.value.replace(/\D/g, ''))
                      }
                      placeholder="Card number"
                      maxLength={19}
                      className={inputClass}
                    />
                    {detectedCardType && (
                      <p className="text-xs text-blue-500 mt-0.5">{detectedCardType}</p>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className={labelClass}>Expiry</label>
                      <input
                        type="text"
                        value={cardExpiry}
                        onChange={(e) =>
                          setCardExpiry(e.target.value.replace(/\D/g, '').slice(0, 4))
                        }
                        placeholder="MMYY"
                        maxLength={4}
                        className={inputClass}
                      />
                    </div>
                    <div>
                      <label className={labelClass}>CVV</label>
                      <input
                        type="text"
                        value={cardCvv}
                        onChange={(e) =>
                          setCardCvv(e.target.value.replace(/\D/g, '').slice(0, 4))
                        }
                        placeholder="CVV"
                        maxLength={4}
                        className={inputClass}
                      />
                    </div>
                  </div>
                </div>
                <div>
                  <label className={labelClass}>Approval Code</label>
                  <input
                    type="text"
                    value={cardApproval}
                    onChange={(e) => setCardApproval(e.target.value)}
                    placeholder="Authorization / approval code"
                    className={inputClass}
                  />
                </div>
              </div>
            )}

            {/* Check section */}
            <button
              type="button"
              onClick={() => setShowCheck((v) => !v)}
              className="flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400 hover:underline"
            >
              <FaMoneyCheck size={12} />
              {showCheck ? 'Hide' : 'Show'} Check Fields
            </button>
            {showCheck && (
              <div className="pl-4 space-y-3 border-l-2 border-blue-200 dark:border-blue-800">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className={labelClass}>Check Number</label>
                    <input
                      type="text"
                      value={checkNumber}
                      onChange={(e) => setCheckNumber(e.target.value)}
                      placeholder="Check #"
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className={labelClass}>Bank</label>
                    <input
                      type="text"
                      value={bankName}
                      onChange={(e) => setBankName(e.target.value)}
                      placeholder="Bank name"
                      className={inputClass}
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Address section */}
            <button
              type="button"
              onClick={() => setShowAddress((v) => !v)}
              className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400 hover:underline"
            >
              {showAddress ? 'Hide' : 'Show'} Billing Address
            </button>
            {showAddress && (
              <div className="pl-4 space-y-3 border-l-2 border-slate-200 dark:border-slate-700">
                <div>
                  <label className={labelClass}>Address 1</label>
                  <input
                    type="text"
                    value={address1}
                    onChange={(e) => setAddress1(e.target.value)}
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Address 2</label>
                  <input
                    type="text"
                    value={address2}
                    onChange={(e) => setAddress2(e.target.value)}
                    className={inputClass}
                  />
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <label className={labelClass}>City</label>
                    <input
                      type="text"
                      value={city}
                      onChange={(e) => setCity(e.target.value)}
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className={labelClass}>State</label>
                    <input
                      type="text"
                      value={state}
                      onChange={(e) => setState(e.target.value)}
                      className={inputClass}
                    />
                  </div>
                  <div>
                    <label className={labelClass}>Zip</label>
                    <input
                      type="text"
                      value={zip}
                      onChange={(e) => setZip(e.target.value)}
                      className={inputClass}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Notes */}
          <div>
            <label className={labelClass}>Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="Optional notes..."
              className={`${inputClass} resize-none`}
            />
          </div>

          </>
          )}
        </div>

        {/* Footer — only for manual mode (card mode has its own buttons) */}
        {paymentMode === 'manual' && (
          <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-200 dark:border-slate-700 shrink-0">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving || !amount || parseFloat(amount) <= 0}
              className="px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {saving ? (
                <>
                  <FaSpinner className="animate-spin" size={14} />
                  Saving...
                </>
              ) : (
                <>
                  <FaCheck size={14} />
                  {isCredit ? 'Apply Credit' : 'Add Payment'}
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default withDevIdentifier(PaymentDialog, 'PaymentDialog', 'rose', 'apps/transactions/components/PaymentDialog.tsx');
