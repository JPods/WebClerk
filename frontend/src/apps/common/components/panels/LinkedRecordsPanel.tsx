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
import React, { useState, useEffect, useCallback, useRef } from "react";
import { useWindowManager } from "@/context/WindowManagerContext";
import { getRecord, getRecords, saveRecord } from "@/api/wcapi";
import { DbColumns } from "./DbColumns";
import type { DbColumnDef } from "./DbColumns";
import { getModelDetailPath, getModelWindowTitle, getModelWindowPreset } from "./getModelDetailPath";
import { FaTimes, FaExternalLinkAlt } from "react-icons/fa";
import { formatDt } from "@/utils/fieldFormatters";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type Rec = Record<string, any>;

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
  /** Allow add/remove (default true) */
  editable?: boolean;
  /** Extra columns beyond the defaults */
  extraColumns?: DbColumnDef<Rec>[];
  /** Callback after link changes */
  onLinksChanged?: (linkedIds: number[]) => void;
}

// ---------------------------------------------------------------------------
// Default columns — every model gets these; hamburger hides what's not needed
// ---------------------------------------------------------------------------

const MODEL_ICONS: Record<string, string> = {
  action: "📋", touch: "📞", document: "📄", contact: "👤",
  item: "📦", order: "🛒", invoice: "🧾", proposal: "📝",
  purchase: "🏷️", receipt: "📥", workorder: "🔧", project: "📊",
  customer: "🏢", vendor: "🏭", manufacturer: "🏭", email: "✉️",
  serial: "🔢", payment: "💳", warehouse: "🏪", campaign: "📣",
  setting: "⚙️", report: "📈",
};

function defaultColumns(
  linkedModel: string,
  editable: boolean,
  onRemove: (id: number) => void,
  onOpen: (record: Rec) => void,
): DbColumnDef<Rec>[] {
  const cols: DbColumnDef<Rec>[] = [
    {
      key: "ida",
      label: "id",
      width: "80px",
      className: "font-mono",
      render: (r) => <span>{r.ida || `#${r.id}`}</span>,
    },
    {
      key: "name",
      label: "name",
      render: (r) => (
        <span className="truncate">
          {r.name || r.attention || r.display_name || r.subject || r.title || r.description || ""}
        </span>
      ),
    },
    {
      key: "status",
      label: "status",
      width: "90px",
      defaultVisible: true,
      render: (r) => r.status ? (
        <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold" style={{
          background: 'var(--db-surface-alt)',
          color: 'var(--db-text)',
        }}>
          {r.status}
        </span>
      ) : null,
    },
    {
      key: "dt_created",
      label: "created",
      width: "90px",
      defaultVisible: false,
      render: (r) => <span style={{ color: 'var(--db-text-muted)' }}>{r.dt_created ? formatDt(r.dt_created, 'date') : ""}</span>,
    },
    {
      key: "channel",
      label: "channel",
      width: "80px",
      defaultVisible: linkedModel === "touch",
      render: (r) => <span>{r.channel || ""}</span>,
    },
    {
      key: "direction",
      label: "dir",
      width: "40px",
      defaultVisible: linkedModel === "touch",
      render: (r) => <span>{r.direction === "in" ? "←" : r.direction === "out" ? "→" : ""}</span>,
    },
    {
      key: "sku",
      label: "sku",
      width: "100px",
      defaultVisible: linkedModel === "item",
      render: (r) => <span className="font-mono">{r.sku || ""}</span>,
    },
    {
      key: "totals_total",
      label: "total",
      width: "90px",
      className: "text-right",
      defaultVisible: ["order", "invoice", "proposal", "purchase", "payment"].includes(linkedModel),
      render: (r) => {
        const total = r.totals?.total ?? r.total;
        return total != null ? <span>${Number(total).toFixed(2)}</span> : null;
      },
    },
    {
      key: "_actions",
      label: "",
      width: "56px",
      render: (r) => (
        <span className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          {editable && (
            <button
              type="button"
              title="Unlink"
              className="p-1 rounded transition-colors db-text-dim"
              onClick={() => onRemove(r.id)}
            >
              <FaTimes size={10} />
            </button>
          )}
          <button
            type="button"
            title="Open"
            className="p-1 rounded transition-colors db-text-dim"
            onClick={() => onOpen(r)}
          >
            <FaExternalLinkAlt size={10} />
          </button>
        </span>
      ),
    },
  ];

  return cols;
}

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
          style={{ flex: 1, fontSize: 11, padding: '3px 8px' }}
        />
        <button onClick={onClose} className="db-text-dim" style={{ fontSize: 11 }}>Cancel</button>
      </div>
      {searching && <div style={{ fontSize: 10, color: 'var(--db-text-muted)', padding: '4px 0' }}>Searching...</div>}
      {results.length > 0 && (
        <div style={{ maxHeight: 160, overflowY: 'auto', marginTop: 4 }}>
          {results.map((r) => (
            <button
              key={r.id}
              onClick={() => { onSelect(r); setQuery(""); setResults([]); }}
              className="db-list-row"
              style={{ display: 'flex', gap: 8, padding: '4px 8px', width: '100%', textAlign: 'left', fontSize: 11, cursor: 'pointer' }}
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
  editable = true,
  extraColumns,
  onLinksChanged,
}) => {
  const windowManager = useWindowManager();
  const [records, setRecords] = useState<Rec[]>([]);
  const [linkedIds, setLinkedIds] = useState<number[]>([]);
  const [adding, setAdding] = useState(false);
  const [loading, setLoading] = useState(false);

  // Load linked record IDs from parent's refs.links.{linkedModel}
  const loadLinks = useCallback(async () => {
    try {
      const res = await getRecord(parentModel, parentId);
      const parent = res?.record || res;
      const links = parent?.refs?.links?.[linkedModel] || [];
      const ids: number[] = links.map((l: any) => typeof l === 'number' ? l : l?.id).filter(Boolean);
      setLinkedIds(ids);
      return ids;
    } catch {
      return [];
    }
  }, [parentModel, parentId, linkedModel]);

  // Fetch the actual records by IDs
  const fetchRecords = useCallback(async (ids: number[]) => {
    if (ids.length === 0) { setRecords([]); return; }
    setLoading(true);
    try {
      const res = await getRecords(linkedModel, { id__in: ids.join(','), limit: 100 }) as any;
      setRecords(res?.results || []);
    } catch { setRecords([]); }
    setLoading(false);
  }, [linkedModel]);

  // Initial load
  useEffect(() => {
    loadLinks().then(fetchRecords);
  }, [loadLinks, fetchRecords]);

  // Save updated links to parent record
  const saveLinks = useCallback(async (newIds: number[]) => {
    const linkRefs = newIds.map(id => ({ id }));
    try {
      await saveRecord(parentModel, {
        id: parentId,
        [`refs.links.${linkedModel}`]: linkRefs,
      });
      setLinkedIds(newIds);
      onLinksChanged?.(newIds);
    } catch (err) {
      console.error(`Failed to save ${linkedModel} links:`, err);
    }
  }, [parentModel, parentId, linkedModel, onLinksChanged]);

  // Add a linked record
  const handleAdd = useCallback(async (record: Rec) => {
    const newIds = [...linkedIds, record.id];
    await saveLinks(newIds);
    setRecords(prev => [...prev, record]);
    setAdding(false);
  }, [linkedIds, saveLinks]);

  // Remove a linked record
  const handleRemove = useCallback(async (recordId: number) => {
    const newIds = linkedIds.filter(id => id !== recordId);
    await saveLinks(newIds);
    setRecords(prev => prev.filter(r => r.id !== recordId));
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

  const sectionLabel = title || linkedModel.charAt(0).toUpperCase() + linkedModel.slice(1) + 's';
  const sectionIcon = icon || MODEL_ICONS[linkedModel] || "🔗";
  const excludeIds = new Set(linkedIds);

  const columns = [
    ...defaultColumns(linkedModel, editable, handleRemove, handleOpen),
    ...(extraColumns || []),
  ];

  return (
    <DbColumns<Rec>
      storageKey={`panel:${parentModel}:${linkedModel}`}
      columns={columns}
      data={records}
      rowKey={(r) => r.id}
      onSelectRow={handleOpen}
      sectionLabel={sectionLabel}
      sectionIcon={sectionIcon}
      onAdd={editable ? () => setAdding(true) : undefined}
      defaultCollapsed={defaultCollapsed}
      compact
      emptyMessage={loading ? "Loading..." : `No ${linkedModel}s linked`}
    >
      {adding && (
        <RecordSearchInline
          linkedModel={linkedModel}
          excludeIds={excludeIds}
          parentId={linkedModel === parentModel ? parentId : undefined}
          onSelect={handleAdd}
          onClose={() => setAdding(false)}
        />
      )}
    </DbColumns>
  );
};

export default LinkedRecordsPanel;
