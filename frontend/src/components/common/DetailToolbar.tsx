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
import { WorkflowSelect } from './WorkflowSelect';
import { manageAction } from '@/api/wcapi';
import { CurrencyDollar } from '@phosphor-icons/react';

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
  onWorkflowComplete?: (result?: any) => void;
  /** Add Payment (order) — creates a new payment record */
  onAddPayment?: () => void;
  /** Apply Payment (invoice) — applies existing payment to this invoice */
  onApplyPayment?: () => void;
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
  onWorkflowComplete,
  onAddPayment, onApplyPayment,
  className = '',
}) => {
  const dispatch = useDispatch();
  const isEditing = modeProp ? modeProp !== 'view' : (isEditingProp ?? false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  const handlePrintSelect = async (report: ReportRecord) => {
    const rec = currentData || data;
    if (!rec?.id) return;

    const config = report.config || {};

    // URL-type report — opens a page
    if (config.action === 'open_url' && config.url) {
      window.open(config.url as string, '_blank');
      return;
    }

    // Dialog-type report — emit custom event for parent to handle
    if (config.action === 'import_vcard_dialog') {
      window.dispatchEvent(new CustomEvent('wc:open-vcard-import', {
        detail: { recordId: rec.id, modelName },
      }));
      return;
    }

    // Action-type report — calls a manage action
    if (config.action) {
      const confirmMsg = config.confirm as string;
      if (confirmMsg && !confirm(confirmMsg)) return;

      // Build params from record fields
      const paramsMap = (config.params_from_record || {}) as Record<string, string>;
      const params: Record<string, unknown> = {};
      for (const [paramKey, recordField] of Object.entries(paramsMap)) {
        params[paramKey] = rec[recordField as string];
      }
      // Merge any static params
      if (config.params) Object.assign(params, config.params);

      try {
        const result = await manageAction(config.action as string, params);
        const resData = result?.data?.data ?? result?.data ?? result;

        // Download-type action — result contains file content
        if (config.download && resData && !resData.error) {
          const content = resData[config.download_field as string || 'vcard'] || resData.content || '';
          const filename = resData.filename || `${report.name || 'export'}.${config.download_ext || 'txt'}`;
          const mime = (config.download_mime as string) || 'text/vcard';
          const blob = new Blob([content], { type: mime });
          const a = document.createElement('a');
          a.href = URL.createObjectURL(blob);
          a.download = filename;
          a.click();
          URL.revokeObjectURL(a.href);
          dispatch(showToast({ message: `Downloaded ${filename}`, type: 'success' }));
        } else {
          const msg = resData?.error
            ? `Error: ${resData.error}`
            : resData?.message || `${report.name}: done`;
          dispatch(showToast({ message: msg, type: resData?.error ? 'error' : 'success' }));
        }
        onWorkflowComplete?.(resData);
      } catch (e: any) {
        dispatch(showToast({ message: `${report.name} failed: ${e.message || e}`, type: 'error' }));
      }
      return;
    }

    const printForm = config.form;
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

      <WorkflowSelect modelName={modelName} record={data} onComplete={onWorkflowComplete || (() => {})} />

      {/* Payment buttons */}
      {onAddPayment && data?.id && (
        <button
          onClick={onAddPayment}
          className="flex items-center gap-1 px-2 py-1 text-xs font-medium rounded bg-green-50 text-green-700 hover:bg-green-100 dark:bg-green-900/20 dark:text-green-400 dark:hover:bg-green-900/40 border border-green-200 dark:border-green-800 transition-colors"
          title="Enter a single payment"
        >
          <CurrencyDollar size={16} weight="bold" />
          Enter Payment
        </button>
      )}
      {onApplyPayment && data?.id && (
        <button
          onClick={onApplyPayment}
          className="flex items-center gap-1 px-2 py-1 text-xs font-medium rounded bg-green-50 text-green-700 hover:bg-green-100 dark:bg-green-900/20 dark:text-green-400 dark:hover:bg-green-900/40 border border-green-200 dark:border-green-800 transition-colors"
          title="Apply payments to invoices"
        >
          <CurrencyDollar size={16} weight="bold" />
          Apply Payments
        </button>
      )}

      {/* Status + total + balance badges */}
      <span className="flex-1" />
      {data?.status && (
        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${data.status === 'open' || data.status === 'active' ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-600'}`}>{data.status}</span>
      )}
      {data?.totals?.total != null && (
        <span className="text-xs text-slate-500">total: <span className="font-medium">${(data.totals.total ?? 0).toLocaleString()}</span></span>
      )}
      {(data?.totals?.balance ?? 0) > 0 && (
        <span className="text-xs text-red-500">bal: <span className="font-medium">${(data.totals?.balance ?? 0).toLocaleString()}</span></span>
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
