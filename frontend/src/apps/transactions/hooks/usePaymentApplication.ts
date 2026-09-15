/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * usePaymentApplication - Hook for payment application operations
 * 
 * Provides functions to:
 * - Apply payments to invoices
 * - Auto-apply payments to oldest invoices
 * - Get available payments for a customer
 * - Get unpaid invoices for a customer
 */
import { useCallback, useState } from 'react';
import { useDispatch } from 'react-redux';
import { getRecords } from "@/api/wcapi";
import apiClient from "@/api/axios";
import { showToast } from '../../../store/slices/toastSlice';
import { formatCurrency } from '@/utils/stringUtils';

export interface PaymentRecord {
  id: number;
  ida?: string;
  amount: number;
  amount_available?: number;
  dt_payment?: string;
  dt_created?: string;
  reference_number?: string;
  status?: string;
  gateway?: string;
  paymentmethod_id?: number;
  payment_method_name?: string;
  org_id?: string;
  contact_id?: number;
  refs?: {
    invoice_ids?: number[];
    order_ids?: number[];
    links?: {
      org?: Array<{ id: string; display_name?: string }>;
    };
  };
}

export interface InvoiceRecord {
  id: number;
  ida?: string;
  invoice_no?: string;
  status?: string;
  dt?: string;
  dt_created?: string;
  due_date?: string;
  terms?: string;
  po_number?: string;
  balance_due?: number;
  amount_paid?: number;
  totals?: {
    total?: number;
    subtotal?: number;
    tax?: number;
    received?: number;
    balance?: number;
  };
  org_id?: string;
  customer_name?: string;
  refs?: {
    links?: {
      customer?: Array<{ id: string; display_name?: string; ida?: string }>;
    };
  };
}

export interface ApplyPaymentResult {
  success: boolean;
  amount_applied: number;
  invoice_balance_remaining: number;
  payment_fully_applied: boolean;
  invoice_fully_paid: boolean;
  application_id?: number;
  error?: string;
}

export function usePaymentApplication() {
  const dispatch = useDispatch();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Get available payments for a customer (org)
   * Filters to payments with amount > total applied
   */
  const getAvailablePayments = useCallback(async (orgId: string): Promise<PaymentRecord[]> => {
    try {
      setLoading(true);
      setError(null);
      
      // Get all payments for this org
      const result = await getRecords('payment', { 
        org_id: orgId,
        status: 'completed',
        limit: 100 
      });
      
      const payments = result.results || [];
      
      // Filter to those with available amount
      // Note: Backend should ideally handle this, but filter client-side for now
      return payments.filter((p: PaymentRecord) => {
        const available = p.amount_available ?? p.amount;
        return available > 0;
      });
    } catch (err: any) {
      const msg = err?.message || 'Failed to fetch payments';
      setError(msg);
      dispatch(showToast({ message: msg, type: 'error' }));
      return [];
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  /**
   * Get unpaid invoices for a customer (org)
   */
  const getUnpaidInvoices = useCallback(async (orgId: string): Promise<InvoiceRecord[]> => {
    try {
      setLoading(true);
      setError(null);
      
      const result = await getRecords('invoice', {
        org_id: orgId,
        status__in: 'sent,partially_paid,overdue',
        limit: 100,
        ordering: 'dt_created'
      });
      
      return (result.results || []).filter((inv: InvoiceRecord) => {
        const balance = inv.balance_due ?? (inv.totals?.balance ?? 0);
        return balance > 0;
      });
    } catch (err: any) {
      const msg = err?.message || 'Failed to fetch invoices';
      setError(msg);
      dispatch(showToast({ message: msg, type: 'error' }));
      return [];
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  /**
   * Apply a payment to a specific invoice
   * Uses the invoice's apply_payment endpoint
   */
  const applyPaymentToInvoice = useCallback(async (
    invoiceId: number,
    paymentId: number,
    amount?: number
  ): Promise<ApplyPaymentResult> => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.post(`/wcapi/transactions/invoices/${invoiceId}/apply_payment/`, {
        payment_id: paymentId,
        amount: amount
      });

      const result = response.data;

      if (result.success) {
        dispatch(showToast({ 
          message: `Applied ${formatCurrency(result.amount_applied)} to invoice`, 
          type: 'success' 
        }));
      }

      return result;
    } catch (err: any) {
      const msg = err?.response?.data?.error || err?.message || 'Failed to apply payment';
      setError(msg);
      dispatch(showToast({ message: msg, type: 'error' }));
      return {
        success: false,
        amount_applied: 0,
        invoice_balance_remaining: 0,
        payment_fully_applied: false,
        invoice_fully_paid: false,
        error: msg
      };
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  /**
   * Apply payment via PaymentViewSet action
   * Alternative endpoint: /wcapi/transactions/payments/{id}/apply_to_invoice/
   */
  const applyPaymentViaPaymentEndpoint = useCallback(async (
    paymentId: number,
    invoiceId: number,
    amount?: number
  ): Promise<ApplyPaymentResult> => {
    try {
      setLoading(true);
      setError(null);

      const response = await apiClient.post(`/wcapi/transactions/payments/${paymentId}/apply_to_invoice/`, {
        invoice_id: invoiceId,
        amount: amount
      });

      const result = response.data;

      if (result.success) {
        dispatch(showToast({ 
          message: `Applied ${formatCurrency(result.amount_applied)} to invoice`, 
          type: 'success' 
        }));
      }

      return result;
    } catch (err: any) {
      const msg = err?.response?.data?.error || err?.message || 'Failed to apply payment';
      setError(msg);
      dispatch(showToast({ message: msg, type: 'error' }));
      return {
        success: false,
        amount_applied: 0,
        invoice_balance_remaining: 0,
        payment_fully_applied: false,
        invoice_fully_paid: false,
        error: msg
      };
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  /**
   * Get payment status for an invoice
   */
  const getInvoicePaymentStatus = useCallback(async (invoiceId: number) => {
    try {
      const response = await apiClient.get(`/wcapi/transactions/invoices/${invoiceId}/payment_status/`);
      return response.data;
    } catch (err: any) {
      const msg = err?.response?.data?.error || err?.message || 'Failed to get payment status';
      setError(msg);
      dispatch(showToast({ message: msg, type: 'error' }));
      return null;
    }
  }, [dispatch]);

  /**
   * Calculate days past due for an invoice
   */
  const calculateDaysPastDue = useCallback((invoice: InvoiceRecord): number => {
    const dueDate = invoice.due_date ? new Date(invoice.due_date) : null;
    if (!dueDate) return 0;
    
    const today = new Date();
    const diffTime = today.getTime() - dueDate.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return Math.max(0, diffDays);
  }, []);

  /**
   * Get invoice balance (helper)
   */
  const getInvoiceBalance = useCallback((invoice: InvoiceRecord): number => {
    return invoice.balance_due ?? invoice.totals?.balance ?? 
           ((invoice.totals?.total ?? 0) - (invoice.totals?.received ?? 0));
  }, []);

  /**
   * Get payment available amount (helper)
   */
  const getPaymentAvailable = useCallback((payment: PaymentRecord): number => {
    return payment.amount_available ?? payment.amount;
  }, []);

  return {
    loading,
    error,
    getAvailablePayments,
    getUnpaidInvoices,
    applyPaymentToInvoice,
    applyPaymentViaPaymentEndpoint,
    getInvoicePaymentStatus,
    calculateDaysPastDue,
    getInvoiceBalance,
    getPaymentAvailable,
  };
}

export default usePaymentApplication;
