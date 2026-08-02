/* LastChecked: 2026-08-02 | WhereUsed: TransactionDetail | WhoCreated: Claude */
import React from 'react';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';
import { WcModelMenu } from '@/components/widgets/WcModelMenu';
import { openPrintWindow } from './TransactionPrint';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TransactionToolbarProps {
  data: any;
  currentData: any;
  modelName: string;
  layout: any;
  isEditing: boolean;
  canEdit: boolean;
  saving: boolean;
  companyInfo: any;
  logos: any;
  documentText: any;
  onEdit: () => void;
  onAddNew: () => void;
  onSave: () => void;
  onCancel: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const TransactionToolbar: React.FC<TransactionToolbarProps> = ({
  data,
  currentData,
  modelName,
  layout,
  isEditing,
  canEdit,
  saving,
  companyInfo,
  logos,
  documentText,
  onEdit,
  onAddNew,
  onSave,
  onCancel,
}) => {
  const dispatch = useDispatch();

  // Get model-specific actions from layout JSON
  const lineCardSection = layout.sections.find((s: any) => s.type === 'line_card') as any;
  const modelActions: string[] = lineCardSection?.actions || [];

  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 no-print">
      {/* Record info */}
      <span className="text-sm font-mono text-slate-700 dark:text-slate-200">{data.ida}</span>
      <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${data.status === 'open' ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-600'}`}>{data.status}</span>
      <span className="text-xs text-slate-500 ml-2">Total: <span className="font-medium">${(data.totals?.total ?? 0).toLocaleString()}</span></span>
      {(data.totals?.balance ?? 0) > 0 && (
        <span className="text-xs text-red-500">Bal: <span className="font-medium">${(data.totals?.balance ?? 0).toLocaleString()}</span></span>
      )}

      <span className="w-4" />

      {/* Standard buttons */}
      {canEdit && !isEditing && (
        <button onClick={onEdit} className="px-3 py-1.5 text-sm font-medium bg-blue-600 text-white rounded border border-blue-600 hover:bg-blue-700">Edit</button>
      )}
      <button onClick={onAddNew}
        className="px-3 py-1.5 text-sm font-medium bg-green-600 text-white rounded border border-green-600 hover:bg-green-700">Add</button>
      {isEditing && (
        <>
          <button onClick={onSave} disabled={saving} className="px-3 py-1.5 text-sm font-medium bg-blue-600 text-white rounded border border-blue-600 hover:bg-blue-700 disabled:opacity-50">
            {saving ? 'Saving...' : 'Save'}
          </button>
          <button onClick={onCancel} className="px-3 py-1.5 text-sm font-medium bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 rounded border border-slate-300 dark:border-slate-600 hover:bg-slate-50">Cancel</button>
        </>
      )}
      <div className="relative group/report">
        <button className="px-3 py-1.5 text-sm font-medium bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 rounded border border-slate-300 dark:border-slate-600 hover:bg-slate-50">
          Report ▾
        </button>
        <div className="hidden group-hover/report:block absolute top-full left-0 pt-1 z-50">
          <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded shadow-lg min-w-36">
            <button onClick={() => openPrintWindow(currentData, companyInfo, logos, documentText, modelName)} className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 dark:hover:bg-slate-700 rounded-t">Print</button>
            <button onClick={() => dispatch(showToast({ message: 'Email: coming soon', type: 'info' }))} className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 dark:hover:bg-slate-700">Email</button>
            <button onClick={() => dispatch(showToast({ message: 'Labels: coming soon', type: 'info' }))} className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 dark:hover:bg-slate-700">Labels</button>
            <button onClick={() => dispatch(showToast({ message: 'Clone: coming soon', type: 'info' }))} className="w-full text-left px-3 py-1.5 text-xs hover:bg-slate-50 dark:hover:bg-slate-700 border-t border-slate-100 dark:border-slate-700 rounded-b">Clone</button>
          </div>
        </div>
      </div>

      {/* Model-specific menu */}
      <WcModelMenu
        modelName={modelName}
        actions={modelActions}
        onAction={(actionId) => dispatch(showToast({ message: `${actionId}: coming soon`, type: 'info' }))}
      />

      <span className="flex-1" />

      {/* Delete -- far right */}
      {canEdit && (
        <button onClick={() => dispatch(showToast({ message: 'Delete: coming soon', type: 'info' }))}
          className="px-3 py-1.5 text-sm font-medium text-red-600 rounded border border-red-300 hover:bg-red-50">
          Delete
        </button>
      )}
    </div>
  );
};

export default TransactionToolbar;
