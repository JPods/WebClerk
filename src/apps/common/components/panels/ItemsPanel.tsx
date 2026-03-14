/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * ItemsPanel - Displays line items from an org's transactions plus linked serials
 *
 * Provides a consolidated view of every product the org has interacted with.
 * Aggregates data from transaction lines and serial records linked to the org.
 *
 * @see readmes/tab-navigation.md — Tier 2 Org Tabs
 */
import React, { useEffect, useMemo, useState } from "react";
import {
  FaBoxes,
  FaChevronDown,
  FaChevronUp,
  FaFilter,
  FaSpinner,
} from "react-icons/fa";
import { useWindowManager } from "@/context/WindowManagerContext";
import { getRecords } from "@/api/wcapi";
import { usePermissions } from "./usePermissions";
import { getModelDetailPath, getModelWindowTitle } from "./getModelDetailPath";
import type { UserRole } from "./types";
import { ALL_ROLES, USER_ROLES } from "./types";
import { withDevIdentifier } from '@/components/common/DevIdentifier';
import { PanelTable } from "./PanelTable";
import type { PanelColumnDef } from "./PanelTable";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type OrgType = "customer" | "vendor";

/** A line item record from a transaction */
export interface LineItemRecord {
  id: number;
  ida?: string;
  item_id?: number;
  item_name?: string;
  item_ida?: string;
  description?: string;
  quantity?: number;
  unit_price?: number;
  total?: number;
  currency?: string;
  source_model?: string;
  source_id?: number;
  source_ida?: string;
  [key: string]: unknown;
}

/** A serial record linked to the org */
export interface SerialRecord {
  id: number;
  ida?: string;
  serial_number?: string;
  item_id?: number;
  item_name?: string;
  status?: string;
  location?: string;
  dt_created?: number;
  [key: string]: unknown;
}

type ViewMode = "lines" | "serials";

export interface ItemsPanelProps {
  /** The org type */
  orgType: OrgType;
  /** Parent org ID */
  orgId: number;
  /** Override default view roles */
  viewRoles?: UserRole[];
  /** Override default edit roles */
  editRoles?: UserRole[];
  /** Additional CSS classes */
  className?: string;
  /** Compact display mode */
  compact?: boolean;
  /** Title override */
  title?: string;
  /** Whether panel is initially collapsed */
  defaultCollapsed?: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const formatCurrency = (value?: number, currency?: string) => {
  if (value == null) return "—";
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency || "USD",
    }).format(value);
  } catch {
    return `${currency || "$"}${value.toFixed(2)}`;
  }
};

const formatQty = (value?: number) =>
  value != null ? value.toLocaleString() : "—";

const formatDate = (ts?: number) => {
  if (!ts) return "—";
  const d = new Date(ts * 1000);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleDateString();
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const ItemsPanel: React.FC<ItemsPanelProps> = ({
  orgType,
  orgId,
  viewRoles = ALL_ROLES,
  editRoles = USER_ROLES,
  className = "",
  compact = false,
  title = "Items",
  defaultCollapsed = false,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [viewMode, setViewMode] = useState<ViewMode>("lines");
  const [lines, setLines] = useState<LineItemRecord[]>([]);
  const [serials, setSerials] = useState<SerialRecord[]>([]);
  const [loading, setLoading] = useState(true);

  const windowManager = useWindowManager();

  const { canView } = usePermissions({
    panelType: "items",
    viewRoles,
    editRoles,
    forceReadOnly: true,
  });

  const filterField =
    orgType === "customer" ? "customer_id" : "vendor_id";

  // Column definitions for line items
  const lineColumns = useMemo<PanelColumnDef<LineItemRecord>[]>(() => [
    { key: "ida", label: "ida", cellClassName: "font-mono text-slate-500 dark:text-slate-400 shrink-0 w-[70px]",
      render: (r) => r.item_ida ?? r.ida ?? `#${r.id}` },
    { key: "item_name", label: "item_name", cellClassName: "text-slate-800 dark:text-slate-200 min-w-[120px] flex-1",
      render: (r) => r.item_name ?? r.description ?? "—" },
    { key: "description", label: "description", defaultVisible: false, cellClassName: "text-slate-500 dark:text-slate-400 min-w-[100px] flex-1",
      render: (r) => (r.description && r.description !== r.item_name ? r.description : "—") },
    { key: "quantity", label: "qty", cellClassName: "text-slate-600 dark:text-slate-300 w-[60px] text-right",
      render: (r) => formatQty(r.quantity) },
    { key: "unit_price", label: "unit_price", cellClassName: "text-slate-600 dark:text-slate-300 w-[80px] text-right",
      render: (r) => formatCurrency(r.unit_price, r.currency) },
    { key: "total", label: "total", cellClassName: "font-medium text-slate-700 dark:text-slate-200 w-[80px] text-right",
      render: (r) => formatCurrency(r.total, r.currency) },
    { key: "status", label: "status", defaultVisible: false, cellClassName: "w-[70px]",
      render: (r) => r.status ? <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-600 text-slate-600 dark:text-slate-300">{String(r.status)}</span> : "—" },
    { key: "source_ida", label: "source", cellClassName: "text-slate-400 font-mono w-[70px]",
      render: (r) => r.source_ida ?? "—" },
  ], []);

  // Column definitions for serials
  const serialColumns = useMemo<PanelColumnDef<SerialRecord>[]>(() => [
    { key: "serial_number", label: "serial", cellClassName: "font-mono text-slate-500 dark:text-slate-400 shrink-0 w-[100px]",
      render: (r) => r.serial_number ?? r.ida ?? `#${r.id}` },
    { key: "item_name", label: "item_name", cellClassName: "text-slate-800 dark:text-slate-200 min-w-[120px] flex-1",
      render: (r) => r.item_name ?? "—" },
    { key: "status", label: "status", cellClassName: "w-[80px]",
      render: (r) => r.status ? <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-600 text-slate-600 dark:text-slate-300">{r.status}</span> : "—" },
    { key: "location", label: "location", cellClassName: "text-slate-500 dark:text-slate-400 w-[100px]",
      render: (r) => r.location ?? "—" },
    { key: "dt_created", label: "dt_created", defaultVisible: false, cellClassName: "text-slate-400 w-[80px]",
      render: (r) => formatDate(r.dt_created) },
  ], []);

  // Fetch lines and serials in parallel
  useEffect(() => {
    if (!orgId) return;
    let cancelled = false;
    setLoading(true);

    Promise.all([
      getRecords("line", { [filterField]: orgId, limit: 200 }).catch(
        () => ({ results: [] })
      ),
      getRecords("serial", { [filterField]: orgId, limit: 200 }).catch(
        () => ({ results: [] })
      ),
    ]).then(([lineResult, serialResult]) => {
      if (cancelled) return;
      setLines((lineResult as any)?.results ?? []);
      setSerials((serialResult as any)?.results ?? []);
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [orgId, filterField]);

  if (canView === false) return null;

  const totalLines = lines.length;
  const totalSerials = serials.length;
  const totalCount = totalLines + totalSerials;

  const handleItemClick = (line: LineItemRecord) => {
    if (!line.item_id) return;
    const path = getModelDetailPath("item", line.item_id);
    const title = getModelWindowTitle("item", line.item_id, line.item_ida, line.item_name);
    windowManager.ensureWindow(path, title, { maximized: false });
  };

  const handleSerialClick = (serial: SerialRecord) => {
    const path = getModelDetailPath("serial", serial.id);
    const title = getModelWindowTitle("serial", serial.id, serial.ida, serial.serial_number);
    windowManager.ensureWindow(path, title, { maximized: false });
  };

  return (
    <div
      className={`bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 ${className}`}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700 cursor-pointer"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaBoxes className="text-slate-400" size={14} />
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
            {title}
          </h3>
          {totalCount > 0 && (
            <span className="px-1.5 py-0.5 text-xs bg-slate-200 dark:bg-slate-600 rounded-full">
              {totalCount}
            </span>
          )}
        </div>
        {isCollapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
      </div>

      {!isCollapsed && (
        <div className={compact ? "p-2" : "p-4"}>
          {/* View mode toggle */}
          <div className="flex items-center gap-2 mb-3">
            <FaFilter className="text-slate-400" size={10} />
            <button
              type="button"
              onClick={() => setViewMode("lines")}
              className={`px-2 py-1 text-xs rounded ${
                viewMode === "lines"
                  ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                  : "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300 hover:bg-slate-200"
              }`}
            >
              Line Items ({totalLines})
            </button>
            <button
              type="button"
              onClick={() => setViewMode("serials")}
              className={`px-2 py-1 text-xs rounded ${
                viewMode === "serials"
                  ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                  : "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300 hover:bg-slate-200"
              }`}
            >
              Serials ({totalSerials})
            </button>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-8 text-slate-400">
              <FaSpinner className="animate-spin mr-2" /> Loading…
            </div>
          ) : viewMode === "lines" ? (
            totalLines === 0 ? (
              <p className="text-sm text-slate-400 text-center py-6">
                No line items found.
              </p>
            ) : (
              <div className="border border-slate-200 dark:border-slate-700 rounded-md overflow-hidden">
                <PanelTable<LineItemRecord>
                  storageKey="panel:items:lines"
                  columns={lineColumns}
                  data={lines}
                  rowKey={(r) => r.id}
                  onRowAction={(r) => r.item_id && handleItemClick(r)}
                  compact={compact}
                />
              </div>
            )
          ) : (
            totalSerials === 0 ? (
              <p className="text-sm text-slate-400 text-center py-6">
                No serials found.
              </p>
            ) : (
              <div className="border border-slate-200 dark:border-slate-700 rounded-md overflow-hidden">
                <PanelTable<SerialRecord>
                  storageKey="panel:items:serials"
                  columns={serialColumns}
                  data={serials}
                  rowKey={(r) => r.id}
                  onRowAction={(r) => handleSerialClick(r)}
                  compact={compact}
                />
              </div>
            )
          )}
        </div>
      )}
    </div>
  );
};

export default withDevIdentifier(ItemsPanel, 'ItemsPanel', 'teal');