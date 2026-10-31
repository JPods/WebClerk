/* LastChecked: 2026-08-26 | WhereUsed: DynamicDetail (universal panel) | WhoCreated: Bill+Claude */
/**
 * LinkedRecordsPanel — universal panel for linking any model to any record.
 *
 * Links are stored in refs.links.{modelName} on the parent record.
 * Built on DbColumns for consistent column config, hamburger, section header.
 *
 * Usage:
 *   <LinkedRecordsPanel
 *     linkedModel="item"
 *     parentModel="action"
 *     parentId={42}
 *   />
 *
 * The panel:
 *   1. Reads refs.links.{linkedModel} from parent record → [{id: N}, ...]
 *   2. Fetches those records via getRecords
 *   3. Displays in DbColumns with standard columns (ida, name, status)
 *   4. "+ add" opens inline search → pick record → appends to refs.links
 *   5. "×" removes from refs.links
 *   6. Hamburger for column order/visibility
 *   7. Collapsed by default
 */
import { windowChannel } from '@/utils/windowChannel';
import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { usePanelAdd } from "@/hooks/usePanelAdd";
import { useWindowManager } from "@/context/WindowManagerContext";
import { useDispatch } from "react-redux";
import { getRecord, getRecords, saveRecord, getModelDetail } from "@/api/wcapi";
import { usePanelRecords } from "@/hooks/usePanelRecords";
import { showToast } from "@/store/slices/toastSlice";
import { DbColumns } from "./DbColumns";
import type { DbColumnDef } from "./DbColumns";
import { getModelDetailPath, getModelWindowTitle, getModelWindowPreset } from "./getModelDetailPath";
import { buildColumnsFromSpecs } from "./panelColumnUtils";
import { FaTimes, FaExternalLinkAlt } from "react-icons/fa";
import { getUI } from '@/utils/contactUI';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Rec = Record<string, any>;

/** The orgs a contact belongs to through its own field of the same name. */
const ORG_ROLES = ['customer', 'vendor', 'manufacturer', 'rep'];

interface LinkedRecordsPanelProps {
  /** Model name to link (e.g. "item", "action", "touch", "document") */
  linkedModel: string;
  /** Parent model name (e.g. "order", "contact") */
  parentModel: string;
  /** Parent record ID */
  parentId: number;
  /** Override section label (default: capitalized linkedModel) */
  title?: string;
  /** Override section icon */
  icon?: string;
  /** Start collapsed (default true) */
  defaultCollapsed?: boolean;
  /** Collapse to one line when no records (default false) */
  collapseWhenEmpty?: boolean;
  /** Allow add/remove (default true) */
  editable?: boolean;
  /** Extra columns beyond the defaults */
  extraColumns?: DbColumnDef<Rec>[];
  /** Callback after link changes */
  onLinksChanged?: (linkedIds: number[]) => void;
  /** Allow Option+Cmd+click to remove this panel */
  removable?: boolean;
  /** Called when panel is removed */
  onRemovePanel?: () => void;
}

// ---------------------------------------------------------------------------
// Default columns — every model gets these; hamburger hides what's not needed
// ---------------------------------------------------------------------------

const MODEL_ICONS: Record<string, string> = {
  action: "📋", touch: "📞", document: "📄", contact: "👤",
  item: "📦", order: "🛒", invoice: "🧾", quote: "📝",
  purchase: "🏷️", receipt: "📥", workorder: "🔧", project: "📊",
  customer: "🏢", vendor: "🏭", manufacturer: "🏭", email: "✉️",
  serial: "🔢", cash: "💳", warehouse: "🏪", campaign: "📣",
  setting: "⚙️", report: "📈",
};

// ---------------------------------------------------------------------------
// Inline search for adding linked records
// ---------------------------------------------------------------------------

const RecordSearchInline: React.FC<{
  linkedModel: string;
  excludeIds: Set<number>;
  parentId?: number;
  onSelect: (record: Rec) => void;
  onClose: () => void;
}> = ({ linkedModel, excludeIds, parentId, onSelect, onClose }) => {
  const active = getUI<string>('theme.active', 'dark');
  const baseFontSize = getUI<number>(`theme.${active}.font.size`, 13);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Rec[]>([]);
  const [searching, setSearching] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  const doSearch = useCallback(async (q: string) => {
    if (q.length < 2) { setResults([]); return; }
    setSearching(true);
    try {
      const res = await getRecords(linkedModel, { keyword: q, limit: 10 }) as any;
      const records = (res?.results || []).filter((r: Rec) => !excludeIds.has(r.id) && r.id !== parentId);
      setResults(records);
    } catch { setResults([]); }
    setSearching(false);
  }, [linkedModel, excludeIds]);

  const handleInput = (val: string) => {
    setQuery(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(val), 300);
  };

  return (
    <div style={{ padding: '6px 12px', borderTop: '1px solid var(--db-border)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => handleInput(e.target.value)}
          placeholder={`Search ${linkedModel}...`}
          className="db-input"
          style={{ flex: 1, fontSize: baseFontSize - 2, padding: '3px 8px' }}
        />
        <button onClick={onClose} className="db-text-dim" style={{ fontSize: baseFontSize - 2 }}>Cancel</button>
      </div>
      {searching && <div style={{ fontSize: 10, color: 'var(--db-text-muted)', padding: '4px 0' }}>Searching...</div>}
      {results.length > 0 && (
        <div style={{ maxHeight: 160, overflowY: 'auto', marginTop: 4 }}>
          {results.map((r) => (
            <button
              key={r.id}
              onClick={() => { onSelect(r); setQuery(""); setResults([]); }}
              className="db-list-row"
              style={{ display: 'flex', gap: 8, padding: '4px 8px', width: '100%', textAlign: 'left', fontSize: baseFontSize - 2, cursor: 'pointer' }}
            >
              <span className="font-mono" style={{ width: 60, flexShrink: 0, color: 'var(--db-text-dim)' }}>
                {r.ida || `#${r.id}`}
              </span>
              <span className="truncate" style={{ flex: 1 }}>
                {r.name || r.attention || r.display_name || r.subject || r.title || r.description || ""}
              </span>
              {r.status && (
                <span style={{ fontSize: 10, color: 'var(--db-text-muted)' }}>{r.status}</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// LinkedRecordsPanel
// ---------------------------------------------------------------------------

export const LinkedRecordsPanel: React.FC<LinkedRecordsPanelProps> = ({
  linkedModel,
  parentModel,
  parentId,
  title,
  icon,
  defaultCollapsed = true,
  collapseWhenEmpty = false,
  editable = true,
  extraColumns,
  onLinksChanged,
  removable = false,
  onRemovePanel,
}) => {
  const windowManager = useWindowManager();
  const dispatch = useDispatch();
  const [linkedIds, setLinkedIds] = useState<number[]>([]);
  const [assigning, setAssigning] = useState(false);
  const [settingPanelCols, setSettingPanelCols] = useState<DbColumnDef<Rec>[] | null>(null);
  const [settingLoaded, setSettingLoaded] = useState(false);
  const panelKey = `${parentModel}:${parentId}:${linkedModel}`;

  // Load panel columns from wc:model Setting → config.layout.panel
  const [settingsVersion, setSettingsVersion] = useState(0);

  // Listen for flush events — Alice or admin bumped dt_changed
  useEffect(() => {
    const handler = () => setSettingsVersion(v => v + 1);
    window.addEventListener('wc3-settings-changed', handler);
    return () => window.removeEventListener('wc3-settings-changed', handler);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const res = await getRecords('setting', {
          parent_model: linkedModel,
          purpose: 'wc:model',
          limit: 1,
        }) as any;
        const setting = res?.results?.[0] ?? res?.records?.[0];
        const panelSpecs = setting?.config?.layout?.panel;
        if (Array.isArray(panelSpecs) && panelSpecs.length > 0) {
          setSettingPanelCols(buildColumnsFromSpecs(panelSpecs) as DbColumnDef<Rec>[]);
        }
      } catch { /* no setting */ }
      setSettingLoaded(true);
    })();
  }, [linkedModel, settingsVersion]);

  // Dismiss this panel's search when another panel opens its search
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail?.panelKey && detail.panelKey !== panelKey) {
        setAssigning(false);
      }
    };
    window.addEventListener('panel-assign-opened', handler);
    return () => window.removeEventListener('panel-assign-opened', handler);
  }, [panelKey]);

  const openAssign = useCallback(() => {
    // Dismiss any other open assign panels first
    window.dispatchEvent(new CustomEvent('panel-assign-opened', { detail: { panelKey } }));
    setAssigning(true);
  }, [panelKey]);

  // The linked ids are the parent's refs.links.{linkedModel}; the rows are those records. One
  // read through the panel hook: a failure shows in the frame (it read as "none linked" before).
  const readLinked = useCallback(async (): Promise<Rec[]> => {
    const res = await getRecord(parentModel, parentId);
    const parent = res?.record || res;
    const links = parent?.refs?.links?.[linkedModel] || [];
    const ids: number[] = links.map((l: any) => typeof l === 'number' ? l : l?.id).filter(Boolean);
    setLinkedIds(ids);
    if (ids.length === 0) return [];
    const rows = await getRecords(linkedModel, { id__in: ids.join(','), limit: 100 }) as any;
    return rows?.results || [];
  }, [parentModel, parentId, linkedModel]);
  const { records, loading, error, refresh, status } = usePanelRecords<Rec>(linkedModel,
    { parentModel, parentId, linkedModel }, { read: readLinked });
  const initialLoadDone = status.empty || records.length > 0 || !!error;

  // The parent's refs.links changed when the parent was saved, from any window.
  useEffect(() => windowChannel.on('record-saved', ({ model, id }) => {
    if (model === parentModel && id === parentId) refresh();
  }), [parentModel, parentId, refresh]);

  // Save updated links to parent record, then read the server again. A refused save says so.
  const saveLinks = useCallback(async (newIds: number[]): Promise<boolean> => {
    const linkRefs = newIds.map(id => ({ id }));
    try {
      if (linkedModel === 'contact' && ORG_ROLES.includes(parentModel)) {
        // An org's contacts are the contacts' own customer/vendor/… field (Bill, 2026-10-17):
        // linking edits the contact; the org serves the list and stores no copy.
        const added = newIds.filter(id => !linkedIds.includes(id));
        const removed = linkedIds.filter(id => !newIds.includes(id));
        for (const id of added) await saveRecord('contact', { id, [parentModel]: parentId });
        for (const id of removed) await saveRecord('contact', { id, [parentModel]: { mode: 'delete' } });
      } else await saveRecord(parentModel, {
        id: parentId,
        [`refs.links.${linkedModel}`]: linkRefs,
      });
      onLinksChanged?.(newIds);
      return true;
    } catch (err: any) {
      dispatch(showToast({ message: `Could not save ${linkedModel} links: ${err?.response?.data?.message || err?.message || err}`, type: 'error' }));
      return false;
    } finally {
      refresh();
    }
  }, [parentModel, parentId, linkedModel, linkedIds, onLinksChanged, dispatch, refresh]);

  // Assign an existing record (search → link)
  const handleAssign = useCallback(async (record: Rec) => {
    if (await saveLinks([...linkedIds, record.id])) setAssigning(false);
  }, [linkedIds, saveLinks]);

  // Create a new record and link it — opens in floating window for editing
  // + add (Bill, 2026-10-30): an org's contact is born with the org in its own field; any
  // other linked record is listed in the parent's refs.links once made. The ids the parent
  // holds that are fields of the new record are copied to it.
  const [inherited, setInherited] = useState<Record<string, unknown>>({});
  useEffect(() => {
    if (!editable || !parentId) return;
    let cancelled = false;
    (async () => {
      const [parentRes, detail] = await Promise.all([getRecord(parentModel, parentId), getModelDetail(linkedModel)]);
      const parent = parentRes?.record || parentRes;
      const fieldNames = new Set((detail?.model?.fields || []).map((f: any) => (typeof f === 'string' ? f : f?.name)));
      const has = (k: string) => fieldNames.has(k) || fieldNames.has(k.replace(/_id$/, ''));
      const copied: Record<string, unknown> = {};
      if (parentModel !== linkedModel && has(`${parentModel}_id`)) copied[`${parentModel}_id`] = parentId;
      for (const k of ['contact_id', 'customer_id', 'vendor_id', 'project_id']) if (parent?.[k] && has(k)) copied[k] = parent[k];
      if (!cancelled) setInherited(copied);
    })().catch(() => {});
    return () => { cancelled = true; };
  }, [editable, parentModel, parentId, linkedModel]);
  const orgContact = linkedModel === 'contact' && ORG_ROLES.includes(parentModel);
  const addOptions = useMemo(() => !editable || !parentId ? null : orgContact
    ? { parent: { field: `${parentModel}_id`, id: parentId } }
    : { values: inherited,
        afterMade: async (id: number) => { await saveLinks([...linkedIds, id]); } },
  [editable, parentId, orgContact, parentModel, linkedModel, inherited, linkedIds, saveLinks]);
  const { onAdd, addCard } = usePanelAdd(linkedModel, addOptions);

  // Remove a linked record
  const handleRemove = useCallback(async (recordId: number) => {
    await saveLinks(linkedIds.filter(id => id !== recordId));
  }, [linkedIds, saveLinks]);

  // Open record in floating window — never navigate current view
  // Guard: never open yourself (same model + same ID = viewing yourself)
  const handleOpen = useCallback((record: Rec) => {
    if (linkedModel === parentModel && record.id === parentId) return;
    const path = getModelDetailPath(linkedModel, record.id);
    const title = getModelWindowTitle(linkedModel, record.id, record.ida, record.name || record.attention || record.subject);
    const options = getModelWindowPreset(linkedModel);
    windowManager.ensureWindow(path, title, options);
  }, [linkedModel, parentModel, parentId, windowManager]);

  // Remove panel — confirm if records are linked
  const handleRemovePanel = useCallback(() => {
    if (!removable || !onRemovePanel) return;
    if (linkedIds.length > 0) {
      const pm = linkedModel.endsWith('ch') || linkedModel.endsWith('sh') || linkedModel.endsWith('s') || linkedModel.endsWith('x')
        ? linkedModel + 'es' : linkedModel + 's';
      const label = title || pm.charAt(0).toUpperCase() + pm.slice(1);
      if (!confirm(`Remove ${label} panel? ${linkedIds.length} linked record${linkedIds.length !== 1 ? 's' : ''} will be unlinked.`)) return;
    }
    // Clear refs.links.{model} on the parent record
    saveRecord(parentModel, {
      id: parentId,
      [`refs.links.${linkedModel}`]: null,
    }).catch(() => {});
    onRemovePanel();
  }, [removable, onRemovePanel, linkedIds, linkedModel, parentModel, parentId, title]);

  const pluralModel = linkedModel.endsWith('s') ? linkedModel
    : linkedModel.endsWith('ch') || linkedModel.endsWith('sh') || linkedModel.endsWith('x')
    ? linkedModel + 'es' : linkedModel + 's';
  const sectionLabel = title || pluralModel.charAt(0).toUpperCase() + pluralModel.slice(1);
  const sectionIcon = icon || MODEL_ICONS[linkedModel] || "🔗";
  const excludeIds = new Set(linkedIds);

  // Action column (unlink + open buttons) — always present
  const actionCol: DbColumnDef<Rec> = {
    key: "_actions",
    label: "",
    width: "56px",
    render: (r) => (
      <span className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
        {editable && (
          <button type="button" title="Unlink" className="p-1 rounded transition-colors db-text-dim"
            onClick={() => handleRemove(r.id)}><FaTimes size={10} /></button>
        )}
        <button type="button" title="Open" className="p-1 rounded transition-colors db-text-dim"
          onClick={() => handleOpen(r)}><FaExternalLinkAlt size={10} /></button>
      </span>
    ),
  };

  // Columns from Setting config.layout.panel — single source of truth
  // If no Setting exists, show a flag so Alice/WC_HQ can create one
  const columns = settingPanelCols
    ? [...settingPanelCols, actionCol, ...(extraColumns || [])]
    : [actionCol];  // minimal — missing panel definition

  const missingPanelDef = settingLoaded && !settingPanelCols;

  return (
    <DbColumns<Rec>
      storageKey={`panel:${parentModel}:${linkedModel}`}
      columns={columns}
      data={records}
      rowKey={(r) => r.id}
      onSelectRow={handleOpen}
      sectionLabel={sectionLabel}
      sectionIcon={sectionIcon}
      onAdd={onAdd}
      onAssign={editable ? openAssign : undefined}
      onRemove={removable ? handleRemovePanel : undefined}
      defaultCollapsed={collapseWhenEmpty && initialLoadDone ? records.length === 0 : defaultCollapsed}
      key={collapseWhenEmpty ? `${panelKey}-${initialLoadDone}-${records.length > 0}` : panelKey}
      compact
      loading={loading}
      error={error}
      onRetry={refresh}
      emptyMessage={`No ${(sectionLabel || linkedModel).toLowerCase()} linked`}
    >
      {missingPanelDef && (
        <div className="px-3 py-2 db-font-xs font-mono" style={{ color: 'var(--db-accent-red, #e05252)', background: 'var(--db-surface-alt)' }}>
          missing: setting.config.layout.panel for {linkedModel} — run seed_layouts or ask Alice
        </div>
      )}
      {assigning && (
        <RecordSearchInline
          linkedModel={linkedModel}
          excludeIds={excludeIds}
          parentId={linkedModel === parentModel ? parentId : undefined}
          onSelect={handleAssign}
          onClose={() => setAssigning(false)}
        />
      )}
      {addCard}
    </DbColumns>
  );
};

export default LinkedRecordsPanel;
