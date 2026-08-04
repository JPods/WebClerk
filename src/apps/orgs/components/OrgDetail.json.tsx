/* LastChecked: 2026-08-03 | WhereUsed: Router, protectedRoutesConfig | WhoCreated: Claude */
/**
 * OrgDetailJson — JSON-driven org detail page.
 *
 * Works for customer, vendor, manufacturer, employee, rep.
 * Same pattern as TransactionDetail and ContactDetailJson:
 * - Layout JSON from detail_layout Setting drives rendering
 * - CommPanel for communications tab
 * - OrgPanel not needed here (this IS the org detail)
 * - Reuses RecordToolbar, FieldRow, existing panels
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import type { RootState } from '@/store';
import { showToast } from '@/store/slices/toastSlice';
import { getRecord, saveRecord } from '@/api/wcapi';
import { useWindowManager } from '@/context/WindowManagerContext';
import { useDetailLayout } from '@/hooks/useDetailLayout';
import { selectCompanyInfo, selectLogos } from '@/store/slices/companySlice';
import { withDevIdentifier } from '@/components/common/DevIdentifier';

import FieldRow from '@/apps/transactions/components/detail/FieldRow';
import RecordToolbar from '@/components/common/RecordToolbar';
import { CommPanel } from '@/apps/communications/components';
import CommentsPanel from '@/apps/common/components/panels/CommentsPanel';
import { DocumentsPanel } from '@/apps/common/components/panels';
import ActionsPanel from '@/apps/common/components/panels/ActionsPanel';
import DataGrid from '@/components/common/DataGrid';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface OrgDetailJsonProps {
  modelName?: string;
  recordId?: number;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const OrgDetailJson: React.FC<OrgDetailJsonProps> = ({ modelName: propModel, recordId: propId }) => {
  const params = useParams<{ model?: string; id?: string }>();
  const modelName = propModel || params.model || 'customer';
  const recordId = propId || (params.id ? Number(params.id) : 0);

  const dispatch = useDispatch();
  const windowManager = useWindowManager();
  const authUser = useSelector((s: RootState) => s.auth?.user);
  const companyInfo = useSelector(selectCompanyInfo);
  const logos = useSelector(selectLogos);
  const documentText = useSelector((s: RootState) => (s as any).company?.document_text) || {};

  const { layout, loading: layoutLoading, invalidate: invalidateLayout } = useDetailLayout(modelName);

  const [data, setData] = useState<any>(null);
  const [editData, setEditData] = useState<any>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('summary');
  const [designMode, setDesignMode] = useState(false);
  const [designLayout, setDesignLayout] = useState<any>(null);

  const activeLayout = designMode && designLayout ? designLayout : layout;
  const autoEdit = authUser?.prefs?.layout?.detail?.auto_edit === true;

  // Fetch
  const fetchData = useCallback(async () => {
    if (!recordId) return;
    setLoading(true);
    try {
      const response = await getRecord(modelName, recordId);
      const record = response?.record || response;

      // Fetch primary contact if contact_id exists
      const contactId = record?.contact_id || record?.contact;
      if (contactId) {
        try {
          const ctResp = await getRecord('contact', contactId);
          const ct = ctResp?.record || ctResp;
          if (ct) record._contact = ct;
        } catch { /* contact not found */ }
      }

      setData(record);
      setEditData(record);
    } catch {
      dispatch(showToast({ message: `Failed to load ${modelName}`, type: 'error' }));
    }
    setLoading(false);
  }, [modelName, recordId, dispatch]);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    if (autoEdit && data && !isEditing) {
      setEditData({ ...data });
      setIsEditing(true);
    }
  }, [autoEdit, data]); // eslint-disable-line react-hooks/exhaustive-deps

  // Edit handlers
  const handleEdit = () => { setEditData({ ...data }); setIsEditing(true); };
  const handleCancel = () => { setEditData(data); setIsEditing(false); };

  const handleFieldChange = useCallback((field: string, value: unknown) => {
    setEditData((prev: any) => {
      if (!prev) return prev;
      if (!field.includes('.')) return { ...prev, [field]: value };
      const parts = field.split('.');
      const clone = JSON.parse(JSON.stringify(prev));
      let obj = clone;
      for (let i = 0; i < parts.length - 1; i++) {
        if (obj[parts[i]] == null || typeof obj[parts[i]] !== 'object') obj[parts[i]] = {};
        obj = obj[parts[i]];
      }
      obj[parts[parts.length - 1]] = value;
      return clone;
    });
  }, []);

  const handleSave = async () => {
    if (!editData) return;
    setSaving(true);
    try {
      const { uuid: _u, metadata: _m, refs: _r, prefs: _p, _contact: _c, ...clean } = editData;
      await saveRecord(modelName, clean);
      dispatch(showToast({ message: `${modelName} saved`, type: 'success' }));
      setIsEditing(false);
      fetchData();
    } catch {
      dispatch(showToast({ message: 'Save failed', type: 'error' }));
    }
    setSaving(false);
  };

  const handleAddNew = async () => {
    try {
      const res = await saveRecord(modelName, { is_active: true });
      const newId = res?.record?.id || res?.id;
      if (newId) windowManager.ensureWindow(`/${modelName}/${newId}`, `${modelName} #${newId}`);
    } catch {
      dispatch(showToast({ message: `Failed to create ${modelName}`, type: 'error' }));
    }
  };

  // Loading
  if (loading || layoutLoading) {
    return <div className="flex items-center justify-center py-20 text-slate-400">Loading {modelName}...</div>;
  }
  if (!data || !activeLayout) {
    return <div className="flex items-center justify-center py-20 text-slate-400">Record not found</div>;
  }

  const currentData = isEditing ? editData : data;
  const headerSection = activeLayout.sections?.find((s: any) => s.type === 'header') as any;
  const tabsSection = activeLayout.sections?.find((s: any) => s.type === 'tabs') as any;
  const columns = headerSection?.columns || [];
  const tabs = tabsSection?.tabs || [
    { label: 'Summary', content: 'summary' },
    { label: 'Contacts', content: 'contacts' },
    { label: 'Communications', content: 'communications' },
    { label: 'Transactions', content: 'transactions' },
    { label: 'Actions', content: 'actions' },
    { label: 'Documents', content: 'documents' },
    { label: 'Notes', content: 'notes' },
  ];

  return (
    <div className="flex flex-col h-full overflow-hidden" data-wc={`${modelName}-detail`}>
      {/* Header bar */}
      <div className="flex items-center gap-2 px-4 py-1 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shrink-0">
        <span className="text-sm font-bold text-slate-900 dark:text-white capitalize">{modelName}</span>
        <span className="text-sm font-mono text-slate-600 dark:text-slate-400">{data.ida || `#${data.id}`}</span>
        <span className="text-xs text-slate-500">{data.company || data.attention || ''}</span>
      </div>

      {/* Toolbar */}
      <RecordToolbar
        data={data}
        currentData={currentData}
        modelName={modelName}
        layout={activeLayout}
        isEditing={isEditing}
        saving={saving}
        companyInfo={companyInfo}
        logos={logos}
        documentText={documentText}
        userRole={authUser?.role}
        onEdit={handleEdit}
        onAddNew={handleAddNew}
        onSave={handleSave}
        onCancel={handleCancel}
        designMode={designMode}
        onToggleDesign={() => {
          if (designMode) { setDesignMode(false); setDesignLayout(null); invalidateLayout(); }
          else { setDesignMode(true); if (layout) setDesignLayout(JSON.parse(JSON.stringify(layout))); }
        }}
      />

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {/* Header columns */}
        {headerSection && (
          <div className={`grid gap-3`} style={{ gridTemplateColumns: `repeat(${columns.length}, 1fr)` }}>
            {columns.map((col: any, colIdx: number) => (
              <div key={colIdx} className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-3">
                <div className="text-xs font-bold text-slate-700 dark:text-slate-200 mb-2 border-b border-slate-100 dark:border-slate-700 pb-1 flex items-center gap-2">
                  <span>{col.title}</span>
                  {col.title_ida && data.id && (
                    <span className="font-mono text-slate-400 text-[10px]">#{data.id}</span>
                  )}
                </div>
                {(col.fields || []).map((f: any) => (
                  <FieldRow
                    key={f.field}
                    field={f.field}
                    label={f.label}
                    data={currentData}
                    isEditing={isEditing}
                    options={f.options}
                    fieldType={f.type}
                    help={f.help}
                    onChange={handleFieldChange}
                  />
                ))}
                {col.action_summary && data.actions?.items?.[0] && (
                  <div className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-700">
                    <div className="text-[10px] text-slate-400">Next Action</div>
                    <div className="text-xs text-slate-600">{data.actions.items[0].action} — {data.actions.items[0].status}</div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Tabs */}
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
          <div className="flex border-b border-slate-200 dark:border-slate-700 overflow-x-auto">
            {tabs.map((tab: any) => (
              <button
                key={tab.content}
                onClick={() => setActiveTab(tab.content)}
                className={`px-4 py-2 text-xs font-medium whitespace-nowrap border-b-2 transition-colors ${
                  activeTab === tab.content
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-slate-500 hover:text-slate-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <div className="p-2">
            {activeTab === 'summary' && (
              <div className="p-4 text-xs text-slate-400">Summary — coming soon</div>
            )}
            {activeTab === 'contacts' && (
              <div className="p-2">
                <DataGrid
                  records={data.refs?.links?.contact || []}
                  columns={['attention', 'email', 'phone', 'title']}
                  sort={null}
                  onSort={() => {}}
                  onSelectRecord={(id) => windowManager.ensureWindow(`/contact/${id}`, `Contact #${id}`)}
                  fontSize={11}
                />
              </div>
            )}
            {activeTab === 'communications' && data.contact_id && (
              <CommPanel
                contactId={data.contact_id}
                emails={data._contact?.refs?.links?.email || data.refs?.links?.email || []}
                phones={data._contact?.refs?.links?.phone || data.refs?.links?.phone || []}
                addresses={data._contact?.refs?.links?.address || data.refs?.links?.address || []}
                domains={data._contact?.refs?.links?.domain || data.refs?.links?.domain || []}
                onRefresh={fetchData}
              />
            )}
            {activeTab === 'transactions' && (
              <div className="p-2">
                <DataGrid
                  records={[
                    ...(data.refs?.links?.order || []).map((o: any) => ({ ...o, type: 'Order' })),
                    ...(data.refs?.links?.invoice || []).map((i: any) => ({ ...i, type: 'Invoice' })),
                  ]}
                  columns={['type', 'ida', 'status', 'total']}
                  sort={null}
                  onSort={() => {}}
                  onSelectRecord={(id) => {}}
                  fontSize={11}
                />
              </div>
            )}
            {activeTab === 'actions' && (
              <ActionsPanel entityType={modelName} entityId={data.id} data={data.actions?.items || []} isEditing={isEditing} />
            )}
            {activeTab === 'documents' && (
              <DocumentsPanel parent_model={modelName} parentId={data.id} data={data.refs?.links?.document} isEditing={isEditing} />
            )}
            {activeTab === 'notes' && (
              <CommentsPanel entityType={modelName} entityId={data.id} data={data.comments} isEditing={isEditing}
                onChange={(comments: any) => handleFieldChange('comments', comments)} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default withDevIdentifier(OrgDetailJson, 'OrgDetailJson');
