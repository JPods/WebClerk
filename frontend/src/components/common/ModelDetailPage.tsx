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
import React, { useState, useEffect, useCallback, useMemo, lazy, Suspense } from 'react';
import { changedFields } from '@/utils/changedFields';
import { checkJsonLimits, describeJsonLimitProblems, jsonLimitsLoaded, loadJsonLimits } from '@/utils/jsonLimits';
import { applyDerived } from '@/utils/derivedFields';
import { useParams } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import type { RootState } from '@/store';
import { showToast } from '@/store/slices/toastSlice';
import { getRecord, newRecord, saveRecord } from '@/api/wcapi';
import { COMMUNICATION_FIELDS, communicationField, communicationValue, showsCommunication } from '@/utils/communicationFields';
import { windowChannel } from '@/utils/windowChannel';
import { useWindowManager } from '@/context/WindowManagerContext';
import { useDetailLayout } from '@/hooks/useDetailLayout';
import { selectCompanyInfo, selectLogos } from '@/store/slices/companySlice';
import { withDevIdentifier } from '@/components/common/DevIdentifier';
import { renderPanel } from './panelRegistry';
import CollapsiblePanel from '@/apps/common/components/CollapsiblePanel';

import FieldRow from '@/apps/transactions/components/detail/FieldRow';
import DetailToolbar from '@/components/common/DetailToolbar';
import CommunicationCard from '@/components/common/CommunicationCard';
import { useFormDraft, type DraftGetter } from '@/hooks/useFormDraft';

const PanelSectionRenderer = lazy(() => import('@/apps/transactions/components/detail/PanelSectionRenderer'));
const JsonSectionRenderer = lazy(() => import('@/apps/transactions/components/detail/JsonSectionRenderer'));

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ModelDetailPageProps {
  modelName?: string;
  recordId?: number;
  inline?: boolean;
  onRegisterActions?: (actions: { save?: () => void; cancel?: () => void; addNew?: () => void; delete?: () => void }) => void;
  /** In a list: hand over unsaved edits before the list moves on; take them back on Undo. */
  onRegisterDraft?: (get: DraftGetter) => void;
  draft?: Record<string, any> | null;
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
  onRegisterDraft,
  draft,
  onEditStateChange,
  onSaved: onSavedProp,
  onCancelInline,
  // Accept legacy prop names (contactId, itemId)
  contactId,
  itemId,
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

  const { layout, loading: layoutLoading, error: layoutError, invalidate: invalidateLayout } = useDetailLayout(modelName);

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

  // Save is off, with the reason beside it, while the edit would break a size limit.
  const [limitsReady, setLimitsReady] = useState(!!jsonLimitsLoaded());
  useEffect(() => { loadJsonLimits().then(l => setLimitsReady(!!l)); }, []);
  const saveBlocked = useMemo(() => {
    if (!limitsReady || !isEditing || !editData) return undefined;
    const problems = checkJsonLimits(modelName, changedFields(data, editData), editData);
    return problems.length ? describeJsonLimitProblems(problems) : undefined;
  }, [limitsReady, isEditing, editData, data, modelName]);

  useEffect(() => {
    if (autoEdit && data && !isEditing) {
      setEditData({ ...data });
      setIsEditing(true);
    }
  }, [autoEdit, data]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Edit handlers ──
  const handleEdit = () => { setEditData({ ...data }); setIsEditing(true); };
  const handleCancel = () => { setEditData(data); setIsEditing(false); };
  useFormDraft({ recordId, data, editData, setEditData, setIsEditing, draft, onRegisterDraft });
  const handleClose = () => {
    if (inline && onCancelInline) { onCancelInline(); return; }
    const path = `/${modelName}/${recordId || ''}`;
    windowManager.closeWindow(path);
  };

  const handleFieldChange = useCallback((field: string, value: unknown) => {
    setEditData((prev: any) => applyDerived(modelName, prev, nestedWrite(prev, field, value), field));
  }, [modelName]);

  const handleSave = async () => {
    if (!editData) return;
    setSaving(true);
    try {
      await saveRecord(modelName, changedFields(data, editData));
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

  // A phone, address or domain is edited in a card floating over this record; the
  // record keeps showing its cache (Bill, 2026-10-16: a separate window lost the contact).
  const [commCard, setCommCard] = useState<{ field: string; anchor: DOMRect } | null>(null);
  const openCommunication = (field: string, el: HTMLElement) => {
    if (communicationField(modelName, field)) setCommCard({ field, anchor: el.getBoundingClientRect() });
  };

  // A card save saves this record on the server too (Bill, 2026-10-16). Take what that
  // save changed — cache, pointers, login email, version — and keep unsaved edits here.
  const refreshCommunications = useCallback(async () => {
    if (!recordId) return;
    const response = await getRecord(modelName, recordId);
    const record = response?.record || response;
    const pointers = Object.values(COMMUNICATION_FIELDS[modelName] || {}).map(c => c.pointer);
    const pick = (prev: any) => prev && ({
      ...prev, refs: record.refs, ...Object.fromEntries(pointers.map(p => [p, record[p]])),
      email: record.email, version: record.version, dt_modified: record.dt_modified,
    });
    setData(pick);
    setEditData(pick);
  }, [modelName, recordId]);

  // Bill, 2026-10-16: a contact whose org search finds nothing makes the org. The backend
  // saves it populated from this contact and links it; it opens in another browser window
  // (opened now, inside the click, so no pop-up blocker stops it) and this form takes the
  // link, company and version without losing unsaved edits.
  const createOrg = async (field: string, typed: string) => {
    if (!recordId) return;
    const win = window.open('about:blank', '_blank');
    try {
      const made = await newRecord(field, { _from_contact: recordId, ...(typed ? { _company: typed } : {}) });
      const id = (made as any)?.id ?? (made as any)?.record?.id;
      if (win && id) win.location.href = `/${field}/${id}`;
      const response = await getRecord(modelName, recordId);
      const record = response?.record || response;
      const pick = (prev: any) => prev && ({ ...prev, [field]: record[field], company: record.company,
        version: record.version, dt_modified: record.dt_modified });
      setData(pick);
      setEditData(pick);
      dispatch(showToast({ message: `${field} "${typed || record.attention || ''}" made and linked`, type: 'success' }));
    } catch (err: any) {
      win?.close();
      const resp = err?.response?.data;
      dispatch(showToast({ message: `Could not make ${field}: ${resp?.message || err?.message || err}`, type: 'error' }));
    }
  };

  // When that card saves, show the server's refreshed cache (unless mid-edit here).
  useEffect(() => {
    return windowChannel.on('record-saved', ({ model }) => {
      if (model && showsCommunication(modelName, model) && !isEditing) fetchData();
    });
  }, [modelName, isEditing, fetchData]);

  const handleAddNew = async () => {
    try {
      const { id: newId } = await newRecord(modelName);
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
  if (!activeLayout && layoutError) {
    return <div className="flex items-center justify-center py-20 text-slate-400">{layoutError}</div>;
  }
  if (!data || !activeLayout) {
    return <div className="flex items-center justify-center py-20 text-slate-400">Record not found</div>;
  }

  const editedData = isEditing ? editData : data;
  // Fields kept in another record show that record's cache entry.
  const currentData = COMMUNICATION_FIELDS[modelName] ? {
    ...editedData,
    ...Object.fromEntries(Object.entries(COMMUNICATION_FIELDS[modelName])
      .map(([f, c]) => [f, communicationValue(c, editedData)])),
  } : editedData;
  const sections = activeLayout.sections || [];

  // Resolve tabs from layout or defaults
  const tabsSection = sections.find((s: any) => s.type === 'tabs');
  const tabs = tabsSection?.tabs || [];

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
                {col.type === 'item_image' && data?.ida ? (
                  <div className="flex justify-center items-center h-full">
                    <img
                      src={`/wcapi/_image/item/${encodeURIComponent(data.ida)}/md.jpg`}
                      alt={data.ida}
                      style={{ maxWidth: '100%', maxHeight: 240, objectFit: 'contain', borderRadius: 4 }}
                      onError={(e: any) => { e.target.onerror = null; e.target.src = '/images/no-image.svg'; }}
                    />
                  </div>
                ) : (col.fields || []).map((f: any) => (
                  <FieldRow
                    key={f.field}
                    field={f.field}
                    label={(f.label === f.field && communicationField(modelName, f.field)?.label) || f.label}
                    data={currentData}
                    isEditing={isEditing}
                    options={f.options}
                    fieldType={f.type}
                    help={f.help}
                    onChange={handleFieldChange}
                    onOpen={communicationField(modelName, f.field) ? (el: HTMLElement) => openCommunication(f.field, el) : undefined}
                    onCreateOrg={modelName === 'contact' ? createOrg : undefined}
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

  const commSpec = commCard && communicationField(modelName, commCard.field);

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
          saveBlocked={saveBlocked}
          companyInfo={companyInfo}
          logos={logos}
          documentText={documentText}
          userRole={authUser?.role}
          onEdit={handleEdit}
          onAddNew={handleAddNew}
          onSave={handleSave}
          onCancel={handleCancel}
          onClose={handleClose}
          designMode={designMode}
          onToggleDesign={() => {
            if (designMode) { setDesignMode(false); setDesignLayout(null); invalidateLayout(); }
            else { setDesignMode(true); if (layout) setDesignLayout(JSON.parse(JSON.stringify(layout))); }
          }}
        />
      )}

      {/* Content — section-driven */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {/* Render sections: header, line_card, panel (not tabs or json_tree) */}
        {sections.filter((s: any) => s.type !== 'tabs' && s.type !== 'json_tree').map((section: any, idx: number) => renderSection(section, idx))}


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
              {/* Every registry panel renders inside the one frame, so what it declares
                  (count, actions, loading / empty / error) shows here as in a layout section. */}
              {activeTab && (
                <CollapsiblePanel key={activeTab} collapsible={false}
                  label={tabs.find((t: any) => t.content === activeTab)?.label ?? activeTab}>
                  {renderPanel(activeTab, panelCtx)}
                </CollapsiblePanel>
              )}
            </div>
          </div>
        )}

        {/* JSON tree — always last (admin tool) */}
        {sections.filter((s: any) => s.type === 'json_tree').map((section: any, idx: number) => renderSection(section, sections.length + idx))}
      </div>
      {commCard && commSpec && (
        <CommunicationCard comm={commSpec} owner={data} anchor={commCard.anchor}
          onChanged={refreshCommunications} onClose={() => setCommCard(null)} />
      )}
    </div>
  );
};

export default withDevIdentifier(ModelDetailPage, 'ModelDetailPage', 'indigo', 'components/common/ModelDetailPage.tsx');
export { ModelDetailPage };
