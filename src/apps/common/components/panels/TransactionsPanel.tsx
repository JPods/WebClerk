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
  const d = new Date(ts * 1000);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleDateString();
};

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
        cellClassName:
          "font-mono text-slate-500 dark:text-slate-400 shrink-0 w-[70px]",
        render: (r) => r.ida ?? `#${r.id}`,
      },
      {
        key: "name",
        label: "name",
        cellClassName:
          "text-slate-800 dark:text-slate-200 min-w-[120px] flex-1",
        render: (r) => r.name ?? "\u2014",
      },
      {
        key: "status",
        label: "status",
        cellClassName: "w-[80px]",
        render: (r) =>
          r.status ? (
            <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-600 text-slate-600 dark:text-slate-300">
              {r.status}
            </span>
          ) : (
            "\u2014"
          ),
      },
      {
        key: "total",
        label: "total",
        cellClassName: "text-slate-600 dark:text-slate-300 w-[90px] text-right",
        render: (r) => formatCurrency(r.total, r.currency),
      },
      {
        key: "dt_created",
        label: "dt_created",
        cellClassName: "text-slate-400 w-[80px]",
        render: (r) => formatDate(r.dt_created),
      },
      {
        key: "dt_modified",
        label: "dt_modified",
        defaultVisible: false,
        cellClassName: "text-slate-400 w-[80px]",
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
      className={`bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 ${className}`}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700 cursor-pointer"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <div className="flex items-center gap-2">
          <FaExchangeAlt className="text-slate-400" size={14} />
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
          {/* Filters */}
          {tables.length > 1 && (
            <div className="flex items-center gap-2 mb-3 flex-wrap">
              <FaFilter className="text-slate-400" size={10} />
              <button
                type="button"
                onClick={() => setActiveFilter(null)}
                className={`px-2 py-1 text-xs rounded ${
                  activeFilter === null
                    ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                    : "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300 hover:bg-slate-200"
                }`}
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
                  className={`px-2 py-1 text-xs rounded ${
                    activeFilter === t.model
                      ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                      : "bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300 hover:bg-slate-200"
                  }`}
                >
                  {t.label} ({data[t.model]?.length ?? 0})
                </button>
              ))}
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-8 text-slate-400">
              <FaSpinner className="animate-spin mr-2" /> Loading…
            </div>
          ) : totalCount === 0 ? (
            <p className="text-sm text-slate-400 text-center py-6">
              No transactions found.
            </p>
          ) : (
            <div className="space-y-4">
              {filteredTables.map((t) => {
                const records = data[t.model] ?? [];
                if (records.length === 0) return null;
                return (
                  <div key={t.model}>
                    <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
                      {t.label}
                    </h4>
                    <div className="border border-slate-200 dark:border-slate-700 rounded-md overflow-hidden">
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
