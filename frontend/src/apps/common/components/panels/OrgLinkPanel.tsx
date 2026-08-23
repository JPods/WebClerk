/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * OrgLinkPanel — Panel showing all org FK associations for a contact.
 *
 * Layout (edit mode):
 *   ┌─ Organization Associations ─────────────────────────┐
 *   │  customer_id :  #42  Acme Corp        🔍            │
 *   │  vendor_id   :  —                     🔍            │
 *   │  rep_id      :  #7   John Doe         🔍            │
 *   │  employee_id :  —                     🔍            │
 *   │  mfg_id      :  —                     🔍            │
 *   │  other_id    :  #99  Legacy Org        🔍            │
 *   └─────────────────────────────────────────────────────┘
 *
 * Save-as-you-go: each selection triggers an immediate
 * `updateContact({ id, [field]: orgId })` call.
 *
 * @see readmes/contact-save-panel-plan.md §6
 */

import React, { useState, useCallback, useEffect } from "react";
import {
  FaSearch,
  FaSpinner,
  FaTimes,
  FaBuilding,
  FaSave,
  FaEdit,
  FaPlus,
  FaUndo,
} from "react-icons/fa";
import { ChevronDown, ChevronRight, Building2 } from "lucide-react";
import { getRecord, saveRecord } from "@/api/wcapi";
import { updateContact } from "@/apps/core/models/contact/services/contactApi";
import { useDispatch } from "react-redux";
import { showToast } from "@/store/slices/toastSlice";

import OrgSearchDialog from "@/apps/common/components/OrgSearchDialog";
import type {
  OrgSearchResult,
  SearchableOrgType,
} from "@/apps/common/components/OrgSearchDialog";
import { withDevIdentifier } from "@/components/common/DevIdentifier";
import InternationalPhoneInput from "@/components/form/input/InternationalPhoneInput";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface OrgField {
  /** The field name on the contact record (e.g. "customer_id") */
  fieldName: string;
  /** Display label (e.g. "Customer") */
  label: string;
  /** Current FK value (number id or null) */
  value: number | null | undefined;
  /** Resolved display name (if known) */
  displayName?: string | null;
  /** Org type for search dialog */
  orgType: SearchableOrgType;
}

export interface OrgScalarField {
  /** Field name on the contact record (e.g. "company") */
  fieldName: string;
  /** Display label */
  label: string;
  /** Current value */
  value: string | null | undefined;
  /** Input placeholder */
  placeholder?: string;
  /** "text" (default) or "select" for dropdown */
  type?: "text" | "select";
  /** Select options (when type === "select") */
  options?: { value: string; label: string }[];
  /** Disable the input */
  disabled?: boolean;
}

export interface OrgLinkPanelProps {
  /** Array of org FK fields to show */
  fields: OrgField[];
  /** Whether the form is in edit/add mode */
  isEditing: boolean;
  /** Contact ID (null → panels disabled) */
  contactId: number | null | undefined;
  /** Called after a successful save with (fieldName, orgId, orgDisplayName) */
  onOrgChanged?: (
    fieldName: string,
    orgId: number | null,
    displayName: string | null,
  ) => void;
  /** Start expanded? */
  defaultExpanded?: boolean;
  /** Scalar org-related fields (company, title, department, role, etc.) */
  scalarFields?: OrgScalarField[];
  /** Called when a scalar field value changes (for live form sync) */
  onScalarFieldChange?: (fieldName: string, value: string) => void;
  /** Called when Save button is clicked to persist scalar org fields */
  onSaveScalars?: (values: Record<string, string>) => Promise<void>;
}

// ---------------------------------------------------------------------------
// Per-org-type inline editor field definitions
// ---------------------------------------------------------------------------

interface OrgRecordFieldDef {
  key: string;
  label: string;
  width?: "full" | "half";
  placeholder?: string;
  inputType?: "text" | "select";
  options?: { value: string; label: string }[];
}

/** All org types share the same OrgBase table — common editable fields */
const ORG_RECORD_FIELDS: OrgRecordFieldDef[] = [
  {
    key: "display_name",
    label: "display name",
    width: "full",
    placeholder: "Company or person name",
  },
  {
    key: "company",
    label: "company",
    width: "half",
    placeholder: "Company alias",
  },
  {
    key: "attention",
    label: "attention",
    width: "half",
    placeholder: "Attn line",
  },
  { key: "email", label: "email", width: "half", placeholder: "Primary email" },
  { key: "phone", label: "phone", width: "half", placeholder: "Primary phone" },
  {
    key: "status",
    label: "status",
    width: "half",
    inputType: "select",
    options: [
      { value: "active", label: "Active" },
      { value: "prospect", label: "Prospect" },
      { value: "suspended", label: "Suspended" },
      { value: "inactive", label: "Inactive" },
      { value: "retired", label: "Retired" },
      { value: "", label: "(none)" },
    ],
  },
  {
    key: "price_level",
    label: "price level",
    width: "half",
    placeholder: "retail, wholesale…",
  },
  { key: "notes", label: "notes", width: "full", placeholder: "Notes" },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Given an org type, return the wcapi model name for resolution lookups */
function orgTypeToModelName(orgType: SearchableOrgType): string {
  // All org types live on the orgbase model (or their subclass).
  // The WCAPI uses "customer", "vendor" etc. as model names.
  return orgType === "organization" ? "orgbase" : orgType;
}

// ---------------------------------------------------------------------------
// Module-level cache for org record resolution (prevents duplicate API calls)
// ---------------------------------------------------------------------------

/** Cache key format: "model:id" → resolved display name */
const orgDisplayNameCache = new Map<string, string>();

/** In-flight promises to prevent duplicate simultaneous requests */
const orgFetchInFlight = new Map<string, Promise<string>>();

/**
 * Fetch org display name with caching.
 * Returns cached value if available, otherwise fetches and caches.
 */
async function fetchOrgDisplayName(model: string, id: number): Promise<string> {
  const cacheKey = `${model}:${id}`;

  // Return cached value if available
  if (orgDisplayNameCache.has(cacheKey)) {
    return orgDisplayNameCache.get(cacheKey)!;
  }

  // If already fetching, wait for that promise
  if (orgFetchInFlight.has(cacheKey)) {
    return orgFetchInFlight.get(cacheKey)!;
  }

  // Start new fetch
  const fetchPromise = (async () => {
    try {
      const res: any = await getRecord(model, id);
      const record = res?.record ?? res;
      const name =
        record?.display_name ||
        record?.company ||
        record?.attention ||
        `#${id}`;
      orgDisplayNameCache.set(cacheKey, name);
      return name;
    } catch {
      const fallback = `#${id}`;
      orgDisplayNameCache.set(cacheKey, fallback);
      return fallback;
    } finally {
      orgFetchInFlight.delete(cacheKey);
    }
  })();

  orgFetchInFlight.set(cacheKey, fetchPromise);
  return fetchPromise;
}

/**
 * Update cache when an org is modified (so stale names don't persist)
 */
function updateOrgDisplayNameCache(
  model: string,
  id: number,
  displayName: string,
): void {
  const cacheKey = `${model}:${id}`;
  orgDisplayNameCache.set(cacheKey, displayName);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const OrgLinkPanel: React.FC<OrgLinkPanelProps> = ({
  fields,
  isEditing,
  contactId,
  onOrgChanged,
  defaultExpanded,
  scalarFields,
  onScalarFieldChange,
  onSaveScalars,
}) => {
  const dispatch = useDispatch();
  const [expanded, setExpanded] = useState(
    defaultExpanded ?? (isEditing ? true : false),
  );

  // Track resolved display names (keyed by fieldName)
  const [resolvedNames, setResolvedNames] = useState<
    Record<string, string | null>
  >({});

  // Search dialog state
  const [searchField, setSearchField] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [scalarsSaving, setScalarsSaving] = useState(false);
  const [scalarsSaved, setScalarsSaved] = useState(false);

  // ----- Inline org record editing state -----
  /** Which org FK field is currently being edited (e.g. "customer_id") */
  const [editingOrgField, setEditingOrgField] = useState<string | null>(null);
  /** Working copy of the org record fields for inline editing */
  const [editingOrgValues, setEditingOrgValues] = useState<Record<string, any>>(
    {},
  );
  /** Is the inline org record being saved? */
  const [orgRecordSaving, setOrgRecordSaving] = useState(false);
  /** Is the org record being fetched for editing? */
  const [orgRecordLoading, setOrgRecordLoading] = useState(false);
  /** Are we creating a new org record? (fieldName → true) */
  const [creatingNewOrg, setCreatingNewOrg] = useState<string | null>(null);

  /** Find the OrgField config for the currently searching field */
  const activeOrgField = fields.find((f) => f.fieldName === searchField);

  // Resolve display names for populated fields
  useEffect(() => {
    let cancelled = false;
    const toResolve = fields.filter(
      (f) =>
        f.value != null &&
        Number.isFinite(Number(f.value)) &&
        Number(f.value) > 0 &&
        !f.displayName &&
        resolvedNames[f.fieldName] === undefined,
    );

    if (toResolve.length === 0) return;

    Promise.allSettled(
      toResolve.map(async (f) => {
        const model = orgTypeToModelName(f.orgType);
        const name = await fetchOrgDisplayName(model, Number(f.value));
        return { fieldName: f.fieldName, name };
      }),
    ).then((results) => {
      if (cancelled) return;
      const updates: Record<string, string> = {};
      for (const r of results) {
        if (r.status === "fulfilled") {
          updates[r.value.fieldName] = r.value.name;
        }
      }
      if (Object.keys(updates).length > 0) {
        setResolvedNames((prev) => ({ ...prev, ...updates }));
      }
    });

    return () => {
      cancelled = true;
    };
  }, [fields, resolvedNames]);

  /** Handle selection from OrgSearchDialog */
  const handleOrgSelect = useCallback(
    async (org: OrgSearchResult) => {
      if (!contactId || !searchField) return;
      setSaving(true);
      try {
        const payload: Record<string, any> = {
          id: contactId,
          mode: "update",
          [searchField]: org.id,
        };
        await updateContact(payload as any);

        // Update resolved name cache
        setResolvedNames((prev) => ({
          ...prev,
          [searchField]: org.display_name || org.company || `#${org.id}`,
        }));

        onOrgChanged?.(
          searchField,
          org.id,
          org.display_name || org.company || null,
        );
        setSearchField(null);

        dispatch(
          showToast({
            message: `${searchField.replace("_id", "")} assigned`,
            type: "success",
          }),
        );
      } catch (err: any) {
        console.error("[OrgLinkPanel] Failed to assign org:", err);
        dispatch(
          showToast({
            message: `Failed to assign ${searchField.replace("_id", "")}`,
            type: "error",
          }),
        );
      } finally {
        setSaving(false);
      }
    },
    [contactId, searchField, onOrgChanged, dispatch],
  );

  /** Clear an org association */
  const handleClear = useCallback(
    async (fieldName: string) => {
      if (!contactId) return;
      setSaving(true);
      try {
        const payload: Record<string, any> = {
          id: contactId,
          mode: "update",
          [fieldName]: null,
        };
        await updateContact(payload as any);

        setResolvedNames((prev) => {
          const next = { ...prev };
          delete next[fieldName];
          return next;
        });

        onOrgChanged?.(fieldName, null, null);

        dispatch(
          showToast({
            message: `${fieldName.replace("_id", "")} cleared`,
            type: "success",
          }),
        );
      } catch (err: any) {
        console.error("[OrgLinkPanel] Failed to clear org:", err);
        dispatch(
          showToast({
            message: `Failed to clear ${fieldName.replace("_id", "")}`,
            type: "error",
          }),
        );
      } finally {
        setSaving(false);
      }
    },
    [contactId, onOrgChanged, dispatch],
  );

  /** Save scalar org fields (company, title, department, role, etc.) */
  const handleSaveScalars = useCallback(async () => {
    if (!onSaveScalars || !scalarFields) return;
    setScalarsSaving(true);
    setScalarsSaved(false);
    try {
      const values: Record<string, string> = {};
      for (const sf of scalarFields) {
        values[sf.fieldName] = sf.value ?? "";
      }
      await onSaveScalars(values);
      setScalarsSaved(true);
      setTimeout(() => setScalarsSaved(false), 2000);
    } catch {
      // parent handles toast
    } finally {
      setScalarsSaving(false);
    }
  }, [onSaveScalars, scalarFields]);

  // ----- Inline org record editing handlers -----

  /** Open inline editor for an existing org record (fetch its data first) */
  const handleEditOrgRecord = useCallback(
    async (field: OrgField) => {
      if (!field.value) return;
      setEditingOrgField(field.fieldName);
      setCreatingNewOrg(null);
      setOrgRecordLoading(true);
      try {
        const model = orgTypeToModelName(field.orgType);
        const res: any = await getRecord(model, Number(field.value));
        const record = res?.record ?? res;
        const values: Record<string, any> = {};
        for (const fd of ORG_RECORD_FIELDS) {
          values[fd.key] = record?.[fd.key] ?? "";
        }
        setEditingOrgValues(values);
      } catch (err: any) {
        console.error("[OrgLinkPanel] Failed to fetch org record:", err);
        dispatch(
          showToast({ message: "Failed to load org record", type: "error" }),
        );
        setEditingOrgField(null);
      } finally {
        setOrgRecordLoading(false);
      }
    },
    [dispatch],
  );

  /** Open inline editor for creating a new org record for a field */
  const handleCreateNewOrg = useCallback((field: OrgField) => {
    setEditingOrgField(field.fieldName);
    setCreatingNewOrg(field.fieldName);
    const values: Record<string, any> = {};
    for (const fd of ORG_RECORD_FIELDS) {
      values[fd.key] = "";
    }
    // Pre-set org_type based on the field
    values._orgType = field.orgType;
    setEditingOrgValues(values);
  }, []);

  /** Cancel org record editing */
  const handleCancelOrgEdit = useCallback(() => {
    setEditingOrgField(null);
    setEditingOrgValues({});
    setCreatingNewOrg(null);
  }, []);

  /** Save the inline-edited org record */
  const handleSaveOrgRecord = useCallback(async () => {
    if (!editingOrgField) return;
    const field = fields.find((f) => f.fieldName === editingOrgField);
    if (!field) return;

    setOrgRecordSaving(true);
    try {
      const model = orgTypeToModelName(field.orgType);
      const payload: Record<string, any> = { ...editingOrgValues };
      delete payload._orgType;

      if (creatingNewOrg) {
        // Creating a new org record
        payload.org_type =
          field.orgType === "organization" ? "other" : field.orgType;
        const res: any = await saveRecord(model, payload);
        const record = res?.record ?? res;
        const newId = Number(record?.id ?? res?.id);
        if (!Number.isFinite(newId) || newId <= 0) {
          throw new Error("Failed to create org record");
        }

        // Auto-assign this new org to the contact
        if (contactId) {
          await updateContact({
            id: contactId,
            mode: "update",
            [field.fieldName]: newId,
          } as any);
        }

        setResolvedNames((prev) => ({
          ...prev,
          [field.fieldName]:
            payload.display_name || payload.company || `#${newId}`,
        }));

        onOrgChanged?.(
          field.fieldName,
          newId,
          payload.display_name || payload.company || null,
        );

        dispatch(
          showToast({
            message: `${field.label} created and assigned`,
            type: "success",
          }),
        );
      } else {
        // Updating existing org record
        payload.id = Number(field.value);
        await saveRecord(model, payload);

        // Update resolved name
        setResolvedNames((prev) => ({
          ...prev,
          [field.fieldName]:
            payload.display_name || payload.company || `#${field.value}`,
        }));

        dispatch(
          showToast({
            message: `${field.label} record saved`,
            type: "success",
          }),
        );
      }

      setEditingOrgField(null);
      setEditingOrgValues({});
      setCreatingNewOrg(null);
    } catch (err: any) {
      console.error("[OrgLinkPanel] Failed to save org record:", err);
      dispatch(
        showToast({
          message: `Failed to save ${field.label} record`,
          type: "error",
        }),
      );
    } finally {
      setOrgRecordSaving(false);
    }
  }, [
    editingOrgField,
    editingOrgValues,
    creatingNewOrg,
    fields,
    contactId,
    onOrgChanged,
    dispatch,
  ]);

  const disabled = !contactId;

  // Count how many fields are populated
  const populatedCount = fields.filter(
    (f) => f.value != null && Number(f.value) > 0,
  ).length;

  return (
    <div className="rounded-lg overflow-hidden mb-3 db-border-all">
      {/* ─── Header ─── */}
      <button
        type="button"
        className="db-list-row w-full flex items-center justify-between px-4 py-2.5 transition-colors db-bg-surface-alt"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          {expanded ? (
            <ChevronDown className="w-3 h-3 db-text-dim" />
          ) : (
            <ChevronRight className="w-3 h-3 db-text-dim" />
          )}
          <Building2 size={14} className="db-text-muted" />
          <span className="font-semibold text-sm db-text">
            Company & Organizations
          </span>
          {populatedCount > 0 && (
            <span className="text-xs px-1.5 py-0.5 rounded-full font-medium db-row-active-accent">
              {populatedCount}
            </span>
          )}
          {/* DEV: show contactId for debugging */}
          {contactId && (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded db-bg-surface-alt db-text-dim">
              c#{contactId}
            </span>
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-4 py-3 space-y-1 db-bg-surface">
          {/* ─── Scalar org fields (company, title, department, role, etc.) ─── */}
          {scalarFields && scalarFields.length > 0 && (
            <div className="space-y-1 pb-2 mb-2 db-border-bottom-light">
              {scalarFields.map((sf) => (
                <div
                  key={sf.fieldName}
                  className="flex items-center gap-2 py-1.5"
                >
                  <span className="w-32 shrink-0 text-xs font-medium db-text-muted">
                    {sf.label} :
                  </span>
                  {isEditing ? (
                    sf.type === "select" && sf.options ? (
                      <select
                        value={sf.value || ""}
                        onChange={(e) =>
                          onScalarFieldChange?.(sf.fieldName, e.target.value)
                        }
                        disabled={sf.disabled || disabled}
                        className="flex-1 px-2 py-1 text-sm rounded db-panel-input-text"
                      >
                        {sf.options.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        value={sf.value || ""}
                        onChange={(e) =>
                          onScalarFieldChange?.(sf.fieldName, e.target.value)
                        }
                        disabled={sf.disabled || disabled}
                        placeholder={sf.placeholder || ""}
                        className="flex-1 px-2 py-1 text-sm rounded db-panel-input-text"
                      />
                    )
                  ) : (
                    <span className="text-sm flex-1 db-text">
                      {sf.value || "—"}
                    </span>
                  )}
                </div>
              ))}
              {/* Save button for scalar fields */}
              {isEditing && onSaveScalars && (
                <div className="flex justify-end pt-1">
                  <button
                    type="button"
                    onClick={handleSaveScalars}
                    disabled={disabled || scalarsSaving}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors disabled:opacity-40"
                    style={{
                      background: scalarsSaved ? 'var(--db-accent-green)' : 'var(--db-row-active)',
                      color: scalarsSaved ? 'var(--db-surface)' : 'var(--db-accent)',
                      opacity: scalarsSaved ? 0.8 : 1,
                    }}
                  >
                    {scalarsSaving ? (
                      <FaSpinner className="animate-spin" size={10} />
                    ) : scalarsSaved ? (
                      "Saved ✓"
                    ) : (
                      <>
                        <FaSave size={10} />
                        Save Company Info
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* ─── Org FK association rows ─── */}
          {fields.map((field) => {
            const hasValue =
              field.value != null &&
              Number.isFinite(Number(field.value)) &&
              Number(field.value) > 0;
            const name =
              field.displayName ||
              resolvedNames[field.fieldName] ||
              (hasValue ? `#${field.value}` : null);
            const isEditingThisOrg = editingOrgField === field.fieldName;

            return (
              <div key={field.fieldName}>
                {/* ─── Summary row ─── */}
                <div
                  className={`flex items-center gap-2 py-1.5 ${
                    isEditingThisOrg ? "px-2 rounded db-bg-row-active" : ""
                  }`}
                >
                  {/* Label */}
                  <span className="w-32 shrink-0 text-xs font-medium db-text-muted">
                    {field.label} :
                  </span>

                  {/* Value */}
                  {hasValue ? (
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <span className="text-xs font-mono db-text-dim">
                        #{field.value}
                      </span>
                      <span className="text-sm font-medium truncate db-text">
                        {name}
                      </span>
                      {isEditing && (
                        <button
                          type="button"
                          onClick={() => handleClear(field.fieldName)}
                          disabled={disabled || saving}
                          className="shrink-0 p-1 rounded transition-colors disabled:opacity-40 db-text-dim"
                          title="Clear association"
                        >
                          <FaTimes size={10} />
                        </button>
                      )}
                    </div>
                  ) : (
                    <span className="text-sm flex-1 db-text-dim">—</span>
                  )}

                  {/* Action buttons (edit mode only) */}
                  {isEditing && (
                    <div className="flex items-center gap-1 shrink-0">
                      {/* Edit button — only when org record exists */}
                      {hasValue && (
                        <button
                          type="button"
                          onClick={() =>
                            isEditingThisOrg
                              ? handleCancelOrgEdit()
                              : handleEditOrgRecord(field)
                          }
                          disabled={
                            disabled ||
                            orgRecordSaving ||
                            (editingOrgField != null && !isEditingThisOrg)
                          }
                          className="p-1 rounded transition-colors disabled:opacity-30"
                          style={{
                            color: isEditingThisOrg ? 'var(--db-accent)' : 'var(--db-text-dim)',
                            background: isEditingThisOrg ? 'var(--db-row-active)' : undefined,
                          }}
                          title={
                            isEditingThisOrg
                              ? "Cancel edit"
                              : `Edit ${field.label} record`
                          }
                        >
                          <FaEdit size={11} />
                        </button>
                      )}
                      {/* Add new button — only when no org is assigned */}
                      {!hasValue && (
                        <button
                          type="button"
                          onClick={() => handleCreateNewOrg(field)}
                          disabled={
                            disabled ||
                            orgRecordSaving ||
                            (editingOrgField != null && !isEditingThisOrg)
                          }
                          className="p-1 rounded transition-colors disabled:opacity-30 db-text-dim"
                          title={`Create new ${field.label}`}
                        >
                          <FaPlus size={11} />
                        </button>
                      )}
                      {/* Search button */}
                      <button
                        type="button"
                        onClick={() => setSearchField(field.fieldName)}
                        disabled={disabled || saving}
                        className="p-1.5 rounded-lg transition-colors disabled:opacity-40 db-text-dim"
                        title={`Search ${field.label}`}
                      >
                        {saving && searchField === field.fieldName ? (
                          <FaSpinner className="animate-spin" size={12} />
                        ) : (
                          <FaSearch size={12} />
                        )}
                      </button>
                    </div>
                  )}
                </div>

                {/* ─── Inline org record editor ─── */}
                {isEditingThisOrg && (
                  <OrgRecordEditor
                    fieldLabel={field.label}
                    orgId={creatingNewOrg ? null : Number(field.value)}
                    values={editingOrgValues}
                    onChange={(key, val) =>
                      setEditingOrgValues((prev) => ({ ...prev, [key]: val }))
                    }
                    onSave={handleSaveOrgRecord}
                    onCancel={handleCancelOrgEdit}
                    saving={orgRecordSaving}
                    loading={orgRecordLoading}
                    isNew={!!creatingNewOrg}
                  />
                )}
              </div>
            );
          })}

          {disabled && isEditing && (
            <p className="text-xs italic pt-1 db-text-gold">
              Save contact first to assign organizations
            </p>
          )}
        </div>
      )}

      {/* ─── OrgSearchDialog ─── */}
      {searchField && activeOrgField && (
        <OrgSearchDialog
          open={true}
          orgType={activeOrgField.orgType}
          allowTypeSwitch={activeOrgField.orgType === "organization"}
          onSelect={handleOrgSelect}
          onClose={() => setSearchField(null)}
          title={`Search ${activeOrgField.label}`}
        />
      )}
    </div>
  );
};

export default withDevIdentifier(OrgLinkPanel, "OrgLinkPanel", "teal", 'apps/common/components/panels/OrgLinkPanel.tsx');
// ---------------------------------------------------------------------------
// Inline org record editor
// ---------------------------------------------------------------------------

interface OrgRecordEditorProps {
  fieldLabel: string;
  orgId: number | null;
  values: Record<string, any>;
  onChange: (key: string, value: any) => void;
  onSave: () => void;
  onCancel: () => void;
  saving: boolean;
  loading: boolean;
  isNew: boolean;
}

function OrgRecordEditor({
  fieldLabel,
  orgId,
  values,
  onChange,
  onSave,
  onCancel,
  saving,
  loading,
  isNew,
}: OrgRecordEditorProps) {
  if (loading) {
    return (
      <div className="px-3 py-4 flex items-center gap-2 text-sm db-surface-alt-muted">
        <FaSpinner className="animate-spin" size={12} />
        Loading {fieldLabel} record…
      </div>
    );
  }

  return (
    <div className="ml-4 mr-2 mb-2 mt-1 px-3 py-3 rounded-lg space-y-2 db-panel-alt">
      {/* DEV: editing badge */}
      <div className="text-[10px] font-mono mb-1 db-text-dim">
        {isNew ? `new ${fieldLabel}` : `editing ${fieldLabel} #${orgId}`}
      </div>

      {/* ─── Field grid ─── */}
      <div className="grid grid-cols-2 gap-x-3 gap-y-2">
        {ORG_RECORD_FIELDS.map((fd) => {
          const isFullWidth = fd.width === "full";

          if (fd.inputType === "select" && fd.options) {
            return (
              <div
                key={fd.key}
                className={isFullWidth ? "col-span-2" : "col-span-1"}
              >
                <label className="block text-[11px] font-medium mb-0.5 db-text-muted">
                  {fd.label}
                </label>
                <select
                  value={values[fd.key] ?? ""}
                  onChange={(e) => onChange(fd.key, e.target.value)}
                  className="w-full px-2 py-1 text-sm rounded db-panel-input-text"
                >
                  {fd.options.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            );
          }

          return (
            <div
              key={fd.key}
              className={isFullWidth ? "col-span-2" : "col-span-1"}
            >
              <label className="block text-[11px] font-medium mb-0.5 db-text-muted">
                {fd.label}
              </label>
              {fd.key === "phone" ? (
                <InternationalPhoneInput
                  value={values[fd.key] ?? ""}
                  onChange={(value) => onChange(fd.key, value)}
                  placeholder={fd.placeholder || ""}
                />
              ) : (
                <input
                  type="text"
                  value={values[fd.key] ?? ""}
                  onChange={(e) => onChange(fd.key, e.target.value)}
                  placeholder={fd.placeholder || ""}
                  className="w-full px-2 py-1 text-sm rounded db-panel-input-text"
                />
              )}
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
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors disabled:opacity-40"
          style={{ background: 'var(--db-accent)', color: '#fff' }}
        >
          {saving ? (
            <FaSpinner className="animate-spin" size={10} />
          ) : (
            <FaSave size={10} />
          )}
          {isNew ? `Create ${fieldLabel}` : "Save"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          disabled={saving}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors disabled:opacity-40 db-surface-alt-text"
        >
          <FaUndo size={10} />
          Cancel
        </button>
      </div>
    </div>
  );
}
