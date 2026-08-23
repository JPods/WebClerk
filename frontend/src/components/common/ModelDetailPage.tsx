/* LastChecked: 2026-08-21 | WhereUsed: Router, protectedRoutesConfig | WhoCreated: Bill+Claude */
/**
 * ModelDetailPage — Unified JSON-driven detail page.
 *
 * Replaces ContactDetailJson (335 lines), OrgDetailJson (375 lines),
 * and ItemDetailJson (292 lines) with one component (~200 lines).
 *
 * Layout JSON from useDetailLayout drives header columns and tabs.
 * Tab→panel mapping handled by panelRegistry — no switch statements.
 * Works for any model: contact, customer, vendor, manufacturer,
 * employee, rep, item, or any future model with a detail_layout Setting.
 */
import React, { useState, useEffect, useCallback, lazy, Suspense } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import type { RootState } from '@/store';
import { showToast } from '@/store/slices/toastSlice';
import { getRecord, saveRecord } from '@/api/wcapi';
import { useWindowManager } from '@/context/WindowManagerContext';
import { useDetailLayout } from '@/hooks/useDetailLayout';
import { selectCompanyInfo, selectLogos } from '@/store/slices/companySlice';
import { withDevIdentifier } from '@/components/common/DevIdentifier';
import { renderPanel, getDefaultTabs } from './panelRegistry';

import FieldRow from '@/apps/transactions/components/detail/FieldRow';
import DetailToolbar from '@/components/common/DetailToolbar';

const PanelSectionRenderer = lazy(() => import('@/apps/transactions/components/detail/PanelSectionRenderer'));
const JsonSectionRenderer = lazy(() => import('@/apps/transactions/components/detail/JsonSectionRenderer'));

// ---------------------------------------------------------------------------
// Default layout sections — card-style headers per model
// Numbers together, text separate, actions on left.
// ---------------------------------------------------------------------------

const DEFAULT_SECTIONS: Record<string, any[]> = {
  action: [
    { type: 'header', columns: [
      { title: 'Task', fields: [
        { field: 'ida', label: 'id', type: 'readonly' },
        { field: 'action', label: 'action', type: 'json-text' },
        { field: 'description', label: 'description', type: 'json-text' },
      ]},
      { title: 'Assignment', fields: [
        { field: 'assigned_to', label: 'assigned to', type: 'contact-select' },
        { field: 'project_name', label: 'project', type: 'readonly' },
        { field: 'status', label: 'status', type: 'select', options: [
          { value: 'open', label: 'Open' }, { value: 'in_progress', label: 'In Progress' },
          { value: 'complete', label: 'Complete' }, { value: 'on_hold', label: 'On Hold' },
          { value: 'cancelled', label: 'Cancelled' },
        ]},
        { field: 'kanban_column', label: 'column' },
      ]},
      { title: 'Schedule', fields: [
        { field: 'priority', label: 'priority', type: 'select', options: [
          { value: 1, label: '1 - Highest' }, { value: 2, label: '2 - High' },
          { value: 3, label: '3 - Medium' }, { value: 4, label: '4 - Normal' },
          { value: 5, label: '5 - Low' }, { value: 6, label: '6 - Lowest' },
        ]},
        { field: 'difficulty', label: 'difficulty', type: 'select', options: [
          { value: 1, label: 'Easy (1)' }, { value: 4, label: 'Average (4)' },
          { value: 8, label: 'Hard (8)' }, { value: 13, label: 'Complex (13)' },
          { value: 21, label: 'Expert (21)' },
        ]},
        { field: 'percent_complete', label: '% complete', type: 'select', options: [
          { value: 0, label: '0%' }, { value: 20, label: '20%' },
          { value: 50, label: '50%' }, { value: 70, label: '70%' },
          { value: 100, label: '100%' },
        ]},
        { field: 'dt_start', label: 'start', type: 'date' },
        { field: 'dt_deadline', label: 'deadline', type: 'date' },
        { field: 'dt_completed', label: 'completed', type: 'date' },
      ]},
    ]},
  ],
  touch: [
    { type: 'header', columns: [
      { title: 'Touch', fields: [
        { field: 'ida', label: 'id', type: 'readonly' },
        { field: 'channel', label: 'channel', type: 'select', options: [
          { value: 'call', label: 'Call' }, { value: 'email', label: 'Email' },
          { value: 'visit', label: 'Visit' }, { value: 'text', label: 'Text' },
          { value: 'meeting', label: 'Meeting' },
        ]},
        { field: 'direction', label: 'direction', type: 'select', options: [
          { value: 'out', label: 'Outbound' }, { value: 'in', label: 'Inbound' },
        ]},
        { field: 'subject', label: 'subject' },
        { field: 'summary', label: 'summary', type: 'textarea' },
      ]},
      { title: 'Result', fields: [
        { field: 'outcome', label: 'outcome', type: 'select', options: [
          { value: '', label: '—' }, { value: 'connected', label: 'Connected' },
          { value: 'voicemail', label: 'Voicemail' }, { value: 'no_answer', label: 'No Answer' },
          { value: 'bounced', label: 'Bounced' }, { value: 'rescheduled', label: 'Rescheduled' },
        ]},
        { field: 'purpose', label: 'purpose' },
        { field: 'impact', label: 'impact', type: 'number' },
        { field: 'duration', label: 'duration (min)', type: 'number' },
        { field: 'plan', label: 'follow-up (days)', type: 'number' },
      ]},
      { title: 'People', fields: [
        { field: 'contact_id', label: 'contact', type: 'readonly' },
        { field: 'logged_by', label: 'logged by', type: 'readonly' },
        { field: 'dt_created', label: 'created', type: 'date' },
        { field: 'dt_next', label: 'next touch', type: 'date' },
      ]},
    ]},
  ],
};

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ModelDetailPageProps {
  modelName?: string;
  recordId?: number;
  inline?: boolean;
  onRegisterActions?: (actions: { save?: () => void; cancel?: () => void; addNew?: () => void; delete?: () => void }) => void;
  onEditStateChange?: (editing: boolean) => void;
  onSaved?: () => void;
  onCancelInline?: () => void;
  [key: string]: any;
}

// ---------------------------------------------------------------------------
// Dot-notation nested write
// ---------------------------------------------------------------------------

function nestedWrite(prev: any, field: string, value: unknown): any {
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
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const ModelDetailPage: React.FC<ModelDetailPageProps> = ({
  modelName: propModel,
  recordId: propId,
  inline,
  onRegisterActions,
  onEditStateChange,
  onSaved: onSavedProp,
  onCancelInline,
  // Accept legacy prop names (contactId, itemId)
  contactId,
  itemId,
  ...rest
}) => {
  const params = useParams<{ model?: string; id?: string }>();
  const modelName = propModel || params.model || 'contact';
  const resolvedPropId = propId || contactId || itemId;
  const recordId = resolvedPropId || (params.id ? Number(params.id) : 0);

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
  const [activeTab, setActiveTab] = useState('');
  const [designMode, setDesignMode] = useState(false);
  const [designLayout, setDesignLayout] = useState<any>(null);

  const activeLayout = designMode && designLayout ? designLayout : layout;
  const autoEdit = authUser?.prefs?.layout?.detail?.auto_edit === true;

  // ── Fetch ──
  const fetchData = useCallback(async () => {
    if (!recordId) return;
    setLoading(true);
    try {
      const response = await getRecord(modelName, recordId);
      const record = response?.record || response;

      // Fetch primary contact for org models
      const contactIdVal = record?.contact_id || record?.contact;
      if (contactIdVal && modelName !== 'contact') {
        try {
          const ctResp = await getRecord('contact', contactIdVal);
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

  // ── Edit handlers ──
  const handleEdit = () => { setEditData({ ...data }); setIsEditing(true); };
  const handleCancel = () => { setEditData(data); setIsEditing(false); };

  const handleFieldChange = useCallback((field: string, value: unknown) => {
    setEditData((prev: any) => nestedWrite(prev, field, value));
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
      onSavedProp?.();
    } catch (err: any) {
      const resp = err?.response?.data;
      const detail = resp?.detail || resp?.message || resp?.error?.details || err?.message || String(err);
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

  // ── Register actions for parent toolbar (databrowser inline) ──
  useEffect(() => {
    if (onRegisterActions) onRegisterActions({ save: handleSave, cancel: handleCancel, addNew: handleAddNew });
  }, [onRegisterActions, handleSave, handleCancel, handleAddNew]);

  useEffect(() => {
    if (onEditStateChange) onEditStateChange(isEditing);
  }, [isEditing, onEditStateChange]);

  // ── Loading ──
  if (loading || layoutLoading) {
    return <div className="flex items-center justify-center py-20 text-slate-400">Loading {modelName}...</div>;
  }
  if (!data || !activeLayout) {
    return <div className="flex items-center justify-center py-20 text-slate-400">Record not found</div>;
  }

  const currentData = isEditing ? editData : data;
  const sections = activeLayout.sections?.length > 0
    ? activeLayout.sections
    : (DEFAULT_SECTIONS[modelName] || []);

  // Resolve tabs from layout or defaults
  const tabsSection = sections.find((s: any) => s.type === 'tabs');
  const tabs = tabsSection?.tabs || getDefaultTabs(modelName);

  // Set initial active tab on first render
  if (!activeTab && tabs.length > 0) {
    // Use setTimeout to avoid setState during render
    setTimeout(() => setActiveTab(tabs[0].content), 0);
  }

  // Panel context for tab rendering
  const panelCtx = {
    modelName,
    recordId,
    data: currentData,
    isEditing,
    onFieldChange: handleFieldChange,
    onRefresh: fetchData,
    ensureWindow: (path: string, title: string) => windowManager.ensureWindow(path, title),
  };

  // ── Section renderer ──
  const renderSection = (section: any, idx: number) => {
    switch (section.type) {
      case 'header': {
        const columns = section.columns || [];
        return (
          <div key={idx} className="grid gap-3" style={{ gridTemplateColumns: `repeat(${columns.length}, 1fr)` }}>
            {columns.map((col: any, colIdx: number) => (
              <div key={colIdx} className="bg-[var(--db-surface,#fff)] dark:bg-slate-800 rounded-lg border border-[var(--db-border,#dee2e6)] dark:border-slate-700 p-3">
                <div className="flex items-center justify-between text-xs font-bold text-[var(--db-text,#212529)] dark:text-slate-200 mb-2 border-b border-[var(--db-border,#dee2e6)] dark:border-slate-700 pb-1">
                  <span>{col.title}</span>
                  {colIdx === 0 && data.ida && (
                    <span className="font-mono font-normal text-[var(--db-text-muted,#6c757d)] dark:text-slate-500">{data.ida}</span>
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
          <Suspense key={idx} fallback={<div className="p-4 text-xs text-slate-400">Loading...</div>}>
            <PanelSectionRenderer
              section={section}
              data={currentData}
              isEditing={isEditing}
              modelName={modelName}
              onChange={handleFieldChange}
              onRefresh={fetchData}
            />
          </Suspense>
        );
      case 'json_tree':
        return (
          <Suspense key={idx} fallback={<div className="p-4 text-xs text-slate-400">Loading...</div>}>
            <JsonSectionRenderer
              section={section}
              data={currentData}
              isEditing={isEditing}
              modelName={modelName}
              onChange={handleFieldChange}
            />
          </Suspense>
        );
      case 'tabs':
        // Tabs rendered below all sections — skip here
        return null;
      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden" data-wc={`${modelName}-detail`} data-zone={`db.detail.form | .${modelName}-detail | ModelDetailPage.tsx`}>
      {/* Toolbar — hidden when inline (databrowser owns it) */}
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
        {/* Render non-tab sections (header, panel, json_tree) */}
        {sections.filter((s: any) => s.type !== 'tabs').map((section: any, idx: number) => renderSection(section, idx))}

        {/* If no header section in layout, render default fallback header */}
        {!sections.some((s: any) => s.type === 'header') && (
          <div className="bg-[var(--db-surface,#fff)] dark:bg-slate-800 rounded-lg border border-[var(--db-border,#dee2e6)] dark:border-slate-700 p-3">
            <div className="text-xs font-bold text-[var(--db-text,#212529)] dark:text-slate-200 mb-2">
              {data.ida || `${modelName} #${data.id}`}
            </div>
          </div>
        )}

        {/* Tabs */}
        {tabs.length > 0 && (
          <div className="bg-[var(--db-surface,#fff)] dark:bg-slate-800 rounded-lg border border-[var(--db-border,#dee2e6)] dark:border-slate-700">
            <div className="flex border-b border-[var(--db-border,#dee2e6)] dark:border-slate-700 overflow-x-auto">
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
              {activeTab && renderPanel(activeTab, panelCtx)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default withDevIdentifier(ModelDetailPage, 'ModelDetailPage', 'indigo', 'components/common/ModelDetailPage.tsx');
export { ModelDetailPage };
