/* LastChecked: 2026-11-11 | WhereUsed: DbForm | WhoCreated: Claude */
/**
 * Receive — a stand-alone button on a receipt (Bill, 2026-11-11: not buried in Workflow).
 * One click, one act:
 *   - edits not yet saved  → saves them; saving a receipt receives what was typed (readme 108 R1);
 *   - a held receipt, no edits → the receive command puts what is planned on the shelf (R2).
 * Off when nothing is pending, and on a journalized receipt (locked).
 */
import React, { useState } from 'react';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';
import apiClient from '@/api/axios';
import { refusalMessage } from '@/hooks/useRecordForm';

/** What a held receipt has planned and not yet received, over its lines. */
export function waitingToReceive(record: any): number {
  return (record?.lines || []).reduce((sum: number, line: any) => {
    const q = line?.quantity || {};
    return sum + Math.max(Number(q.staged || 0) - Number(q.active || 0), 0);
  }, 0);
}

export interface ReceiveButtonProps {
  record: any;                 // the receipt as loaded
  hasChanges: boolean;         // the form holds edits not yet saved
  saving: boolean;
  onSave: () => Promise<void> | void;
  onReceived: () => void;      // reload the record
}

const ReceiveButton: React.FC<ReceiveButtonProps> = ({ record, hasChanges, saving, onSave, onReceived }) => {
  const dispatch = useDispatch();
  const [busy, setBusy] = useState(false);
  const journalized = !!record?.dt_journaled;
  const waiting = waitingToReceive(record);
  const active = !journalized && (hasChanges || waiting > 0);
  const why = journalized ? 'This receipt is journalized: it is locked.'
    : hasChanges ? 'Save these changes: the quantities typed are received.'
    : waiting > 0 ? `${waiting} planned and not yet received: put them on the shelf.`
    : 'Nothing is pending: every quantity on this receipt is received.';

  const click = async () => {
    if (!active || busy) return;
    if (hasChanges) { await onSave(); return; }
    setBusy(true);
    try {
      const res = await apiClient.post(`/wcapi/receipt/${record.id}/receive/`, {});
      const notes = res.data?.data?.result?.messages;
      dispatch(showToast({ message: ['Received', ...(Array.isArray(notes) ? notes.filter(Boolean) : [])].join('. '), type: 'success' }));
      onReceived();
    } catch (err: any) {
      dispatch(showToast({ message: `Receive failed: ${refusalMessage(err)}`, type: 'error' }));
    } finally {
      setBusy(false);
    }
  };

  return (
    <button type="button" data-wc="receipt-receive" disabled={!active || busy || saving} title={why} onClick={click}
      className={`ml-auto text-sm px-3 py-0.5 rounded font-medium ${active
        ? 'bg-blue-600 text-white hover:bg-blue-700'
        : 'bg-slate-100 dark:bg-slate-700 text-slate-400 cursor-not-allowed'}`}>
      {busy ? 'Receiving…' : 'Receive'}
    </button>
  );
};

export default ReceiveButton;
