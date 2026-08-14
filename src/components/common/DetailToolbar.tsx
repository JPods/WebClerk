/* LastChecked: 2026-08-06 | WhereUsed: All ui.json detail pages, all Display pages | WhoCreated: Claude */
/**
 * DetailToolbar — universal action bar for any record detail page.
 *
 * Print templates come from Report records (model_name + output_type='print').
 * Report.config.layout holds a PrintLayout JSON that UniversalPrint renders.
 */
import React, { useState } from 'react';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';
import { openUniversalPrint } from '@/components/print/UniversalPrint';
import { openPrintWindow } from '@/apps/transactions/components/detail/TransactionPrint';
import PrintReportDropdown from './PrintReportDropdown';
import type { ReportRecord } from './PrintReportDropdown';
import ToolbarIcon from './ToolbarIcon';
import { TB } from './toolbarActions';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface DetailToolbarProps {
  data?: any;
  currentData?: any;
  modelName: string;
  layout?: any;
  mode?: 'add' | 'edit' | 'view';
  isEditing?: boolean;
  canEdit?: boolean;
  saving?: boolean;
  canDelete?: boolean;
  companyInfo?: any;
  logos?: any;
  documentText?: any;
  designMode?: boolean;
  userRole?: string;
  onEdit?: () => void;
  onAddNew?: () => void;
  onSave?: () => void;
  onCancel?: () => void;
  onDelete?: () => void;
  onToggleDesign?: () => void;
  className?: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const DetailToolbar: React.FC<DetailToolbarProps> = ({
  data, currentData, modelName, layout,
  mode: modeProp, isEditing: isEditingProp,
  canEdit = true, saving = false, canDelete = true,
  companyInfo, logos, documentText,
  onEdit, onAddNew, onSave, onCancel, onDelete,
  designMode, userRole, onToggleDesign,
  className = '',
}) => {
  const dispatch = useDispatch();
  const isEditing = modeProp ? modeProp !== 'view' : (isEditingProp ?? false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  const handlePrintSelect = (report: ReportRecord) => {
    const rec = currentData || data;
    if (!rec?.id) return;

    const printForm = report.config?.form;
    if (printForm) {
      // Report has a form.json — use UniversalPrint
      openUniversalPrint(rec, companyInfo, printForm);
    } else if (layout) {
      // Fallback to detail-layout-based HTML print
      openPrintWindow(rec, companyInfo, logos, documentText, modelName, layout);
    } else {
      dispatch(showToast({ message: `${report.name || 'Report'}: no layout configured`, type: 'info' }));
    }
  };

  return (
    <div className={`flex items-center gap-1 px-2 py-1 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 no-print ${className}`}
      style={{ minHeight: 60 }}>

      {onAddNew && (
        <ToolbarIcon action={TB.addRecord} title="Add New Record" onClick={onAddNew} />
      )}

      <ToolbarIcon action={TB.save} title={saving ? 'Saving...' : 'Save'} disabled={!isEditing || saving} onClick={onSave} />
      <ToolbarIcon action={TB.discard} title="Cancel" disabled={!isEditing} onClick={onCancel} />

      {/* Report / Print — reads Report records */}
      <PrintReportDropdown
        modelKey={modelName}
        disabled={!data?.id}
        onSelect={handlePrintSelect}
      />

      <ToolbarIcon action={TB.modelMenu} title={`${modelName} menu`}
        onClick={() => dispatch(showToast({ message: `${modelName} menu: coming soon`, type: 'info' }))} />

      {/* Status + total + balance badges */}
      <span className="flex-1" />
      {data?.status && (
        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${data.status === 'open' || data.status === 'active' ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-600'}`}>{data.status}</span>
      )}
      {data?.totals?.total != null && (
        <span className="text-xs text-slate-500">Total: <span className="font-medium">${(data.totals.total ?? 0).toLocaleString()}</span></span>
      )}
      {(data?.totals?.balance ?? data?.balance ?? 0) > 0 && (
        <span className="text-xs text-red-500">Bal: <span className="font-medium">${((data.totals?.balance ?? data?.balance ?? 0)).toLocaleString()}</span></span>
      )}
      {data?.id && <span className="text-xs font-mono text-slate-400 dark:text-slate-500">#{data.id}</span>}

      {/* Delete — far right, single confirm */}
      {canDelete && onDelete && (
        deleteConfirm ? (
          <button
            className="ml-2 px-2 py-0.5 text-xs font-semibold rounded bg-red-600 text-white hover:bg-red-700 transition-colors"
            onClick={() => { setDeleteConfirm(false); onDelete(); }}
            onBlur={() => setDeleteConfirm(false)}
            autoFocus
            title="Click again to confirm delete"
          >
            Confirm?
          </button>
        ) : (
          <ToolbarIcon action={TB.deleteRecord} title="Delete Record" danger
            disabled={!canEdit || !data?.id}
            onClick={() => setDeleteConfirm(true)} />
        )
      )}
    </div>
  );
};

export default DetailToolbar;
export { DetailToolbar };
