/**
 * CommLinkPanel — Inline panel for a single communication type (email/phone/address/domain).
 *
 * Layout:
 *   ┌─ Email ─────────────────────────────────────────────┐
 *   │  email: user@example.com          (scalar, editable) │
 *   │  ┌──────────────────────────────────────────────────┐│
 *   │  │ ★ #42  user@example.com   Work           ✎  ✕  ││
 *   │  │   #87  alt@example.com    Personal        ✎  ✕  ││
 *   │  │   + Add   🔍 Search existing                    ││
 *   │  └──────────────────────────────────────────────────┘│
 *   └─────────────────────────────────────────────────────┘
 *
 * Save-as-you-go: each add / set-primary / unlink triggers an immediate API call.
 *
 * @see readmes/contact-save-panel-plan.md §5
 */

import React, { useState, useCallback, useEffect } from "react";
import {
  FaStar,
  FaRegStar,
  FaPlus,
  FaSearch,
  FaSpinner,
  FaTimes,
} from "react-icons/fa";
import { ChevronDown, ChevronRight } from "lucide-react";
import { getRecords, saveRecord } from "@/api/wcapi";
import { useDispatch } from "react-redux";
import { showToast } from "@/store/slices/toastSlice";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type CommType = "email" | "phone" | "address" | "domain";

export interface CommLinkPanelProps {
  /** Communication type */
  type: CommType;
  /** Panel title (defaults to capitalised type) */
  title?: string;
  /** The denormalized scalar value from the contact record */
  scalarValue: string | null | undefined;
  /** The *_id field value — which linked record is primary */
  primaryId: number | null | undefined;
  /** All linked records for this type */
  items: any[];
  /** Whether the form is in edit/add mode */
  isEditing: boolean;
  /** Contact ID (null → panels disabled until contact is saved) */
  contactId: number | null | undefined;
  /** Called when user updates the scalar value via the input */
  onScalarChange?: (value: string) => void;
  /** Called after a record is set as primary (id, displayValue) */
  onSetPrimary?: (id: number, displayValue: string) => void;
  /** Called when the items list changes (caller should refresh state) */
  onItemsChanged?: () => void;
  /** Start expanded (default: true in edit mode, false in view) */
  defaultExpanded?: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const COMM_LABELS: Record<CommType, string> = {
  email: "Email",
  phone: "Phone",
  address: "Address",
  domain: "Domain",
};

const SCALAR_LABEL: Record<CommType, string> = {
  email: "email",
  phone: "phone",
  address: "address_full",
  domain: "domain",
};

function displayValue(type: CommType, item: any): string {
  if (!item) return "";
  if (type === "email") return item.email || item.address || item.value || "";
  if (type === "phone") return item.number || item.value || item.format || "";
  if (type === "domain") return item.domain || item.value || item.path || "";
  // address
  return (
    item.full ||
    [
      item.address1,
      [item.city, item.state, item.zip].filter(Boolean).join(", "),
      item.country,
    ]
      .filter(Boolean)
      .join(", ")
  );
}

function secondaryLabel(type: CommType, item: any): string {
  if (type === "email") return item.type || item.name || "";
  if (type === "phone") return item.name || "";
  if (type === "address") return item.name || item.address_type || "";
  if (type === "domain") return item.type || item.name || "";
  return "";
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const CommLinkPanel: React.FC<CommLinkPanelProps> = ({
  type,
  title,
  scalarValue,
  primaryId,
  items,
  isEditing,
  contactId,
  onScalarChange,
  onSetPrimary,
  onItemsChanged,
  defaultExpanded,
}) => {
  const dispatch = useDispatch();
  const label = title || COMM_LABELS[type];
  const [expanded, setExpanded] = useState(
    defaultExpanded ?? (isEditing ? true : false),
  );

  // ----- Search dialog state -----
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // Fetch search results when dialog is open
  useEffect(() => {
    if (!searchOpen) return;
    let cancelled = false;
    (async () => {
      setSearchLoading(true);
      try {
        const params: Record<string, any> = { limit: 50 };
        const q = searchQuery.trim();
        if (q) {
          params.search = q;
          params.q = q;
        }
        const res: any = await getRecords(type, params);
        if (!cancelled) setSearchResults(res?.results || []);
      } catch {
        if (!cancelled) setSearchResults([]);
      } finally {
        if (!cancelled) setSearchLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [searchOpen, searchQuery, type]);

  /** Link an existing record (or create a copy) for this contact, then set primary */
  const handleSearchSelect = useCallback(
    async (item: any) => {
      if (!contactId) return;
      setSaving(true);
      try {
        const existingContact = Number(item?.contact ?? item?.contact_id);
        let linkedId: number;

        if (
          Number.isFinite(existingContact) &&
          existingContact === contactId &&
          item?.id
        ) {
          // Already linked to this contact
          linkedId = Number(item.id);
        } else {
          // Create a new record linked to this contact
          const payload = buildCreatePayload(type, item, contactId);
          const res: any = await saveRecord(type, payload);
          const record = res?.record ?? res;
          linkedId = Number(record?.id ?? res?.id);
          if (!Number.isFinite(linkedId) || linkedId <= 0) {
            throw new Error("Failed to link record");
          }
        }

        onSetPrimary?.(linkedId, displayValue(type, item));
        onItemsChanged?.();
        setSearchOpen(false);
        dispatch(
          showToast({
            message: `${COMM_LABELS[type]} linked`,
            type: "success",
          }),
        );
      } catch (err: any) {
        console.error("[CommLinkPanel] searchSelect failed:", err);
        dispatch(
          showToast({
            message: `Failed to link ${type}`,
            type: "error",
          }),
        );
      } finally {
        setSaving(false);
      }
    },
    [contactId, type, onSetPrimary, onItemsChanged, dispatch],
  );

  /** Add a new blank record for this contact */
  const handleAddNew = useCallback(async () => {
    if (!contactId) return;
    setSaving(true);
    try {
      const payload = buildBlankPayload(type, contactId);
      const res: any = await saveRecord(type, payload);
      const record = res?.record ?? res;
      const newId = Number(record?.id ?? res?.id);
      if (!Number.isFinite(newId) || newId <= 0) {
        throw new Error("Failed to create record");
      }
      onItemsChanged?.();
      dispatch(
        showToast({
          message: `${COMM_LABELS[type]} created`,
          type: "success",
        }),
      );
    } catch (err: any) {
      console.error("[CommLinkPanel] addNew failed:", err);
      dispatch(
        showToast({ message: `Failed to add ${type}`, type: "error" }),
      );
    } finally {
      setSaving(false);
    }
  }, [contactId, type, onItemsChanged, dispatch]);

  /** Set a record as primary */
  const handleSetPrimary = useCallback(
    (item: any) => {
      if (!item?.id) return;
      onSetPrimary?.(Number(item.id), displayValue(type, item));
    },
    [type, onSetPrimary],
  );

  const disabled = !contactId;

  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-lg overflow-hidden mb-3">
      {/* ─── Header ─── */}
      <button
        type="button"
        className="w-full flex items-center justify-between px-4 py-2.5 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          {expanded ? (
            <ChevronDown className="text-slate-400 w-3 h-3" />
          ) : (
            <ChevronRight className="text-slate-400 w-3 h-3" />
          )}
          <span className="font-semibold text-sm text-slate-700 dark:text-slate-200">
            {label}
          </span>
          <span className="text-xs text-slate-400 ml-1">
            ({items.length})
          </span>
          {/* Primary scalar value as a subtle badge in the header */}
          {!expanded && scalarValue && (
            <span className="ml-2 text-xs text-slate-500 dark:text-slate-400 truncate max-w-[200px]">
              {scalarValue}
            </span>
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-4 py-3 bg-white dark:bg-slate-900 space-y-3">
          {/* ─── Scalar value row ─── */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400 w-24 shrink-0">
              {SCALAR_LABEL[type]} :
            </span>
            {isEditing ? (
              <input
                type="text"
                value={scalarValue || ""}
                onChange={(e) => onScalarChange?.(e.target.value)}
                className="flex-1 px-2 py-1 text-sm border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                placeholder={`Primary ${type}`}
                disabled={disabled}
              />
            ) : (
              <span className="text-sm font-medium text-slate-900 dark:text-slate-100">
                {scalarValue || "—"}
              </span>
            )}
          </div>

          {/* ─── Linked records list ─── */}
          {items.length > 0 && (
            <div className="border border-slate-100 dark:border-slate-800 rounded-lg divide-y divide-slate-100 dark:divide-slate-800">
              {items.map((item: any, idx: number) => {
                const isPrimary = item.id != null && Number(item.id) === Number(primaryId);
                const val = displayValue(type, item);
                const sub = secondaryLabel(type, item);
                return (
                  <div
                    key={item.id ?? idx}
                    className="flex items-center gap-2 px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-800/50"
                  >
                    {/* Star badge */}
                    <button
                      type="button"
                      onClick={() => isEditing && handleSetPrimary(item)}
                      className={`shrink-0 ${
                        isPrimary
                          ? "text-amber-500"
                          : "text-slate-300 dark:text-slate-600"
                      } ${isEditing ? "cursor-pointer hover:text-amber-400" : "cursor-default"}`}
                      title={isPrimary ? "Primary" : "Set as primary"}
                      disabled={!isEditing}
                    >
                      {isPrimary ? <FaStar size={12} /> : <FaRegStar size={12} />}
                    </button>

                    {/* ID */}
                    <span className="text-xs font-mono text-slate-400 w-10 shrink-0">
                      #{item.id}
                    </span>

                    {/* Display value */}
                    <span
                      className={`flex-1 truncate ${
                        isPrimary
                          ? "font-semibold text-slate-900 dark:text-slate-100"
                          : "text-slate-700 dark:text-slate-300"
                      }`}
                    >
                      {val || "—"}
                    </span>

                    {/* Secondary label */}
                    {sub && (
                      <span className="text-xs text-slate-400 shrink-0">
                        {sub}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {items.length === 0 && (
            <p className="text-xs text-slate-400 italic">
              No {type} records linked
            </p>
          )}

          {/* ─── Action buttons (edit mode only) ─── */}
          {isEditing && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleAddNew}
                disabled={disabled || saving}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30 rounded-lg transition-colors disabled:opacity-40"
              >
                {saving ? (
                  <FaSpinner className="animate-spin" size={10} />
                ) : (
                  <FaPlus size={10} />
                )}
                Add
              </button>
              <button
                type="button"
                onClick={() => setSearchOpen(true)}
                disabled={disabled || saving}
                className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600 rounded-lg transition-colors disabled:opacity-40"
              >
                <FaSearch size={10} />
                Search existing
              </button>
              {disabled && (
                <span className="text-xs text-amber-600 dark:text-amber-400 italic">
                  Save contact first
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {/* ─── Search dialog (portal) ─── */}
      {searchOpen &&
        <SearchDialog
          type={type}
          query={searchQuery}
          onQueryChange={setSearchQuery}
          results={searchResults}
          loading={searchLoading}
          saving={saving}
          linkedIds={new Set(items.map((i: any) => Number(i.id)).filter(Number.isFinite))}
          onSelect={handleSearchSelect}
          onClose={() => setSearchOpen(false)}
        />
      }
    </div>
  );
};

export default CommLinkPanel;

// ---------------------------------------------------------------------------
// Search dialog (rendered via portal)
// ---------------------------------------------------------------------------

interface SearchDialogProps {
  type: CommType;
  query: string;
  onQueryChange: (q: string) => void;
  results: any[];
  loading: boolean;
  saving: boolean;
  linkedIds: Set<number>;
  onSelect: (item: any) => void;
  onClose: () => void;
}

function SearchDialog({
  type,
  query,
  onQueryChange,
  results,
  loading,
  saving,
  linkedIds,
  onSelect,
  onClose,
}: SearchDialogProps) {
  const filtered = query.trim()
    ? results.filter((item: any) => {
        const val = displayValue(type, item).toLowerCase();
        const label = String(item?.name || item?.type || "").toLowerCase();
        const q = query.trim().toLowerCase();
        return (
          val.includes(q) ||
          label.includes(q) ||
          String(item?.id || "").includes(q)
        );
      })
    : results;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-black/40"
        onClick={onClose}
      />
      {/* Dialog */}
      <div className="fixed inset-x-0 top-[12vh] z-50 flex justify-center px-4">
        <div
          className="w-full max-w-lg bg-white dark:bg-slate-900 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-700"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
            <span className="text-sm font-semibold text-slate-900 dark:text-slate-100 capitalize">
              Search {type} records
            </span>
            <button
              type="button"
              onClick={onClose}
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
            >
              <FaTimes size={14} />
            </button>
          </div>
          <div className="p-4 space-y-3">
            <input
              value={query}
              onChange={(e) => onQueryChange(e.target.value)}
              placeholder="Search…"
              className="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800"
              autoFocus
            />
            <div className="max-h-72 overflow-y-auto border border-slate-200 dark:border-slate-700 rounded-lg">
              {loading ? (
                <div className="p-3 text-sm text-slate-500 flex items-center gap-2">
                  <FaSpinner className="animate-spin" size={12} />
                  Loading…
                </div>
              ) : filtered.length === 0 ? (
                <div className="p-3 text-sm text-slate-500">No matches</div>
              ) : (
                filtered.map((item: any, idx: number) => {
                  const val = displayValue(type, item);
                  const sub = secondaryLabel(type, item);
                  const isLinked = linkedIds.has(Number(item?.id));
                  return (
                    <button
                      key={`${item?.id ?? idx}`}
                      type="button"
                      onClick={() => onSelect(item)}
                      disabled={saving}
                      className="w-full text-left px-3 py-2 border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <div className="text-sm text-slate-900 dark:text-slate-100 truncate">
                            {val || "—"}
                          </div>
                          {sub && (
                            <div className="text-xs text-slate-500 truncate">
                              {sub}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          {isLinked && (
                            <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                              linked
                            </span>
                          )}
                          <span className="text-xs text-slate-400 font-mono">
                            #{item?.id}
                          </span>
                        </div>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
            {saving && (
              <div className="text-xs text-slate-500 flex items-center gap-2">
                <FaSpinner className="animate-spin" size={12} />
                Saving…
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Payload builders
// ---------------------------------------------------------------------------

function buildCreatePayload(
  type: CommType,
  source: any,
  contactId: number,
): Record<string, any> {
  const base = { contact_id: contactId };
  if (type === "email") {
    return {
      ...base,
      email: source?.email || source?.address || source?.value || "",
      name: source?.name || "",
      attention: source?.attention || "",
      type: source?.type || "",
      is_primary: false,
    };
  }
  if (type === "phone") {
    return {
      ...base,
      number: source?.number || source?.value || "",
      name: source?.name || "",
      attention: source?.attention || "",
      country_code: source?.country_code || "",
      format: source?.format || "",
    };
  }
  if (type === "domain") {
    return {
      ...base,
      path: source?.path || source?.domain || source?.value || "",
      type: source?.type || "",
      status: source?.status || "active",
    };
  }
  // address
  return {
    ...base,
    address1: source?.address1 || "",
    address2: source?.address2 || "",
    city: source?.city || "",
    state: source?.state || "",
    zip: source?.zip || "",
    country: source?.country || "",
    full: source?.full || "",
    address_type: source?.address_type || source?.name || "",
  };
}

function buildBlankPayload(
  type: CommType,
  contactId: number,
): Record<string, any> {
  const base = { contact_id: contactId };
  if (type === "email") return { ...base, email: "", name: "" };
  if (type === "phone") return { ...base, number: "", name: "" };
  if (type === "domain")
    return { ...base, path: "", type: "", status: "active" };
  // address
  return { ...base, address1: "", city: "", state: "", zip: "", country: "" };
}
