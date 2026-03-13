/**
 * TransactionTabPanel - second-row tab bar for navigating transaction sub-types
 *
 * Sits below detail tabs on org detail pages (Customer, Vendor).
 *
 * Behavior:
 * - No "All" tab. User chooses one transaction type.
 * - Selected type is persisted to localStorage per machine (Alice preference key).
 * - Data is fetched only for the selected tab to avoid unnecessary API calls.
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  FaClipboardList,
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

export type OrgType = "customer" | "vendor";

interface TransactionRecord {
  id: number;
  ida?: string;
  status?: string;
  priority?: string | number;
  total?: number;
  balance?: number;
  attention?: string;
  phone?: string;
  name?: string;
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

export interface TransactionTabPanelProps {
  orgType: OrgType;
  orgId: number;
  className?: string;
}

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

const STORAGE_KEY_PREFIX = "alice.preferences.transactionTabPanel";

const formatWholeNumber = (value?: number) => {
  if (value == null || Number.isNaN(value)) return "-";
  return Math.round(value).toLocaleString();
};

const getStoredModel = (orgType: OrgType): string | null => {
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}.${orgType}`);
    return raw || null;
  } catch {
    return null;
  }
};

const storeModel = (orgType: OrgType, model: string) => {
  try {
    localStorage.setItem(`${STORAGE_KEY_PREFIX}.${orgType}`, model);
  } catch {
    // Ignore localStorage errors.
  }
};

const normalizeRecords = (records: any[]): TransactionRecord[] =>
  records.map((r) => ({
    ...r,
    priority: r?.priority ?? r?.metadata?.priority ?? "",
    total: Number(r?.total ?? r?.totals?.total ?? 0),
    balance: Number(r?.balance ?? r?.totals?.balance ?? 0),
    attention: r?.attention ?? r?.to?.attention ?? r?.from?.attention ?? "",
    phone: r?.phone ?? r?.to?.phone ?? r?.from?.phone ?? "",
  }));

const TransactionTabPanel: React.FC<TransactionTabPanelProps> = ({
  orgType,
  orgId,
  className = "",
}) => {
  const windowManager = useWindowManager();
  const tables = useMemo(() => SUB_TABLES[orgType] ?? [], [orgType]);

  const [activeModel, setActiveModel] = useState<string | null>(() =>
    getStoredModel(orgType),
  );
  const [dataByModel, setDataByModel] = useState<Record<string, TransactionRecord[]>>({});
  const [loading, setLoading] = useState(false);

  // If org type changes, recover machine preference for that org type.
  useEffect(() => {
    setActiveModel(getStoredModel(orgType));
  }, [orgType]);

  // If org record changes, clear prior fetched data so we do not show stale records.
  useEffect(() => {
    setDataByModel({});
  }, [orgId, orgType]);

  // Fetch only the selected model when needed.
  useEffect(() => {
    if (!orgId || !activeModel) return;
    if (dataByModel[activeModel]) return;

    const selectedTable = tables.find((t) => t.model === activeModel);
    if (!selectedTable) return;

    let cancelled = false;
    setLoading(true);

    const params: Record<string, unknown> = {
      [selectedTable.filterField]: orgId,
      limit: 100,
    };
    if (orgType === "vendor") {
      params.org_type = "vendor";
    }

    getRecords(selectedTable.model, params)
      .then((result) => {
        if (cancelled) return;
        const records = normalizeRecords(result?.results ?? []);
        setDataByModel((prev) => ({
          ...prev,
          [selectedTable.model]: records,
        }));
      })
      .catch(() => {
        if (cancelled) return;
        setDataByModel((prev) => ({
          ...prev,
          [selectedTable.model]: [],
        }));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [orgId, orgType, activeModel, tables, dataByModel]);

  const handleRowClick = useCallback(
    (model: string, rec: TransactionRecord) => {
      const path = getModelDetailPath(model, rec.id);
      const title = getModelWindowTitle(model, rec.id, rec.ida, rec.name);
      windowManager.ensureWindow(path, title, { maximized: false });
    },
    [windowManager],
  );

  const handleTabChange = useCallback(
    (model: string) => {
      setActiveModel(model);
      storeModel(orgType, model);
    },
    [orgType],
  );

  const visibleRecords = useMemo(() => {
    if (!activeModel) return [];
    return dataByModel[activeModel] ?? [];
  }, [activeModel, dataByModel]);

  return (
    <div
      className={`bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 ${className}`}
    >
      <div className="border-b border-slate-200 dark:border-slate-700">
        <nav className="px-4">
          <div className="flex items-center gap-1 py-2 overflow-x-auto">
            {tables.map((t) => {
              const count = dataByModel[t.model]?.length ?? 0;
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

      <div className="p-4 max-h-[500px] overflow-y-auto">
        {!activeModel ? (
          <p className="text-sm text-slate-400 text-center py-6">
            Select a transaction type to load records.
          </p>
        ) : loading ? (
          <div className="flex items-center justify-center py-8 text-slate-400">
            <FaSpinner className="animate-spin mr-2" /> Loading transactions...
          </div>
        ) : visibleRecords.length === 0 ? (
          <p className="text-sm text-slate-400 text-center py-6">
            No transactions found.
          </p>
        ) : (
          <div className="border border-slate-200 dark:border-slate-700 rounded-md overflow-hidden text-xs">
            <div className="grid grid-cols-[1.2fr_1fr_1fr_1fr_1fr_1.2fr_1.2fr_auto] gap-2 px-3 py-2 bg-slate-50 dark:bg-slate-900/40 border-b border-slate-200 dark:border-slate-700 font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide">
              <span>ida</span>
              <span>status</span>
              <span>priority</span>
              <span className="text-right">total</span>
              <span className="text-right">balance</span>
              <span>attention</span>
              <span>phone</span>
              <span className="text-right">open</span>
            </div>

            <div className="divide-y divide-slate-100 dark:divide-slate-700">
              {visibleRecords.map((rec) => (
                <div
                  key={`${activeModel}-${rec.id}`}
                  className="grid grid-cols-[1.2fr_1fr_1fr_1fr_1fr_1.2fr_1.2fr_auto] gap-2 px-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-700/50 cursor-pointer items-center"
                  onClick={() => handleRowClick(activeModel, rec)}
                >
                  <span className="font-mono text-slate-600 dark:text-slate-300 truncate">
                    {rec.ida ?? `#${rec.id}`}
                  </span>
                  <span className="truncate text-slate-700 dark:text-slate-200">
                    {String(rec.status ?? "-")}
                  </span>
                  <span className="truncate text-slate-700 dark:text-slate-200">
                    {String(rec.priority ?? "-")}
                  </span>
                  <span className="text-right text-slate-700 dark:text-slate-200">
                    {formatWholeNumber(rec.total)}
                  </span>
                  <span className="text-right text-slate-700 dark:text-slate-200">
                    {formatWholeNumber(rec.balance)}
                  </span>
                  <span className="truncate text-slate-700 dark:text-slate-200">
                    {String(rec.attention ?? "-")}
                  </span>
                  <span className="truncate text-slate-700 dark:text-slate-200">
                    {String(rec.phone ?? "-")}
                  </span>
                  <div className="flex justify-end">
                    <button
                      type="button"
                      title="Open in floating window"
                      className="p-1 rounded hover:bg-blue-100 dark:hover:bg-blue-900/30 text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRowClick(activeModel, rec);
                      }}
                    >
                      <FaExternalLinkAlt size={10} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TransactionTabPanel;
