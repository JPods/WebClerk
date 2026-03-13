/**
 * ContactPanel - Flat list display of contacts linked to a record
 *
 * Shows contacts as rows in a compact list with purpose, name, email, phone
 * and an "open" button to launch the contact detail in a floating window.
 *
 * This replaces the older grouped-by-purpose card layout (now ContactPanelx2).
 *
 * @see ContactPanelx2 for the legacy grouped layout
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useWindowManager } from "@/context/WindowManagerContext";
import {
  FaChevronDown,
  FaChevronUp,
  FaEdit,
  FaEnvelope,
  FaExternalLinkAlt,
  FaPhone,
  FaPlus,
  FaSlidersH,
  FaSpinner,
  FaStar,
  FaSyncAlt,
  FaTimes,
  FaUser,
} from "react-icons/fa";
import { getRecord } from "@/api/wcapi";
import { getModelDetailPath, getModelWindowTitle } from "./getModelDetailPath";
import { ColumnSetupDialog } from "@/components/common/ColumnSetupDialog";
import { useColumnSetups } from "@/hooks/useColumnSetups";

// Re-export RefContact and normalizeRefsLinksContact from the original file
// so existing imports keep working.
export type { RefContact } from "./ContactPanelx2";
export { normalizeRefsLinksContact } from "./ContactPanelx2";

// Import the type locally for use in this file
import type { RefContact } from "./ContactPanelx2";
import { withDevIdentifier } from "@/components/common/DevIdentifier";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ContactPanelProps {
  contacts: RefContact[];
  isEditing?: boolean;
  /** Generic parent model name for persistence (e.g. 'order', 'invoice', 'vendor') */
  parent_model?: string;
  /** Generic parent record ID for persistence */
  parentId?: number;
  /** Back-compat for transaction/order callers */
  order_id?: number;
  /** Customer ID from parent transaction – used when creating a new contact */
  customer_id?: number;
  /** Customer display name – pre-fills company on new contact */
  customer_name?: string;
  onAdd?: (purpose: string) => void;
  onRemove?: (contactId: number) => void;
  onEdit?: (contact: RefContact) => void;
  onChange?: (contacts: RefContact[]) => void;
  onSaveSuccess?: () => void;
  /** Callback to manually refresh FK-based contact list */
  onRefresh?: () => void;
  /** Whether the contact list is currently loading */
  loading?: boolean;
  /** Allow Create Contact button even when isEditing is false */
  allowCreate?: boolean;
  /** The contact_id currently set as primary on the parent record */
  primaryContactId?: number | null;
  /** Callback when user clicks "Set as Primary" on a contact row */
  onSetPrimary?: (contact: RefContact) => void;
  /** Panel title override */
  title?: string;
  /** Start collapsed */
  defaultCollapsed?: boolean;
}

// Standard purposes in display order
const STANDARD_PURPOSES = [
  "billto",
  "shipto",
  "attention",
  "approver",
  "buyer",
  "cc",
  "notify",
  "support",
  "rep",
  "sales",
];

// Purpose badge colours
const PURPOSE_COLORS: Record<string, string> = {
  billto: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  shipto:
    "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  attention:
    "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  approver:
    "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
  buyer: "bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400",
};

const purposeBadge = (purpose: string) =>
  PURPOSE_COLORS[purpose] ??
  "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300";

/** Column metadata for ColumnSetupDialog */
const CONTACT_COLUMN_METAS = [
  { key: "purpose", label: "purpose" },
  { key: "contact_id", label: "#" },
  { key: "name", label: "name" },
  { key: "email", label: "email" },
  { key: "phone", label: "phone" },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Extract a single display email string from the polymorphic email field */
const extractEmail = (field: RefContact["email"]): string => {
  if (!field) return "";
  if (typeof field === "string") return field;
  if (Array.isArray(field) && field.length > 0) {
    const first = field[0];
    return typeof first === "object"
      ? first.value ?? first.name ?? ""
      : String(first);
  }
  return "";
};

/** Extract a single display phone string */
const extractPhone = (field: RefContact["phone"]): string => {
  if (!field) return "";
  if (typeof field === "string") return field;
  if (Array.isArray(field) && field.length > 0) {
    const first = field[0];
    return typeof first === "object"
      ? first.value ?? first.name ?? ""
      : String(first);
  }
  return "";
};

// ---------------------------------------------------------------------------
// ContactRow - fetches communications from contact model when needed
// ---------------------------------------------------------------------------

interface ContactRowComms {
  email: string;
  phone: string;
  name: string;
}

const ContactRow: React.FC<{
  contact: RefContact;
  isEditing?: boolean;
  isPrimary?: boolean;
  visibleColumns?: Set<string>;
  onRemove?: () => void;
  onEdit?: () => void;
  onOpen?: () => void;
  onSetPrimary?: () => void;
}> = ({
  contact,
  isEditing,
  isPrimary,
  visibleColumns,
  onRemove,
  onEdit,
  onOpen,
  onSetPrimary,
}) => {
  const [comms, setComms] = useState<ContactRowComms | null>(null);
  const [loading, setLoading] = useState(false);

  // Derive inline values first
  const inlineEmail = extractEmail(contact.email);
  const inlinePhone = extractPhone(contact.phone);
  const displayName = contact.attention ?? `Contact #${contact.contact_id}`;

  // Fetch from contact model only when inline data is missing
  useEffect(() => {
    if (inlineEmail || inlinePhone) return; // already have data
    if (!contact.contact_id || contact.contact_id <= 0) return;

    let cancelled = false;
    setLoading(true);

    getRecord("contact", contact.contact_id)
      .then((result: any) => {
        if (cancelled) return;
        const data = result?.record ?? result;
        const c = data?.communications;
        setComms({
          email: c?.emails?.[0]?.email ?? "",
          phone: c?.phones?.[0]?.number ?? "",
          name:
            data?.attention ??
            data?.name ??
            [data?.name_first, data?.name_last].filter(Boolean).join(" ") ??
            "",
        });
      })
      .catch(() => {
        if (!cancelled) setComms({ email: "", phone: "", name: "" });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [contact.contact_id, inlineEmail, inlinePhone]);

  const email = inlineEmail || comms?.email || "";
  const phone = inlinePhone || comms?.phone || "";
  const name =
    displayName !== `Contact #${contact.contact_id}`
      ? displayName
      : comms?.name || displayName;

  return (
    <div className="flex items-center gap-3 px-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-700/50 text-xs group">
      {/* Purpose badge */}
      {(!visibleColumns || visibleColumns.has("purpose")) && (
        <span
          className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide shrink-0 min-w-[56px] text-center ${purposeBadge(
            contact.purpose,
          )}`}
        >
          {contact.purpose || "—"}
        </span>
      )}

      {/* Contact ID */}
      {(!visibleColumns || visibleColumns.has("contact_id")) && (
        <span className="font-mono text-slate-400 shrink-0 w-10 text-right">
          #{contact.contact_id}
        </span>
      )}

      {/* Name */}
      {(!visibleColumns || visibleColumns.has("name")) && (
        <span className="text-slate-800 dark:text-slate-200 truncate min-w-[100px] max-w-[180px]">
          {loading ? (
            <FaSpinner className="inline animate-spin text-slate-300" size={10} />
          ) : (
            name
          )}
        </span>
      )}

      {/* Email */}
      {(!visibleColumns || visibleColumns.has("email")) && (
        <span className="text-slate-500 dark:text-slate-400 truncate min-w-0 flex-1 flex items-center gap-1">
          {email && (
            <>
              <FaEnvelope size={9} className="shrink-0 text-slate-300" />
              <span className="truncate">{email}</span>
            </>
          )}
        </span>
      )}

      {/* Phone */}
      {(!visibleColumns || visibleColumns.has("phone")) && (
        <span className="text-slate-500 dark:text-slate-400 truncate w-[120px] shrink-0 flex items-center gap-1">
          {phone && (
            <>
              <FaPhone size={9} className="shrink-0 text-slate-300" />
              <span className="truncate">{phone}</span>
            </>
          )}
        </span>
      )}

      {/* Actions */}
      <div className="flex items-center gap-1 shrink-0">
        {onSetPrimary && (
          <button
            type="button"
            title={isPrimary ? "Primary contact" : "Set as primary contact"}
            className={`p-1 rounded transition-colors ${
              isPrimary
                ? "text-amber-500"
                : "text-slate-300 hover:text-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/20"
            }`}
            onClick={(e) => {
              e.stopPropagation();
              if (!isPrimary) onSetPrimary();
            }}
            disabled={isPrimary}
          >
            <FaStar size={10} />
          </button>
        )}
        {isEditing && onEdit && (
          <button
            type="button"
            title="Edit contact link"
            className="p-1 rounded text-slate-400 hover:text-blue-600 hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors"
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
          >
            <FaEdit size={10} />
          </button>
        )}
        {isEditing && onRemove && (
          <button
            type="button"
            title="Remove contact"
            className="p-1 rounded text-slate-400 hover:text-red-600 hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
            onClick={(e) => {
              e.stopPropagation();
              onRemove();
            }}
          >
            <FaTimes size={10} />
          </button>
        )}
        <button
          type="button"
          title="Open contact in floating window"
          className="p-1 rounded text-slate-400 hover:text-blue-600 hover:bg-blue-100 dark:hover:bg-blue-900/30 transition-colors"
          onClick={(e) => {
            e.stopPropagation();
            onOpen?.();
          }}
        >
          <FaExternalLinkAlt size={10} />
        </button>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// ContactPanel (list format)
// ---------------------------------------------------------------------------

const ContactPanel: React.FC<ContactPanelProps> = ({
  contacts = [],
  isEditing = false,
  parent_model,
  parentId,
  order_id: _order_id,
  customer_id,
  customer_name,
  onRemove,
  onEdit,
  onChange,
  onSaveSuccess,
  onRefresh,
  loading: externalLoading,
  allowCreate,
  primaryContactId,
  onSetPrimary,
  title = "Contacts",
  defaultCollapsed = false,
}) => {
  console.log("contacts", contacts);
  // Reserved for future edit/create modals
  // const effectiveParentModel = parent_model || (order_id ? "order" : undefined);
  // const effectiveParentId = parentId ?? order_id;
  const windowManager = useWindowManager();
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [showColumnDialog, setShowColumnDialog] = useState(false);
  const columnSetups = useColumnSetups("panel:contacts");

  // Build default config from column metas
  const defaultConfig = useMemo<import("@/hooks/useColumnSetups").ColumnSetupEntry>(() => {
    const order = CONTACT_COLUMN_METAS.map((m) => m.key);
    const visibility: Record<string, boolean> = {};
    CONTACT_COLUMN_METAS.forEach((m) => { visibility[m.key] = true; });
    return { order, visibility, widths: {}, sort: null };
  }, []);

  // Apply active setup (if any) over default
  const activeConfig = useMemo(() => {
    if (!columnSetups.activeSetupName) return defaultConfig;
    const applied = columnSetups.applySetup(columnSetups.activeSetupName);
    return applied ?? defaultConfig;
  }, [columnSetups, defaultConfig]);

  const visibleCols = useMemo(() => {
    const vis = activeConfig.visibility;
    const result = new Set<string>();
    for (const m of CONTACT_COLUMN_METAS) {
      if (vis[m.key] !== false) result.add(m.key);
    }
    return result;
  }, [activeConfig]);

  // ---------------------------------------------------------------------------
  // Auto-refresh when ContactDetail dispatches a "contact-saved" event
  // ---------------------------------------------------------------------------
  const handleContactSaved = useCallback(
    (e: Event) => {
      const detail = (e as CustomEvent).detail;
      // Refresh if this panel matches the saved contact's parent
      if (
        detail &&
        parent_model &&
        parentId &&
        detail.parentModel === parent_model &&
        detail.parentId === parentId
      ) {
        onSaveSuccess?.();
      }
    },
    [parent_model, parentId, onSaveSuccess],
  );

  useEffect(() => {
    window.addEventListener("contact-saved", handleContactSaved);
    return () =>
      window.removeEventListener("contact-saved", handleContactSaved);
  }, [handleContactSaved]);

  // Sort contacts: standard purposes first, then alphabetical
  const sorted = [...contacts].sort((a, b) => {
    const idxA = STANDARD_PURPOSES.indexOf(a.purpose);
    const idxB = STANDARD_PURPOSES.indexOf(b.purpose);
    const orderA = idxA >= 0 ? idxA : STANDARD_PURPOSES.length;
    const orderB = idxB >= 0 ? idxB : STANDARD_PURPOSES.length;
    if (orderA !== orderB) return orderA - orderB;
    return (a.purpose || "").localeCompare(b.purpose || "");
  });

  const handleOpen = (contact: RefContact) => {
    const path = getModelDetailPath("contact", contact.contact_id);
    const label = getModelWindowTitle(
      "contact",
      contact.contact_id,
      undefined,
      contact.attention,
    );
    windowManager.ensureWindow(path, label, { maximized: false });
  };

  const handleRemoveContact = (contactId: number) => {
    if (onChange) {
      onChange(contacts.filter((c) => c.contact_id !== contactId));
    }
    if (onRemove) {
      onRemove(contactId);
    }
  };

  const handleEditContact = (contact: RefContact) => {
    if (onEdit) {
      onEdit(contact);
    }
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700 cursor-pointer"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaUser className="text-slate-400" size={14} />
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
            {title}
          </h3>
          {contacts.length > 0 && (
            <span className="px-1.5 py-0.5 text-xs bg-slate-200 dark:bg-slate-600 rounded-full">
              {contacts.length}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {(isEditing || allowCreate) && !isCollapsed && (
            <button
              type="button"
              className="px-2 py-1 text-xs font-medium text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors flex items-center gap-1"
              onClick={(e) => {
                e.stopPropagation();
                // Open a blank ContactDetail for creating a new contact.
                // Pass parent context via query params so the form auto-populates
                // the appropriate parent_id and syncs refs.links on save.
                const qs = new URLSearchParams();
                if (parent_model) qs.set("parent_model", parent_model);
                if (parentId) qs.set("parent_id", String(parentId));
                if (customer_id) qs.set("customer_id", String(customer_id));
                if (customer_name) qs.set("customer_name", customer_name);
                const query = qs.toString();
                // Trailing slash needed so resolveWindowElement matches the :id? route
                const path = `/core/contact/detail/${query ? `?${query}` : ""}`;
                windowManager.ensureWindow(path, "New Contact", {
                  maximized: false,
                });
              }}
            >
              <FaPlus size={8} />
              Add
            </button>
          )}
          {/* Refresh button */}
          {onRefresh && !isCollapsed && (
            <button
              type="button"
              title="Refresh contacts"
              className="px-2 py-1 text-xs font-medium text-slate-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors flex items-center gap-1"
              onClick={(e) => {
                e.stopPropagation();
                onRefresh();
              }}
              disabled={externalLoading}
            >
              <FaSyncAlt
                size={10}
                className={externalLoading ? "animate-spin" : ""}
              />
            </button>
          )}
          {/* Column setup badge */}
          {!isCollapsed && (
            <button
              type="button"
              title="Configure columns"
              className="px-2 py-1 text-xs font-medium text-slate-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors flex items-center gap-1"
              onClick={(e) => {
                e.stopPropagation();
                setShowColumnDialog(true);
              }}
            >
              <FaSlidersH size={10} />
            </button>
          )}
          {isCollapsed ? (
            <FaChevronDown size={12} className="text-slate-400" />
          ) : (
            <FaChevronUp size={12} className="text-slate-400" />
          )}
        </div>
      </div>

      {/* List */}
      {!isCollapsed && (
        <div>
          {sorted.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-6 italic">
              {externalLoading ? (
                <span className="flex items-center justify-center gap-2">
                  <FaSpinner className="animate-spin" size={12} />
                  Loading contacts…
                </span>
              ) : (
                "No contacts linked"
              )}
            </p>
          ) : (
            <div className="divide-y divide-slate-100 dark:divide-slate-700">
              {/* Column headers */}
              <div className="flex items-center gap-3 px-3 py-1.5 bg-slate-50 dark:bg-slate-700/50 text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                {visibleCols.has("purpose") && <span className="min-w-[56px] shrink-0 text-center">purpose</span>}
                {visibleCols.has("contact_id") && <span className="w-10 text-right shrink-0">#</span>}
                {visibleCols.has("name") && <span className="min-w-[100px] max-w-[180px]">name</span>}
                {visibleCols.has("email") && <span className="flex-1 min-w-0">email</span>}
                {visibleCols.has("phone") && <span className="w-[120px] shrink-0">phone</span>}
                <span className="shrink-0 w-[72px]" />
              </div>
              {sorted.map((contact, idx) => (
                <ContactRow
                  key={`${contact.contact_id}-${contact.purpose}-${idx}`}
                  contact={contact}
                  isEditing={isEditing}
                  isPrimary={
                    !!primaryContactId &&
                    contact.contact_id === primaryContactId
                  }
                  visibleColumns={visibleCols}
                  onRemove={() => handleRemoveContact(contact.contact_id)}
                  onEdit={() => handleEditContact(contact)}
                  onOpen={() => handleOpen(contact)}
                  onSetPrimary={
                    onSetPrimary ? () => onSetPrimary(contact) : undefined
                  }
                />
              ))}
            </div>
          )}
        </div>
      )}
      {/* Column setup dialog */}
      <ColumnSetupDialog
        open={showColumnDialog}
        title="Contact Columns"
        columnMetas={CONTACT_COLUMN_METAS}
        config={activeConfig}
        onSave={(entry) => {
          columnSetups.saveSetup("current", entry);
          setShowColumnDialog(false);
        }}
        onClose={() => setShowColumnDialog(false)}
        namedSetups={columnSetups.setups}
        onSaveNamed={(name, config) => columnSetups.saveSetup(name, config)}
      />
    </div>
  );
};

export default withDevIdentifier(ContactPanel, "ContactPanel", "teal");
