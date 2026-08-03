/* LastChecked: 2026-08-02 | WhereUsed: AdminWorkbench, Router | WhoCreated: Claude */
/**
 * TransactionDetail — JSON-driven transaction detail renderer.
 *
 * Thin orchestrator: fetches data, manages edit state, delegates rendering
 * to sub-components in ./detail/.
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { getRecord, saveRecord, saveTransactionWithLines } from '@/api/wcapi';
import { showToast } from '@/store/slices/toastSlice';
import { useDispatch, useSelector } from 'react-redux';
import type { RootState } from '@/store';
import { useWindowManager } from '@/context/WindowManagerContext';
import { useDetailLayout } from '@/hooks/useDetailLayout';
import { applyCustomerDefaults } from '@/apps/transactions/utils/applyCustomerDefaults';
import { getNextLineNumber } from '../utils/lineHelpers';
import type { TransactionLine } from '../types/transactionTypes';
import { selectCompanyInfo, selectLogos } from '@/store/slices/companySlice';

import { useCustomerSearch } from './detail/CustomerSearch';
import HeaderRenderer from './detail/HeaderRenderer';
import LineCardRenderer from './detail/LineCardRenderer';
import TabsRenderer from './detail/TabsRenderer';
import TransactionToolbar from './detail/TransactionToolbar';
import DesignMode from './detail/DesignMode';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TransactionDetailProps {
  modelName?: string;
  recordId?: number;
  onClose?: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const TransactionDetail: React.FC<TransactionDetailProps> = ({
  modelName: propModelName,
  recordId: propRecordId,
  onClose,
}) => {
  const params = useParams<{ model?: string; id?: string }>();
  const modelName = propModelName || params.model || 'order';
  const recordId = propRecordId || (params.id ? Number(params.id) : 0);

  const dispatch = useDispatch();
  const windowManager = useWindowManager();
  const authUser = useSelector((s: RootState) => s.auth?.user);
  const companyInfo = useSelector(selectCompanyInfo);
  const logos = useSelector(selectLogos);
  const documentText = useSelector((s: RootState) => (s as any).company?.document_text) || {};
  const loggedInUserName = authUser?.name || authUser?.email || 'User';

  // ── Layout ───────────────────────────────────────────────────────
  const { layout, loading: layoutLoading } = useDetailLayout(modelName);

  // ── Record state ─────────────────────────────────────────────────
  const [data, setData] = useState<any>(null);
  const [editData, setEditData] = useState<any>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('summary');
  const [designMode, setDesignMode] = useState(false);
  const [designLayout, setDesignLayout] = useState<any>(null);

  // Active layout — design mode uses local copy, normal mode uses cached
  const activeLayout = designMode && designLayout ? designLayout : layout;

  // ── Fetch record ─────────────────────────────────────────────────
  const fetchData = useCallback(async () => {
    if (!recordId) return;
    setLoading(true);
    try {
      const response = await getRecord(modelName, recordId);
      const record = response?.record || response;

      // Fetch customer config if customer_id exists
      const custId = record?.customer_id || record?.customer;
      if (custId) {
        try {
          const custResp = await getRecord('customer', custId);
          const cust = custResp?.record || custResp;
          if (cust?.config) record.customer_config = cust.config;
          record.customer_company = cust?.company || cust?.display_name || cust?.name || '';
          if (!record.price_level && cust?.price_level) record.price_level = cust.price_level;
          if (!record.terms && cust?.terms) record.terms = cust.terms;
        } catch { /* customer not found */ }
      }

      setData(record);
      setEditData(record);
    } catch (err) {
      dispatch(showToast({ message: `Failed to load ${modelName}`, type: 'error' }));
    } finally {
      setLoading(false);
    }
  }, [modelName, recordId, dispatch]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // ── Edit state ───────────────────────────────────────────────────
  const editTier = useMemo((): 'open' | 'pend' | 'closed' => {
    if (!data || !layout) return 'closed';
    const rules = layout.edit_rules as any;
    const statusField = rules.status_field || 'status';
    const status = String(data[statusField] || '').toLowerCase();

    if (rules.closed_statuses?.includes(status)) return 'closed';
    if (rules.pend_statuses?.includes(status)) return 'pend';
    if (rules.open_statuses?.includes(status)) return 'open';
    if (rules.locked_statuses?.includes(status)) return 'closed';
    return 'open';
  }, [data, layout]);

  const canEdit = editTier !== 'closed';
  const isPendMode = editTier === 'pend';

  // Auto-edit
  const autoEdit = authUser?.prefs?.layout?.detail?.auto_edit === true;
  useEffect(() => {
    if (autoEdit && canEdit && data && !isEditing) {
      setEditData({ ...data });
      setIsEditing(true);
    }
  }, [autoEdit, canEdit, data]);  // eslint-disable-line react-hooks/exhaustive-deps

  const handleEdit = () => {
    if (canEdit) { setEditData({ ...data }); setIsEditing(true); }
  };

  const handleAddNew = async () => {
    try {
      const res = await saveRecord(modelName, { status: 'open' });
      const newId = res?.record?.id || res?.id;
      if (newId) windowManager.ensureWindow(`/${modelName}/${newId}`, `${modelName} #${newId}`);
    } catch {
      dispatch(showToast({ message: `Failed to create ${modelName}`, type: 'error' }));
    }
  };

  const handleCancel = () => { setEditData(data); setIsEditing(false); };

  const handleFieldChange = useCallback((field: string, value: unknown) => {
    setEditData((prev: any) => {
      if (!prev) return prev;
      return { ...prev, [field]: value };
    });

    if ((field === 'customer' || field === 'customer_id') && value) {
      const custId = typeof value === 'number' ? value : Number(value);
      if (custId > 0) {
        applyCustomerDefaults(custId).then(defaults => {
          setEditData((prev: any) => prev ? { ...prev, ...defaults } : prev);
          dispatch(showToast({ message: `Customer defaults applied: ${defaults.company}`, type: 'success' }));
        }).catch(() => {
          dispatch(showToast({ message: 'Could not load customer defaults', type: 'error' }));
        });
      }
    }
  }, [dispatch]);

  const handleLinesChange = useCallback((lines: TransactionLine[]) => {
    setEditData((prev: any) => prev ? { ...prev, lines } : prev);
  }, []);

  const handleAddLine = () => {
    const lines = (isEditing ? editData : data)?.lines || [];
    const newLine: TransactionLine = {
      line_number: getNextLineNumber(lines),
      item_code: '', description: '', qty: 1, remain: 1, unit_price: 0, extended: 0,
    } as any;
    handleLinesChange([...lines, newLine]);
  };

  const handleSave = async () => {
    if (!editData) return;
    setSaving(true);
    try {
      const hasLines = editData.lines && Array.isArray(editData.lines);
      if (hasLines) { await saveTransactionWithLines(modelName, editData); }
      else { await saveRecord(modelName, editData); }
      dispatch(showToast({ message: `${modelName} saved`, type: 'success' }));
      setIsEditing(false);
      fetchData();
    } catch (err) {
      dispatch(showToast({ message: `Save failed`, type: 'error' }));
    } finally {
      setSaving(false);
    }
  };

  // ── Customer search hook ────────────────────────────────────────
  const custSearch = useCustomerSearch(handleFieldChange);

  // ── Current data (edit or read) ─────────────────────────────────
  const currentData = isEditing ? editData : data;

  // ── Loading states ──────────────────────────────────────────────
  if (layoutLoading || loading) {
    return (
      <div className="flex items-center justify-center py-20 text-slate-400">
        Loading {modelName}...
      </div>
    );
  }

  if (!data || !layout) {
    return (
      <div className="flex items-center justify-center py-20 text-slate-400">
        Record not found
      </div>
    );
  }

  // ── Render ──────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full overflow-hidden" data-wc={`${modelName}-detail`}>
      {/* Header bar */}
      <div className="flex items-center gap-2 px-4 py-1 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shrink-0 no-print">
        <span className="text-sm font-bold text-slate-900 dark:text-white capitalize">{modelName}</span>
        <span className="text-sm font-mono text-slate-600 dark:text-slate-400">{data.ida || `#${data.id}`}</span>
        {data.status && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
            {data.status}
          </span>
        )}
        {isPendMode && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">
            journalized — changes pend
          </span>
        )}
        {editTier === 'closed' && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400">
            closed
          </span>
        )}
        {designMode && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 font-medium">
            DESIGN
          </span>
        )}
      </div>

      {/* Toolbar */}
      <TransactionToolbar
        data={data}
        currentData={currentData}
        modelName={modelName}
        layout={activeLayout}
        isEditing={isEditing}
        canEdit={canEdit}
        saving={saving}
        companyInfo={companyInfo}
        logos={logos}
        documentText={documentText}
        onEdit={handleEdit}
        onAddNew={handleAddNew}
        onSave={handleSave}
        onCancel={handleCancel}
        designMode={designMode}
        userRole={authUser?.role}
        onToggleDesign={() => { setDesignMode(!designMode); if (!designMode && layout) setDesignLayout(JSON.parse(JSON.stringify(layout))); }}
      />

      {/* Design mode panel */}
      {designMode && activeLayout && (
        <div className="px-4 pt-3">
          <DesignMode
            layout={activeLayout}
            modelName={modelName}
            onLayoutChange={(newLayout) => setDesignLayout(newLayout)}
          />
        </div>
      )}

      {/* Content — scrollable */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {activeLayout.sections.map((section, idx) => {
          switch (section.type) {
            case 'header':
              return (
                <HeaderRenderer
                  key={idx}
                  section={section}
                  data={currentData}
                  isEditing={isEditing}
                  modelName={modelName}
                  onChange={handleFieldChange}
                  custSearch={{
                    open: custSearch.open,
                    query: custSearch.query,
                    results: custSearch.results,
                    searching: custSearch.searching,
                    inputRef: custSearch.inputRef,
                    onToggle: custSearch.toggle,
                    onSearch: custSearch.search,
                    onSelect: custSearch.select,
                  }}
                />
              );
            case 'line_card':
              return (
                <LineCardRenderer
                  key={idx}
                  section={section}
                  data={currentData}
                  isEditing={isEditing}
                  isLocked={editTier === 'closed'}
                  onLinesChange={handleLinesChange}
                />
              );
            case 'tabs':
              return (
                <TabsRenderer
                  key={idx}
                  section={section}
                  data={currentData}
                  isEditing={isEditing}
                  modelName={modelName}
                  activeTab={activeTab}
                  onTabChange={setActiveTab}
                  onChange={handleFieldChange}
                  onRefresh={fetchData}
                  loggedInUserName={loggedInUserName}
                />
              );
            default:
              return null;
          }
        })}
      </div>
    </div>
  );
};

export default TransactionDetail;
