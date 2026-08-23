/* LastChecked: 2026-08-02 | WhereUsed: UiDetail, all .td views | WhoCreated: Claude */
/**
 * WcToolbar — standard toolbar for .td views.
 *
 * Renders from a button config array. Layout JSON declares which buttons show.
 * Standard buttons always available. Model-specific buttons added from layout.
 *
 * Usage:
 *   <WcToolbar
 *     buttons={[
 *       { id: 'save', label: 'Save', variant: 'primary', onClick: handleSave },
 *       { id: 'cancel', label: 'Cancel', onClick: handleCancel },
 *       { id: 'clone', label: 'Clone', onClick: handleClone },
 *       { id: 'print', label: 'Print', onClick: handlePrint },
 *       { id: 'delete', label: 'Delete', variant: 'danger', onClick: handleDelete },
 *     ]}
 *     record={{ ida: 'DEV-34', status: 'open', total: 6492, balance: 5381 }}
 *   />
 */
import React from 'react';
import { WcButton, type WcButtonProps } from './WcButton';
import { WcBadge } from './WcBadge';

export interface ToolbarButton extends WcButtonProps {
  id: string;
  position?: 'left' | 'right';  // default: left
}

export interface WcToolbarProps {
  buttons: ToolbarButton[];
  record?: {
    ida?: string;
    status?: string;
    total?: number;
    balance?: number;
  };
  className?: string;
}

const formatCurrency = (v?: number) =>
  v == null ? '' : new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v);

export const WcToolbar: React.FC<WcToolbarProps> = ({ buttons, record, className }) => {
  const leftButtons = buttons.filter(b => b.position !== 'right');
  const rightButtons = buttons.filter(b => b.position === 'right');

  return (
    <div className={`flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 ${className || ''}`}>
      {/* Record info */}
      {record && (
        <div className="flex items-center gap-2 mr-4">
          {record.ida && <span className="text-sm font-mono text-slate-700 dark:text-slate-200">{record.ida}</span>}
          {record.status && <WcBadge value={record.status} />}
          <span className="flex-1" />
          {record.totals?.total != null && (
            <span className="text-xs text-slate-500">Total: <span className="font-medium text-slate-900 dark:text-white">{formatCurrency(record.totals.total)}</span></span>
          )}
          {record.totals?.balance != null && record.totals.balance > 0 && (
            <span className="text-xs text-slate-500 ml-2">Bal: <span className="font-medium text-red-600">{formatCurrency(record.totals.balance)}</span></span>
          )}
        </div>
      )}

      {/* Left buttons */}
      <div className="flex items-center gap-1">
        {leftButtons.map(({ id, ...props }) => <WcButton key={id} {...props} />)}
      </div>

      <span className="flex-1" />

      {/* Right buttons */}
      <div className="flex items-center gap-1">
        {rightButtons.map(({ id, ...props }) => <WcButton key={id} {...props} />)}
      </div>
    </div>
  );
};
