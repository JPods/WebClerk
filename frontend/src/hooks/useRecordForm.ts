/**
 * useRecordForm — one record on a form: read, edit, save through the door (plan 101, step 2).
 *
 * The common parent Bill asked for (2026-11-01) is this hook, not a component: it holds what
 * ModelDetailPage and TransactionDetail each held on their own — the record and its edit copy,
 * the edit tier from the layout's edit_rules and the journal, the edit hold, the draft a list
 * hands over, changed-fields save (lines included, identified by `_delete`), the refused-save
 * sentence, the totals the browser computes while editing (readme 107), the communication cards a
 * contact's phone and address are edited in, the window-channel refresh, and the host contract
 * DataBrowser's inline pane uses. db.form draws on it; db.detail (step 5) will too.
 *
 * What is a transaction here is read from the layout, not a model list: a layout with a
 * line_card section has lines, totals and a party. Picking the party saves the pick at once and
 * reloads: the server fills the header from the org (readme 106 rule 3, party_fill.py).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useDispatch } from 'react-redux';
import { getRecord, newRecord, saveRecord, saveTransactionWithLines } from '@/api/wcapi';
import { showToast } from '@/store/slices/toastSlice';
import { useWindowManager } from '@/context/WindowManagerContext';
import { useEditHold, type HeldBy } from '@/hooks/useEditHold';
import type { DetailLayout } from '@/hooks/useDetailLayout';
import { useFormDraft, type DraftGetter } from '@/hooks/useFormDraft';
import { changedFields } from '@/utils/changedFields';
import { contactsToSend } from '@/apps/transactions/components/panels/LineContactsPanel';
import { applyDerived } from '@/utils/derivedFields';
import { checkJsonLimits, describeJsonLimitProblems, jsonLimitsLoaded, loadJsonLimits } from '@/utils/jsonLimits';
import { COMMUNICATION_FIELDS, communicationField, communicationValue, showsCommunication } from '@/utils/communicationFields';
import { windowChannel } from '@/utils/windowChannel';
import { partyOf } from '@/apps/transactions/components/detail/CustomerSearch';
import { getActiveLines, getRemovedLines, isPersistedLine } from '@/apps/transactions/services/lineItemService';
import { computeTotals, settlementOf, type LineTotals } from '@/apps/transactions/services/totalsCompute';
import { takeClosedDraft } from '@/hooks/closedDrafts';
import type { TransactionLine } from '@/apps/transactions/types/transactionTypes';

/** Keys the screen shows but the document does not store; never sent on save. */
export const DISPLAY_ONLY_KEYS = ['customer_config', 'customer_company', 'parent_summary', 'calc_context'] as const;

/** What the browser reports of its preview at save; the server says if what it saved differs
 *  (browser_totals.check_preview). */
const PREVIEW_REPORT_KEYS = ['amount', 'tax', 'shipping', 'other', 'total'] as const;

/** Of a line's refs the form writes only the people it names (readme 110): the links, the
 *  source and the keywords are the server's, and an echo of them is refused or would replace
 *  them. A line whose contacts did not change sends no refs. */
export function lineRefsToSend(body: Record<string, any>, loaded?: Record<string, any>): Record<string, any> {
  if (!body.refs || typeof body.refs !== 'object') return body;
  const { refs, ...rest } = body;
  const now = contactsToSend(refs.contacts);
  const before = contactsToSend(loaded?.refs?.contacts);
  return JSON.stringify(now) === JSON.stringify(before) ? rest : { ...rest, refs: { contacts: now } };
}

/** Orgs whose primary contact's name, email, phone and address they show (PrimaryContactCard). */
export const ORGS_WITH_CONTACTS = ['customer', 'vendor', 'manufacturer', 'rep'];

export type EditTier = 'open' | 'pend' | 'closed';

export interface RecordFormActions {
  save?: () => void;
  cancel?: () => void;
  addNew?: () => void;
  delete?: () => void;
}

export interface RecordFormOptions {
  modelName: string;
  recordId: number;
  layout: DetailLayout | null;
  /** The person's prefs.layout.detail.auto_edit: open straight into edit. */
  autoEdit?: boolean;
  /** In a list: hand over unsaved edits before the list moves on; take them back on Undo. */
  draft?: Record<string, any> | null;
  onRegisterDraft?: (get: DraftGetter) => void;
  /** The host's toolbar (DataBrowser inline pane) takes the form's actions. */
  onRegisterActions?: (actions: RecordFormActions) => void;
  onEditStateChange?: (editing: boolean) => void;
  onAfterSave?: () => void;
}

/** A new line without the empty envelopes it was built with: `{}`, `[]` and `''` say
 *  nothing about a line that does not exist yet, and each is a path to refuse. */
export function withoutEmpties(value: any): any {
  if (Array.isArray(value)) return value.map(withoutEmpties);
  if (value === null || typeof value !== 'object') return value;
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(value)) {
    const kept = withoutEmpties(v);
    if (kept === '' || kept === null || kept === undefined) continue;
    if (Array.isArray(kept) && kept.length === 0) continue;
    if (typeof kept === 'object' && !Array.isArray(kept) && Object.keys(kept).length === 0) continue;
    out[k] = kept;
  }
  return out;
}

/** `prev` with `field` set, a dotted field written into its envelope (config.ship_to.company). */
export function nestedWrite(prev: any, field: string, value: unknown): any {
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

/** What the save repriced, in a sentence: the server's structured detail (readme 106 rule 5,
 *  transactions/services/reprice.py) — "2 lines repriced to wholesale, 1 kept". */
export function repriceNote(messages: unknown): string {
  const detail = (Array.isArray(messages) ? messages : []).find((m: any) => m && typeof m === 'object' && Array.isArray(m.repriced)) as any;
  if (!detail) return '';
  const n = detail.repriced.length;
  const kept = Array.isArray(detail.kept) ? detail.kept.length : 0;
  const parts = [];
  if (n) parts.push(`${n} line${n === 1 ? '' : 's'} repriced to ${detail.price_level || 'the new level'}`);
  if (kept) parts.push(`${kept} kept`);
  return parts.join(', ');
}

/** The server's sentence for a refused save, else the error's. */
export function refusalMessage(err: any): string {
  const resp = err?.response?.data;
  const raw = resp?.message || resp?.detail || resp?.error?.details || err?.message || String(err);
  const detail = Array.isArray(raw) ? raw.join('; ') : raw;
  return typeof detail === 'string' ? detail : JSON.stringify(detail);
}

/** The tier the layout's rules and the journal give a record: closed, pend (journalized,
 *  changes pend) or open. */
export function editTierOf(data: any, layout: DetailLayout | null): EditTier {
  if (!data || !layout) return 'closed';
  if (data.dt_journaled) return 'closed';
  const rules = (layout.edit_rules || {}) as any;
  const status = String(data[rules.status_field || 'status'] || '').toLowerCase();
  if (rules.closed_statuses?.includes(status)) return 'closed';
  if (rules.pend_statuses?.includes(status)) return 'pend';
  if (rules.open_statuses?.includes(status)) return 'open';
  if (rules.locked_statuses?.includes(status)) return 'closed';
  return 'open';
}

export function hasLineCard(layout: DetailLayout | null): boolean {
  return !!layout?.sections?.some((s: any) => s.type === 'line_card');
}

export function useRecordForm(opts: RecordFormOptions) {
  const { modelName, recordId, layout, autoEdit, draft, onRegisterDraft,
          onRegisterActions, onEditStateChange, onAfterSave } = opts;
  const dispatch = useDispatch();
  const windowManager = useWindowManager();
  const withLines = hasLineCard(layout);

  // ── Record state ─────────────────────────────────────────────────
  const [data, setData] = useState<any>(null);
  const [editData, setEditData] = useState<any>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  // A window closed with edits set them aside (closedDrafts); Undo reopens it and takes them back.
  const closedDraft = useRef<Record<string, any> | null | undefined>(undefined);
  if (closedDraft.current === undefined) closedDraft.current = recordId ? takeClosedDraft(modelName, recordId) : null;
  useFormDraft({ recordId, data, editData, setEditData, setIsEditing, draft: draft ?? closedDraft.current, onRegisterDraft });

  // ── Fetch ────────────────────────────────────────────────────────
  const fetchData = useCallback(async () => {
    if (!recordId) return;
    setLoading(true);
    try {
      const response = await getRecord(modelName, recordId);
      const record = (response as any)?.record || response;
      // The party's credit figures and name are shown beside the document, never stored on it.
      const party = partyOf(modelName);
      const custId = withLines ? (record?.[`${party}_id`] || record?.[party]) : null;
      if (custId) {
        try {
          const custResp = await getRecord(party, custId);
          const cust = (custResp as any)?.record || custResp;
          if (cust?.config) record.customer_config = cust.config;
          record.customer_company = cust?.company || cust?.display_name || cust?.name || '';
        } catch { /* customer not found */ }
      }
      // An org shows its primary contact (PrimaryContactCard reads it from the record).
      const contactId = ORGS_WITH_CONTACTS.includes(modelName) ? (record?.contact_id || record?.contact) : null;
      if (contactId) {
        try {
          const ctResp = await getRecord('contact', contactId);
          const ct = (ctResp as any)?.record || ctResp;
          if (ct) record._contact = ct;
        } catch { /* contact not found */ }
      }
      setData(record);
      setEditData({ ...record });
    } catch {
      dispatch(showToast({ message: `Failed to load ${modelName}`, type: 'error' }));
    } finally {
      setLoading(false);
    }
  }, [modelName, recordId, withLines, dispatch]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // ── Edit tier, hold, auto-edit ───────────────────────────────────
  const editTier = useMemo(() => editTierOf(data, layout), [data, layout]);
  const hold = useEditHold(modelName, recordId || undefined);
  useEffect(() => { if (isEditing) hold.touch(); }, [editData]); // eslint-disable-line react-hooks/exhaustive-deps
  const canEdit = editTier !== 'closed' && !hold.heldBy;

  const startEdit = useCallback(() => {
    if (!canEdit || !data) return;
    setEditData((prev: any) => prev ?? { ...data });
    setIsEditing(true);
  }, [canEdit, data]);
  const cancel = useCallback(() => { setEditData(data); setIsEditing(false); }, [data]);

  useEffect(() => {
    if (autoEdit && canEdit && data && !isEditing) {
      setEditData({ ...data });
      setIsEditing(true);
    }
  }, [autoEdit, canEdit, data]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Field and line changes ───────────────────────────────────────
  const setField = useCallback((field: string, value: unknown) => {
    setEditData((prev: any) => {
      if (!prev) return prev;
      const next = nestedWrite(prev, field, value);
      return field.includes('.') ? next : applyDerived(modelName, prev, next, field);
    });
    // A document's party is saved the moment it is picked: the server fills terms, level, the
    // bill-to and ship-to blocks and tax from the org, and the form reloads what it returns
    // (readme 106 rule 3; Bill, 2026-11-07: "the quote reloads with that customer's values").
    const party = partyOf(modelName);
    if (withLines && (field === party || field === `${party}_id`) && Number(value) > 0) {
      partyPicked.current = party;
    }
  }, [modelName, withLines]);
  const partyPicked = useRef<string | null>(null);

  // The ship-to search's pick rides the save as a signal; the server fills the block from the
  // contact or customer and the form reloads what it returns (Bill, 2026-11-11; party_fill.py).
  const shipToPicked = useRef(false);
  const pickShipTo = useCallback((model: 'contact' | 'customer', id: number) => {
    shipToPicked.current = true;
    setEditData((prev: any) => (prev ? { ...prev, _ship_to_from: { model, id } } : prev));
  }, []);

  // Every line, removed ones included — they stay on screen marked deleted until the save.
  // If a child hands back a filtered array, the removed lines are merged back in, or the
  // `_delete` identification is lost and the rows would silently survive the save.
  const setLines = useCallback((lines: TransactionLine[]) => {
    setEditData((prev: any) => {
      if (!prev) return prev;
      const key = (l: TransactionLine) => `${l.id ?? ''}|${l.line_number ?? ''}`;
      const incoming = new Set(lines.map(key));
      const stillRemoved = getRemovedLines(prev.lines || []).filter((r: TransactionLine) => !incoming.has(key(r)));
      return { ...prev, lines: [...lines, ...stillRemoved] };
    });
  }, []);

  // ── Totals while editing: the browser's engine on the unsaved values (readme 107) ──
  // Display only: the computed totals never enter editData, so the save never sends totals.
  // It sends `_totals_preview`, and the server says if what it saved differs. The engine is
  // compute_totals' mirror, held to it by the pytest-written fixture; what it cannot read from
  // the document comes with the record as calc_context, and the settlement figures are the
  // loaded record's (journal facts, not arithmetic).
  const computed = useMemo((): { preview: { totals: Record<string, any>; byLine: Map<any, LineTotals | null> } | null; error: string | null } => {
    if (!withLines || !isEditing || !editData || !('totals' in editData)) return { preview: null, error: null };
    const active = getActiveLines(editData.lines || []);
    try {
      const out = computeTotals(editData, active, modelName,
                                { ...(editData.calc_context || {}), settlement: settlementOf(data, modelName) });
      return { preview: { totals: out.totals, byLine: new Map(active.map((l, i) => [l, out.lineTotals[i]])) }, error: null };
    } catch (err: any) {
      return { preview: null, error: err?.message || 'Totals could not be calculated' };
    }
  }, [withLines, isEditing, editData, data, modelName]);
  const preview = computed.preview;
  const previewError = computed.error;

  // ── Unsaved edits: what a close or a reload would lose ──
  const hasChanges = useMemo(() => {
    if (!isEditing || !editData) return false;
    const header: Record<string, any> = { ...editData };
    for (const k of ["lines", ...DISPLAY_ONLY_KEYS]) delete header[k];
    if (Object.keys(changedFields(data, header)).some((k) => k !== 'id' && k !== 'version')) return true;
    return (editData.lines || []).some((l: any) => l._dirty || l._new || (l._removed && isPersistedLine(l)));
  }, [isEditing, editData, data]);
  useEffect(() => {
    if (!hasChanges) return;
    const warn = (e: BeforeUnloadEvent) => { e.preventDefault(); e.returnValue = ''; };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [hasChanges]);


  // ── Save: only what changed, lines identified ───────────────────
  // Save is off, with the reason beside it, while the edit would break a size limit.
  const [limitsReady, setLimitsReady] = useState(!!jsonLimitsLoaded());
  useEffect(() => { loadJsonLimits().then((l) => setLimitsReady(!!l)); }, []);
  const saveBlocked = useMemo(() => {
    if (!limitsReady || !isEditing || !editData) return undefined;
    const problems = checkJsonLimits(modelName, changedFields(data, editData), editData);
    return problems.length ? describeJsonLimitProblems(problems) : undefined;
  }, [limitsReady, isEditing, editData, data, modelName]);

  const save = useCallback(async (opts?: { keepEditing?: boolean; message?: string; report?: boolean }) => {
    if (!editData || saveBlocked) return;
    setSaving(true);
    try {
      // A removed line that was never saved simply disappears. A removed line that exists
      // in the database STAYS in the payload, identified with `_delete: true`, so the
      // backend deletes that row inside the same save as the header.
      const allLines: TransactionLine[] = editData.lines || [];
      const deletions = getRemovedLines(allLines).filter(isPersistedLine)
        .map((l: TransactionLine) => ({ ...l, _delete: true }));
      const dirtyLines = getActiveLines(allLines).filter((l: any) => l._dirty || l._new);
      // Only what changed goes: the header fields that differ from the record as loaded and
      // the lines the person touched. The door accepts the fields the role's enumeration
      // names and refuses the rest, so echoing the whole record back refused every save
      // with lines from 2026-09-20 to 2026-10-25 (wc3).
      const editedHeader: Record<string, any> = { ...editData };
      for (const k of ["lines", ...DISPLAY_ONLY_KEYS]) delete editedHeader[k];
      const loadedById = new Map<number, any>((data?.lines || []).map((l: any) => [l.id, l]));
      const linesToSend = dirtyLines.map((l: any) => lineRefsToSend(isPersistedLine(l)
        ? { ...changedFields(loadedById.get(l.id), l), _dirty: true }
        : withoutEmpties(l), loadedById.get(l.id)));
      const header: Record<string, any> = changedFields(data, editedHeader);
      // The figures the person saw: the server compares them with what it saved and says so.
      // Not on the party pick: its save reprices the lines, so the figures change by right.
      if (preview && opts?.report !== false) header._totals_preview = Object.fromEntries(PREVIEW_REPORT_KEYS.map((k) => [k, preview.totals[k]]));
      const saved = (linesToSend.length || deletions.length)
        ? await saveTransactionWithLines(modelName, { ...header, lines: [...linesToSend, ...deletions] })
        : await saveRecord(modelName, header);
      const repriced = repriceNote(saved?.messages);
      const said = (Array.isArray(saved?.messages) ? saved.messages : []).filter((m: unknown) => typeof m === 'string');
      dispatch(showToast({ message: [opts?.message || `${modelName} saved`, repriced, ...said].filter(Boolean).join('. '), type: 'success' }));
      if (opts?.keepEditing !== true) setIsEditing(false);
      fetchData();
      onAfterSave?.();
    } catch (err: any) {
      dispatch(showToast({ message: `Save failed: ${refusalMessage(err)}`, type: 'error' }));
    } finally {
      setSaving(false);
    }
  }, [editData, data, saveBlocked, modelName, dispatch, fetchData, onAfterSave, preview]);

  // The party pick is on the edit copy now: save it and stay in edit on the reloaded record.
  useEffect(() => {
    if (!partyPicked.current || !editData) return;
    const party = partyPicked.current;
    partyPicked.current = null;
    save({ keepEditing: true, report: false, message: `${party === 'vendor' ? 'Vendor' : 'Customer'} applied` });
  }, [editData, save]);

  useEffect(() => {
    if (!shipToPicked.current || !editData?._ship_to_from) return;
    shipToPicked.current = false;
    save({ keepEditing: true, report: false, message: 'Ship-to applied' });
  }, [editData, save]);

  const addNew = useCallback(async () => {
    try {
      const { id: newId } = await newRecord(modelName);
      if (newId) windowManager.ensureWindow(`/${modelName}/${newId}`, `${modelName} #${newId}`);
    } catch {
      dispatch(showToast({ message: `Failed to create ${modelName}`, type: 'error' }));
    }
  }, [modelName, windowManager, dispatch]);

  // ── Communications: a phone, address or domain is edited in its own record's card ──
  const [commCard, setCommCard] = useState<{ field: string; anchor: DOMRect } | null>(null);
  const openCommunication = useCallback((field: string, el: HTMLElement) => {
    if (communicationField(modelName, field)) setCommCard({ field, anchor: el.getBoundingClientRect() });
  }, [modelName]);
  const closeCommunication = useCallback(() => setCommCard(null), []);
  // A card save saves this record on the server too: take what changed — cache, pointers,
  // login email, version — and keep unsaved edits here.
  const refreshCommunications = useCallback(async () => {
    if (!recordId) return;
    const response = await getRecord(modelName, recordId);
    const record = (response as any)?.record || response;
    const pointers = Object.values(COMMUNICATION_FIELDS[modelName] || {}).map((c) => c.pointer);
    const pick = (prev: any) => prev && ({
      ...prev, refs: record.refs, ...Object.fromEntries(pointers.map((p) => [p, record[p]])),
      email: record.email, version: record.version, dt_modified: record.dt_modified,
    });
    setData(pick);
    setEditData(pick);
  }, [modelName, recordId]);
  // When a card in another window saves, show the server's refreshed cache (unless mid-edit).
  useEffect(() => windowChannel.on('record-saved', ({ model }: any) => {
    if (model && showsCommunication(modelName, model) && !isEditing) fetchData();
  }), [modelName, isEditing, fetchData]);

  /** What the form shows: the edit copy while editing, with the communication cache entries
   *  the pointers name, and the server's preview totals on the document and its lines. */
  const currentData = useMemo(() => {
    const withCache = (rec: any) => rec && COMMUNICATION_FIELDS[modelName] ? {
      ...rec,
      ...Object.fromEntries(Object.entries(COMMUNICATION_FIELDS[modelName]).map(([f, c]) => [f, communicationValue(c, rec)])),
    } : rec;
    if (!isEditing) return withCache(data);
    if (!editData || !preview) return withCache(editData);
    return {
      ...withCache(editData),
      totals: preview.totals,
      lines: (editData.lines || []).map((l: any) => {
        const t = preview.byLine.get(l);
        return t ? { ...l, totals: t } : l;
      }),
    };
  }, [isEditing, data, editData, preview, modelName]);

  // ── Host contract (DataBrowser's inline pane owns the toolbar) ───
  // Registered while mounted, forgotten on unmount: an earlier record's save must not stay in
  // the host's ref after the pane moves on (the inventory of 2026-11-05 found it could).
  useEffect(() => {
    onRegisterActions?.({ save, cancel, addNew });
    return () => { onRegisterActions?.({}); };
  }, [onRegisterActions, save, cancel, addNew]);
  useEffect(() => { onEditStateChange?.(isEditing); }, [isEditing, onEditStateChange]);

  return {
    data, editData, currentData, isEditing, loading, saving, saveBlocked, hasChanges,
    editTier, canEdit, isPendMode: editTier === 'pend', hold: hold.heldBy as HeldBy | null,
    withLines, preview, previewError,
    fetchData, startEdit, cancel, setField, setLines, pickShipTo, save, addNew, setData, setEditData,
    comm: { card: commCard, spec: commCard && communicationField(modelName, commCard.field),
            open: openCommunication, close: closeCommunication, refresh: refreshCommunications },
  };
}
