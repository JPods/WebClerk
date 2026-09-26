/**
 * AddCashDialog — add cash from an order, invoice or receipt (release #9, Bill 2026-09-26).
 *
 * Built on AddRelatedDialog (one generic add-a-related-record dialog). Save calls
 * POST /wcapi/<model>/<id>/add_cash/: the Cash is saved, then applied (invoice, receipt) or
 * kept as a deposit (order). "Write off the rest" adds a second Cash, method write_off, for
 * what is left — a company record against a loss account, never refused (Bill). On an invoice,
 * the customer's available cash is listed and applied through apply_balance.
 * Replaces CashDialog and AddCashModal, which sent non-fields (cash_method_id, notes).
 */
import React, { useCallback, useEffect, useState } from 'react';
import { useDispatch } from 'react-redux';
import AddRelatedDialog, { RelatedField, RelatedValues } from '@/apps/common/components/dialogs/AddRelatedDialog';
import { getRecords } from '@/api/wcapi';
import { addCash, applyBalance } from '../models/cash/services/cashApi';
import { showToast } from '@/store/slices/toastSlice';
import { formatCurrency } from '@/utils/stringUtils';

type CashDocument = 'order' | 'invoice' | 'receipt';

interface AddCashDialogProps {
  isOpen: boolean;
  onClose: () => void;
  model: CashDocument;
  id: number;
  /** What is still open on the document (an order: its total). */
  balance: number;
  customerId?: number | null;
  partyName?: string;
  onDone?: () => void;
}

const METHODS = [
  { value: 'check', label: 'Check' },
  { value: 'cash', label: 'Cash' },
  { value: 'ach', label: 'ACH' },
  { value: 'wire', label: 'Wire' },
  { value: 'card', label: 'Card (entered by hand)' },
  { value: 'other', label: 'Other' },
];

const today = () => new Date().toISOString().slice(0, 10);

const AddCashDialog: React.FC<AddCashDialogProps> = ({
  isOpen, onClose, model, id, balance, customerId, partyName, onDone,
}) => {
  const dispatch = useDispatch();
  const [available, setAvailable] = useState<any[]>([]);
  const applies = model !== 'order';

  const loadAvailable = useCallback(async () => {
    if (model !== 'invoice' || !customerId) { setAvailable([]); return; }
    const res = await getRecords('cash', { customer_id: customerId, limit: 50 });
    setAvailable((res?.results || []).filter((c: any) => (c.available ?? 0) > 0.005));
  }, [model, customerId]);

  useEffect(() => { if (isOpen) loadAvailable(); }, [isOpen, loadAvailable]);

  const fields: RelatedField[] = [
    { name: 'amount', label: model === 'receipt' ? 'Amount paid' : 'Amount received', kind: 'number', required: true },
    { name: 'method', label: 'Method', kind: 'select', options: METHODS },
    { name: 'date', label: 'Date', kind: 'date' },
    { name: 'reference', label: 'Reference / check #', kind: 'text', placeholder: 'Check #, trans ID…' },
    { name: 'reason', label: 'Note', kind: 'textarea', placeholder: 'Optional' },
    ...(applies ? [{ name: 'write_off_rest', label: 'Write off what is left', kind: 'checkbox' as const,
                     hint: 'A write-off Cash for the remaining balance, posted to bad debt' }] : []),
  ];

  const save = async (v: RelatedValues) => {
    const amount = Number(v.amount);
    const result: any = await addCash(model, id, {
      amount, method: String(v.method || 'check'), reference: String(v.reference || ''),
      reason: String(v.reason || ''), date: v.date ? new Date(String(v.date)).toISOString() : undefined,
    });
    if (result?.applied?.state === 'refused') {
      dispatch(showToast({ message: result.applied.reason, type: 'info' }));
    } else {
      dispatch(showToast({ message: model === 'order'
        ? `Deposit of ${formatCurrency(amount)} recorded` : `${formatCurrency(amount)} applied`, type: 'success' }));
    }
    const rest = Math.round((balance - amount) * 100) / 100;
    if (applies && v.write_off_rest && rest > 0) {
      await addCash(model, id, { amount: rest, method: 'write_off', reason: String(v.reason || 'written off') });
      dispatch(showToast({ message: `${formatCurrency(rest)} written off`, type: 'success' }));
    }
    onDone?.();
  };

  const applyExisting = async (cash: any) => {
    const amount = Math.min(Number(cash.available) || 0, balance);
    try {
      await applyBalance(id, { cash_id: cash.id, amount });
      dispatch(showToast({ message: `${formatCurrency(amount)} applied from cash ${cash.ida || cash.id}`, type: 'success' }));
      onDone?.();
      onClose();
    } catch (e: any) {
      dispatch(showToast({ message: e.message, type: 'error' }));
    }
  };

  return (
    <AddRelatedDialog
      isOpen={isOpen}
      title={model === 'order' ? 'Add a deposit' : model === 'receipt' ? 'Pay this bill' : 'Add cash'}
      subtitle={<>{partyName ? `${partyName} · ` : ''}{formatCurrency(balance)} open</>}
      fields={fields}
      initial={{ amount: balance > 0 ? String(balance) : '', method: 'check', date: today() }}
      saveLabel={model === 'order' ? 'Record deposit' : 'Add and apply'}
      onSave={save}
      onClose={onClose}
    >
      {available.length > 0 && (
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider db-text-muted mb-1">
            Or apply cash already received
          </div>
          {available.map((c) => (
            <div key={c.id} className="flex items-center justify-between py-1 text-sm db-text">
              <span>{c.ida || c.id} · {c.method || 'cash'} · {formatCurrency(c.available)} available</span>
              <button onClick={() => applyExisting(c)} className="px-2 py-0.5 text-xs rounded"
                      style={{ background: 'var(--db-btn-primary)', color: 'var(--db-btn-primary-text)' }}>
                Apply
              </button>
            </div>
          ))}
        </div>
      )}
    </AddRelatedDialog>
  );
};

export default AddCashDialog;
