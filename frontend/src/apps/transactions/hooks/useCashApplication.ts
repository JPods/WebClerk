/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * useCashApplication - Hook for cash application operations
 * 
 * Provides functions to:
 * - Apply cash to invoices
 * - Auto-apply cash to oldest invoices
 * - Get available cash for a customer
 * - Get unpaid invoices for a customer
 */
import { useCallback, useState } from 'react';
import { useDispatch } from 'react-redux';
import { getRecords, manageAction, refusedFrom } from "@/api/wcapi";
import { showToast } from '../../../store/slices/toastSlice';

export interface CashRecord {
  id: number;
  ida?: string;
  amount: number;
  available: number;
  dt_cash?: string;
  dt_created?: string;
  reference_number?: string;
  status?: string;
  gateway?: string;
  cash_method_id?: number;
  cash_method_name?: string;
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

/** Invoices that can still take cash (totals.cash_state, derived server-side). */
const UNPAID_CASH_STATES = ['open', 'partial'] as const;

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
  totals?: {
    total?: number;
    amount?: number;
    tax?: number;
    received?: number;
    balance?: number;
    cash_state?: 'open' | 'partial' | 'paid' | 'credit' | 'over';
  };
  org_id?: string;
  customer_name?: string;
  refs?: {
    links?: {
      customer?: Array<{ id: string; display_name?: string; ida?: string }>;
    };
  };
}

export interface ApplyCashResult {
  success: boolean;
  applied: boolean;
  state?: 'applied' | 'pending';
  amount: number;
  pending_id?: number;
  error?: string;
}

export function useCashApplication() {
  const dispatch = useDispatch();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Get available cash for a customer (org)
   * Filters to cash with amount > total applied
   */
  const getAvailableCashEntries = useCallback(async (orgId: string): Promise<CashRecord[]> => {
    try {
      setLoading(true);
      setError(null);
      
      // Get all cash for this org
      const result = await getRecords('cash', { 
        org_id: orgId,
        status: 'completed',
        limit: 100 
      });
      
      const cashEntries = result.results || [];
      
      // Filter to those with available amount
      // Note: Backend should ideally handle this, but filter client-side for now
      return cashEntries.filter((p: CashRecord) => {
        return p.available > 0;
      });
    } catch (err: any) {
      const msg = err?.message || 'Failed to fetch cash';
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
      
      // Invoice links its org as customer (org_id is not a field; wcapi drops unknown filters).
      // Money state is totals.cash_state, never status (status is workflow only).
      const result = await getRecords('invoice', {
        customer_id: orgId,
        totals__cash_state__in: [...UNPAID_CASH_STATES].join(','),
        limit: 100,
        ordering: 'dt_created'
      });

      return result.results || [];
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
   * Apply cash to an invoice — one path: manage action → Pending application record.
   * Applied at once when the invoice is unlocked; otherwise queued (state 'pending').
   */
  const applyCashToInvoice = useCallback(async (
    invoiceId: number,
    cashId: number,
    amount: number
  ): Promise<ApplyCashResult> => {
    try {
      setLoading(true);
      setError(null);
      const result = await manageAction('apply_cash_to_invoice', {
        cash_id: cashId,
        invoice_id: invoiceId,
        amount,
      });
      return { success: true, applied: !!result?.applied, state: result?.state, amount: result?.amount ?? amount, pending_id: result?.pending_id };
    } catch (err: any) {
      const msg = refusedFrom(err, 'Failed to apply cash').message;
      setError(msg);
      dispatch(showToast({ message: msg, type: 'error' }));
      return { success: false, applied: false, amount: 0, error: msg };
    } finally {
      setLoading(false);
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
    // One source: totals.balance (recomputed from applications). No fallbacks.
    return invoice.totals?.balance ?? 0;
  }, []);

  /**
   * Get cash available amount (helper)
   */
  const getCashAvailable = useCallback((cash: CashRecord): number => {
    return cash.available;
  }, []);

  return {
    loading,
    error,
    getAvailableCashEntries,
    getUnpaidInvoices,
    applyCashToInvoice,
    calculateDaysPastDue,
    getInvoiceBalance,
    getCashAvailable,
  };
}

export default useCashApplication;
