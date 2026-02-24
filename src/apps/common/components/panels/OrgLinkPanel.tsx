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
} from "react-icons/fa";
import { ChevronDown, ChevronRight, Building2 } from "lucide-react";
import { getRecord } from "@/api/wcapi";
import { updateContact } from "@/apps/core/models/contact/services/contactApi";
import { useDispatch } from "react-redux";
import { showToast } from "@/store/slices/toastSlice";

import OrgSearchDialog from "@/apps/common/components/OrgSearchDialog";
import type {
  OrgSearchResult,
  SearchableOrgType,
} from "@/apps/common/components/OrgSearchDialog";

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
}

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
// Component
// ---------------------------------------------------------------------------

const OrgLinkPanel: React.FC<OrgLinkPanelProps> = ({
  fields,
  isEditing,
  contactId,
  onOrgChanged,
  defaultExpanded,
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
        try {
          const model = orgTypeToModelName(f.orgType);
          const res: any = await getRecord(model, Number(f.value));
          const record = res?.record ?? res;
          const name =
            record?.display_name ||
            record?.company ||
            record?.attention ||
            `#${f.value}`;
          return { fieldName: f.fieldName, name };
        } catch {
          return { fieldName: f.fieldName, name: `#${f.value}` };
        }
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

  const disabled = !contactId;

  // Count how many fields are populated
  const populatedCount = fields.filter(
    (f) => f.value != null && Number(f.value) > 0,
  ).length;

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
          <Building2 size={14} className="text-slate-500" />
          <span className="font-semibold text-sm text-slate-700 dark:text-slate-200">
            Organization Associations
          </span>
          {populatedCount > 0 && (
            <span className="text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 px-1.5 py-0.5 rounded-full font-medium">
              {populatedCount}
            </span>
          )}
        </div>
      </button>

      {expanded && (
        <div className="px-4 py-3 bg-white dark:bg-slate-900 space-y-1">
          {fields.map((field) => {
            const hasValue =
              field.value != null &&
              Number.isFinite(Number(field.value)) &&
              Number(field.value) > 0;
            const name =
              field.displayName ||
              resolvedNames[field.fieldName] ||
              (hasValue ? `#${field.value}` : null);

            return (
              <div
                key={field.fieldName}
                className="flex items-center gap-2 py-1.5"
              >
                {/* Label */}
                <span className="w-32 shrink-0 text-xs font-medium text-slate-500 dark:text-slate-400">
                  {field.label} :
                </span>

                {/* Value */}
                {hasValue ? (
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <span className="text-xs font-mono text-slate-400">
                      #{field.value}
                    </span>
                    <span className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
                      {name}
                    </span>
                    {isEditing && (
                      <button
                        type="button"
                        onClick={() => handleClear(field.fieldName)}
                        disabled={disabled || saving}
                        className="shrink-0 p-1 text-slate-400 hover:text-red-500 rounded transition-colors disabled:opacity-40"
                        title="Clear association"
                      >
                        <FaTimes size={10} />
                      </button>
                    )}
                  </div>
                ) : (
                  <span className="text-sm text-slate-400 flex-1">—</span>
                )}

                {/* Search button (edit mode only) */}
                {isEditing && (
                  <button
                    type="button"
                    onClick={() => setSearchField(field.fieldName)}
                    disabled={disabled || saving}
                    className="shrink-0 p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors disabled:opacity-40"
                    title={`Search ${field.label}`}
                  >
                    {saving && searchField === field.fieldName ? (
                      <FaSpinner className="animate-spin" size={12} />
                    ) : (
                      <FaSearch size={12} />
                    )}
                  </button>
                )}
              </div>
            );
          })}

          {disabled && isEditing && (
            <p className="text-xs text-amber-600 dark:text-amber-400 italic pt-1">
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

export default OrgLinkPanel;
