/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
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
import { formatDt } from '@/utils/fieldFormatters';
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
  return formatDt(ts, 'date');
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

const STATUS_STYLES: Record<string, React.CSSProperties> = {
  active: { background: 'var(--db-surface-alt)', color: 'var(--db-text)' },
  inactive: { background: 'var(--db-surface-alt)', color: 'var(--db-text-dim)' },
  sold: { background: 'var(--db-surface-alt)', color: 'var(--db-accent)' },
  returned: { background: 'var(--db-surface-alt)', color: 'var(--db-text-muted)' },
  defective: { background: 'var(--db-surface-alt)', color: 'var(--db-text)' },
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
    { key: "serial_number", label: "serial_number", cellClassName: "font-mono shrink-0 w-[120px]",
      cellStyle: { color: 'var(--db-text-muted)' },
      render: (r) => r.serial_number ?? r.ida ?? `#${r.id}` },
    { key: "item_name", label: "item_name", cellClassName: "min-w-[120px] flex-1",
      cellStyle: { color: 'var(--db-text)' },
      render: (r) => r.item_name ?? "\u2014" },
    { key: "status", label: "status", cellClassName: "w-[80px]",
      render: (r) => r.status ? (
        <span className="px-1.5 py-0.5 rounded text-xs"
          style={STATUS_STYLES[r.status.toLowerCase()] ?? { background: 'var(--db-surface-alt)', color: 'var(--db-text-dim)' }}
        >{r.status}</span>
      ) : "\u2014" },
    { key: "location", label: "location", cellClassName: "w-[100px]",
      cellStyle: { color: 'var(--db-text-muted)' },
      render: (r) => r.location ?? "\u2014" },
    { key: "condition", label: "condition", defaultVisible: false, cellClassName: "w-[80px]",
      cellStyle: { color: 'var(--db-text-muted)' },
      render: (r) => r.condition ?? "\u2014" },
    { key: "dt_created", label: "dt_created", cellClassName: "w-[80px]",
      cellStyle: { color: 'var(--db-text-dim)' },
      render: (r) => formatDate(r.dt_created) },
    { key: "dt_modified", label: "dt_modified", defaultVisible: false, cellClassName: "w-[80px]",
      cellStyle: { color: 'var(--db-text-dim)' },
      render: (r) => formatDate(r.dt_modified) },
  ], []);

  return (
    <div
      className={`rounded-lg border ${className}`}
      style={{ background: 'var(--db-surface)', borderColor: 'var(--db-border)' }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b cursor-pointer"
        style={{ borderColor: 'var(--db-border)' }}
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaBarcode style={{ color: 'var(--db-text-dim)' }} size={14} />
          <h3 className="text-sm font-semibold" style={{ color: 'var(--db-text)' }}>
            {title}
          </h3>
          {serials.length > 0 && (
            <span className="px-1.5 py-0.5 text-xs rounded-full" style={{ background: 'var(--db-surface-alt)' }}>
              {serials.length}
            </span>
          )}
        </div>
        {isCollapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
      </div>

      {!isCollapsed && (
        <div className={compact ? "p-2" : "p-4"}>
          {loading ? (
            <div className="flex items-center justify-center py-8" style={{ color: 'var(--db-text-dim)' }}>
              <FaSpinner className="animate-spin mr-2" /> Loading…
            </div>
          ) : serials.length === 0 ? (
            <p className="text-sm text-center py-6" style={{ color: 'var(--db-text-dim)' }}>
              No serials found.
            </p>
          ) : (
            <div className="border rounded-md overflow-hidden" style={{ borderColor: 'var(--db-border)' }}>
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

export default withDevIdentifier(SerialPanel, 'SerialPanel', 'teal', 'apps/common/components/panels/SerialPanel.tsx');