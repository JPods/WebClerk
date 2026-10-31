/* LastChecked: 2026-10-20 | WhereUsed: panelRegistry `transactions` (org forms) | WhoCreated: Unknown */
/**
 * TransactionsPanel - Displays transactions for an org (Customer or Vendor)
 *
 * Customer sub-tables: quotes, orders, invoices, ledgers, cash
 * Vendor sub-tables:   purchases, receipts
 * Rep sub-tables:      the quotes, orders, invoices it is credited on
 *
 * Each document's own org field is the one source (Bill, 2026-10-20: restored after a
 * copy on the org, refs.links.order, had drifted — Riverside's 7 orders showed 0).
 *
 * Fetches records via wcapi getRecords filtered by parent org ID.
 * Each row links to its transaction detail page.
 *
 * @see readmes/tab-navigation.md — Tier 2 Org Tabs
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  FaFilter,
} from "react-icons/fa";
import { useWindowManager } from "@/context/WindowManagerContext";
import { PanelFrame } from "@/apps/common/components/CollapsiblePanel";
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
export type OrgType = "customer" | "vendor" | "rep";

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
  { model: "quote", label: "Quotes", filterField: "customer" },
  { model: "order", label: "Orders", filterField: "customer" },
  { model: "invoice", label: "Invoices", filterField: "customer" },
  { model: "ledger", label: "Ledgers", filterField: "org" },
  { model: "cash", label: "Cash", filterField: "customer" },
];

const VENDOR_TABLES: SubTable[] = [
  { model: "purchase", label: "Purchases", filterField: "vendor" },
  { model: "receipt", label: "Receipts", filterField: "vendor" },
];

const REP_TABLES: SubTable[] = [
  { model: "quote", label: "Quotes", filterField: "rep_id" },
  { model: "order", label: "Orders", filterField: "rep_id" },
  { model: "invoice", label: "Invoices", filterField: "rep_id" },
];

const SUB_TABLES: Record<OrgType, SubTable[]> = {
  customer: CUSTOMER_TABLES,
  vendor: VENDOR_TABLES,
  rep: REP_TABLES,
};

/** A document's total; cash carries amount, a ledger instalment its unpaid balance. */
const recordTotal = (r: TransactionRecord) =>
  (r.totals as { total?: number } | undefined)?.total ?? (r.amount as number | undefined) ?? (r.value_available as number | undefined);

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
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  const [data, setData] = useState<Record<string, TransactionRecord[]>>({});
  const [loading, setLoading] = useState(true);
  /** Sub-tables whose fetch failed — shown, never silently empty (Axiom 6). */
  const [errors, setErrors] = useState<Record<string, string>>({});
  const inflightRequests = useRef<
    Map<string, Promise<{ map: Record<string, TransactionRecord[]>; errs: Record<string, string> }>>
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
        width: '70px', className: 'font-mono',
        cellStyle: { color: 'var(--db-text-muted)' },
        render: (r) => r.ida ?? `#${r.id}`,
      },
      {
        key: "name",
        label: "name",
        cellStyle: { color: 'var(--db-text)' },
        render: (r) => r.name ?? "\u2014",
      },
      {
        key: "status",
        label: "status",
        width: '80px',
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
        width: '90px', className: 'text-right',
        cellStyle: { color: 'var(--db-text)' },
        render: (r) => formatCurrency(recordTotal(r)),
      },
      {
        key: "dt_created",
        label: "dt_created",
        width: '80px',
        cellStyle: { color: 'var(--db-text-dim)' },
        render: (r) => formatDate(r.dt_created),
      },
      {
        key: "dt_modified",
        label: "dt_modified",
        defaultVisible: false,
        width: '80px',
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

    const executeFetch = async (): Promise<{
      map: Record<string, TransactionRecord[]>;
      errs: Record<string, string>;
    }> => {
      const results = await Promise.all(
        tables.map(async (t) => {
          try {
            const result = await getRecords(t.model, {
              [t.filterField]: orgId,
              limit: 100,
            });
            return { model: t.model, records: result?.results ?? [], error: "" };
          } catch (err: any) {
            return { model: t.model, records: [], error: err?.message || "could not load" };
          }
        }),
      );

      const map: Record<string, TransactionRecord[]> = {};
      const errs: Record<string, string> = {};
      results.forEach((r) => {
        map[r.model] = r.records;
        if (r.error) errs[r.model] = r.error;
      });
      return { map, errs };
    };

    const existingRequest = inflightRequests.current.get(cacheKey);
    const request = existingRequest ?? executeFetch();
    inflightRequests.current.set(cacheKey, request);

    request
      .then(({ map, errs }) => {
        if (cancelled) return;
        setData(map);
        setErrors(errs);
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
    <div className={className}>
      <PanelFrame label={title} defaultCollapsed={defaultCollapsed} badge={totalCount || undefined}
        status={{ loading, empty: !loading && totalCount === 0, emptyText: 'No transactions found.' }}>
        <div className={compact ? "p-1" : "p-2"}>
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

          {Object.keys(errors).length > 0 && (
            <div className="mb-3 px-2 py-1 text-xs rounded" style={{ color: 'var(--db-danger, #dc2626)', background: 'var(--db-surface-alt)' }}>
              {Object.entries(errors).map(([model, msg]) => `${model}: ${msg}`).join(' · ')}
            </div>
          )}

          {totalCount > 0 && (
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
                        onOpenRow={(r) => handleRowClick(t.model, r)}
                        onOpenWindow={(r) => window.open(getModelDetailPath(t.model, r.id), `${t.model}-${r.id}`, 'popup,width=1200,height=850')}
                        compact={compact}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </PanelFrame>
    </div>
  );
};

export default withDevIdentifier(
  TransactionsPanel,
  "TransactionsPanel",
  "teal",
  'apps/common/components/panels/TransactionsPanel.tsx',
);
