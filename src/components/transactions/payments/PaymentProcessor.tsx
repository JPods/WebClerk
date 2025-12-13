import React, { useState, useEffect } from 'react';
import { useWCAPI } from '../../../hooks/useWCAPI';
import { useAuditTrail } from '../../../hooks/useAuditTrail';

export interface PaymentProcessorProps {
  invoiceId?: number;
  orderId?: number;
  amount: number;
  currency?: string;
  onPaymentComplete?: (payment: any) => void;
  onCancel?: () => void;
}

export const PaymentProcessor: React.FC<PaymentProcessorProps> = ({
  invoiceId,
  orderId,
  amount,
  currency = 'USD',
  onPaymentComplete,
  onCancel,
}) => {
  const { create } = useWCAPI();
  const [loading, setLoading] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState('credit_card');
  const [paymentData, setPaymentData] = useState({
    cardNumber: '',
    expiryMonth: '',
    expiryYear: '',
    cvv: '',
    cardholderName: '',
    billingAddress: '',
  });

  const { addEntry } = useAuditTrail(0, 'payment'); // Will be set after creation

  const handleInputChange = (field: string, value: string) => {
    setPaymentData(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const processPayment = async () => {
    setLoading(true);
    try {
      // Create payment record
      const paymentRecord = {
        amount,
        currency,
        method: paymentMethod,
        status: 'processing',
        invoice_id: invoiceId || 0,
        order_id: orderId || 0,
        payment_data: {
          ...paymentData,
          processed_at: new Date().toISOString(),
        },
      };

      const response = await create('payment', paymentRecord);

      if (response?.record) {
        // Simulate payment gateway processing
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Update payment status
        const updatedPayment = {
          ...response.record,
          status: 'completed',
          transaction_id: `txn_${Date.now()}`,
        };

        await addEntry('created', {
          amount,
          currency,
          method: paymentMethod,
          invoice_id: invoiceId,
          order_id: orderId,
        });

        onPaymentComplete?.(updatedPayment);
      }
    } catch (error) {
      console.error('Payment processing failed:', error);
      // Handle payment failure
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(amount);
  };

  return (
    <div className="payment-processor max-w-md mx-auto bg-white p-6 rounded-lg shadow-lg border">
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-gray-800 mb-2">Payment Details</h2>
        <div className="text-2xl font-bold text-green-600">
          {formatCurrency(amount)}
        </div>
      </div>

      <div className="space-y-4">
        {/* Payment Method Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Payment Method
          </label>
          <select
            value={paymentMethod}
            onChange={(e) => setPaymentMethod(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="credit_card">Credit Card</option>
            <option value="debit_card">Debit Card</option>
            <option value="paypal">PayPal</option>
            <option value="bank_transfer">Bank Transfer</option>
          </select>
        </div>

        {/* Credit Card Form */}
        {(paymentMethod === 'credit_card' || paymentMethod === 'debit_card') && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Card Number
              </label>
              <input
                type="text"
                placeholder="1234 5678 9012 3456"
                value={paymentData.cardNumber}
                onChange={(e) => handleInputChange('cardNumber', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                maxLength={19}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Expiry Month
                </label>
                <select
                  value={paymentData.expiryMonth}
                  onChange={(e) => handleInputChange('expiryMonth', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">MM</option>
                  {Array.from({ length: 12 }, (_, i) => (
                    <option key={i + 1} value={String(i + 1).padStart(2, '0')}>
                      {String(i + 1).padStart(2, '0')}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Expiry Year
                </label>
                <select
                  value={paymentData.expiryYear}
                  onChange={(e) => handleInputChange('expiryYear', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="">YYYY</option>
                  {Array.from({ length: 10 }, (_, i) => {
                    const year = new Date().getFullYear() + i;
                    return (
                      <option key={year} value={year}>
                        {year}
                      </option>
                    );
                  })}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                CVV
              </label>
              <input
                type="text"
                placeholder="123"
                value={paymentData.cvv}
                onChange={(e) => handleInputChange('cvv', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                maxLength={4}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Cardholder Name
              </label>
              <input
                type="text"
                placeholder="John Doe"
                value={paymentData.cardholderName}
                onChange={(e) => handleInputChange('cardholderName', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        )}

        {/* PayPal Placeholder */}
        {paymentMethod === 'paypal' && (
          <div className="text-center p-4 bg-gray-50 rounded">
            <p className="text-gray-600">PayPal integration would go here</p>
          </div>
        )}

        {/* Bank Transfer Placeholder */}
        {paymentMethod === 'bank_transfer' && (
          <div className="text-center p-4 bg-gray-50 rounded">
            <p className="text-gray-600">Bank transfer instructions would go here</p>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex space-x-4 mt-6">
        <button
          onClick={onCancel}
          className="flex-1 px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
          disabled={loading}
        >
          Cancel
        </button>
        <button
          onClick={processPayment}
          disabled={loading}
          className="flex-1 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
        >
          {loading ? (
            <div className="flex items-center justify-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Processing...
            </div>
          ) : (
            `Pay ${formatCurrency(amount)}`
          )}
        </button>
      </div>
    </div>
  );
};