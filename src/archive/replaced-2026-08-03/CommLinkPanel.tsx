/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * CommLinkPanel — Inline panel for a single communication type (email/phone/address/domain).
 *
 * Layout:
 *   ┌─ Email ─────────────────────────────────────────────┐
 *   │  email: user@example.com          (scalar, editable) │
 *   │  ┌──────────────────────────────────────────────────┐│
 *   │  │ ★ #42  user@example.com   Work     ✎  🗑  ✕    ││
 *   │  │   ┌─ Editing #42 ──────────────────────────────┐ ││
 *   │  │   │  email: [          ]  name: [          ]   │ ││
 *   │  │   │  type:  [          ]  attention: [     ]   │ ││
 *   │  │   │              [Save]  [Cancel]              │ ││
 *   │  │   └────────────────────────────────────────────┘ ││
 *   │  │   #87  alt@example.com    Personal   ✎  🗑  ✕  ││
 *   │  │   + Add   🔍 Search existing                    ││
 *   │  └──────────────────────────────────────────────────┘│
 *   └─────────────────────────────────────────────────────┘
 *
 * Save-as-you-go: each add / set-primary / edit / delete triggers an immediate API call.
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
  FaEdit,
  FaTrash,
  FaSave,
  FaUndo,
} from "react-icons/fa";
import { ChevronDown, ChevronRight } from "lucide-react";
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import { useDispatch } from "react-redux";
import { showToast } from "@/store/slices/toastSlice";
import { withDevIdentifier } from "@/components/common/DevIdentifier";
import { PhoneFormat, PhoneLable } from "../detail/PhoneFormat";
import { EmailFormat, EmailLable } from "../detail/EmailFormat";
import { AddressFormat, AddressLable } from "../detail/AddressFormat";
import { DomainFormat, DomainLable } from "../detail/DomainFormat";

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
  /** Reflinks array or object (optional) */
  reflinks?: any[] | Record<string, any[]>;
  /** Whether the form is in edit/add mode */
  isEditing: boolean;
  /** Contact ID (null → panels disabled until contact is saved) */
  contactId: number | null | undefined;
  /** Called when user updates the scalar value via the input */
  onScalarChange?: (value: string) => void;
  /** Called after a record is set as primary (id, displayValue) */
  onSetPrimary?: (id: number, displayValue: string) => void;
  /** Called when the items list changes (caller should refresh state) */
  onItemsChanged?: () => Promise<void> | void;
  /** Start expanded (default: true in edit mode, false in view) */
  defaultExpanded?: boolean;
  /** Called when user clicks Save to persist the scalar value to the contact */
  onSaveScalar?: (value: string) => Promise<void>;
}

// ---------------------------------------------------------------------------
// Per-model field definitions for inline editing
// ---------------------------------------------------------------------------

interface CommFieldDef {
  /** Field key on the record (e.g. "email", "name", "city") */
  key: string;
  /** Display label */
  label: string;
  /** Input type — "text" (default), "checkbox", "select" */
  inputType?: "text" | "checkbox" | "select";
  /** Percent width hint: "full" (100%), "half" (50%) */
  width?: "full" | "half";
  /** Placeholder text */
  placeholder?: string;
  /** For select inputs — options list */
  options?: { value: string; label: string }[];
}

/**
 * Field layout per comm type. Each model's editable fields are listed
 * in display order. The key names must match the API record properties.
 */
const COMM_FIELD_CONFIGS: Record<CommType, CommFieldDef[]> = {
  email: [
    {
      key: "email",
      label: "Email",
      width: "full",
      placeholder: "user@example.com",
    },
    {
      key: "name",
      label: "Name / Label",
      width: "half",
      placeholder: "Work, Personal…",
    },
    {
      key: "attention",
      label: "Attention",
      width: "half",
      placeholder: "Attn line",
    },
    { key: "type", label: "Type", width: "half", placeholder: "type" },
    { key: "opt_out", label: "Opt Out", inputType: "checkbox", width: "half" },
    {
      key: "is_primary",
      label: "Primary",
      inputType: "checkbox",
      width: "half",
    },
  ],
  phone: [
    {
      key: "number",
      label: "Number",
      width: "full",
      placeholder: "+91 (123) 456-7890",
    },
    {
      key: "name",
      label: "Name / Label",
      width: "half",
      placeholder: "Mobile, Office…",
    },
    {
      key: "country_code",
      label: "Country Code",
      width: "half",
      placeholder: "+91",
    },
    {
      key: "attention",
      label: "Attention",
      width: "half",
      placeholder: "Attn line",
    },
    {
      key: "format",
      label: "Format",
      width: "half",
      placeholder: "formatted number",
    },
    { key: "opt_out", label: "Opt Out", inputType: "checkbox", width: "half" },
  ],
  address: [
    {
      key: "address1",
      label: "Address 1",
      width: "full",
      placeholder: "Street address",
    },
    {
      key: "address2",
      label: "Address 2",
      width: "full",
      placeholder: "Suite, Unit, etc.",
    },
    { key: "city", label: "City", width: "half", placeholder: "City" },
    {
      key: "state",
      label: "State",
      width: "half",
      placeholder: "State / Province",
    },
    { key: "zip", label: "Zip", width: "half", placeholder: "Postal code" },
    { key: "country", label: "Country", width: "half", placeholder: "Country" },
    {
      key: "address_type",
      label: "Type",
      width: "half",
      placeholder: "Billing, Shipping…",
    },
    {
      key: "full",
      label: "Full (display)",
      width: "full",
      placeholder: "Full formatted address",
    },
  ],
  domain: [
    {
      key: "path",
      label: "Domain / URL",
      width: "full",
      placeholder: "example.com",
    },
    {
      key: "type",
      label: "Type",
      width: "half",
      placeholder: "website, social…",
    },
    { key: "status", label: "Status", width: "half", placeholder: "active" },
  ],
};

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

/**
 * Format phone number as +CC (XXX) XXX-XXXX (International style)
 * Supports country code (1-3 digits) + 10 digit number
 */
function formatPhoneNumber(value: string, countryCode?: string | null): string {
  if (!value) return "";

  // Remove all non-digit characters except leading +
  const hasPlus = value.startsWith("+");
  const digits = value.replace(/\D/g, "");

  // If no digits, return empty or just +
  if (digits.length === 0) return hasPlus ? "+" : "";

  // If country code is provided separately, prepend it
  let fullDigits = digits;
  if (countryCode) {
    const ccDigits = countryCode.replace(/\D/g, "");
    // Only prepend if the number doesn't already start with the country code
    if (ccDigits && !digits.startsWith(ccDigits)) {
      fullDigits = ccDigits + digits;
    }
  }

  // Assume max 13 digits (3 country code + 10 local)
  const limited = fullDigits.slice(0, 13);

  // If 10 or fewer digits, treat as local number without country code
  if (limited.length <= 10) {
    const local = limited;
    if (local.length <= 3) return hasPlus || countryCode ? `+${local}` : local;
    if (local.length <= 6) {
      return hasPlus || countryCode
        ? `+${local.slice(0, 3)} (${local.slice(3)})`
        : `(${local.slice(0, 3)}) ${local.slice(3)}`;
    }
    return hasPlus || countryCode
      ? `+${local.slice(0, 3)} (${local.slice(3, 6)}) ${local.slice(6)}`
      : `(${local.slice(0, 3)}) ${local.slice(3, 6)}-${local.slice(6)}`;
  }

  // More than 10 digits: extract country code (first 1-3 digits)
  // Assume country code is everything before the last 10 digits
  const countryCodeLen = limited.length - 10;
  const cc = limited.slice(0, countryCodeLen);
  const local = limited.slice(countryCodeLen);

  // Format as +CC (XXX) XXX-XXXX
  return `+${cc} (${local.slice(0, 3)}) ${local.slice(3, 6)}-${local.slice(6)}`;
}

function displayValue(type: CommType, item: any): string {
  if (!item) return "";
  if (type === "email") return item.email || item.address || item.value || "";
  if (type === "phone") {
    const rawNumber = item.number || item.value || item.format || "";
    const countryCode = item.country_code || null;
    return formatPhoneNumber(rawNumber, countryCode);
  }
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
  reflinks = [],
  isEditing,
  contactId,
  onScalarChange,
  onSetPrimary,
  onItemsChanged,
  defaultExpanded,
  onSaveScalar,
}) => {
  const dispatch = useDispatch();
  const label = title || COMM_LABELS[type];
  const [expanded, setExpanded] = useState(
    defaultExpanded ?? (isEditing ? true : false),
  );

  //console.log("reflinks", reflinks);

  // ----- Scalar save state -----
  const [scalarSaving, setScalarSaving] = useState(false);
  const [scalarSaved, setScalarSaved] = useState(false);

  const handleSaveScalar = useCallback(async () => {
    if (!onSaveScalar) return;
    setScalarSaving(true);
    setScalarSaved(false);
    try {
      await onSaveScalar(scalarValue ?? "");
      setScalarSaved(true);
      setTimeout(() => setScalarSaved(false), 2000);
    } catch {
      // parent handles toast
    } finally {
      setScalarSaving(false);
    }
  }, [onSaveScalar, scalarValue]);

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
        // Await parent refresh before closing search dialog
        await Promise.resolve(onItemsChanged?.());
        // Give React time to process the prop update
        await new Promise((resolve) => setTimeout(resolve, 100));

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
      onSetPrimary?.(Number(item.id), displayValue(type, item));
    },
    [type, onSetPrimary],
  );

  // ----- Inline editing state -----
  /** ID of the record currently being edited inline, or "new" for a freshly-added blank */
  const [editingItemId, setEditingItemId] = useState<number | "new" | null>(
    null,
  );
  /** Working copy of field values for the record being edited */
  const [editingValues, setEditingValues] = useState<Record<string, any>>({});
  /** Per-record save spinner */
  const [recordSaving, setRecordSaving] = useState(false);
  /** Per-record delete spinner — tracks which ID is being deleted */
  const [deletingId, setDeletingId] = useState<number | null>(null);

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
      const payload: Record<string, any> = { ...editingValues };
      if (editingItemId !== "new") {
        payload.id = editingItemId;
      } else {
        payload.contact_id = contactId;
      }
      const res: any = await saveRecord(type, payload);
      const record = res?.record ?? res;
      const savedId = Number(record?.id ?? res?.id);

      // If it was a new record and it's the first, auto-set as primary
      if (editingItemId === "new" && items.length === 0 && savedId > 0) {
        onSetPrimary?.(savedId, displayValue(type, record ?? payload));
      }

      // Await parent refresh before clearing edit state
      await Promise.resolve(onItemsChanged?.());
      // Give React time to process the prop update
      await new Promise((resolve) => setTimeout(resolve, 100));

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
      console.error("[CommLinkPanel] saveRecord failed:", err);
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
    editingItemId,
    editingValues,
    type,
    contactId,
    items.length,
    onSetPrimary,
    onItemsChanged,
    dispatch,
  ]);

  /** Delete (soft-delete) a linked record */
  const handleDeleteRecord = useCallback(
    async (item: any) => {
      if (!item?.id) return;
      const id = Number(item.id);
      setDeletingId(id);
      try {
        await deleteRecord(type, id);

        // Await parent refresh - this should update items prop
        await Promise.resolve(onItemsChanged?.());

        // Give React time to process the prop update and re-render
        // The items prop should now exclude the deleted record
        await new Promise((resolve) => setTimeout(resolve, 200));

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
        console.error("[CommLinkPanel] deleteRecord failed:", err);
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
    [type, editingItemId, onItemsChanged, dispatch],
  );

  const disabled = !contactId;
  const ref_links_array = Array.isArray(reflinks)
    ? reflinks
    : reflinks?.[type] || [];
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
          <span className="text-xs text-slate-400 ml-1">({items.length})</span>
          {/* DEV: show contactId + primaryId for debugging */}
          {contactId && (
            <span className="text-[10px] font-mono text-slate-400 bg-slate-100 dark:bg-slate-700 px-1.5 py-0.5 rounded">
              c#{contactId}
              {primaryId ? ` → ${type}_id:${primaryId}` : ""}
            </span>
          )}
          {/* Primary scalar value as a subtle badge in the header */}
          {!expanded && scalarValue && (
            <span className="ml-2 text-xs text-slate-500 dark:text-slate-400 truncate max-w-[200px]">
              {type === "phone" ? formatPhoneNumber(scalarValue) : scalarValue}
            </span>
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-4 py-3 bg-white dark:bg-slate-900 space-y-3">
          {/* ─── Scalar value row ─── */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400 w-24 shrink-0">
              {type === "phone" ? (
                <PhoneLable value={formatPhoneNumber(scalarValue || "")} />
              ) : type === "email" ? (
                <EmailLable value={scalarValue} />
              ) : type === "address" ? (
                <AddressLable value={scalarValue} />
              ) : type === "domain" ? (
                <DomainLable value={scalarValue} />
              ) : (
                SCALAR_LABEL[type]
              )}{" "}
              :
            </span>
            {isEditing ? (
              <>
                <input
                  type="text"
                  value={scalarValue || ""}
                  onChange={(e) => {
                    const val =
                      type === "phone"
                        ? formatPhoneNumber(e.target.value)
                        : e.target.value;
                    onScalarChange?.(val);
                  }}
                  className="flex-1 px-2 py-1 text-sm border border-slate-300 dark:border-slate-600 rounded bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100"
                  placeholder={
                    type === "phone" ? "+91 (123) 456-7890" : `Primary ${type}`
                  }
                  disabled={disabled}
                />
                {onSaveScalar && (
                  <button
                    type="button"
                    onClick={handleSaveScalar}
                    disabled={disabled || scalarSaving}
                    className={`shrink-0 px-2.5 py-1 text-xs font-medium rounded-lg transition-colors ${
                      scalarSaved
                        ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                        : "bg-blue-50 text-blue-600 hover:bg-blue-100 dark:bg-blue-900/20 dark:text-blue-400 dark:hover:bg-blue-900/30"
                    } disabled:opacity-40`}
                  >
                    {scalarSaving ? (
                      <FaSpinner className="animate-spin" size={10} />
                    ) : scalarSaved ? (
                      "Saved ✓"
                    ) : (
                      "Save"
                    )}
                  </button>
                )}
              </>
            ) : (
              <span className="text-sm font-medium text-slate-900 dark:text-slate-100">
                {type === "phone" && scalarValue
                  ? formatPhoneNumber(scalarValue)
                  : scalarValue || "—"}
              </span>
            )}
          </div>

          {/* ─── Linked records list ─── */}

          {/*
            Filter out items already linked in ref_links_array
            Only show items whose IDs are NOT in the reflinks
          */}
          {(() => {
            const displayItems = items.filter((item: any) => {
              const itemId = Number(item.id);
              if (!Number.isFinite(itemId)) return false;
              // Exclude if already in ref_links_array
              const isAlreadyLinked = ref_links_array.some((rl: any) => {
                const rlId = Number(rl.id);
                return Number.isFinite(rlId) && rlId === itemId;
              });
              return !isAlreadyLinked;
            });
            console.log("displayItems", displayItems);
            return displayItems.length > 0 ? (
              <div className="border border-slate-100 dark:border-slate-800 rounded-lg divide-y divide-slate-100 dark:divide-slate-800">
                {displayItems.map((item: any, idx: number) => {
                  // Find matching reflink by comparing IDs

                  const matchingReflink = ref_links_array.find((rl: any) => {
                    const rlId = Number(rl.id);
                    const itemId = Number(item.id);
                    return (
                      Number.isFinite(rlId) &&
                      Number.isFinite(itemId) &&
                      rlId === itemId
                    );
                  });

                  const isPrimary =
                    matchingReflink?.is_primary === true ||
                    matchingReflink?.is_primary === 1;
                  const val = displayValue(type, item);
                  const sub = secondaryLabel(type, item);
                  const isEditingThis = editingItemId === Number(item.id);
                  const isDeleting = deletingId === Number(item.id);

                  return (
                    <div key={item.id ?? idx}>
                      {/* ─── Record summary row ─── */}
                      <div
                        className={`flex items-center gap-2 px-3 py-2 text-sm hover:bg-slate-50 dark:hover:bg-slate-800/50 ${
                          isEditingThis
                            ? "bg-blue-50/50 dark:bg-blue-900/10"
                            : ""
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
                              title="Delete record"
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
                          recordId={Number(item.id)}
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
            );
          })()}

          {/* ─── "New record" inline editor ─── */}
          {editingItemId === "new" && (
            <div className="border border-blue-200 dark:border-blue-800 rounded-lg overflow-hidden">
              <div className="px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 border-b border-blue-200 dark:border-blue-800">
                <span className="text-xs font-semibold text-blue-700 dark:text-blue-400">
                  New {COMM_LABELS[type]} Record
                </span>
              </div>
              {/* This component for Primary contact record */}
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
            new Set(items.map((i: any) => Number(i.id)).filter(Number.isFinite))
          }
          onSelect={handleSearchSelect}
          onClose={() => setSearchOpen(false)}
        />
      )}
    </div>
  );
};

export default withDevIdentifier(CommLinkPanel, "CommLinkPanel", "teal");
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
      {/* DEV: editing record badge */}
      {recordId && (
        <div className="text-[10px] font-mono text-slate-400 mb-1">
          editing {type} #{recordId}
        </div>
      )}

      {/* ─── Field grid (half fields sit side by side, full fields span row) ─── */}
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

      {/* ─── Save / Cancel ─── */}
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
    // Exclude already-linked records
    const isLinked = linkedIds.has(Number(item?.id));
    if (isLinked) return false;
    // Apply query filter if provided
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
      {/* Backdrop */}
      <div className="fixed inset-0 z-50 bg-black/40" onClick={onClose} />
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
