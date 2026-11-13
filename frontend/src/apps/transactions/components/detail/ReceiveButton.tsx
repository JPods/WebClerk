/* LastChecked: 2026-11-13 | WhereUsed: DbForm | WhoCreated: Claude */
/**
 * Receive — a stand-alone button on a receipt (Bill, 2026-11-11: not buried in Workflow).
 * It saves the edits; saving a receipt receives what was typed. A receipt has no hold (Bill,
 * 2026-11-13): it is made when the goods are here. Off when nothing is typed, and on a
 * journalized receipt (locked).
 */
import React from 'react';

export interface ReceiveButtonProps {
  record: any;                 // the receipt as loaded
  hasChanges: boolean;         // the form holds edits not yet saved
  saving: boolean;
  onSave: () => Promise<void> | void;
}

const ReceiveButton: React.FC<ReceiveButtonProps> = ({ record, hasChanges, saving, onSave }) => {
  const journalized = !!record?.dt_journaled;
  const active = !journalized && hasChanges;
  const why = journalized ? 'This receipt is journalized: it is locked.'
    : hasChanges ? 'Save these changes: the quantities typed are received.'
    : 'Nothing is pending: every quantity on this receipt is received.';
  return (
    <button type="button" data-wc="receipt-receive" disabled={!active || saving} title={why}
      onClick={() => { if (active) void onSave(); }}
      className={`ml-auto text-sm px-3 py-0.5 rounded font-medium ${active
        ? 'bg-blue-600 text-white hover:bg-blue-700'
        : 'bg-slate-100 dark:bg-slate-700 text-slate-400 cursor-not-allowed'}`}>
      Receive
    </button>
  );
};

export default ReceiveButton;
