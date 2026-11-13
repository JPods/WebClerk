/* WhereUsed: recordRoutes, protectedRoutesConfig, Router, dbRoutes (DataBrowser inline), FlightSimConsole */
/**
 * DbForm — db.form: the one record form, for every model with a layout (plan 101, step 2).
 *
 * TransactionDetail generalized: lines, totals, the customer search, the document flow and
 * Add Cash appear when the layout and the model have them; ModelDetailPage's models — the
 * contact, the orgs, the item, the action — draw here too, with their communication cards,
 * the primary-contact card and create-org. One layout source: the wc:model Setting
 * (useDetailLayout). One record state: useRecordForm. Tabs render through panelRegistry.
 *
 * Hosted by a route (/<model>/:id), DataBrowser's inline pane (toolbar hidden; actions
 * registered with the host), the flight simulator and a window. A workflow that converts
 * this document opens what it made, with the lines for review, here — every host, one path.
 */
import { FormattingProvider } from '@/context/FormattingContext';
import { resolveFormatting } from '@/utils/formatting';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import type { RootState } from '@/store';
import { showToast } from '@/store/slices/toastSlice';
import { getRecord, newRecord } from '@/api/wcapi';
import { useWindowManager } from '@/context/WindowManagerContext';
import { heldNotice } from '@/hooks/useEditHold';
import { useDetailLayout, type DetailLayout } from '@/hooks/useDetailLayout';
import { useRecordForm, ORGS_WITH_CONTACTS, refusalMessage, type RecordFormActions } from '@/hooks/useRecordForm';
import type { DraftGetter } from '@/hooks/useFormDraft';
import { stashClosedDraft } from '@/hooks/closedDrafts';
import { registerToastAction } from '@/utils/toastActions';
import { COMMUNICATION_FIELDS, communicationField } from '@/utils/communicationFields';
import { selectCompanyInfo, selectLogos } from '@/store/slices/companySlice';
import { convertedTarget, type ConvertedTarget } from '@/apps/transactions/utils/convertedTarget';
import { useCustomerSearch, partyOf } from '@/apps/transactions/components/detail/CustomerSearch';
import HeaderRenderer from '@/apps/transactions/components/detail/HeaderRenderer';
import ReceiveButton from '@/apps/transactions/components/detail/ReceiveButton';
import LineCardRenderer from '@/apps/transactions/components/detail/LineCardRenderer';
import PanelSectionRenderer from '@/apps/transactions/components/detail/PanelSectionRenderer';
import JsonSectionRenderer from '@/apps/transactions/components/detail/JsonSectionRenderer';
import TransactionFlowIndicator from '@/apps/transactions/components/detail/TransactionFlowIndicator';
import RelatedTransactionsPanel from '@/apps/transactions/components/detail/RelatedTransactionsPanel';
import DesignMode from '@/apps/transactions/components/detail/DesignMode';
import AddCashDialog from '@/apps/transactions/components/AddCashDialog';
// Ensure card components are registered
import '@/components/cards';
import { DetailToolbar } from '@/components/common/DetailToolbar';
import CommunicationCard from '@/components/common/CommunicationCard';
import PrimaryContactCard from '@/components/common/PrimaryContactCard';
import CollapsiblePanel from '@/apps/common/components/CollapsiblePanel';
import { renderPanel } from './panelRegistry';
import { withDevIdentifier } from '@/components/common/DevIdentifier';

/** An org shows these from its primary contact: attention chooses the contact, the others open
 *  that contact's own card (Bill, 2026-10-31: a de-normalized value is edited where it comes from). */
const FROM_CONTACT = ['attention', 'email', 'phone', 'address_full', 'domain'];
/** Documents money comes in against (AddCashDialog). */
const CASH_IN_MODELS = ['order', 'invoice', 'receipt'];

export interface DbFormProps {
  modelName?: string;
  recordId?: number;
  onClose?: () => void;
  /** Inside DataBrowser: the host owns the toolbar and takes the form's actions. */
  inline?: boolean;
  onRegisterActions?: (actions: RecordFormActions) => void;
  onEditStateChange?: (editing: boolean) => void;
  onCancelInline?: () => void;
  /** After a save (DataBrowser passes onSaved, the flight simulator onAfterSave). */
  onSaved?: () => void;
  onAfterSave?: () => void;
  /** In a list: hand over unsaved edits before the list moves on; take them back on Undo. */
  onRegisterDraft?: (get: DraftGetter) => void;
  draft?: Record<string, any> | null;
  onWorkflowComplete?: (result?: any) => void;
  onNavigate?: (model: string, id: number) => void;
  [key: string]: unknown;   // a host's extra props (DataBrowser: modeProp, id, dataProp, hideBreadcrumb)
}

const badge = (tone: 'amber' | 'red' | 'slate', text: string, title?: string) => (
  <span title={title} className={`text-xs px-2 py-0.5 rounded-full ${
    tone === 'amber' ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400'
    : tone === 'red' ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
    : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300'}`}>{text}</span>
);

const DbFormView: React.FC<DbFormProps> = (props) => {
  const { modelName: propModel, recordId: propId, onClose, inline, onRegisterActions, onEditStateChange,
          onCancelInline, onSaved, onAfterSave, onRegisterDraft, draft, onWorkflowComplete, onNavigate } = props;
  const params = useParams<{ model?: string; id?: string }>();
  const modelName = propModel || params.model || '';
  const recordId = propId || (params.id ? Number(params.id) : 0);

  const dispatch = useDispatch();
  const windowManager = useWindowManager();
  const authUser = useSelector((s: RootState) => s.auth?.user);
  const companyInfo = useSelector(selectCompanyInfo);
  const logos = useSelector(selectLogos);
  const documentText = useSelector((s: RootState) => (s as any).company?.document_text) || {};
  const loggedInUserName = [authUser?.name_first, authUser?.name_last].filter(Boolean).join(' ') || authUser?.email || 'User';

  // ── Layout, design mode ──
  const { layout, loading: layoutLoading, error: layoutError, invalidate: invalidateLayout } = useDetailLayout(modelName);
  const [designMode, setDesignMode] = useState(false);
  const [designLayout, setDesignLayout] = useState<DetailLayout | null>(null);
  const activeLayout = designMode && designLayout ? designLayout : layout;
  const toggleDesign = () => {
    if (designMode) { setDesignMode(false); setDesignLayout(null); invalidateLayout(); }
    else { setDesignMode(true); if (layout) setDesignLayout(JSON.parse(JSON.stringify(layout))); }
  };

  // ── The record ──
  const afterSave = useCallback(() => { onSaved?.(); onAfterSave?.(); }, [onSaved, onAfterSave]);
  const form = useRecordForm({
    modelName, recordId, layout: activeLayout,
    autoEdit: authUser?.prefs?.layout?.detail?.auto_edit === true,
    draft, onRegisterDraft, onRegisterActions, onEditStateChange, onAfterSave: afterSave,
  });
  const { data, currentData, isEditing } = form;
  const custSearch = useCustomerSearch(form.setField, partyOf(modelName));

  // ── An org's primary contact ──
  const copiesContact = (field: string) => ORGS_WITH_CONTACTS.includes(modelName) && FROM_CONTACT.includes(field);
  const [primaryCard, setPrimaryCard] = useState<DOMRect | null>(null);
  const [contactComm, setContactComm] = useState<{ field: string; owner: Record<string, any>; anchor: DOMRect } | null>(null);
  const openFromContact = async (field: string, el: HTMLElement) => {
    const anchor = el.getBoundingClientRect();
    if (field === 'attention' || !data?.contact_id) { setPrimaryCard(anchor); return; }
    const response = await getRecord('contact', data.contact_id);
    setContactComm({ field, owner: (response as any)?.record || response, anchor });
  };
  const openContact = (id: number) => windowManager.ensureWindow(`/contact/${id}`, `contact #${id}`);
  const openField = (field: string, el: HTMLElement) =>
    copiesContact(field) ? openFromContact(field, el) : form.comm.open(field, el);
  const opensField = (field: string) => copiesContact(field) || !!communicationField(modelName, field);

  // Bill, 2026-10-16: a contact whose org search finds nothing makes the org. The backend saves
  // it populated from this contact and links it; it opens in another browser window (opened
  // now, inside the click, so no pop-up blocker stops it) and this form takes the link, company
  // and version without losing unsaved edits.
  const createOrg = async (field: string, typed: string) => {
    if (!recordId) return;
    const win = window.open('about:blank', '_blank');
    try {
      const made = await newRecord(field, { _from_contact: recordId, ...(typed ? { _company: typed } : {}) });
      const id = (made as any)?.id ?? (made as any)?.record?.id;
      if (win && id) win.location.href = `/${field}/${id}`;
      const response = await getRecord(modelName, recordId);
      const record = (response as any)?.record || response;
      const pick = (prev: any) => prev && ({ ...prev, [field]: record[field], company: record.company,
        version: record.version, dt_modified: record.dt_modified });
      form.setData(pick);
      form.setEditData(pick);
      dispatch(showToast({ message: `${field} "${typed || record.attention || ''}" made and linked`, type: 'success' }));
    } catch (err: any) {
      win?.close();
      dispatch(showToast({ message: `Could not make ${field}: ${refusalMessage(err)}`, type: 'error' }));
    }
  };

  // ── Tabs: the layout's, plus the ones "+ link" adds; every one through the registry ──
  const sections = activeLayout?.sections || [];
  const tabsSection: any = sections.find((s: any) => s.type === 'tabs');
  const tabs: { label: string; content: string }[] = tabsSection?.tabs || [];
  const [extraTabs, setExtraTabs] = useState<string[]>([]);
  const [activeTab, setActiveTab] = useState('');
  const addTab = useCallback((model: string) => {
    setExtraTabs((prev) => (prev.includes(model) ? prev : [...prev, model]));
    setActiveTab(model);
  }, []);
  const hasLinkTab = tabs.some((t) => t.content === 'link' || t.content === '_link');
  const tabIds = [...tabs.map((t) => t.content), ...extraTabs, ...(hasLinkTab ? [] : ['_link'])];
  const currentTab = tabIds.includes(activeTab) ? activeTab : tabIds[0] || '';
  const tabLabel = (id: string) => tabs.find((t) => t.content === id)?.label ?? (id === '_link' ? '+ link' : id);
  const panelCtx = useMemo(() => ({
    modelName, recordId, data: currentData, isEditing,
    onFieldChange: form.setField, onRefresh: form.fetchData, addTab,
    ensureWindow: (path: string, title: string) => windowManager.ensureWindow(path, title),
  }), [modelName, recordId, currentData, isEditing, form.setField, form.fetchData, addTab, windowManager]);

  const [showAddCash, setShowAddCash] = useState(false);
  const handleClose = () => {
    if (inline && onCancelInline) { onCancelInline(); return; }
    // Unsaved edits are set aside, not refused (guide, not barriers): the toast offers Undo,
    // which reopens the record with them (readme 107, closedDrafts).
    if (form.hasChanges && form.editData && recordId) {
      stashClosedDraft(modelName, recordId, form.editData);
      const label = `${modelName} ${data?.ida || `#${recordId}`}`;
      const path = `/${modelName}/${recordId}`;
      const action = registerToastAction(() => windowManager.ensureWindow(path, label));
      dispatch(showToast({ message: `Edits to ${label} were not saved`, type: 'warning', duration: 8000,
                           action: { id: action, label: 'Undo' } }));
    }
    if (onClose) { onClose(); return; }
    windowManager.closeWindow(`/${modelName}/${recordId || ''}`);
  };

  // ── Loading states ──
  if (layoutLoading || form.loading) {
    return <div className="flex items-center justify-center py-20 text-slate-400">Loading {modelName}...</div>;
  }
  if (!layout && layoutError) {
    return <div className="flex items-center justify-center py-20 text-slate-400">{layoutError}</div>;
  }
  if (!data || !activeLayout) {
    return <div className="flex items-center justify-center py-20 text-slate-400">Record not found</div>;
  }

  const commSpec = form.comm.spec;
  const isCashIn = CASH_IN_MODELS.includes(modelName);
  // The stored formatting: the model's definition, overlaid by the party org's (readme 106).
  const formatting = resolveFormatting(activeLayout?.formatting ?? layout?.formatting, data?.customer_config);

  return (
    <FormattingProvider value={formatting}>
    <div
      className="flex flex-col h-full overflow-hidden"
      data-wc={`${modelName}-detail`}
      data-zone={`db.form | .${modelName}-detail | DbForm.tsx`}
      data-model={modelName}
      data-record-id={data.id}
      data-record-ida={data.ida}
      data-layout-source={`Setting(purpose='wc:model', name='${modelName}') → config.layout.form`}
      data-formatting={`${formatting.currency} ${formatting.locale} ${formatting.date_format} ${formatting.number_precision}`}
    >
      {/* Header bar */}
      <div className="flex items-center gap-2 px-4 py-1 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 shrink-0 no-print">
        <span className="text-sm font-bold text-slate-900 dark:text-white capitalize">{modelName}</span>
        <span className="text-sm font-mono text-slate-600 dark:text-slate-400">{data.ida || `#${data.id}`}</span>
        {data.status && badge('slate', data.status)}
        {form.isPendMode && badge('amber', 'journalized — changes pend')}
        {isEditing && form.previewError && badge('amber', `totals not computed — ${form.previewError}`, form.previewError)}
        {form.editTier === 'closed' && badge('red', 'closed')}
        {form.hold && <span data-wc="edit-hold-notice">{badge('amber', heldNotice(form.hold))}</span>}
        {designMode && badge('amber', 'DESIGN')}
        {modelName === 'receipt' && (
          <ReceiveButton record={data} hasChanges={form.hasChanges} saving={form.saving}
            onSave={() => form.save({ keepEditing: true })} />
        )}
      </div>

      {/* Toolbar — hidden when inline (DataBrowser has its own) */}
      {!inline && (
        <DetailToolbar
          data={data}
          currentData={currentData}
          modelName={modelName}
          layout={activeLayout}
          isEditing={isEditing}
          canEdit={form.canEdit}
          saving={form.saving}
          saveBlocked={form.saveBlocked}
          companyInfo={companyInfo}
          logos={logos}
          documentText={documentText}
          userRole={authUser?.role}
          designMode={designMode}
          onEdit={form.startEdit}
          onAddNew={form.addNew}
          onSave={form.save}
          onCancel={form.cancel}
          onClose={handleClose}
          onToggleDesign={toggleDesign}
          onWorkflowComplete={onWorkflowComplete}
          // Money in with some left: apply it across the customer's open invoices (one check, many)
          onApplyCash={modelName === 'cash' && data?.type === 'cash_in' && Number(data?.available) > 0
            ? () => windowManager.ensureWindow(`/transactions/apply-cash?cash=${data.id}`, 'Apply Cash') : undefined}
        />
      )}

      {designMode && activeLayout && (
        <div className="px-4 pt-3">
          <DesignMode layout={activeLayout} modelName={modelName} onLayoutChange={(l) => setDesignLayout(l)} />
        </div>
      )}

      {/* Document lineage — the chain when this record has a parent or children */}
      {form.withLines && currentData && (
        <TransactionFlowIndicator modelName={modelName} record={currentData} onNavigate={onNavigate as any} />
      )}

      {/* Content — sections in the layout's order */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {sections.map((section: any, idx: number) => {
          switch (section.type) {
            case 'header':
              return (
                <HeaderRenderer
                  key={idx}
                  section={section}
                  data={currentData}
                  isEditing={isEditing}
                  modelName={modelName}
                  onChange={form.setField}
                  cardSpecs={activeLayout.card}
                  behaviors={activeLayout.behaviors}
                  onOpenField={openField}
                  opensField={opensField}
                  onCreateOrg={modelName === 'contact' ? createOrg : undefined}
                  onPickShipTo={form.withLines ? form.pickShipTo : undefined}
                  custSearch={form.withLines ? {
                    party: custSearch.party, open: custSearch.open, query: custSearch.query,
                    results: custSearch.results, searching: custSearch.searching, inputRef: custSearch.inputRef,
                    onToggle: custSearch.toggle, onSearch: custSearch.search, onSelect: custSearch.select,
                  } : undefined}
                />
              );
            case 'line_card':
              return (
                <React.Fragment key={idx}>
                  <LineCardRenderer
                    section={section}
                    data={currentData}
                    isEditing={isEditing}
                    isLocked={form.editTier === 'closed'}
                    onLinesChange={form.setLines}
                    modelName={modelName}
                    lineContacts={(activeLayout?.features ?? layout?.features)?.line_contacts === true}
                    onEnterCash={isCashIn ? () => setShowAddCash(true) : undefined}
                  />
                  {/* The documents around this one, under its lines (Bill, 2026-10-25) */}
                  <RelatedTransactionsPanel modelName={modelName} record={data} onNavigate={onNavigate as any} />
                </React.Fragment>
              );
            case 'tabs':
              return (
                <div key={idx} className="bg-[var(--db-surface,#fff)] dark:bg-slate-800 rounded-lg border border-[var(--db-border,#dee2e6)] dark:border-slate-700">
                  <div className="flex flex-wrap border-b border-[var(--db-border,#dee2e6)] dark:border-slate-700 overflow-x-auto no-print">
                    {tabIds.map((id) => (
                      <button
                        key={id}
                        data-wc-tab={id}
                        onClick={() => setActiveTab(id)}
                        className={`px-4 py-2 db-font-xs font-medium whitespace-nowrap border-b-2 transition-colors ${
                          currentTab === id ? 'border-blue-600 text-blue-600'
                          : 'border-transparent text-[var(--db-text-muted,#6c757d)] hover:text-[var(--db-text,#212529)]'}`}
                      >{tabLabel(id)}</button>
                    ))}
                  </div>
                  <div className="p-2">
                    {/* Every registry panel renders inside the one frame, so what it declares
                        (count, actions, loading / empty / error) shows here as in a layout section. */}
                    {currentTab && (
                      <CollapsiblePanel key={currentTab} collapsible={false} label={tabLabel(currentTab)}>
                        {renderPanel(currentTab === '_link' ? 'link' : currentTab, panelCtx)}
                      </CollapsiblePanel>
                    )}
                  </div>
                </div>
              );
            case 'panel':
              return (
                <PanelSectionRenderer key={idx} section={section} data={currentData} isEditing={isEditing}
                  modelName={modelName} onChange={form.setField} onRefresh={form.fetchData} loggedInUserName={loggedInUserName} />
              );
            case 'json_tree':
              return (
                <JsonSectionRenderer key={idx} section={section} data={currentData} isEditing={isEditing}
                  modelName={modelName} onChange={form.setField} />
              );
            default:
              return null;
          }
        })}
        {/* Every form has the json panel: one whose layout names none gets it here (Bill, 2026-11-12) */}
        {!sections.some((s: any) => s.type === 'json_tree') && (
          <JsonSectionRenderer section={{ type: 'json_tree', label: 'json' }} data={currentData} isEditing={isEditing}
            modelName={modelName} onChange={form.setField} />
        )}
      </div>

      {/* Cards floating over the record */}
      {form.comm.card && commSpec && (
        <CommunicationCard comm={commSpec} owner={data} anchor={form.comm.card.anchor}
          onChanged={form.comm.refresh} onClose={form.comm.close} />
      )}
      {primaryCard && (
        <PrimaryContactCard model={modelName} org={data} anchor={primaryCard} onOpenContact={openContact}
          onChanged={form.fetchData} onClose={() => setPrimaryCard(null)} />
      )}
      {contactComm && COMMUNICATION_FIELDS.contact[contactComm.field] && (
        <CommunicationCard comm={COMMUNICATION_FIELDS.contact[contactComm.field]} owner={contactComm.owner}
          anchor={contactComm.anchor} onChanged={form.fetchData} onClose={() => setContactComm(null)} />
      )}

      {/* Add cash from this document (release #9): add_cash, apply_balance */}
      {isCashIn && data?.id && (
        <AddCashDialog
          isOpen={showAddCash}
          onClose={() => setShowAddCash(false)}
          model={modelName as 'order' | 'invoice' | 'receipt'}
          id={data.id}
          balance={Number(modelName === 'order' ? (data?.totals?.total ?? 0) : (data?.totals?.balance ?? data?.totals?.total ?? 0))}
          customerId={data?.customer_id ?? null}
          partyName={data?.company?.name || data?.customer_company || data?.customer_name || ''}
          onDone={form.fetchData}
        />
      )}
    </div>
    </FormattingProvider>
  );
};

/**
 * The form wherever it is hosted. A workflow that converts this document opens what it made,
 * with the lines for review, here — every host, one path (before 2026-10-25 only the flight
 * simulator did; elsewhere the lines were dropped and an empty purchase was left behind).
 * The host is told after, through onNavigate.
 */
const DbForm: React.FC<DbFormProps> = (props) => {
  const params = useParams<{ model?: string; id?: string }>();
  const hostModel = (props.modelName as string) || params.model || '';
  const hostId = (props.recordId as number) || (params.id ? Number(params.id) : 0);
  const [opened, setOpened] = useState<ConvertedTarget | null>(null);

  // The host moved to another record: show that one. (A host following our own jump
  // through onNavigate lands on the record already opened.)
  useEffect(() => {
    setOpened((o) => (o && o.model === hostModel && o.id === hostId ? o : null));
  }, [hostModel, hostId]);

  const onWorkflowComplete = useCallback((result: any) => {
    const target = convertedTarget(result);
    if (target) {
      setOpened(target);
      props.onNavigate?.(target.model, target.id);
    }
    props.onWorkflowComplete?.(result);
  }, [props.onNavigate, props.onWorkflowComplete]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!opened) return <DbFormView {...props} onWorkflowComplete={onWorkflowComplete} />;
  return (
    <DbFormView
      key={`${opened.model}:${opened.id}`}
      {...props}
      modelName={opened.model}
      recordId={opened.id}
      onWorkflowComplete={onWorkflowComplete}
    />
  );
};

export default withDevIdentifier(DbForm, 'DbForm', 'indigo', 'components/common/DbForm.tsx');
export { DbForm };
