/* LastChecked: 2026-08-03 | WhereUsed: Router, protectedRoutesConfig | WhoCreated: Claude */
/**
 * OrgDetailJson — JSON-driven org detail page.
 *
 * Works for customer, vendor, manufacturer, employee, rep.
 * Same pattern as UiDetail and ContactDetailJson:
 * - Layout JSON from detail_layout Setting drives rendering
 * - CommPanel for communications tab
 * - OrgPanel not needed here (this IS the org detail)
 * - Reuses DetailToolbar, FieldRow, existing panels
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
import DetailToolbar from '@/components/common/DetailToolbar';
import { CommPanel } from '@/apps/communications/components';
import CommentsPanel from '@/apps/common/components/panels/CommentsPanel';
import { DocumentsPanel } from '@/apps/common/components/panels';
import ActionsPanel from '@/apps/common/components/panels/ActionsPanel';
import DataGrid from '@/components/common/DataGrid';
import PanelSectionRenderer from '@/apps/transactions/components/detail/PanelSectionRenderer';
import JsonSectionRenderer from '@/apps/transactions/components/detail/JsonSectionRenderer';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface OrgDetailJsonProps {
  modelName?: string;
  recordId?: number;
  inline?: boolean;
  onRegisterActions?: (actions: { save?: () => void; cancel?: () => void; addNew?: () => void; delete?: () => void }) => void;
  onEditStateChange?: (editing: boolean) => void;
  [key: string]: any;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const OrgDetailJson: React.FC<OrgDetailJsonProps> = ({ modelName: propModel, recordId: propId, inline, onRegisterActions, onEditStateChange }) => {
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
    } catch (err: any) {
      const resp = err?.response?.data;
      const detail = resp?.detail || resp?.message || resp?.error?.details || err?.message || String(err);
      console.error('[OrgDetail] Save failed:', { err, response: resp, status: err?.response?.status });
      dispatch(showToast({ message: `Save failed: ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`, type: 'error' }));
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

  // Register actions for parent toolbar
  useEffect(() => {
    if (onRegisterActions) onRegisterActions({ save: handleSave, cancel: handleCancel, addNew: handleAddNew });
  }, [onRegisterActions, handleSave, handleCancel, handleAddNew]);
  useEffect(() => {
    if (onEditStateChange) onEditStateChange(isEditing);
  }, [isEditing, onEditStateChange]);

  // Loading
  if (loading || layoutLoading) {
    return <div className="flex items-center justify-center py-20 text-slate-400">Loading {modelName}...</div>;
  }
  if (!data || !activeLayout) {
    return <div className="flex items-center justify-center py-20 text-slate-400">Record not found</div>;
  }

  const currentData = isEditing ? editData : data;
  const sections = activeLayout.sections || [];

  // Fallback: if no sections defined, build default org sections
  const effectiveSections = sections.length > 0 ? sections : [
    { type: 'header', columns: [
      { title: 'Identity', fields: [
        { field: 'ida', label: 'ID' }, { field: 'display_name', label: 'Name' },
        { field: 'type', label: 'Type' }, { field: 'status', label: 'Status' },
      ]},
      { title: 'Contact', fields: [
        { field: 'attention', label: 'Attn' }, { field: 'email', label: 'Email' },
        { field: 'phone', label: 'Phone' }, { field: 'address_full', label: 'Address' },
      ]},
      { title: 'Account', fields: [
        { field: 'price_level', label: 'Price Level' }, { field: 'terms', label: 'Terms' },
      ]},
    ]},
    { type: 'panel', content: 'transactions', label: 'Transactions' },
    { type: 'panel', content: 'contacts', label: 'Contacts' },
    { type: 'panel', content: 'notes', label: 'Comments' },
    { type: 'json_tree', label: 'Data', collapsed: true },
  ];

  const renderSection = (section: any, idx: number) => {
    switch (section.type) {
      case 'header': {
        const columns = section.columns || [];
        return (
          <div key={idx} className="grid gap-3" style={{ gridTemplateColumns: `repeat(${columns.length}, 1fr)` }}>
            {columns.map((col: any, colIdx: number) => (
              <div key={colIdx} className="bg-[var(--db-surface,#fff)] rounded-lg border border-[var(--db-border,#dee2e6)] p-3">
                <div className="flex items-center justify-between text-xs font-bold text-[var(--db-text,#212529)] mb-2 border-b border-[var(--db-border,#dee2e6)] pb-1">
                  <span>{col.title}</span>
                  {colIdx === 0 && data.ida && (
                    <span className="font-mono font-normal text-[var(--db-text-muted,#6c757d)]">{data.ida}</span>
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
                  <div className="mt-2 pt-2 border-t border-[var(--db-border,#dee2e6)]">
                    <div className="text-[10px] text-[var(--db-text-muted,#6c757d)]">Next Action</div>
                    <div className="text-xs text-[var(--db-text,#212529)]">{data.actions.items[0].action} — {data.actions.items[0].status}</div>
                  </div>
                )}
              </div>
            ))}
          </div>
        );
      }
      case 'panel':
        return (
          <PanelSectionRenderer
            key={idx}
            section={section}
            data={currentData}
            isEditing={isEditing}
            modelName={modelName}
            onChange={handleFieldChange}
            onRefresh={fetchData}
          />
        );
      case 'json_tree':
        return (
          <JsonSectionRenderer
            key={idx}
            section={section}
            data={currentData}
            isEditing={isEditing}
            modelName={modelName}
            onChange={handleFieldChange}
          />
        );
      case 'tabs': {
        const tabs = section.tabs || [];
        return (
          <div key={idx} className="bg-[var(--db-surface,#fff)] rounded-lg border border-[var(--db-border,#dee2e6)]">
            <div className="flex border-b border-[var(--db-border,#dee2e6)] overflow-x-auto">
              {tabs.map((tab: any) => (
                <button
                  key={tab.content}
                  onClick={() => setActiveTab(tab.content)}
                  className={`px-4 py-2 text-xs font-medium whitespace-nowrap border-b-2 transition-colors ${
                    activeTab === tab.content
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-[var(--db-text-muted,#6c757d)] hover:text-[var(--db-text,#212529)]'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
            <div className="p-2">
              {activeTab === 'summary' && (
                <div className="p-4 text-xs text-[var(--db-text-muted,#6c757d)]">Summary — coming soon</div>
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
        );
      }
      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden" data-wc={`${modelName}-detail`} data-zone={`db.detail.form | .${modelName}-detail | OrgDetail.json.tsx`}>
      {/* Toolbar — hidden when inline (DataBrowser owns the toolbar) */}
      {!inline && (
        <DetailToolbar
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
      )}

      {/* Content — section-driven */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {effectiveSections.map((section: any, idx: number) => renderSection(section, idx))}
      </div>
    </div>
  );
};

export default withDevIdentifier(OrgDetailJson, 'OrgDetailJson', 'indigo', 'apps/orgs/components/OrgDetail.json.tsx');
