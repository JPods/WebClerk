/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * TransactionsPanel - Displays transactions for an org (Customer or Vendor)
 *
 * Customer sub-tables: proposals, orders, invoices, ledgers, payments
 * Vendor sub-tables:   purchases, receipts
 *
 * Fetches records via wcapi getRecords filtered by parent org ID.
 * Each row links to its transaction detail page.
 *
 * @see readmes/tab-navigation.md — Tier 2 Org Tabs
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  FaChevronDown,
  FaChevronUp,
  FaExchangeAlt,
  FaFilter,
  FaSpinner,
} from "react-icons/fa";
import { useWindowManager } from "@/context/WindowManagerContext";
import { getRecords } from "@/api/wcapi";
import { usePermissions } from "./usePermissions";
import { getModelDetailPath, getModelWindowTitle } from "./getModelDetailPath";
import type { UserRole } from "./types";
import { ALL_ROLES, USER_ROLES } from "./types";
import { withDevIdentifier } from "@/components/common/DevIdentifier";
import { PanelTable } from "./PanelTable";
import type { PanelColumnDef } from "./PanelTable";
import { formatDt } from '@/utils/fieldFormatters';
import { formatCurrency } from '@/utils/stringUtils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Org type determines which sub-tables to display */
export type OrgType = "customer" | "vendor";

/** Minimal transaction record returned from the API */
export interface TransactionRecord {
  id: number;
  ida?: string;
  name?: string;
  status?: string;
  total?: number;
  currency?: string;
  dt_created?: number;
  dt_modified?: number;
  [key: string]: unknown;
}

/** Sub-table configuration */
interface SubTable {
  model: string;
  label: string;
  filterField: string;
}

export interface TransactionsPanelProps {
  /** The org type — determines which sub-tables are shown */
  orgType: OrgType;
  /** Parent org ID to filter transactions */
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
// Sub-table definitions by org type
// ---------------------------------------------------------------------------

const CUSTOMER_TABLES: SubTable[] = [
  { model: "proposal", label: "Proposals", filterField: "customer" },
  { model: "order", label: "Orders", filterField: "customer" },
  { model: "invoice", label: "Invoices", filterField: "customer" },
  { model: "ledger", label: "Ledgers", filterField: "customer" },
  { model: "payment", label: "Payments", filterField: "customer" },
];

const VENDOR_TABLES: SubTable[] = [
  { model: "purchase", label: "Purchases", filterField: "vendor" },
  { model: "receipt", label: "Receipts", filterField: "vendor" },
];

const SUB_TABLES: Record<OrgType, SubTable[]> = {
  customer: CUSTOMER_TABLES,
  vendor: VENDOR_TABLES,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const formatDate = (ts?: number) => {
  if (!ts) return "—";
  return formatDt(ts, 'date');
};


// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const TransactionsPanel: React.FC<TransactionsPanelProps> = ({
  orgType,
  orgId,
  viewRoles = ALL_ROLES,
  editRoles = USER_ROLES,
  className = "",
  compact = false,
  title = "Transactions",
  defaultCollapsed = false,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(defaultCollapsed);
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  const [data, setData] = useState<Record<string, TransactionRecord[]>>({});
  const [loading, setLoading] = useState(true);
  const inflightRequests = useRef<
    Map<string, Promise<Record<string, TransactionRecord[]>>>
  >(new Map());

  const windowManager = useWindowManager();

  const { canView } = usePermissions({
    panelType: "transactions",
    viewRoles,
    editRoles,
    forceReadOnly: true,
  });

  const tables = useMemo(() => SUB_TABLES[orgType] ?? [], [orgType]);

  // Column definitions for transaction rows
  const txnColumns = useMemo<PanelColumnDef<TransactionRecord>[]>(
    () => [
      {
        key: "ida",
        label: "ida",
        cellClassName: "font-mono shrink-0 w-[70px]",
        cellStyle: { color: 'var(--db-text-muted)' },
        render: (r) => r.ida ?? `#${r.id}`,
      },
      {
        key: "name",
        label: "name",
        cellClassName: "min-w-[120px] flex-1",
        cellStyle: { color: 'var(--db-text)' },
        render: (r) => r.name ?? "\u2014",
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
            "\u2014"
          ),
      },
      {
        key: "total",
        label: "total",
        cellClassName: "w-[90px] text-right",
        cellStyle: { color: 'var(--db-text)' },
        render: (r) => formatCurrency(r.totals?.total),
      },
      {
        key: "dt_created",
        label: "dt_created",
        cellClassName: "w-[80px]",
        cellStyle: { color: 'var(--db-text-dim)' },
        render: (r) => formatDate(r.dt_created),
      },
      {
        key: "dt_modified",
        label: "dt_modified",
        defaultVisible: false,
        cellClassName: "w-[80px]",
        cellStyle: { color: 'var(--db-text-dim)' },
        render: (r) => formatDate(r.dt_modified),
      },
    ],
    [],
  );

  // Fetch all sub-tables in parallel
  useEffect(() => {
    if (!orgId) return;
    const cacheKey = `${orgType}-${orgId}`;
    let cancelled = false;
    setLoading(true);

    const executeFetch = async (): Promise<
      Record<string, TransactionRecord[]>
    > => {
      const results = await Promise.all(
        tables.map(async (t) => {
          try {
            const result = await getRecords(t.model, {
              [t.filterField]: orgId,
              limit: 100,
            });
            return { model: t.model, records: result?.results ?? [] };
          } catch {
            return { model: t.model, records: [] };
          }
        }),
      );

      const map: Record<string, TransactionRecord[]> = {};
      results.forEach((r) => {
        map[r.model] = r.records;
      });
      return map;
    };

    const existingRequest = inflightRequests.current.get(cacheKey);
    const request = existingRequest ?? executeFetch();
    inflightRequests.current.set(cacheKey, request);

    request
      .then((map) => {
        if (cancelled) return;
        setData(map);
      })
      .catch(() => {
        if (cancelled) return;
        setData({});
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
        if (inflightRequests.current.get(cacheKey) === request) {
          inflightRequests.current.delete(cacheKey);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [orgId, orgType, tables]);

  if (canView === false) return null;

  const filteredTables = activeFilter
    ? tables.filter((t) => t.model === activeFilter)
    : tables;

  const totalCount = tables.reduce(
    (sum, t) => sum + (data[t.model]?.length ?? 0),
    0,
  );

  const handleRowClick = (model: string, rec: TransactionRecord) => {
    const path = getModelDetailPath(model, rec.id);
    const title = getModelWindowTitle(model, rec.id, rec.ida, rec.name);
    windowManager.ensureWindow(path, title, { maximized: false });
  };

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
          <FaExchangeAlt style={{ color: 'var(--db-text-dim)' }} size={14} />
          <h3 className="text-sm font-semibold" style={{ color: 'var(--db-text)' }}>
            {title}
          </h3>
          {totalCount > 0 && (
            <span className="px-1.5 py-0.5 text-xs rounded-full" style={{ background: 'var(--db-surface-alt)' }}>
              {totalCount}
            </span>
          )}
        </div>
        {isCollapsed ? <FaChevronDown size={12} /> : <FaChevronUp size={12} />}
      </div>

      {!isCollapsed && (
        <div className={compact ? "p-2" : "p-4"}>
          {/* Filters */}
          {tables.length > 1 && (
            <div className="flex items-center gap-2 mb-3 flex-wrap">
              <FaFilter style={{ color: 'var(--db-text-dim)' }} size={10} />
              <button
                type="button"
                onClick={() => setActiveFilter(null)}
                className="px-2 py-1 text-xs rounded"
                style={activeFilter === null
                  ? { background: 'var(--db-row-active)', color: 'var(--db-accent)' }
                  : { background: 'var(--db-surface-alt)', color: 'var(--db-text)' }
                }
              >
                All
              </button>
              {tables.map((t) => (
                <button
                  key={t.model}
                  type="button"
                  onClick={() =>
                    setActiveFilter(activeFilter === t.model ? null : t.model)
                  }
                  className="px-2 py-1 text-xs rounded"
                  style={activeFilter === t.model
                    ? { background: 'var(--db-row-active)', color: 'var(--db-accent)' }
                    : { background: 'var(--db-surface-alt)', color: 'var(--db-text)' }
                  }
                >
                  {t.label} ({data[t.model]?.length ?? 0})
                </button>
              ))}
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-8" style={{ color: 'var(--db-text-dim)' }}>
              <FaSpinner className="animate-spin mr-2" /> Loading…
            </div>
          ) : totalCount === 0 ? (
            <p className="text-sm text-center py-6" style={{ color: 'var(--db-text-dim)' }}>
              No transactions found.
            </p>
          ) : (
            <div className="space-y-4">
              {filteredTables.map((t) => {
                const records = data[t.model] ?? [];
                if (records.length === 0) return null;
                return (
                  <div key={t.model}>
                    <h4 className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--db-text-muted)' }}>
                      {t.label}
                    </h4>
                    <div className="border rounded-md overflow-hidden" style={{ borderColor: 'var(--db-border)' }}>
                      <PanelTable<TransactionRecord>
                        storageKey={`panel:transactions:${t.model}`}
                        columns={txnColumns}
                        data={records}
                        rowKey={(r) => r.id}
                        onRowAction={(r) => handleRowClick(t.model, r)}
                        compact={compact}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default withDevIdentifier(
  TransactionsPanel,
  "TransactionsPanel",
  "teal",
  'apps/common/components/panels/TransactionsPanel.tsx',
);
