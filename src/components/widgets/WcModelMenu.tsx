/* LastChecked: 2026-08-02 | WhereUsed: TransactionDetail toolbar | WhoCreated: Claude */
/**
 * WcModelMenu — model-specific action dropdown.
 *
 * One button per model. Opens a dropdown of model-specific features.
 * Actions declared in the layout JSON's "actions" array.
 * Same toolbar, different dropdown per model. JSON-driven.
 *
 * Usage:
 *   <WcModelMenu
 *     modelName="order"
 *     actions={["post_to_invoice", "post_to_po", "apply_discount"]}
 *     onAction={(actionId) => handleAction(actionId)}
 *   />
 */
import React, { useState, useRef, useEffect } from 'react';

export interface ModelAction {
  id: string;
  label: string;
  icon?: string;
  separator?: boolean;
}

// Known actions with labels — layout JSON only needs the ID
const ACTION_LABELS: Record<string, string> = {
  post_to_invoice: 'Post to Invoice',
  post_to_order: 'Post to Order',
  post_to_proposal: 'Post to Proposal',
  post_to_po: 'Post to PO',
  apply_payment: 'Apply Payment',
  apply_discount: 'Apply Discount',
  receive: 'Receive',
  clone: 'Clone',
  convert: 'Convert',
  post_gl: 'Post to GL',
  reverse_gl: 'Reverse GL',
  create_po: 'Create PO from Lines',
  ship: 'Ship',
  assign_org: 'Assign Customer/Vendor',
  add_task: 'Add Task',
  add_note: 'Add Note',
  add_document: 'Attach Document',
  print_packing_slip: 'Print Packing Slip',
  print_pick_list: 'Print Pick List',
};

export interface WcModelMenuProps {
  modelName: string;
  actions: string[];
  onAction: (actionId: string) => void;
  disabled?: boolean;
}

export const WcModelMenu: React.FC<WcModelMenuProps> = ({
  modelName, actions, onAction, disabled,
}) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  const label = modelName.charAt(0).toUpperCase() + modelName.slice(1).replace(/_/g, ' ');

  const handleClick = (e: React.MouseEvent) => {
    if (e.shiftKey) {
      // Shift+click: open Setting to add/edit model actions
      window.open(`/setting?parent_model=${modelName}&purpose=detail_layout`, '_blank');
      return;
    }
    setOpen(!open);
  };

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        disabled={disabled}
        onClick={handleClick}
        className={`
          inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded border transition-colors
          ${open
            ? 'bg-blue-600 text-white border-blue-600'
            : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 border-slate-300 dark:border-slate-600'
          }
          disabled:opacity-50 disabled:cursor-not-allowed
        `}
      >
        {label} ▾
      </button>

      {open && (
        <div className="absolute left-0 top-full mt-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg shadow-lg py-1 min-w-[200px] z-50">
          {actions.length > 0 ? actions.map((actionId) => {
            const actionLabel = ACTION_LABELS[actionId] || actionId.replace(/_/g, ' ');
            return (
              <button
                key={actionId}
                type="button"
                onClick={() => { onAction(actionId); setOpen(false); }}
                className="w-full text-left px-3 py-1.5 text-sm text-slate-700 dark:text-slate-200 hover:bg-blue-50 dark:hover:bg-blue-900/20 hover:text-blue-700 dark:hover:text-blue-400 transition-colors"
              >
                {actionLabel}
              </button>
            );
          }) : (
            <div className="px-3 py-2 text-xs text-slate-400">
              No actions configured. Shift+click to add.
            </div>
          )}
        </div>
      )}
    </div>
  );
};
