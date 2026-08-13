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
import { getModelNames, getRecords } from "@/api/wcapi";
import { usePermissions } from "./usePermissions";
import { getModelDetailPath, getModelWindowTitle } from "./getModelDetailPath";
import type { UserRole } from "./types";
import { ALL_ROLES, USER_ROLES } from "./types";
import { withDevIdentifier } from "@/components/common/DevIdentifier";
import { PanelTable } from "./PanelTable";
import type { PanelColumnDef } from "./PanelTable";
import { formatDt } from '@/utils/fieldFormatters';

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
  return formatDt(ts, 'date');
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
  const [canFetchLines, setCanFetchLines] = useState<boolean | null>(null);

  const windowManager = useWindowManager();

  const { canView } = usePermissions({
    panelType: "items",
    viewRoles,
    editRoles,
    forceReadOnly: true,
  });

  const filterField = orgType === "customer" ? "customer_id" : "vendor_id";

  // Discover if the backend exposes the generic "line" model to avoid 400s
  useEffect(() => {
    let cancelled = false;
    getModelNames()
      .then((payload) => {
        if (cancelled) return;
        const names = payload?.model_names || [];
        setCanFetchLines(names.includes("line"));
      })
      .catch(() => {
        if (!cancelled) setCanFetchLines(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Column definitions for line items
  const lineColumns = useMemo<PanelColumnDef<LineItemRecord>[]>(
    () => [
      {
        key: "ida",
        label: "ida",
        cellClassName: "font-mono shrink-0 w-[70px]",
        render: (r) => <span style={{ color: 'var(--db-text-muted)' }}>{r.item_ida ?? r.ida ?? `#${r.id}`}</span>,
      },
      {
        key: "item_name",
        label: "item_name",
        cellClassName: "min-w-[120px] flex-1",
        render: (r) => <span style={{ color: 'var(--db-text)' }}>{r.item_name ?? r.description ?? "—"}</span>,
      },
      {
        key: "description",
        label: "description",
        defaultVisible: false,
        cellClassName: "min-w-[100px] flex-1",
        render: (r) => <span style={{ color: 'var(--db-text-muted)' }}>{r.description && r.description !== r.item_name ? r.description : "—"}</span>,
      },
      {
        key: "quantity",
        label: "qty",
        cellClassName: "w-[60px] text-right",
        render: (r) => <span style={{ color: 'var(--db-text)' }}>{formatQty(r.quantity)}</span>,
      },
      {
        key: "unit_price",
        label: "unit_price",
        cellClassName: "w-[80px] text-right",
        render: (r) => <span style={{ color: 'var(--db-text)' }}>{formatCurrency(r.unit_price, r.currency)}</span>,
      },
      {
        key: "total",
        label: "total",
        cellClassName: "font-medium w-[80px] text-right",
        render: (r) => <span style={{ color: 'var(--db-text)' }}>{formatCurrency(r.total, r.currency)}</span>,
      },
      {
        key: "status",
        label: "status",
        defaultVisible: false,
        cellClassName: "w-[70px]",
        render: (r) =>
          r.status ? (
            <span className="px-1.5 py-0.5 rounded" style={{ background: 'var(--db-surface-alt)', color: 'var(--db-text)' }}>
              {String(r.status)}
            </span>
          ) : (
            "—"
          ),
      },
      {
        key: "source_ida",
        label: "source",
        cellClassName: "font-mono w-[70px]",
        render: (r) => <span style={{ color: 'var(--db-text-dim)' }}>{r.source_ida ?? "—"}</span>,
      },
    ],
    [],
  );

  // Column definitions for serials
  const serialColumns = useMemo<PanelColumnDef<SerialRecord>[]>(
    () => [
      {
        key: "serial_number",
        label: "serial",
        cellClassName: "font-mono shrink-0 w-[100px]",
        render: (r) => <span style={{ color: 'var(--db-text-muted)' }}>{r.serial_number ?? r.ida ?? `#${r.id}`}</span>,
      },
      {
        key: "item_name",
        label: "item_name",
        cellClassName: "min-w-[120px] flex-1",
        render: (r) => <span style={{ color: 'var(--db-text)' }}>{r.item_name ?? "—"}</span>,
      },
      {
        key: "status",
        label: "status",
        cellClassName: "w-[80px]",
        render: (r) =>
          r.status ? (
            <span className="px-1.5 py-0.5 rounded" style={{ background: 'var(--db-surface-alt)', color: 'var(--db-text)' }}>
              {r.status}
            </span>
          ) : (
            "—"
          ),
      },
      {
        key: "location",
        label: "location",
        cellClassName: "w-[100px]",
        render: (r) => <span style={{ color: 'var(--db-text-muted)' }}>{r.location ?? "—"}</span>,
      },
      {
        key: "dt_created",
        label: "dt_created",
        defaultVisible: false,
        cellClassName: "w-[80px]",
        render: (r) => <span style={{ color: 'var(--db-text-dim)' }}>{formatDate(r.dt_created)}</span>,
      },
    ],
    [],
  );

  // Fetch lines and serials in parallel (skip lines if model is unavailable)
  useEffect(() => {
    if (!orgId || canFetchLines === null) return;
    let cancelled = false;
    setLoading(true);

    const linePromise = canFetchLines
      ? getRecords("line", { [filterField]: orgId, limit: 200 }).catch(() => ({
          results: [],
        }))
      : Promise.resolve({ results: [] });

    Promise.all([
      linePromise,
      getRecords("serial", { [filterField]: orgId, limit: 200 }).catch(() => ({
        results: [],
      })),
    ]).then(([lineResult, serialResult]) => {
      if (cancelled) return;
      setLines((lineResult as any)?.results ?? []);
      setSerials((serialResult as any)?.results ?? []);
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [orgId, filterField, canFetchLines]);

  if (canView === false) return null;

  const totalLines = lines.length;
  const totalSerials = serials.length;
  const totalCount = totalLines + totalSerials;

  const handleItemClick = (line: LineItemRecord) => {
    if (!line.item_id) return;
    const path = getModelDetailPath("item", line.item_id);
    const title = getModelWindowTitle(
      "item",
      line.item_id,
      line.item_ida,
      line.item_name,
    );
    windowManager.ensureWindow(path, title, { maximized: false });
  };

  const handleSerialClick = (serial: SerialRecord) => {
    const path = getModelDetailPath("serial", serial.id);
    const title = getModelWindowTitle(
      "serial",
      serial.id,
      serial.ida,
      serial.serial_number,
    );
    windowManager.ensureWindow(path, title, { maximized: false });
  };

  return (
    <div
      className={`rounded-lg ${className}`}
      style={{ background: 'var(--db-surface)', border: '1px solid var(--db-border)' }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer"
        style={{ borderBottom: '1px solid var(--db-border)' }}
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaBoxes style={{ color: 'var(--db-text-dim)' }} size={14} />
          <h3 className="text-sm font-semibold" style={{ color: 'var(--db-text)' }}>
            {title}
          </h3>
          {totalCount > 0 && (
            <span className="px-1.5 py-0.5 text-xs rounded-full" style={{ background: 'var(--db-surface-alt)', color: 'var(--db-text)' }}>
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
            <FaFilter style={{ color: 'var(--db-text-dim)' }} size={10} />
            <button
              type="button"
              onClick={() => setViewMode("lines")}
              className="px-2 py-1 text-xs rounded"
              style={{
                background: viewMode === "lines" ? 'var(--db-row-active)' : 'var(--db-surface-alt)',
                color: viewMode === "lines" ? 'var(--db-accent)' : 'var(--db-text)',
              }}
            >
              Line Items ({totalLines})
            </button>
            <button
              type="button"
              onClick={() => setViewMode("serials")}
              className="px-2 py-1 text-xs rounded"
              style={{
                background: viewMode === "serials" ? 'var(--db-row-active)' : 'var(--db-surface-alt)',
                color: viewMode === "serials" ? 'var(--db-accent)' : 'var(--db-text)',
              }}
            >
              Serials ({totalSerials})
            </button>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-8" style={{ color: 'var(--db-text-dim)' }}>
              <FaSpinner className="animate-spin mr-2" /> Loading…
            </div>
          ) : viewMode === "lines" ? (
            totalLines === 0 ? (
              <p className="text-sm text-center py-6" style={{ color: 'var(--db-text-dim)' }}>
                No line items found.
              </p>
            ) : (
              <div className="rounded-md overflow-hidden" style={{ border: '1px solid var(--db-border)' }}>
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
          ) : totalSerials === 0 ? (
            <p className="text-sm text-center py-6" style={{ color: 'var(--db-text-dim)' }}>
              No serials found.
            </p>
          ) : (
            <div className="rounded-md overflow-hidden" style={{ border: '1px solid var(--db-border)' }}>
              <PanelTable<SerialRecord>
                storageKey="panel:items:serials"
                columns={serialColumns}
                data={serials}
                rowKey={(r) => r.id}
                onRowAction={(r) => handleSerialClick(r)}
                compact={compact}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default withDevIdentifier(ItemsPanel, "ItemsPanel", "teal", 'apps/common/components/panels/ItemsPanel.tsx');
