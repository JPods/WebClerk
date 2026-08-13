/* LastChecked: 2026-08-03 | WhereUsed: Router, protectedRoutesConfig | WhoCreated: Claude */
/**
 * ContactDetailJson — JSON-driven contact detail page.
 *
 * Replaces ContactDetail.tsx (4,114 lines) with the same pattern as TransactionDetail:
 * - Layout JSON from detail_layout Setting drives header rendering
 * - CommPanel handles communications tab
 * - Existing panels reused for actions, documents, notes
 * - Single-purpose components, thin orchestrator
 */
import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import type { RootState } from '@/store';
import { showToast } from '@/store/slices/toastSlice';
import { getRecord, getRecords, saveRecord } from '@/api/wcapi';
import { useWindowManager } from '@/context/WindowManagerContext';
import { useDetailLayout } from '@/hooks/useDetailLayout';
import { withDevIdentifier } from '@/components/common/DevIdentifier';

// Detail components — same as TransactionDetail uses
import FieldRow from '@/apps/transactions/components/detail/FieldRow';
import { CommPanel } from '@/apps/communications/components';

// Shared detail components
import DetailToolbar from '@/components/common/DetailToolbar';
import { selectCompanyInfo, selectLogos } from '@/store/slices/companySlice';

// Existing panels — reuse as-is
import CommentsPanel from '@/apps/common/components/panels/CommentsPanel';
import { DocumentsPanel } from '@/apps/common/components/panels';
import ActionsPanel from '@/apps/common/components/panels/ActionsPanel';
import { PanelTable, type PanelColumnDef } from '@/apps/common/components/panels/PanelTable';
import ProjectKanbanPanel from '@/apps/common/components/panels/ProjectKanbanPanel';
import ProjectGanttPanel from '@/apps/common/components/panels/ProjectGanttPanel';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ContactDetailJsonProps {
  contactId?: number;
  recordId?: number;
  inline?: boolean;
  onRegisterActions?: (actions: { save?: () => void; cancel?: () => void; addNew?: () => void; delete?: () => void }) => void;
  onEditStateChange?: (editing: boolean) => void;
  onSaved?: () => void;
  onCancelInline?: () => void;
  [key: string]: any;
}

// ---------------------------------------------------------------------------
// Panel column definitions
// ---------------------------------------------------------------------------

const ORG_PANEL_COLUMNS: PanelColumnDef<Record<string, unknown>>[] = [
  { key: 'type', label: 'type', cellClassName: 'w-[80px] font-semibold text-slate-600 dark:text-slate-300', render: (r) => String(r.type ?? '—') },
  { key: 'company', label: 'company', cellClassName: 'min-w-[120px] flex-1 text-slate-800 dark:text-slate-200', render: (r) => String(r.company ?? r.name ?? '—') },
  { key: 'ida', label: 'ida', cellClassName: 'w-[70px] font-mono text-slate-500 dark:text-slate-400', render: (r) => String(r.ida ?? '—') },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const ContactDetailJson: React.FC<ContactDetailJsonProps> = ({ contactId, recordId: propId, inline, onRegisterActions, onEditStateChange, onSaved: onSavedProp, onCancelInline }) => {
  const resolvedPropId = propId || contactId;
  const params = useParams<{ id?: string }>();
  const recordId = resolvedPropId || (params.id ? Number(params.id) : 0);
  const dispatch = useDispatch();
  const windowManager = useWindowManager();
  const authUser = useSelector((s: RootState) => s.auth?.user);
  const companyInfo = useSelector(selectCompanyInfo);
  const logos = useSelector(selectLogos);
  const documentText = useSelector((s: RootState) => (s as any).company?.document_text) || {};

  // Layout
  const { layout, loading: layoutLoading, invalidate: invalidateLayout } = useDetailLayout('contact');

  // State
  const [data, setData] = useState<any>(null);
  const [editData, setEditData] = useState<any>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('communications');

  // Auto-edit from user prefs
  const autoEdit = authUser?.prefs?.layout?.detail?.auto_edit === true;

  // Fetch
  const fetchData = useCallback(async () => {
    if (!recordId) return;
    setLoading(true);
    try {
      const response = await getRecord('contact', recordId);
      const record = response?.record || response;
      setData(record);
      setEditData(record);
    } catch {
      dispatch(showToast({ message: 'Failed to load contact', type: 'error' }));
    }
    setLoading(false);
  }, [recordId, dispatch]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Auto-edit
  useEffect(() => {
    if (autoEdit && data && !isEditing) {
      setEditData({ ...data });
      setIsEditing(true);
    }
  }, [autoEdit, data]); // eslint-disable-line react-hooks/exhaustive-deps

  // Edit handlers
  const handleEdit = () => { setEditData({ ...data }); setIsEditing(true); };
  const handleCancel = () => { setEditData(data); setIsEditing(false); };

  const handleAddNew = async () => {
    try {
      const res = await saveRecord('contact', { is_active: true });
      const newId = res?.record?.id || res?.id;
      if (newId) windowManager.ensureWindow(`/contact/${newId}`, `Contact #${newId}`);
    } catch {
      dispatch(showToast({ message: 'Failed to create contact', type: 'error' }));
    }
  };

  const handleFieldChange = useCallback((field: string, value: unknown) => {
    setEditData((prev: any) => {
      if (!prev) return prev;
      if (!field.includes('.')) return { ...prev, [field]: value };
      // Nested write: config.prospect_status → prev.config.prospect_status
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
      const { uuid: _u, metadata: _m, refs: _r, prefs: _p, ...clean } = editData;
      await saveRecord('contact', clean);
      dispatch(showToast({ message: 'Contact saved', type: 'success' }));
      setIsEditing(false);
      fetchData();
    } catch {
      dispatch(showToast({ message: 'Save failed', type: 'error' }));
    }
    setSaving(false);
  };

  // Register actions for parent toolbar (when inline in DataBrowser)
  useEffect(() => {
    if (onRegisterActions) {
      onRegisterActions({ save: handleSave, cancel: handleCancel, addNew: handleAddNew });
    }
  }, [onRegisterActions, handleSave, handleCancel, handleAddNew]);

  // Report editing state to parent
  useEffect(() => {
    if (onEditStateChange) onEditStateChange(isEditing);
  }, [isEditing, onEditStateChange]);

  // Loading states
  if (loading || layoutLoading) {
    return <div className="flex items-center justify-center py-20 text-slate-400">Loading contact...</div>;
  }
  if (!data || !layout) {
    return <div className="flex items-center justify-center py-20 text-slate-400">Contact not found</div>;
  }

  const currentData = isEditing ? editData : data;
  const headerSection = layout.sections?.find((s: any) => s.type === 'header') as any;
  const tabsSection = layout.sections?.find((s: any) => s.type === 'tabs') as any;
  const columns = headerSection?.columns || [];
  const tabs = tabsSection?.tabs || [
    { label: 'Communications', content: 'communications' },
    { label: 'Actions', content: 'actions' },
    { label: 'Kanban', content: 'kanban' },
    { label: 'Gantt', content: 'gantt' },
    { label: 'Documents', content: 'documents' },
    { label: 'Notes', content: 'notes' },
  ];

  return (
    <div className="flex flex-col h-full overflow-hidden" data-wc="contact-detail" data-zone="db.detail.form | .contact-detail | ContactDetailJson.tsx">
      {/* Toolbar — hidden when inline (DataBrowser owns the toolbar) */}
      {!inline && (
        <DetailToolbar
          data={data}
          currentData={currentData}
          modelName="contact"
          layout={layout}
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
        />
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {/* Header columns */}
        {headerSection && (
          <div className={`grid grid-cols-${columns.length} gap-3`}>
            {columns.map((col: any, colIdx: number) => (
              <div key={colIdx} className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-3">
                <div className="flex items-center justify-between text-xs font-bold text-slate-700 dark:text-slate-200 mb-2 border-b border-slate-100 dark:border-slate-700 pb-1">
                  <span>{col.title}</span>
                  {colIdx === 0 && data.ida && (
                    <span className="font-mono font-normal text-slate-400 dark:text-slate-500">{data.ida}</span>
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
            {activeTab === 'communications' && (
              <CommPanel
                contactId={data.id}
                emails={data.refs?.links?.email || []}
                phones={data.refs?.links?.phone || []}
                addresses={data.refs?.links?.address || []}
                domains={data.refs?.links?.domain || []}
                onRefresh={fetchData}
              />
            )}
            {activeTab === 'organizations' && (
              <div className="p-2">
                <PanelTable
                  storageKey="panel:contact:organizations"
                  columns={ORG_PANEL_COLUMNS}
                  data={[
                    ...(data.refs?.links?.customer ? [{ type: 'Customer', ...data.refs.links.customer }] : []),
                    ...(data.refs?.links?.vendor ? [{ type: 'Vendor', ...data.refs.links.vendor }] : []),
                  ]}
                  rowKey={(r: any) => `${r.type}-${r.id ?? r.ida}`}
                  compact
                />
              </div>
            )}
            {activeTab === 'actions' && (
              <ActionsPanel
                entityType="contact"
                entityId={data.id}
                data={data.actions?.items || []}
                isEditing={isEditing}
              />
            )}
            {activeTab === 'kanban' && data.id && (
              <ProjectKanbanPanel contactId={data.id} />
            )}
            {activeTab === 'gantt' && data.id && (
              <ProjectGanttPanel contactId={data.id} />
            )}
            {activeTab === 'documents' && (
              <DocumentsPanel
                parent_model="contact"
                parentId={data.id}
                data={data.refs?.links?.document}
                isEditing={isEditing}
              />
            )}
            {activeTab === 'notes' && (
              <CommentsPanel
                entityType="contact"
                entityId={data.id}
                data={data.comments}
                isEditing={isEditing}
                onChange={(comments: any) => handleFieldChange('comments', comments)}
              />
            )}
            {activeTab === 'qa' && (
              <div className="p-4 text-xs text-slate-400">QA panel — coming soon</div>
            )}
            {activeTab === 'history' && (
              <div className="p-4 text-xs text-slate-400">History panel — coming soon</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default withDevIdentifier(ContactDetailJson, 'ContactDetailJson', 'indigo', 'apps/core/models/contact/pages/ContactDetailJson.tsx');
