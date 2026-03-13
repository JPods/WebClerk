/**
 * SerialPanel - Displays serial numbers linked to an entity
 *
 * Shows serial records associated with an item, transaction, or org.
 * Each row links to its serial detail page.
 *
 * @see readmes/tab-navigation.md — Tier 2 Org Tabs
 */
import React, { useEffect, useMemo, useState } from "react";
import {
  FaBarcode,
  FaChevronDown,
  FaChevronUp,
  FaSpinner,
} from "react-icons/fa";
import { useWindowManager } from "@/context/WindowManagerContext";
import { getRecords } from "@/api/wcapi";
import { usePermissions } from "./usePermissions";
import { getModelDetailPath, getModelWindowTitle } from "./getModelDetailPath";
import type { EntityType, UserRole } from "./types";
import { ALL_ROLES, USER_ROLES } from "./types";
import { withDevIdentifier } from '@/components/common/DevIdentifier';
import { PanelTable } from "./PanelTable";
import type { PanelColumnDef } from "./PanelTable";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Serial record from the API */
export interface SerialRecord {
  id: number;
  ida?: string;
  serial_number?: string;
  item_id?: number;
  item_name?: string;
  status?: string;
  location?: string;
  condition?: string;
  notes?: string;
  dt_created?: number;
  dt_modified?: number;
  [key: string]: unknown;
}

export interface SerialPanelProps {
  /** Entity type of the parent record */
  entityType: EntityType;
  /** ID of the parent record */
  entityId: number;
  /** Pre-loaded serial data (skips fetch when provided) */
  data?: SerialRecord[];
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

const formatDate = (ts?: number) => {
  if (!ts) return "—";
  const d = new Date(ts * 1000);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleDateString();
};

/** Map parent entity type to the filter field used in the serial query */
const getFilterField = (entityType: EntityType): string => {
  switch (entityType) {
    case "item":
      return "item_id";
    case "customer":
      return "customer_id";
    case "vendor":
      return "vendor_id";
    case "order":
      return "order_id";
    case "invoice":
      return "invoice_id";
    case "purchase":
      return "purchase_id";
    default:
      return "parent_id";
  }
};

const STATUS_COLORS: Record<string, string> = {
  active: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  inactive: "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300",
  sold: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  returned: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  defective: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const SerialPanel: React.FC<SerialPanelProps> = ({
  entityType,
  entityId,
  data: preloaded,
  viewRoles = ALL_ROLES,
  editRoles = USER_ROLES,
  className = "",
  compact = false,
  title = "Serials",
  defaultCollapsed = false,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [serials, setSerials] = useState<SerialRecord[]>(preloaded ?? []);
  const [loading, setLoading] = useState(!preloaded);

  const windowManager = useWindowManager();

  const { canView } = usePermissions({
    panelType: "serials",
    viewRoles,
    editRoles,
    forceReadOnly: true,
  });

  // Fetch serials if not preloaded
  useEffect(() => {
    if (preloaded || !entityId) return;
    let cancelled = false;
    setLoading(true);

    const filterField = getFilterField(entityType);

    getRecords("serial", { [filterField]: entityId, limit: 200 })
      .then((result: any) => {
        if (!cancelled) {
          setSerials(result?.results ?? []);
        }
      })
      .catch(() => {
        if (!cancelled) setSerials([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [entityType, entityId, preloaded]);

  // Sync with preloaded data when it changes
  useEffect(() => {
    if (preloaded) {
      setSerials(preloaded);
      setLoading(false);
    }
  }, [preloaded]);

  if (canView === false) return null;

  const handleClick = (serial: SerialRecord) => {
    const path = getModelDetailPath("serial", serial.id);
    const title = getModelWindowTitle("serial", serial.id, serial.ida, serial.serial_number);
    windowManager.ensureWindow(path, title, { maximized: false });
  };

  // Column definitions for serial rows
  const serialColumns = useMemo<PanelColumnDef<SerialRecord>[]>(() => [
    { key: "serial_number", label: "serial_number", cellClassName: "font-mono text-slate-500 dark:text-slate-400 shrink-0 w-[120px]",
      render: (r) => r.serial_number ?? r.ida ?? `#${r.id}` },
    { key: "item_name", label: "item_name", cellClassName: "text-slate-800 dark:text-slate-200 min-w-[120px] flex-1",
      render: (r) => r.item_name ?? "\u2014" },
    { key: "status", label: "status", cellClassName: "w-[80px]",
      render: (r) => r.status ? (
        <span className={`px-1.5 py-0.5 rounded text-xs ${
          STATUS_COLORS[r.status.toLowerCase()] ??
          "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300"
        }`}>{r.status}</span>
      ) : "\u2014" },
    { key: "location", label: "location", cellClassName: "text-slate-500 dark:text-slate-400 w-[100px]",
      render: (r) => r.location ?? "\u2014" },
    { key: "condition", label: "condition", defaultVisible: false, cellClassName: "text-slate-500 dark:text-slate-400 w-[80px]",
      render: (r) => r.condition ?? "\u2014" },
    { key: "dt_created", label: "dt_created", cellClassName: "text-slate-400 w-[80px]",
      render: (r) => formatDate(r.dt_created) },
    { key: "dt_modified", label: "dt_modified", defaultVisible: false, cellClassName: "text-slate-400 w-[80px]",
      render: (r) => formatDate(r.dt_modified) },
  ], []);

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
          <FaBarcode className="text-slate-400" size={14} />
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
            {title}
          </h3>
          {serials.length > 0 && (
            <span className="px-1.5 py-0.5 text-xs bg-slate-200 dark:bg-slate-600 rounded-full">
              {serials.length}
            </span>
          )}
        </div>
        {isCollapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
      </div>

      {!isCollapsed && (
        <div className={compact ? "p-2" : "p-4"}>
          {loading ? (
            <div className="flex items-center justify-center py-8 text-slate-400">
              <FaSpinner className="animate-spin mr-2" /> Loading…
            </div>
          ) : serials.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-6">
              No serials found.
            </p>
          ) : (
            <div className="border border-slate-200 dark:border-slate-700 rounded-md overflow-hidden">
              <PanelTable<SerialRecord>
                storageKey="panel:serials"
                columns={serialColumns}
                data={serials}
                rowKey={(r) => r.id}
                onRowAction={handleClick}
                compact={compact}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default withDevIdentifier(SerialPanel, 'SerialPanel', 'teal');