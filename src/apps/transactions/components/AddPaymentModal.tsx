/**
 * AddPaymentModal - Modal for adding a new payment to an order
 * 
 * Used from OrderDetail to record payments received at order time.
 * These payments are not applied to an invoice until the invoice ships.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { FaTimes, FaDollarSign, FaCheck, FaSpinner } from 'react-icons/fa';
import { useDispatch } from 'react-redux';
import apiClient from '@/api/axios';
import { getRecords } from '@/api/wcapi';
import { showToast } from '@/store/slices/toastSlice';

interface PaymentMethod {
  id: number;
  name: string;
  is_active: boolean;
}

interface AddPaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
  orderId: number;
  contactId?: number | null;
  customerName?: string;
  orderTotal?: number;
  onPaymentAdded?: () => void;
}

const AddPaymentModal: React.FC<AddPaymentModalProps> = ({
  isOpen,
  onClose,
  orderId,
  contactId,
  customerName,
  orderTotal,
  onPaymentAdded
}) => {
  const dispatch = useDispatch();
  
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [saving, setSaving] = useState(false);
  
  // Form state
  const [amount, setAmount] = useState('');
  const [paymentMethodId, setPaymentMethodId] = useState<number | null>(null);
  const [referenceNumber, setReferenceNumber] = useState('');
  const [notes, setNotes] = useState('');
  const [paymentDate, setPaymentDate] = useState(() => {
    const today = new Date();
    return today.toISOString().split('T')[0];
  });

  // Load payment methods when modal opens
  useEffect(() => {
    if (isOpen) {
      getRecords('paymentmethod', { is_active: true, limit: 50 })
        .then((response) => {
          const methods = response?.results || response || [];
          setPaymentMethods(methods);
          // Default to first method if available
          if (methods.length > 0 && !paymentMethodId) {
            setPaymentMethodId(methods[0].id);
          }
        })
        .catch(console.error);
    }
  }, [isOpen]);

  // Reset form when modal closes
  useEffect(() => {
    if (!isOpen) {
      setAmount('');
      setReferenceNumber('');
      setNotes('');
      setPaymentDate(new Date().toISOString().split('T')[0]);
    }
  }, [isOpen]);

  // Set default amount to order total
  useEffect(() => {
    if (isOpen && orderTotal && !amount) {
      setAmount(orderTotal.toFixed(2));
    }
  }, [isOpen, orderTotal]);

  const handleSave = useCallback(async () => {
    if (!amount || parseFloat(amount) <= 0) {
      dispatch(showToast({ message: 'Please enter a valid amount', type: 'error' }));
      return;
    }

    if (!contactId) {
      dispatch(showToast({ message: 'Order must have a customer to record payment', type: 'error' }));
      return;
    }

    setSaving(true);
    try {
      const paymentData = {
        amount: parseFloat(amount),
        contact_id: contactId,
        dt_payment: new Date(paymentDate).toISOString(),
        paymentmethod_id: paymentMethodId,
        reference_number: referenceNumber,
        notes: notes,
        status: 'completed',
        gateway: 'manual',
        refs: {
          order_ids: [orderId],
          invoice_ids: [],
          source: { type: 'order', id: orderId }
        }
      };

      const response = await apiClient.post('/api/transactions/payments/', paymentData);
      
      if (response.data) {
        dispatch(showToast({ 
          message: `Payment of $${parseFloat(amount).toFixed(2)} recorded successfully`, 
          type: 'success' 
        }));
        onPaymentAdded?.();
        onClose();
      }
    } catch (error: any) {
      console.error('Error creating payment:', error);
      const errorMessage = error.response?.data?.detail || 
                          error.response?.data?.message ||
                          'Failed to create payment';
      dispatch(showToast({ message: errorMessage, type: 'error' }));
    } finally {
      setSaving(false);
    }
  }, [amount, contactId, paymentDate, paymentMethodId, referenceNumber, notes, orderId, dispatch, onPaymentAdded, onClose]);

  if (!isOpen) return null;

  const formatCurrency = (value?: number | null) => {
    if (value === undefined || value === null) return '--';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-white dark:bg-slate-800 rounded-lg shadow-xl w-full max-w-md mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-white flex items-center gap-2">
            <FaDollarSign className="text-green-500" />
            Add Payment
          </h2>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700"
          >
            <FaTimes size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-4">
          {/* Order/Customer Info */}
          <div className="bg-slate-50 dark:bg-slate-900/50 rounded-lg p-3 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-500 dark:text-slate-400">Customer:</span>
              <span className="font-medium text-slate-900 dark:text-white">{customerName || '--'}</span>
            </div>
            <div className="flex justify-between mt-1">
              <span className="text-slate-500 dark:text-slate-400">Order Total:</span>
              <span className="font-medium text-slate-900 dark:text-white">{formatCurrency(orderTotal)}</span>
            </div>
          </div>

          {/* Amount */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Amount *
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">$</span>
              <input
                type="number"
                step="0.01"
                min="0"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
                className="w-full pl-7 pr-4 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Payment Method */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Payment Method
            </label>
            <select
              value={paymentMethodId || ''}
              onChange={(e) => setPaymentMethodId(e.target.value ? parseInt(e.target.value) : null)}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Select method...</option>
              {paymentMethods.map(method => (
                <option key={method.id} value={method.id}>{method.name}</option>
              ))}
            </select>
          </div>

          {/* Payment Date */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Payment Date
            </label>
            <input
              type="date"
              value={paymentDate}
              onChange={(e) => setPaymentDate(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Reference Number */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Reference / Check #
            </label>
            <input
              type="text"
              value={referenceNumber}
              onChange={(e) => setReferenceNumber(e.target.value)}
              placeholder="Check number, transaction ID, etc."
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Notes
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              placeholder="Optional notes about this payment..."
              className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-200 dark:border-slate-700">
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
                Add Payment
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AddPaymentModal;
