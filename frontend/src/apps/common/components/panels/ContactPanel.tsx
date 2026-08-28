/* LastChecked: 2026-08-26 | WhereUsed: DynamicDetail, CoreTabPanel, ActionFloatingWindow, TouchForm | WhoCreated: Bill+Claude */
/**
 * ContactPanel — contacts linked to any record via refs.links.contact.
 *
 * Built on DbColumns (PanelTable) for consistent column config, hamburger,
 * section header, collapse, add/remove. Same pattern as every other panel.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { useWindowManager } from "@/context/WindowManagerContext";
import {
  FaEnvelope,
  FaExternalLinkAlt,
  FaPhone,
  FaStar,
  FaTimes,
} from "react-icons/fa";
import { getRecord, getRecords } from "@/api/wcapi";
import { getModelDetailPath, getModelWindowTitle } from "./getModelDetailPath";
import { DbColumns } from "./DbColumns";
import type { DbColumnDef } from "./DbColumns";
import { withDevIdentifier } from "@/components/common/DevIdentifier";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface RefContact {
  contact_id: number;
  purpose: string;
  attention?: string;
  email?: string | { id: any; name: any; value: any }[];
  phone?: string | { id: any; name: any; value: any }[];
  full?: string | string[];
  domain?: string | { id: any; name: any; value: any }[];
  address?: any;
  /** Runtime — resolved display values (fetched from contact record if inline data missing) */
  _resolved_name?: string;
  _resolved_email?: string;
  _resolved_phone?: string;
}

export function normalizeRefsLinksContact(apiContacts: any[]): RefContact[] {
  if (!Array.isArray(apiContacts)) return [];
  return apiContacts.map((c, idx) => {
    let base = c;
    let purpose = c.purpose || '';
    let contact_id: any;
    if (c.contact && typeof c.contact === 'object') {
      base = c.contact;
      purpose = c.purpose || base.purpose || '';
      contact_id = c.contact.id;
    } else {
      contact_id = c.id;
    }
    if (contact_id == null || contact_id === '') contact_id = idx + 1;
    return { contact_id, purpose, attention: base.attention, email: base.email, phone: base.phone, full: base.full || base.address, domain: base.domain, address: base.address };
  });
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ContactPanelProps {
  contacts: RefContact[];
  isEditing?: boolean;
  parent_model?: string;
  parentId?: number;
  order_id?: number;
  customer_id?: number;
  customer_name?: string;
  onAdd?: (purpose: string) => void;
  onRemove?: (contactId: number) => void;
  onEdit?: (contact: RefContact) => void;
  onChange?: (contacts: RefContact[]) => void;
  onSaveSuccess?: () => void;
  onRefresh?: () => void;
  loading?: boolean;
  allowCreate?: boolean;
  primaryContactId?: number | null;
  onSetPrimary?: (contact: RefContact) => void;
  title?: string;
  defaultCollapsed?: boolean;
}

// Standard purposes in display order
const STANDARD_PURPOSES = [
  "billto", "shipto", "attention", "approver", "buyer",
  "cc", "notify", "support", "rep", "sales",
];

// Purpose badge styles
const PURPOSE_STYLES: Record<string, React.CSSProperties> = {
  billto: { background: 'var(--db-badge-blue-bg)', color: 'var(--db-badge-blue-text)' },
  shipto: { background: 'var(--db-badge-green-bg)', color: 'var(--db-badge-green-text)' },
  attention: { background: 'var(--db-badge-amber-bg)', color: 'var(--db-badge-amber-text)' },
  approver: { background: 'var(--db-badge-purple-bg)', color: 'var(--db-badge-purple-text)' },
  buyer: { background: 'var(--db-badge-cyan-bg)', color: 'var(--db-badge-cyan-text)' },
};

const DEFAULT_PURPOSE_STYLE: React.CSSProperties = {
  background: 'var(--db-surface-alt)',
  color: 'var(--db-text)',
};

const purposeBadgeStyle = (purpose: string): React.CSSProperties =>
  PURPOSE_STYLES[purpose] ?? DEFAULT_PURPOSE_STYLE;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const extractEmail = (field: RefContact["email"]): string => {
  if (!field) return "";
  if (typeof field === "string") return field;
  if (Array.isArray(field) && field.length > 0) {
    const first = field[0];
    return typeof first === "object" ? first.value ?? first.name ?? "" : String(first);
  }
  return "";
};

const extractPhone = (field: RefContact["phone"]): string => {
  if (!field) return "";
  if (typeof field === "string") return field;
  if (Array.isArray(field) && field.length > 0) {
    const first = field[0];
    return typeof first === "object" ? first.value ?? first.name ?? "" : String(first);
  }
  return "";
};

// ---------------------------------------------------------------------------
// Column definitions for DbColumns
// ---------------------------------------------------------------------------

function buildColumns(
  isEditing: boolean,
  primaryContactId: number | null | undefined,
  onSetPrimary: ((contact: RefContact) => void) | undefined,
  onRemove: (contactId: number) => void,
  onOpen: (contact: RefContact) => void,
): DbColumnDef<RefContact>[] {
  return [
    {
      key: "purpose",
      label: "purpose",
      width: "72px",
      render: (c) => (
        <span
          className="px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide"
          style={purposeBadgeStyle(c.purpose)}
        >
          {c.purpose || "—"}
        </span>
      ),
    },
    {
      key: "contact_id",
      label: "#",
      width: "48px",
      className: "font-mono text-right",
      render: (c) => <span>#{c.contact_id}</span>,
    },
    {
      key: "name",
      label: "name",
      width: "180px",
      render: (c) => (
        <span className="truncate">
          {c._resolved_name || c.attention || `Contact #${c.contact_id}`}
        </span>
      ),
    },
    {
      key: "email",
      label: "email",
      render: (c) => {
        const email = c._resolved_email || extractEmail(c.email);
        return email ? (
          <span className="truncate flex items-center gap-1" style={{ color: 'var(--db-text-muted)' }}>
            <FaEnvelope size={9} className="shrink-0" style={{ color: 'var(--db-text-dim)' }} />
            {email}
          </span>
        ) : null;
      },
    },
    {
      key: "phone",
      label: "phone",
      width: "130px",
      render: (c) => {
        const phone = c._resolved_phone || extractPhone(c.phone);
        return phone ? (
          <span className="truncate flex items-center gap-1" style={{ color: 'var(--db-text-muted)' }}>
            <FaPhone size={9} className="shrink-0" style={{ color: 'var(--db-text-dim)' }} />
            {phone}
          </span>
        ) : null;
      },
    },
    {
      key: "actions",
      label: "",
      width: "72px",
      render: (c) => (
        <span className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          {onSetPrimary && (
            <button
              type="button"
              title={primaryContactId === c.contact_id ? "Primary contact" : "Set as primary"}
              className={`p-1 rounded transition-colors ${primaryContactId === c.contact_id ? 'db-text-gold' : 'db-text-dim'}`}
              onClick={() => { if (primaryContactId !== c.contact_id) onSetPrimary(c); }}
              disabled={primaryContactId === c.contact_id}
            >
              <FaStar size={10} />
            </button>
          )}
          {isEditing && (
            <button
              type="button"
              title="Remove contact"
              className="p-1 rounded transition-colors db-text-dim"
              onClick={() => onRemove(c.contact_id)}
            >
              <FaTimes size={10} />
            </button>
          )}
          <button
            type="button"
            title="Open contact"
            className="p-1 rounded transition-colors db-text-dim"
            onClick={() => onOpen(c)}
          >
            <FaExternalLinkAlt size={10} />
          </button>
        </span>
      ),
    },
  ];
}

// ---------------------------------------------------------------------------
// ContactPanel
// ---------------------------------------------------------------------------

const ContactPanel: React.FC<ContactPanelProps> = ({
  contacts = [],
  isEditing = false,
  parent_model,
  parentId,
  customer_id,
  customer_name,
  onRemove,
  onChange,
  onSaveSuccess,
  primaryContactId,
  onSetPrimary,
  title = "Contacts",
  defaultCollapsed = false,
}) => {
  const windowManager = useWindowManager();
  const [resolvedContacts, setResolvedContacts] = useState<RefContact[]>([]);

  // Resolve missing contact data from backend
  useEffect(() => {
    let cancelled = false;
    const resolve = async () => {
      const resolved = await Promise.all(
        contacts.map(async (c) => {
          const inlineEmail = extractEmail(c.email);
          const inlinePhone = extractPhone(c.phone);
          const hasName = c.attention && c.attention !== `Contact #${c.contact_id}`;
          if ((inlineEmail || inlinePhone) && hasName) {
            return { ...c, _resolved_name: c.attention, _resolved_email: inlineEmail, _resolved_phone: inlinePhone };
          }
          if (!c.contact_id || c.contact_id <= 0) return c;
          try {
            const result = await getRecord("contact", c.contact_id);
            const data = result?.record ?? result;
            const comms = data?.communications;
            return {
              ...c,
              _resolved_name: c.attention || data?.attention || data?.name || [data?.name_first, data?.name_last].filter(Boolean).join(" ") || undefined,
              _resolved_email: inlineEmail || comms?.emails?.[0]?.email || "",
              _resolved_phone: inlinePhone || comms?.phones?.[0]?.number || "",
            };
          } catch {
            return c;
          }
        })
      );
      if (!cancelled) setResolvedContacts(resolved);
    };
    resolve();
    return () => { cancelled = true; };
  }, [contacts]);

  // Sort: standard purposes first, then alphabetical
  const sorted = [...resolvedContacts].sort((a, b) => {
    const idxA = STANDARD_PURPOSES.indexOf(a.purpose);
    const idxB = STANDARD_PURPOSES.indexOf(b.purpose);
    const orderA = idxA >= 0 ? idxA : STANDARD_PURPOSES.length;
    const orderB = idxB >= 0 ? idxB : STANDARD_PURPOSES.length;
    if (orderA !== orderB) return orderA - orderB;
    return (a.purpose || "").localeCompare(b.purpose || "");
  });

  // Auto-refresh on contact-saved event
  const handleContactSaved = useCallback(
    (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail && parent_model && parentId && detail.parentModel === parent_model && detail.parentId === parentId) {
        onSaveSuccess?.();
      }
    },
    [parent_model, parentId, onSaveSuccess],
  );

  useEffect(() => {
    window.addEventListener("contact-saved", handleContactSaved);
    return () => window.removeEventListener("contact-saved", handleContactSaved);
  }, [handleContactSaved]);

  const handleOpen = (contact: RefContact) => {
    const path = getModelDetailPath("contact", contact.contact_id);
    const label = getModelWindowTitle("contact", contact.contact_id, undefined, contact.attention);
    windowManager.ensureWindow(path, label, { maximized: false });
  };

  const handleRemove = (contactId: number) => {
    if (onChange) onChange(contacts.filter((c) => c.contact_id !== contactId));
    if (onRemove) onRemove(contactId);
  };

  const [adding, setAdding] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => { if (adding) searchInputRef.current?.focus(); }, [adding]);

  const existingIds = new Set(contacts.map(c => c.contact_id));

  const doSearch = useCallback(async (q: string) => {
    if (q.length < 2) { setSearchResults([]); return; }
    setSearchLoading(true);
    try {
      const res = await getRecords("contact", { keyword: q, limit: 10 }) as any;
      const records = (res?.results || []).filter((r: any) => !existingIds.has(r.id));
      setSearchResults(records);
    } catch { setSearchResults([]); }
    setSearchLoading(false);
  }, [existingIds]);

  const handleSearchInput = (val: string) => {
    setSearchQuery(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(val), 300);
  };

  const handleSelectContact = (record: any) => {
    if (onChange) {
      const newContact: RefContact = {
        contact_id: record.id,
        purpose: "primary",
        attention: record.attention || record.name || [record.name_first, record.name_last].filter(Boolean).join(" ") || undefined,
        email: record.email || record.communications?.emails?.[0]?.email,
        phone: record.phone || record.communications?.phones?.[0]?.number,
      };
      onChange([...contacts, newContact]);
    }
    setAdding(false);
    setSearchQuery("");
    setSearchResults([]);
  };

  const handleAdd = () => setAdding(true);

  const columns = buildColumns(isEditing, primaryContactId, onSetPrimary, handleRemove, handleOpen);

  return (
    <>
      <DbColumns<RefContact>
        storageKey={`panel:${parent_model || 'generic'}:contacts`}
        columns={columns}
        data={sorted}
        rowKey={(c) => `${c.contact_id}-${c.purpose}`}
        onSelectRow={handleOpen}
        sectionLabel={title}
        sectionIcon="👤"
        onAdd={(isEditing) ? handleAdd : undefined}
        defaultCollapsed={defaultCollapsed}
        compact
        emptyMessage="No contacts linked"
      />
      {adding && (
        <div style={{ padding: '6px 12px', borderTop: '1px solid var(--db-border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearchInput(e.target.value)}
              placeholder="Search contact..."
              className="db-input"
              style={{ flex: 1, fontSize: 11, padding: '3px 8px' }}
            />
            <button onClick={() => { setAdding(false); setSearchQuery(""); setSearchResults([]); }} className="db-text-dim" style={{ fontSize: 11 }}>Cancel</button>
          </div>
          {searchLoading && <div style={{ fontSize: 10, color: 'var(--db-text-muted)', padding: '4px 0' }}>Searching...</div>}
          {searchResults.length > 0 && (
            <div style={{ maxHeight: 160, overflowY: 'auto', marginTop: 4 }}>
              {searchResults.map((r) => (
                <button
                  key={r.id}
                  onClick={() => handleSelectContact(r)}
                  className="db-list-row"
                  style={{ display: 'flex', gap: 8, padding: '4px 8px', width: '100%', textAlign: 'left', fontSize: 11, cursor: 'pointer' }}
                >
                  <span className="font-mono" style={{ width: 50, flexShrink: 0, color: 'var(--db-text-dim)' }}>
                    #{r.id}
                  </span>
                  <span className="truncate" style={{ flex: 1 }}>
                    {r.attention || r.name || [r.name_first, r.name_last].filter(Boolean).join(" ") || `Contact #${r.id}`}
                  </span>
                  {r.email && (
                    <span style={{ fontSize: 10, color: 'var(--db-text-muted)' }}>{typeof r.email === 'string' ? r.email : ''}</span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </>
  );
};

const ContactPanelWrapped = withDevIdentifier(ContactPanel, "ContactPanel", "teal", 'apps/common/components/panels/ContactPanel.tsx');
export { ContactPanelWrapped as ContactPanel };
export default ContactPanelWrapped;
