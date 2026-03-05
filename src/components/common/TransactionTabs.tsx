/**
 * TransactionTabs - Second-row tab bar for navigating transaction sub-types
 *
 * Sits below DetailTabs on org detail pages (Customer, Vendor).
 * Each tab shows a filtered list of transactions for that sub-type.
 *
 * Customer tabs: All · Proposals · Orders · Invoices · Ledgers · Payments
 * Vendor tabs:   All · Proposals · Orders · Invoices · Ledgers · Payments · Purchases · Receipts
 *
 * @see readmes/tab-navigation.md — Tier 2 Org Tabs → transactions
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  FaClipboardList,
  FaExchangeAlt,
  FaExternalLinkAlt,
  FaFileInvoiceDollar,
  FaMoneyCheckAlt,
  FaReceipt,
  FaShoppingCart,
  FaSpinner,
  FaTruck,
  FaBook,
} from "react-icons/fa";
import { useWindowManager } from "@/context/WindowManagerContext";
import { getRecords } from "@/api/wcapi";
import {
  getModelDetailPath,
  getModelWindowTitle,
} from "@/apps/common/components/panels/getModelDetailPath";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type OrgType = "customer" | "vendor";

interface TransactionRecord {
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

interface SubTable {
  model: string;
  label: string;
  filterField: string;
  icon: React.ReactNode;
}

export interface TransactionTabsProps {
  /** The org type — determines which sub-tabs are shown */
  orgType: OrgType;
  /** Parent org ID to filter transactions */
  orgId: number;
  /** Additional CSS classes */
  className?: string;
}

// ---------------------------------------------------------------------------
// Sub-table definitions by org type
// ---------------------------------------------------------------------------

const CUSTOMER_TABLES: SubTable[] = [
  {
    model: "proposal",
    label: "Proposals",
    filterField: "customer",
    icon: <FaClipboardList size={12} />,
  },
  {
    model: "order",
    label: "Orders",
    filterField: "customer",
    icon: <FaShoppingCart size={12} />,
  },
  {
    model: "invoice",
    label: "Invoices",
    filterField: "customer",
    icon: <FaFileInvoiceDollar size={12} />,
  },
  {
    model: "ledger",
    label: "Ledgers",
    filterField: "customer",
    icon: <FaBook size={12} />,
  },
  {
    model: "payment",
    label: "Payments",
    filterField: "customer",
    icon: <FaMoneyCheckAlt size={12} />,
  },
];

const VENDOR_TABLES: SubTable[] = [
  {
    model: "proposal",
    label: "Proposals",
    filterField: "vendor",
    icon: <FaClipboardList size={12} />,
  },
  {
    model: "order",
    label: "Orders",
    filterField: "vendor",
    icon: <FaShoppingCart size={12} />,
  },
  {
    model: "invoice",
    label: "Invoices",
    filterField: "vendor",
    icon: <FaFileInvoiceDollar size={12} />,
  },
  {
    model: "ledger",
    label: "Ledgers",
    filterField: "vendor",
    icon: <FaBook size={12} />,
  },
  {
    model: "payment",
    label: "Payments",
    filterField: "vendor",
    icon: <FaMoneyCheckAlt size={12} />,
  },
  {
    model: "purchase",
    label: "Purchases",
    filterField: "vendor",
    icon: <FaTruck size={12} />,
  },
  {
    model: "receipt",
    label: "Receipts",
    filterField: "vendor",
    icon: <FaReceipt size={12} />,
  },
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

const TransactionTabs: React.FC<TransactionTabsProps> = ({
  orgType,
  orgId,
  className = "",
}) => {
  const [activeModel, setActiveModel] = useState<string | null>(null); // null = All
  const [data, setData] = useState<Record<string, TransactionRecord[]>>({});
  const [loading, setLoading] = useState(true);

  const windowManager = useWindowManager();
  const tables = useMemo(() => SUB_TABLES[orgType] ?? [], [orgType]);

  // Fetch all sub-tables in parallel
  useEffect(() => {
    if (!orgId) return;
    let cancelled = false;
    setLoading(true);

    Promise.all(
      tables.map(async (t) => {
        try {
          const params: Record<string, unknown> = {
            [t.filterField]: orgId,
            limit: 100,
          };
          if (orgType === "vendor") {
            params.org_type = "vendor";
          }
          const result = await getRecords(t.model, params);
          return { model: t.model, records: result?.results ?? [] };
        } catch {
          return { model: t.model, records: [] };
        }
      }),
    ).then((results) => {
      if (cancelled) return;
      const map: Record<string, TransactionRecord[]> = {};
      results.forEach((r) => {
        map[r.model] = r.records;
      });
      setData(map);
      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [orgId, tables]);

  const totalCount = tables.reduce(
    (sum, t) => sum + (data[t.model]?.length ?? 0),
    0,
  );

  const handleRowClick = useCallback(
    (model: string, rec: TransactionRecord) => {
      const path = getModelDetailPath(model, rec.id);
      const title = getModelWindowTitle(model, rec.id, rec.ida, rec.name);
      windowManager.ensureWindow(path, title, { maximized: false });
    },
    [windowManager],
  );

  const handleTabChange = useCallback((model: string | null) => {
    setActiveModel(model);
  }, []);

  // Records for the active tab
  const visibleRecords = useMemo(() => {
    if (activeModel === null) {
      // All — flatten all sub-tables, newest first
      return tables
        .flatMap((t) =>
          (data[t.model] ?? []).map((r) => ({
            ...r,
            _model: t.model,
            _label: t.label,
          })),
        )
        .sort((a, b) => (b.dt_created ?? 0) - (a.dt_created ?? 0));
    }
    return (data[activeModel] ?? []).map((r) => ({
      ...r,
      _model: activeModel,
      _label: "",
    }));
  }, [activeModel, data, tables]);

  return (
    <div
      className={`bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 ${className}`}
    >
      {/* Transaction Tab Bar */}
      <div className="border-b border-slate-200 dark:border-slate-700">
        <nav className="px-4">
          <div className="flex items-center gap-1 py-2 overflow-x-auto">
            {/* All tab */}
            <button
              type="button"
              onClick={() => handleTabChange(null)}
              className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-md whitespace-nowrap transition-all duration-200 ${
                activeModel === null
                  ? "text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/20 border-b-2 border-indigo-600"
                  : "text-slate-500 hover:text-slate-700 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700"
              }`}
            >
              <FaExchangeAlt size={12} />
              All
              {!loading && totalCount > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-xs bg-slate-200 dark:bg-slate-600 rounded-full">
                  {totalCount}
                </span>
              )}
            </button>

            {/* Per-type tabs */}
            {tables.map((t) => {
              const count = data[t.model]?.length ?? 0;
              const isActive = activeModel === t.model;
              return (
                <button
                  key={t.model}
                  type="button"
                  onClick={() => handleTabChange(t.model)}
                  className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-md whitespace-nowrap transition-all duration-200 ${
                    isActive
                      ? "text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/20 border-b-2 border-indigo-600"
                      : "text-slate-500 hover:text-slate-700 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700"
                  }`}
                >
                  {t.icon}
                  {t.label}
                  {!loading && count > 0 && (
                    <span className="ml-1 px-1.5 py-0.5 text-xs bg-slate-200 dark:bg-slate-600 rounded-full">
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </nav>
      </div>

      {/* Tab Content — transaction list */}
      <div className="p-4 max-h-[500px] overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-8 text-slate-400">
            <FaSpinner className="animate-spin mr-2" /> Loading transactions…
          </div>
        ) : visibleRecords.length === 0 ? (
          <p className="text-sm text-slate-400 text-center py-6">
            No transactions found.
          </p>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-700 border border-slate-200 dark:border-slate-700 rounded-md overflow-hidden">
            {visibleRecords.map((rec) => (
              <div
                key={`${rec._model}-${rec.id}`}
                className="flex items-center justify-between px-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-700/50 text-xs cursor-pointer"
                onClick={() => handleRowClick(rec._model, rec)}
              >
                <div className="flex items-center gap-3 min-w-0">
                  {/* Show type badge when viewing "All" */}
                  {activeModel === null && rec._label && (
                    <span className="px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded shrink-0">
                      {rec._label}
                    </span>
                  )}
                  <span className="font-mono text-slate-500 dark:text-slate-400 shrink-0">
                    {rec.ida ?? `#${rec.id}`}
                  </span>
                  <span className="text-slate-800 dark:text-slate-200 truncate">
                    {rec.name ?? "—"}
                  </span>
                </div>
                <div className="flex items-center gap-4 shrink-0">
                  {rec.status && (
                    <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-600 text-slate-600 dark:text-slate-300">
                      {rec.status}
                    </span>
                  )}
                  <span className="text-slate-600 dark:text-slate-300">
                    {formatCurrency(rec.total, rec.currency)}
                  </span>
                  <span className="text-slate-400">
                    {formatDate(rec.dt_created)}
                  </span>
                  <button
                    type="button"
                    title="Open in floating window"
                    className="p-1 rounded hover:bg-blue-100 dark:hover:bg-blue-900/30 text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRowClick(rec._model, rec);
                    }}
                  >
                    <FaExternalLinkAlt size={10} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default TransactionTabs;
