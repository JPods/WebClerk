/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * ContactInfoPanel — Inline panel for contact communications (email/phone/address/domain).
 *
 * Persists to contact.refs.links; avoids legacy communications tables.
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import {
  FaEdit,
  FaPlus,
  FaRegStar,
  FaSave,
  FaSearch,
  FaSpinner,
  FaStar,
  FaTimes,
  FaTrash,
  FaUndo,
} from "react-icons/fa";
import { useDispatch } from "react-redux";

import { deleteRecord, getRecords, saveRecord } from "@/api/wcapi";
import { AddressFormat } from "@/apps/common/components/detail/AddressFormat";
import { DomainFormat } from "@/apps/common/components/detail/DomainFormat";
import { EmailFormat } from "@/apps/common/components/detail/EmailFormat";
import { PhoneFormat } from "@/apps/common/components/detail/PhoneFormat";
import { withDevIdentifier } from "@/components/common/DevIdentifier";
import { showToast } from "@/store/slices/toastSlice";

// ---------------------------------------------------------------------------
// Types & constants
// ---------------------------------------------------------------------------

type CommType = "email" | "phone" | "address" | "domain";

interface CommFieldDef {
  key: string;
  label: string;
  width?: "full" | "half";
  placeholder?: string;
  inputType?: "text" | "select" | "checkbox";
  options?: { value: string; label: string }[];
}

export interface ContactInfoPanelProps {
  type: CommType;
  title?: string;
  scalarValue?: string | null;
  primaryId?: number | null;
  items: any[];
  /** Either flat array of links (per type) or refs.links object */
  reflinks?: any[] | Record<string, any[]> | null;
  isEditing: boolean;
  contactId: number | null | undefined;
  onSetPrimary?: (id: number) => void | Promise<void>;
  onItemsChanged?: (
    nextLinksForType: any[],
    nextAllLinks?: Record<string, any[]>,
  ) => void | Promise<void>;
  defaultExpanded?: boolean;
}

const COMM_LABELS: Record<CommType, string> = {
  email: "Email",
  phone: "Phone",
  address: "Address",
  domain: "Domain",
};

const COMM_FIELD_CONFIGS: Record<CommType, CommFieldDef[]> = {
  email: [
    {
      key: "email",
      label: "Email",
      width: "full",
      placeholder: "user@example.com",
    },
    { key: "name", label: "Name", width: "half" },
    { key: "is_primary", label: "Primary", inputType: "checkbox" },
    { key: "is_verified", label: "Verified", inputType: "checkbox" },
    { key: "opt_out", label: "Opt out", inputType: "checkbox" },
  ],
  phone: [
    {
      key: "number",
      label: "Number",
      width: "full",
      placeholder: "+1 (555) 123-4567",
    },
    {
      key: "name",
      label: "Label",
      width: "half",
      placeholder: "Work / Mobile",
    },
    { key: "format", label: "Format", width: "half", placeholder: "mobile" },
    { key: "country_code", label: "Country", width: "half", placeholder: "1" },
    { key: "opt_out", label: "Opt out", inputType: "checkbox" },
  ],
  address: [
    {
      key: "name",
      label: "Label",
      width: "half",
      placeholder: "Home / Billing",
    },
    { key: "address1", label: "Address 1", width: "full" },
    { key: "address2", label: "Address 2", width: "full" },
    { key: "city", label: "City", width: "half" },
    { key: "state", label: "State", width: "half" },
    { key: "zip", label: "Zip", width: "half" },
    { key: "country", label: "Country", width: "half" },
  ],
  domain: [
    { key: "path", label: "Domain", width: "full", placeholder: "example.com" },
    { key: "name", label: "Label", width: "half", placeholder: "Marketing" },
    { key: "type", label: "Type", width: "half", placeholder: "primary" },
    { key: "status", label: "Status", width: "half", placeholder: "active" },
  ],
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function displayValue(type: CommType, item: any): string {
  if (!item) return "";
  if (type === "email") return item.email || item.address || "";
  if (type === "phone") return item.number || "";
  if (type === "domain") return item.path || item.domain || item.name || "";
  const parts = [item.address1, item.city, item.state, item.zip, item.country]
    .filter(Boolean)
    .join(" ");
  return parts || item.full || item.name || item.address_type || "";
}

function secondaryLabel(type: CommType, item: any): string {
  if (!item) return "";
  if (type === "email") return item.type || item.name || "";
  if (type === "phone") return item.name || "";
  if (type === "address") return item.name || item.address_type || "";
  if (type === "domain") return item.type || item.name || "";
  return "";
}

/** Format phone number as +CC (XXX) XXX-XXXX (same helper used in ContactDetail) */
function formatPhoneNumber(value: string): string {
  const hasPlus = value?.startsWith("+") ?? false;
  const digits = (value || "").replace(/\D/g, "");
  if (digits.length === 0) return hasPlus ? "+" : "";
  const limited = digits.slice(0, 13);
  if (limited.length <= 10) {
    const local = limited;
    if (local.length <= 3) return hasPlus ? `+${local}` : local;
    if (local.length <= 6) {
      return hasPlus
        ? `+${local.slice(0, 3)} (${local.slice(3)})`
        : `(${local.slice(0, 3)}) ${local.slice(3)}`;
    }
    return hasPlus
      ? `+${local.slice(0, 3)} (${local.slice(3, 6)}) ${local.slice(6)}`
      : `(${local.slice(0, 3)}) ${local.slice(3, 6)}-${local.slice(6)}`;
  }
  const countryCodeLen = limited.length - 10;
  const countryCode = limited.slice(0, countryCodeLen);
  const local = limited.slice(countryCodeLen);
  return `+${countryCode} (${local.slice(0, 3)}) ${local.slice(
    3,
    6,
  )}-${local.slice(6)}`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const ContactInfoPanel: React.FC<ContactInfoPanelProps> = ({
  type,
  title,
  scalarValue,
  primaryId,
  items,
  reflinks = [],
  isEditing,
  contactId,
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
  //   console.log("scalarValue", scalarValue);
  //   console.log("reflinks", reflinks);
  //   console.log("primaryId", primaryId);
  //   console.log("items", items);
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

  const refLinksArray = useMemo(() => {
    const arr = Array.isArray(reflinks)
      ? reflinks
      : (reflinks as any)?.[type] || [];
    return Array.isArray(arr) ? arr : [];
  }, [reflinks, type]);

  const displayItems = useMemo(() => {
    const baseItems =
      refLinksArray.length > 0
        ? refLinksArray
        : Array.isArray(items)
        ? items
        : [];
    // Exclude the scalar/primary record (email_id, phone_id, etc.) from the list
    if (primaryId != null) {
      return baseItems.filter(
        (item: any) => Number(item?.id) !== Number(primaryId),
      );
    }
    return baseItems;
  }, [items, refLinksArray, primaryId]);

  const persistLinks = useCallback(
    async (nextLinksForType: any[]) => {
      if (!contactId) return;

      // Preserve the primary/scalar item in refs.links (it's excluded from display)
      const primaryItem = refLinksArray.find(
        (item: any) =>
          primaryId != null && Number(item?.id) === Number(primaryId),
      );
      const withPrimary = primaryItem
        ? [
            primaryItem,
            ...nextLinksForType.filter(
              (r: any) => Number(r?.id) !== Number(primaryId),
            ),
          ]
        : nextLinksForType;

      const nextLinks = Array.isArray(reflinks)
        ? { [type]: withPrimary }
        : { ...(reflinks || {}), [type]: withPrimary };

      await saveRecord("contact", {
        id: contactId,
        refs: {
          links: nextLinks,
        },
      });
      await Promise.resolve(onItemsChanged?.(withPrimary, nextLinks));
    },
    [contactId, onItemsChanged, primaryId, refLinksArray, reflinks, type],
  );

  const buildLinkFromValues = useCallback(
    (vals: Record<string, any>, fallbackId?: number) => {
      const numId = Number(vals.id ?? fallbackId);
      const id = Number.isFinite(numId) ? numId : Date.now();
      if (type === "email") {
        return {
          id,
          name: vals.name || "",
          email: vals.email || vals.address || "",
          opt_out: vals.opt_out ?? "",
          is_primary: vals.is_primary ?? false,
          is_verified: vals.is_verified ?? false,
        };
      }
      if (type === "phone") {
        return {
          id,
          name: vals.name || "",
          number: vals.number || "",
          format: vals.format || "",
          country_code: vals.country_code || "",
          opt_out: vals.opt_out ?? false,
        };
      }
      if (type === "domain") {
        return {
          id,
          name: vals.name || vals.type || "",
          path: vals.path || vals.domain || "",
          status: vals.status || "active",
          type: vals.type || "",
        };
      }
      return {
        id,
        name: vals.name || vals.address_type || "",
        address1: vals.address1 || "",
        address2: vals.address2 || "",
        city: vals.city || "",
        state: vals.state || "",
        zip: vals.zip || "",
        country: vals.country || "",
        full:
          vals.full ||
          [vals.address1, vals.city, vals.state, vals.zip, vals.country]
            .filter(Boolean)
            .join(" "),
      } as any;
    },
    [type],
  );

  // ----- Inline editing state -----
  const [editingItemId, setEditingItemId] = useState<number | "new" | null>(
    null,
  );
  const [editingValues, setEditingValues] = useState<Record<string, any>>({});
  const [recordSaving, setRecordSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  /** Link an existing record (or create a copy) for this contact, then set primary */
  const handleSearchSelect = useCallback(
    async (item: any) => {
      if (!contactId) return;
      setSaving(true);
      try {
        const link = buildLinkFromValues(item);
        const next = [...displayItems];
        const idx = next.findIndex(
          (r: any) => Number(r.id) === Number(link.id),
        );
        if (idx >= 0) next[idx] = link;
        else next.push(link);

        await persistLinks(next);
        onSetPrimary?.(link.id);

        setSearchOpen(false);
        dispatch(
          showToast({
            message: `${COMM_LABELS[type]} linked`,
            type: "success",
          }),
        );
      } catch (err: any) {
        console.error("[ContactInfoPanel] searchSelect failed:", err);
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
    [
      buildLinkFromValues,
      contactId,
      dispatch,
      displayItems,
      onSetPrimary,
      persistLinks,
      type,
    ],
  );

  /** Add a new blank record for this contact — opens inline editor */
  const handleAddNew = useCallback(() => {
    if (!contactId) return;
    const values: Record<string, any> = {};
    for (const fd of COMM_FIELD_CONFIGS[type]) {
      values[fd.key] = fd.inputType === "checkbox" ? false : "";
    }
    setEditingValues(values);
    setEditingItemId("new");
  }, [contactId, type]);

  /** Set a record as primary */
  const handleSetPrimary = useCallback(
    (item: any) => {
      if (!item?.id) return;
      onSetPrimary?.(Number(item.id));
    },
    [onSetPrimary],
  );

  /** Open inline editor for an existing record */
  const handleEditRecord = useCallback(
    (item: any) => {
      if (!item?.id) return;
      const values: Record<string, any> = {};
      for (const fd of COMM_FIELD_CONFIGS[type]) {
        values[fd.key] =
          item[fd.key] ?? (fd.inputType === "checkbox" ? false : "");
      }
      setEditingValues(values);
      setEditingItemId(Number(item.id));
    },
    [type],
  );

  /** Cancel inline editing */
  const handleCancelEdit = useCallback(() => {
    setEditingItemId(null);
    setEditingValues({});
  }, []);

  /** Save the inline-edited record */
  const handleSaveRecord = useCallback(async () => {
    if (editingItemId == null) return;
    setRecordSaving(true);
    try {
      const link = buildLinkFromValues(editingValues, editingItemId);
      const next = [...displayItems];
      const idx = next.findIndex((r: any) => Number(r.id) === Number(link.id));
      if (idx >= 0) next[idx] = { ...next[idx], ...link };
      else next.push(link);

      await persistLinks(next);

      if (editingItemId === "new" && displayItems.length === 0) {
        onSetPrimary?.(link.id);
      }

      setEditingItemId(null);
      setEditingValues({});
      dispatch(
        showToast({
          message: `${COMM_LABELS[type]} ${
            editingItemId === "new" ? "created" : "saved"
          }`,
          type: "success",
        }),
      );
    } catch (err: any) {
      console.error("[ContactInfoPanel] saveRecord failed:", err);
      dispatch(
        showToast({
          message: `Failed to save ${type} record`,
          type: "error",
        }),
      );
    } finally {
      setRecordSaving(false);
    }
  }, [
    buildLinkFromValues,
    dispatch,
    displayItems,
    editingItemId,
    editingValues,
    onSetPrimary,
    persistLinks,
    type,
  ]);

  /** Delete (soft-delete) a linked record — also removes from model table */
  const handleDeleteRecord = useCallback(
    async (item: any) => {
      if (!item?.id) return;
      const id = Number(item.id);

      // Prevent deletion of the primary/scalar record
      if (primaryId != null && id === Number(primaryId)) {
        dispatch(
          showToast({
            message: `Cannot delete primary ${type} — change the primary first`,
            type: "warning",
          }),
        );
        return;
      }

      setDeletingId(id);
      try {
        // 1. Delete from the actual model (email/phone/address/domain)
        await deleteRecord(type, id);

        // 2. Remove from refs.links
        const next = displayItems.filter((row: any) => Number(row.id) !== id);
        await persistLinks(next);

        dispatch(
          showToast({
            message: `${COMM_LABELS[type]} #${id} deleted`,
            type: "success",
          }),
        );
        if (editingItemId === id) {
          setEditingItemId(null);
          setEditingValues({});
        }
      } catch (err: any) {
        console.error("[ContactInfoPanel] deleteRecord failed:", err);
        dispatch(
          showToast({
            message: `Failed to delete ${type} #${id}`,
            type: "error",
          }),
        );
      } finally {
        setDeletingId(null);
      }
    },
    [displayItems, dispatch, editingItemId, persistLinks, primaryId, type],
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
            ({displayItems.length})
          </span>

          {/* Primary scalar value as a subtle badge in the header */}
          {!expanded && scalarValue && (
            <span className="ml-2 text-xs text-slate-500 dark:text-slate-400 truncate max-w-50">
              {type === "phone" ? formatPhoneNumber(scalarValue) : scalarValue}
            </span>
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-4 py-3 bg-white dark:bg-slate-900 space-y-3">
          {/* ─── Linked records list ─── */}

          {displayItems.length > 0 ? (
            <div className="border border-slate-100 dark:border-slate-800 rounded-lg divide-y divide-slate-100 dark:divide-slate-800">
              {displayItems.map((item: any, idx: number) => {
                const matchingReflink = refLinksArray.find((rl: any) => {
                  const rlId = Number(rl?.id);
                  const itemId = Number(item?.id);
                  return (
                    Number.isFinite(rlId) &&
                    Number.isFinite(itemId) &&
                    rlId === itemId
                  );
                });

                const isPrimary =
                  matchingReflink?.is_primary === true ||
                  matchingReflink?.is_primary === 1 ||
                  (primaryId != null && Number(item?.id) === Number(primaryId));
                const val = displayValue(type, item);
                const sub = secondaryLabel(type, item);
                const isEditingThis = editingItemId === Number(item?.id);
                const isDeleting = deletingId === Number(item?.id);

                return (
                  <div key={item?.id ?? idx}>
                    {/* ─── Record summary row ─── */}
                    <div
                      className={`flex items-center gap-2 px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-800/50 ${
                        isEditingThis ? "bg-blue-50/50 dark:bg-blue-900/10" : ""
                      }`}
                    >
                      {/* Star badge */}
                      <button
                        type="button"
                        onClick={() => isEditing && handleSetPrimary(item)}
                        className={`shrink-0 ${
                          isPrimary
                            ? "text-amber-500"
                            : "text-slate-300 dark:text-slate-600"
                        } ${
                          isEditing
                            ? "cursor-pointer hover:text-amber-400"
                            : "cursor-default"
                        }`}
                        title={isPrimary ? "Primary" : "Set as primary"}
                        disabled={!isEditing}
                      >
                        {isPrimary ? (
                          <FaStar size={12} />
                        ) : (
                          <FaRegStar size={12} />
                        )}
                      </button>

                      {/* ID */}
                      <span className="text-xs font-mono text-slate-400 w-10 shrink-0">
                        #{item?.id}
                      </span>

                      {/* Display value */}
                      <span
                        className={`flex-1 truncate ${
                          isPrimary
                            ? "font-semibold text-slate-900 dark:text-slate-100"
                            : "text-slate-700 dark:text-slate-300"
                        }`}
                      >
                        {type === "phone" ? (
                          <PhoneFormat value={val} />
                        ) : type === "email" ? (
                          <EmailFormat value={val} />
                        ) : type === "address" ? (
                          <AddressFormat value={val} />
                        ) : type === "domain" ? (
                          <DomainFormat value={val} />
                        ) : (
                          val
                        )}{" "}
                      </span>

                      {/* Secondary label */}
                      {sub && (
                        <span className="text-xs text-slate-400 shrink-0">
                          {sub}
                        </span>
                      )}

                      {/* Edit / Delete buttons (edit mode) */}
                      {isEditing && (
                        <div className="flex items-center gap-1 shrink-0">
                          <button
                            type="button"
                            onClick={() =>
                              isEditingThis
                                ? handleCancelEdit()
                                : handleEditRecord(item)
                            }
                            disabled={
                              disabled ||
                              recordSaving ||
                              (editingItemId != null && !isEditingThis)
                            }
                            className={`p-1 rounded transition-colors disabled:opacity-30 ${
                              isEditingThis
                                ? "text-blue-600 bg-blue-100 dark:bg-blue-900/30"
                                : "text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20"
                            }`}
                            title={
                              isEditingThis ? "Cancel edit" : "Edit record"
                            }
                          >
                            <FaEdit size={11} />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteRecord(item)}
                            disabled={disabled || isDeleting || recordSaving}
                            className="p-1 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors disabled:opacity-30"
                            title={
                              isPrimary
                                ? "Cannot delete primary record"
                                : "Delete record"
                            }
                          >
                            {isDeleting ? (
                              <FaSpinner className="animate-spin" size={11} />
                            ) : (
                              <FaTrash size={11} />
                            )}
                          </button>
                        </div>
                      )}
                    </div>

                    {/* ─── Inline editor for this record ─── */}
                    {isEditingThis && (
                      <CommRecordEditor
                        type={type}
                        values={editingValues}
                        onChange={(key, val) =>
                          setEditingValues((prev) => ({
                            ...prev,
                            [key]: val,
                          }))
                        }
                        onSave={handleSaveRecord}
                        onCancel={handleCancelEdit}
                        saving={recordSaving}
                        recordId={Number(item?.id)}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-slate-400 italic">
              No {type} records available
            </p>
          )}

          {/* ─── "New record" inline editor ─── */}
          {editingItemId === "new" && (
            <div className="border border-blue-200 dark:border-blue-800 rounded-lg overflow-hidden">
              <div className="px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800">
                <span className="text-xs font-semibold text-blue-700 dark:text-blue-400">
                  New {COMM_LABELS[type]} Record
                </span>
              </div>
              <CommRecordEditor
                type={type}
                values={editingValues}
                onChange={(key, val) =>
                  setEditingValues((prev) => ({ ...prev, [key]: val }))
                }
                onSave={handleSaveRecord}
                onCancel={handleCancelEdit}
                saving={recordSaving}
                recordId={null}
              />
            </div>
          )}

          {/* ─── Action buttons (edit mode only) ─── */}
          {isEditing && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleAddNew}
                disabled={disabled || saving || editingItemId != null}
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
                disabled={disabled || saving || editingItemId != null}
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
      {searchOpen && (
        <SearchDialog
          type={type}
          query={searchQuery}
          onQueryChange={setSearchQuery}
          results={searchResults}
          loading={searchLoading}
          saving={saving}
          linkedIds={
            new Set(
              displayItems
                .map((i: any) => Number(i?.id))
                .filter(Number.isFinite),
            )
          }
          onSelect={handleSearchSelect}
          onClose={() => setSearchOpen(false)}
        />
      )}
    </div>
  );
};

export default withDevIdentifier(ContactInfoPanel, "ContactInfoPanel", "teal");

// ---------------------------------------------------------------------------
// Inline record editor — renders per-model fields for a single comm record
// ---------------------------------------------------------------------------

interface CommRecordEditorProps {
  type: CommType;
  values: Record<string, any>;
  onChange: (key: string, value: any) => void;
  onSave: () => void;
  onCancel: () => void;
  saving: boolean;
  /** null when creating a new record */
  recordId: number | null;
}

function CommRecordEditor({
  type,
  values,
  onChange,
  onSave,
  onCancel,
  saving,
  recordId,
}: CommRecordEditorProps) {
  const fields = COMM_FIELD_CONFIGS[type];
  return (
    <div className="px-3 py-3 bg-slate-50/50 dark:bg-slate-800/30 space-y-2">
      {recordId && (
        <div className="text-[10px] font-mono text-slate-400 mb-1">
          editing {type} #{recordId}
        </div>
      )}

      <div className="grid grid-cols-2 gap-x-3 gap-y-2">
        {fields.map((fd) => {
          const isFullWidth = fd.width === "full";
          const isCheckbox = fd.inputType === "checkbox";

          if (isCheckbox) {
            return (
              <label
                key={fd.key}
                className="flex items-center gap-2 col-span-1"
              >
                <input
                  type="checkbox"
                  checked={!!values[fd.key]}
                  onChange={(e) => onChange(fd.key, e.target.checked)}
                  className="rounded border-slate-300 dark:border-slate-600 text-blue-600"
                />
                <span className="text-xs text-slate-600 dark:text-slate-400">
                  {fd.label}
                </span>
              </label>
            );
          }

          return (
            <div
              key={fd.key}
              className={isFullWidth ? "col-span-2" : "col-span-1"}
            >
              <label className="block text-[11px] font-medium text-slate-500 dark:text-slate-400 mb-0.5">
                {fd.label}
              </label>
              <input
                type="text"
                value={values[fd.key] ?? ""}
                onChange={(e) => onChange(fd.key, e.target.value)}
                placeholder={fd.placeholder || ""}
                className="w-full px-2 py-1 text-sm border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
              />
            </div>
          );
        })}
      </div>

      <div className="flex items-center gap-2 pt-1">
        <button
          type="button"
          onClick={onSave}
          disabled={saving}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 rounded-lg transition-colors disabled:opacity-40"
        >
          {saving ? (
            <FaSpinner className="animate-spin" size={10} />
          ) : (
            <FaSave size={10} />
          )}
          {recordId ? "Save" : "Create"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600 rounded-lg transition-colors disabled:opacity-40"
        >
          <FaUndo size={10} />
          Cancel
        </button>
      </div>
    </div>
  );
}

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
  const filtered = results.filter((item: any) => {
    const isLinked = linkedIds.has(Number(item?.id));
    if (isLinked) return false;
    if (!query.trim()) return true;
    const val = displayValue(type, item).toLowerCase();
    const label = String(item?.name || item?.type || "").toLowerCase();
    const q = query.trim().toLowerCase();
    return (
      val.includes(q) || label.includes(q) || String(item?.id || "").includes(q)
    );
  });

  return (
    <>
      <div className="fixed inset-0 z-50 bg-black/40" onClick={onClose} />
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
              placeholder="Search..."
              className="w-full px-3 py-2 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800"
              autoFocus
            />
            <div className="max-h-72 overflow-y-auto border border-slate-200 dark:border-slate-700 rounded-lg">
              {loading ? (
                <div className="p-3 text-sm text-slate-500 flex items-center gap-2">
                  <FaSpinner className="animate-spin" size={12} />
                  Loading...
                </div>
              ) : filtered.length === 0 ? (
                <div className="p-3 text-sm text-slate-500">No matches</div>
              ) : (
                filtered.map((item: any, idx: number) => {
                  const val = displayValue(type, item);
                  const sub = secondaryLabel(type, item);
                  return (
                    <button
                      key={`${item?.id ?? idx}`}
                      type="button"
                      onClick={() => onSelect(item)}
                      disabled={saving}
                      className="w-full text-left px-3 py-2 border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 disabled:opacity-50"
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
                        <span className="text-xs text-slate-400 font-mono shrink-0">
                          #{item?.id}
                        </span>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
            {saving && (
              <div className="text-xs text-slate-500 flex items-center gap-2">
                <FaSpinner className="animate-spin" size={12} />
                Saving...
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
