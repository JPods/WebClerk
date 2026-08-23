/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * OrgSearchDialog.tsx
 *
 * A reusable modal dialog for searching and selecting an organization record
 * (customer, vendor, manufacturer, rep, employee, or org) to assign its ID
 * to a contact or transaction.
 *
 * Usage:
 *   <OrgSearchDialog
 *     open={showDialog}
 *     orgType="customer"
 *     onSelect={(org) => { setValue('customer_id', org.id); }}
 *     onClose={() => setShowDialog(false)}
 *   />
 *
 * Features:
 *  - Keyword search with debounce (300 ms)
 *  - Paginated results list (20 per page)
 *  - Displays display_name, ida, email, phone, status
 *  - Returns selected record data for populating scalar fields or refs.links
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { FaSearch, FaTimes, FaSpinner } from "react-icons/fa";
import { getRecords } from "@/api/wcapi";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type SearchableOrgType =
  | "customer"
  | "vendor"
  | "manufacturer"
  | "rep"
  | "employee"
  | "organization";

export interface OrgSearchResult {
  id: number;
  display_name: string;
  ida?: string;
  email?: string | null;
  phone?: string | null;
  org_type?: string;
  status?: string;
  is_active?: boolean;
  company?: string;
  attention?: string | null;
}

export interface OrgSearchDialogProps {
  /** Whether the dialog is visible */
  open: boolean;
  /** Which org type to search. Defaults to all orgs if "organization". */
  orgType?: SearchableOrgType;
  /** Allow switching org type from within the dialog */
  allowTypeSwitch?: boolean;
  /** Called when a record is selected */
  onSelect: (org: OrgSearchResult) => void;
  /** Called when dialog is closed without selection */
  onClose: () => void;
  /** Optional title override */
  title?: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ORG_TYPE_OPTIONS: { value: SearchableOrgType; label: string }[] = [
  { value: "customer", label: "Customer" },
  { value: "vendor", label: "Vendor" },
  { value: "manufacturer", label: "Manufacturer" },
  { value: "rep", label: "Rep" },
  { value: "employee", label: "Employee" },
  { value: "organization", label: "All Orgs" },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function OrgSearchDialog({
  open,
  orgType = "customer",
  allowTypeSwitch = false,
  onSelect,
  onClose,
  title,
}: OrgSearchDialogProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeType, setActiveType] = useState<SearchableOrgType>(orgType);
  const [results, setResults] = useState<OrgSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const [highlightIndex, setHighlightIndex] = useState(-1);

  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Reset state when dialog opens/closes
  useEffect(() => {
    if (open) {
      setSearchQuery("");
      setResults([]);
      setHighlightIndex(-1);
      setActiveType(orgType);
      // Auto-focus input after a frame
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open, orgType]);

  // Debounced search
  useEffect(() => {
    if (!open) return;

    // Load initial list (empty search) or search results
    const timer = setTimeout(() => {
      performSearch(searchQuery, activeType);
    }, searchQuery ? 300 : 0);

    return () => clearTimeout(timer);
  }, [searchQuery, activeType, open]);

  const performSearch = useCallback(
    async (query: string, type: SearchableOrgType) => {
      setIsSearching(true);
      setHighlightIndex(-1);
      try {
        const params: Record<string, any> = {
          limit: 20,
          is_active: true,
        };
        if (query.trim()) {
          params.search = query.trim();
        }
        // "organization" queries orgbase (registered as "org" on backend)
        const modelName = type === "organization" ? "org" : type;
        const result = await getRecords(modelName, params);
        const records: any[] = result?.results || [];
        setResults(
          records.map((r: any) => ({
            id: r.id,
            display_name: r.display_name || r.company || r.name || `#${r.id}`,
            ida: r.ida,
            email: r.email,
            phone: r.phone,
            org_type: r.org_type,
            status: r.status,
            is_active: r.is_active,
            company: r.company,
            attention: r.attention,
          })),
        );
        setTotalCount(result?.total ?? records.length);
      } catch (err) {
        console.error("[OrgSearchDialog] Search failed:", err);
        setResults([]);
        setTotalCount(0);
      } finally {
        setIsSearching(false);
      }
    },
    [],
  );

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setHighlightIndex((prev) =>
          prev < results.length - 1 ? prev + 1 : prev,
        );
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setHighlightIndex((prev) => (prev > 0 ? prev - 1 : 0));
      } else if (e.key === "Enter" && highlightIndex >= 0) {
        e.preventDefault();
        onSelect(results[highlightIndex]);
      } else if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    },
    [results, highlightIndex, onSelect, onClose],
  );

  // Scroll highlighted row into view
  useEffect(() => {
    if (highlightIndex >= 0 && listRef.current) {
      const row = listRef.current.children[highlightIndex] as HTMLElement;
      row?.scrollIntoView({ block: "nearest" });
    }
  }, [highlightIndex]);

  // Close on backdrop click
  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if ((e.target as HTMLElement).dataset.backdrop) {
        onClose();
      }
    },
    [onClose],
  );

  if (!open) return null;

  const dialogTitle =
    title ||
    `Search ${activeType === "organization" ? "Organizations" : activeType.charAt(0).toUpperCase() + activeType.slice(1) + "s"}`;

  return (
    <div
      data-backdrop="true"
      onClick={handleBackdropClick}
      className="fixed inset-0 z-[9999] flex items-start justify-center pt-[10vh] bg-black/40 backdrop-blur-sm"
    >
      <div
        className="w-full max-w-2xl bg-white dark:bg-slate-900 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-700 flex flex-col max-h-[75vh]"
        onKeyDown={handleKeyDown}
      >
        {/* ─── Header ─── */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200 dark:border-slate-700">
          <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
            {dialogTitle}
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            title="Close"
          >
            <FaTimes size={14} />
          </button>
        </div>

        {/* ─── Search Bar + Type Selector ─── */}
        <div className="px-5 py-3 border-b border-slate-100 dark:border-slate-800 space-y-2">
          {allowTypeSwitch && (
            <div className="flex flex-wrap gap-1.5">
              {ORG_TYPE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setActiveType(opt.value)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-full transition-colors ${
                    activeType === opt.value
                      ? "bg-blue-600 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}
          <div className="relative">
            <FaSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              ref={inputRef}
              type="text"
              placeholder="Type to search by name, ID, email, phone…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-10 py-2.5 text-sm border border-slate-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
            />
            {isSearching && (
              <FaSpinner className="absolute right-3 top-1/2 -translate-y-1/2 text-blue-500 animate-spin" />
            )}
            {!isSearching && searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <FaTimes size={12} />
              </button>
            )}
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {isSearching
              ? "Searching…"
              : `${totalCount} record${totalCount !== 1 ? "s" : ""} found`}
          </p>
        </div>

        {/* ─── Results Table ─── */}
        <div ref={listRef} className="flex-1 overflow-y-auto">
          {results.length === 0 && !isSearching ? (
            <div className="flex items-center justify-center h-32 text-sm text-slate-400">
              {searchQuery
                ? "No records match your search"
                : "Enter a search term or browse records"}
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-slate-50 dark:bg-slate-800 z-10">
                <tr className="text-left text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  <th className="px-5 py-2 font-medium">Name</th>
                  <th className="px-3 py-2 font-medium">ID</th>
                  {allowTypeSwitch && (
                    <th className="px-3 py-2 font-medium">Type</th>
                  )}
                  <th className="px-3 py-2 font-medium">Email</th>
                  <th className="px-3 py-2 font-medium">Phone</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {results.map((org, idx) => (
                  <tr
                    key={org.id}
                    onClick={() => onSelect(org)}
                    onMouseEnter={() => setHighlightIndex(idx)}
                    className={`cursor-pointer border-b border-slate-100 dark:border-slate-800 transition-colors ${
                      idx === highlightIndex
                        ? "bg-blue-50 dark:bg-blue-900/20"
                        : "hover:bg-slate-50 dark:hover:bg-slate-800/60"
                    }`}
                  >
                    <td className="px-5 py-2.5 font-medium text-slate-900 dark:text-slate-100 truncate max-w-[200px]">
                      {org.display_name}
                    </td>
                    <td className="px-3 py-2.5 text-slate-500 dark:text-slate-400 font-mono text-xs">
                      {org.ida || org.id}
                    </td>
                    {allowTypeSwitch && (
                      <td className="px-3 py-2.5">
                        <span className="inline-flex px-2 py-0.5 text-xs font-medium rounded-full bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300 capitalize">
                          {org.org_type || "—"}
                        </span>
                      </td>
                    )}
                    <td className="px-3 py-2.5 text-slate-500 dark:text-slate-400 truncate max-w-[160px]">
                      {org.email || "—"}
                    </td>
                    <td className="px-3 py-2.5 text-slate-500 dark:text-slate-400">
                      {org.phone || "—"}
                    </td>
                    <td className="px-3 py-2.5">
                      <span
                        className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full ${
                          org.status === "active"
                            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                            : org.status === "prospect"
                              ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                              : "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300"
                        } capitalize`}
                      >
                        {org.status || "—"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* ─── Footer ─── */}
        <div className="px-5 py-3 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <p className="text-xs text-slate-400">
            ↑↓ Navigate &nbsp; ↵ Select &nbsp; Esc Close
          </p>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 text-sm font-medium text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
