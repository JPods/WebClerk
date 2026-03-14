/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
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
  FaBarcode,
  FaClipboardList,
  FaDollarSign,
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
import OrgFinancialsPanel from "@/apps/orgs/components/OrgFinancialsPanel";
import OrgMetricsPanel from "@/apps/orgs/components/OrgMetricsPanel";

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

interface ColumnDef {
  key: string;
  header: string;
  width?: string;
  align?: "left" | "right";
  value: (record: TransactionRecord) => React.ReactNode;
  resolvedPath?: (record: TransactionRecord) => string;
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
  onTransactionModifierClick?: (selection: TransactionSelection) => void;
  financial?: any;
}

export interface TransactionSelection {
  model: string;
  id: number;
  ida?: string;
  name?: string;
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
  {
    model: "serial",
    label: "Serials",
    filterField: "customer_id",
    icon: <FaBarcode size={12} />,
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
  {
    model: "serial",
    label: "Serials",
    filterField: "vendor_id",
    icon: <FaBarcode size={12} />,
  },
];

const SUB_TABLES: Record<OrgType, SubTable[]> = {
  customer: CUSTOMER_TABLES,
  vendor: VENDOR_TABLES,
};

const STORAGE_KEY_PREFIX = "alice.preferences.transactionTabPanel";
const DEBUG_STORAGE_KEY = "alice.preferences.transactionTabPanel.debug";

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

const getTextFromPaths = (
  record: TransactionRecord,
  paths: string[],
  fallback = "-",
) => {
  for (const path of paths) {
    const parts = path.split(".");
    let current: any = record;
    for (const part of parts) {
      current = current?.[part];
      if (current == null) break;
    }
    if (current != null && String(current).trim() !== "") {
      return String(current);
    }
  }
  return fallback;
};

const getResolvedTextPath = (record: TransactionRecord, paths: string[]) => {
  for (const path of paths) {
    const parts = path.split(".");
    let current: any = record;
    for (const part of parts) {
      current = current?.[part];
      if (current == null) break;
    }
    if (current != null && String(current).trim() !== "") {
      return path;
    }
  }
  return "-";
};

const getNumberFromPaths = (
  record: TransactionRecord,
  paths: string[],
): number | undefined => {
  for (const path of paths) {
    const parts = path.split(".");
    let current: any = record;
    for (const part of parts) {
      current = current?.[part];
      if (current == null) break;
    }
    const n = Number(current);
    if (Number.isFinite(n)) {
      return n;
    }
  }
  return undefined;
};

const getResolvedNumberPath = (record: TransactionRecord, paths: string[]) => {
  for (const path of paths) {
    const parts = path.split(".");
    let current: any = record;
    for (const part of parts) {
      current = current?.[part];
      if (current == null) break;
    }
    const n = Number(current);
    if (Number.isFinite(n)) {
      return path;
    }
  }
  return "-";
};

const getStoredDebug = () => {
  try {
    return localStorage.getItem(DEBUG_STORAGE_KEY) === "1";
  } catch {
    return false;
  }
};

const storeDebug = (enabled: boolean) => {
  try {
    localStorage.setItem(DEBUG_STORAGE_KEY, enabled ? "1" : "0");
  } catch {
    // Ignore localStorage errors.
  }
};

const BASE_COLUMNS: ColumnDef[] = [
  {
    key: "ida",
    header: "ida",
    width: "1.2fr",
    value: (rec) => rec.ida ?? `#${rec.id}`,
    resolvedPath: (rec) => (rec.ida ? "ida" : "id"),
  },
  {
    key: "status",
    header: "status",
    width: "1fr",
    value: (rec) => getTextFromPaths(rec, ["status"]),
    resolvedPath: (rec) => getResolvedTextPath(rec, ["status"]),
  },
  {
    key: "priority",
    header: "priority",
    width: "1fr",
    value: (rec) => getTextFromPaths(rec, ["priority", "metadata.priority"]),
    resolvedPath: (rec) =>
      getResolvedTextPath(rec, ["priority", "metadata.priority"]),
  },
  {
    key: "total",
    header: "total",
    width: "1fr",
    align: "right",
    value: (rec) =>
      formatWholeNumber(
        getNumberFromPaths(rec, [
          "total",
          "total_amount",
          "totals.total",
          "amount",
        ]),
      ),
    resolvedPath: (rec) =>
      getResolvedNumberPath(rec, [
        "total",
        "total_amount",
        "totals.total",
        "amount",
      ]),
  },
  {
    key: "balance",
    header: "balance",
    width: "1fr",
    align: "right",
    value: (rec) =>
      formatWholeNumber(
        getNumberFromPaths(rec, [
          "balance",
          "balance_due",
          "totals.balance",
          "amount_due",
        ]),
      ),
    resolvedPath: (rec) =>
      getResolvedNumberPath(rec, [
        "balance",
        "balance_due",
        "totals.balance",
        "amount_due",
      ]),
  },
  {
    key: "attention",
    header: "attention",
    width: "1.2fr",
    value: (rec) =>
      getTextFromPaths(rec, ["attention", "to.attention", "from.attention"]),
    resolvedPath: (rec) =>
      getResolvedTextPath(rec, ["attention", "to.attention", "from.attention"]),
  },
  {
    key: "phone",
    header: "phone",
    width: "1.2fr",
    value: (rec) => getTextFromPaths(rec, ["phone", "to.phone", "from.phone"]),
    resolvedPath: (rec) =>
      getResolvedTextPath(rec, ["phone", "to.phone", "from.phone"]),
  },
];

const PAYMENT_COLUMNS: ColumnDef[] = [
  {
    key: "ida",
    header: "ida",
    width: "1.2fr",
    value: (rec) => rec.ida ?? `#${rec.id}`,
    resolvedPath: (rec) => (rec.ida ? "ida" : "id"),
  },
  {
    key: "status",
    header: "status",
    width: "1fr",
    value: (rec) => getTextFromPaths(rec, ["status"]),
    resolvedPath: (rec) => getResolvedTextPath(rec, ["status"]),
  },
  {
    key: "priority",
    header: "priority",
    width: "1fr",
    value: (rec) => getTextFromPaths(rec, ["priority", "metadata.priority"]),
    resolvedPath: (rec) =>
      getResolvedTextPath(rec, ["priority", "metadata.priority"]),
  },
  {
    key: "payment_amount",
    header: "payment",
    width: "1fr",
    align: "right",
    value: (rec) =>
      formatWholeNumber(
        getNumberFromPaths(rec, [
          "amount",
          "payment_amount",
          "total",
          "totals.total",
          "financial.amount",
        ]),
      ),
    resolvedPath: (rec) =>
      getResolvedNumberPath(rec, [
        "amount",
        "payment_amount",
        "total",
        "totals.total",
        "financial.amount",
      ]),
  },
  {
    key: "unapplied",
    header: "unapplied",
    width: "1fr",
    align: "right",
    value: (rec) =>
      formatWholeNumber(
        getNumberFromPaths(rec, [
          "amount_available",
          "unapplied",
          "balance",
          "balance_due",
          "totals.balance",
          "financial.unapplied",
        ]),
      ),
    resolvedPath: (rec) =>
      getResolvedNumberPath(rec, [
        "amount_available",
        "unapplied",
        "balance",
        "balance_due",
        "totals.balance",
        "financial.unapplied",
      ]),
  },
  {
    key: "attention",
    header: "attention",
    width: "1.2fr",
    value: (rec) =>
      getTextFromPaths(rec, ["attention", "to.attention", "from.attention"]),
    resolvedPath: (rec) =>
      getResolvedTextPath(rec, ["attention", "to.attention", "from.attention"]),
  },
  {
    key: "phone",
    header: "phone",
    width: "1.2fr",
    value: (rec) => getTextFromPaths(rec, ["phone", "to.phone", "from.phone"]),
    resolvedPath: (rec) =>
      getResolvedTextPath(rec, ["phone", "to.phone", "from.phone"]),
  },
];

const LEDGER_COLUMNS: ColumnDef[] = [
  {
    key: "ida",
    header: "ida",
    width: "1.2fr",
    value: (rec) => rec.ida ?? `#${rec.id}`,
    resolvedPath: (rec) => (rec.ida ? "ida" : "id"),
  },
  {
    key: "status",
    header: "status",
    width: "1fr",
    value: (rec) => getTextFromPaths(rec, ["status"]),
    resolvedPath: (rec) => getResolvedTextPath(rec, ["status"]),
  },
  {
    key: "type",
    header: "type",
    width: "1fr",
    value: (rec) => getTextFromPaths(rec, ["type", "metadata.type"]),
    resolvedPath: (rec) => getResolvedTextPath(rec, ["type", "metadata.type"]),
  },
  {
    key: "total",
    header: "total",
    width: "1fr",
    align: "right",
    value: (rec) =>
      formatWholeNumber(
        getNumberFromPaths(rec, [
          "total",
          "total_amount",
          "amount",
          "totals.total",
          "debit",
          "totals.debit",
          "amount_debit",
        ]),
      ),
    resolvedPath: (rec) =>
      getResolvedNumberPath(rec, [
        "total",
        "total_amount",
        "amount",
        "totals.total",
        "debit",
        "totals.debit",
        "amount_debit",
      ]),
  },
  {
    key: "balance",
    header: "balance",
    width: "1fr",
    align: "right",
    value: (rec) =>
      formatWholeNumber(
        getNumberFromPaths(rec, ["balance", "totals.balance", "running_balance"]),
      ),
    resolvedPath: (rec) =>
      getResolvedNumberPath(rec, ["balance", "totals.balance", "running_balance"]),
  },
  {
    key: "attention",
    header: "attention",
    width: "1.2fr",
    value: (rec) =>
      getTextFromPaths(rec, ["attention", "to.attention", "from.attention"]),
    resolvedPath: (rec) =>
      getResolvedTextPath(rec, ["attention", "to.attention", "from.attention"]),
  },
  {
    key: "phone",
    header: "phone",
    width: "1.2fr",
    value: (rec) => getTextFromPaths(rec, ["phone", "to.phone", "from.phone"]),
    resolvedPath: (rec) =>
      getResolvedTextPath(rec, ["phone", "to.phone", "from.phone"]),
  },
];

const SERIAL_COLUMNS: ColumnDef[] = [
  {
    key: "serial_number",
    header: "serial_number",
    width: "1.6fr",
    value: (rec) =>
      getTextFromPaths(rec, ["serial_number", "ida", "name"], `#${rec.id}`),
    resolvedPath: (rec) =>
      getResolvedTextPath(rec, ["serial_number", "ida", "name"]),
  },
  {
    key: "status",
    header: "status",
    width: "1fr",
    value: (rec) => getTextFromPaths(rec, ["status"]),
    resolvedPath: (rec) => getResolvedTextPath(rec, ["status"]),
  },
  {
    key: "item_id",
    header: "item_id",
    width: "1fr",
    value: (rec) => getTextFromPaths(rec, ["item_id", "item.id", "item_name"]),
    resolvedPath: (rec) =>
      getResolvedTextPath(rec, ["item_id", "item.id", "item_name"]),
  },
  {
    key: "location",
    header: "location",
    width: "1fr",
    value: (rec) => getTextFromPaths(rec, ["location", "warehouse", "site"]),
    resolvedPath: (rec) =>
      getResolvedTextPath(rec, ["location", "warehouse", "site"]),
  },
  {
    key: "attention",
    header: "attention",
    width: "1.2fr",
    value: (rec) =>
      getTextFromPaths(rec, ["attention", "customer_name", "vendor_name"]),
    resolvedPath: (rec) =>
      getResolvedTextPath(rec, ["attention", "customer_name", "vendor_name"]),
  },
  {
    key: "phone",
    header: "phone",
    width: "1.2fr",
    value: (rec) => getTextFromPaths(rec, ["phone", "customer_phone", "vendor_phone"]),
    resolvedPath: (rec) =>
      getResolvedTextPath(rec, ["phone", "customer_phone", "vendor_phone"]),
  },
];

const getColumnsForModel = (model: string): ColumnDef[] => {
  if (model === "payment") return PAYMENT_COLUMNS;
  if (model === "ledger") return LEDGER_COLUMNS;
  if (model === "serial") return SERIAL_COLUMNS;
  return BASE_COLUMNS;
};

interface TransactionRecordGridProps {
  model: string;
  records: TransactionRecord[];
  onModifierRowClick?: (model: string, record: TransactionRecord) => void;
  onOpenRow: (model: string, record: TransactionRecord) => void;
  debugMode?: boolean;
}

function TransactionRecordGrid({
  model,
  records,
  onModifierRowClick,
  onOpenRow,
  debugMode = false,
}: TransactionRecordGridProps) {
  const columns = useMemo(() => getColumnsForModel(model), [model]);
  const gridTemplateColumns = useMemo(
    () => `${columns.map((c) => c.width ?? "1fr").join(" ")} auto`,
    [columns],
  );

  return (
    <div className="border border-slate-200 dark:border-slate-700 rounded-md overflow-hidden text-xs">
      <div
        className="gap-2 px-3 py-2 bg-slate-50 dark:bg-slate-900/40 border-b border-slate-200 dark:border-slate-700 font-semibold text-slate-600 dark:text-slate-300 uppercase tracking-wide grid"
        style={{ gridTemplateColumns }}
      >
        {columns.map((column) => (
          <span
            key={column.key}
            className={column.align === "right" ? "text-right" : ""}
          >
            {column.header}
          </span>
        ))}
        <span className="text-right">open</span>
      </div>

      <div className="divide-y divide-slate-100 dark:divide-slate-700">
        {records.map((record) => (
          <div
            key={`${model}-${record.id}`}
            className="gap-2 px-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-700/50 cursor-pointer items-center grid"
            style={{ gridTemplateColumns }}
            title="cmd/ctrl-click to load lines, double-click to open detail"
            onClick={(e) => {
              if (e.metaKey || e.ctrlKey) {
                onModifierRowClick?.(model, record);
              }
            }}
            onDoubleClick={() => onOpenRow(model, record)}
          >
            {columns.map((column) => (
              <span
                key={column.key}
                className={`text-slate-700 dark:text-slate-200 truncate ${
                  column.key === "ida"
                    ? "font-mono text-slate-600 dark:text-slate-300"
                    : ""
                } ${column.align === "right" ? "text-right" : ""}`}
              >
                <span className="block truncate">{column.value(record)}</span>
                {debugMode && (
                  <span className="block text-[10px] text-amber-600 dark:text-amber-400 normal-case truncate">
                    {column.resolvedPath?.(record) ?? "-"}
                  </span>
                )}
              </span>
            ))}
            <div className="flex justify-end">
              <button
                type="button"
                title="Open in floating window"
                className="p-1 rounded hover:bg-blue-100 dark:hover:bg-blue-900/30 text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                onClick={(e) => {
                  e.stopPropagation();
                  onOpenRow(model, record);
                }}
              >
                <FaExternalLinkAlt size={10} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

const TransactionTabPanel: React.FC<TransactionTabPanelProps> = ({
  orgType,
  orgId,
  className = "",
  onTransactionModifierClick,
  financial,
}) => {
  const windowManager = useWindowManager();
  const tables = useMemo(() => SUB_TABLES[orgType] ?? [], [orgType]);

  const [activeModel, setActiveModel] = useState<string | null>(() =>
    getStoredModel(orgType),
  );
  const [dataByModel, setDataByModel] = useState<Record<string, TransactionRecord[]>>({});
  const [loading, setLoading] = useState(false);
  const [debugMode, setDebugMode] = useState<boolean>(() => getStoredDebug());
  const [financialView, setFinancialView] = useState<"detail" | "metrics">(
    "detail",
  );

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

  const handleRowOpen = useCallback(
    (model: string, rec: TransactionRecord) => {
      const path = getModelDetailPath(model, rec.id);
      const title = getModelWindowTitle(model, rec.id, rec.ida, rec.name);
      windowManager.ensureWindow(path, title, { maximized: false });
    },
    [windowManager],
  );

  const handleModifierClick = useCallback(
    (model: string, rec: TransactionRecord) => {
      onTransactionModifierClick?.({
        model,
        id: rec.id,
        ida: rec.ida,
        name: rec.name,
      });
    },
    [onTransactionModifierClick],
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

  const handleToggleDebugMode = useCallback(() => {
    setDebugMode((prev) => {
      const next = !prev;
      storeDebug(next);
      return next;
    });
  }, []);

  return (
    <div
      className={`bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 ${className}`}
    >
      <div className="border-b border-slate-200 dark:border-slate-700">
        <nav className="px-4">
          <div className="flex items-center justify-between gap-2 py-2">
            <div className="flex items-center gap-1 overflow-x-auto">
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
            <button
              type="button"
              onClick={() => handleTabChange("__financial__")}
              className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-md whitespace-nowrap transition-all duration-200 ${
                activeModel === "__financial__"
                  ? "text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/20 border-b-2 border-indigo-600"
                  : "text-slate-500 hover:text-slate-700 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700"
              }`}
            >
              <FaDollarSign size={12} />
              Financial
            </button>
            </div>
            <button
              type="button"
              onClick={handleToggleDebugMode}
              className={`shrink-0 px-2 py-1 text-[11px] rounded border transition-colors ${
                debugMode
                  ? "border-amber-500 text-amber-700 bg-amber-50 dark:bg-amber-900/30 dark:text-amber-300"
                  : "border-slate-300 text-slate-500 hover:text-slate-700 dark:border-slate-600 dark:text-slate-400"
              }`}
              title="Toggle field-path debug"
            >
              debug {debugMode ? "on" : "off"}
            </button>
          </div>
        </nav>
      </div>

      <div className="p-4 max-h-[500px] overflow-y-auto">
        {!activeModel ? (
          <p className="text-sm text-slate-400 text-center py-6">
            Select a transaction type to load records.
          </p>
        ) : activeModel === "__financial__" ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setFinancialView("detail")}
                className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors ${
                  financialView === "detail"
                    ? "bg-indigo-50 text-indigo-700 border-indigo-300 dark:bg-indigo-900/30 dark:text-indigo-300 dark:border-indigo-700"
                    : "bg-white text-slate-600 border-slate-300 hover:bg-slate-50 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-600"
                }`}
              >
                Financial Detail
              </button>
              <button
                type="button"
                onClick={() => setFinancialView("metrics")}
                className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors ${
                  financialView === "metrics"
                    ? "bg-indigo-50 text-indigo-700 border-indigo-300 dark:bg-indigo-900/30 dark:text-indigo-300 dark:border-indigo-700"
                    : "bg-white text-slate-600 border-slate-300 hover:bg-slate-50 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-600"
                }`}
              >
                Metrics Snapshot
              </button>
            </div>

            {financialView === "detail" ? (
              <OrgFinancialsPanel financial={financial} orgType={orgType as any} />
            ) : (
              <OrgMetricsPanel financial={financial} orgType={orgType} />
            )}
          </div>
        ) : loading ? (
          <div className="flex items-center justify-center py-8 text-slate-400">
            <FaSpinner className="animate-spin mr-2" /> Loading transactions...
          </div>
        ) : visibleRecords.length === 0 ? (
          <p className="text-sm text-slate-400 text-center py-6">
            No transactions found.
          </p>
        ) : (
          <TransactionRecordGrid
            model={activeModel}
            records={visibleRecords}
            onModifierRowClick={handleModifierClick}
            onOpenRow={handleRowOpen}
            debugMode={debugMode}
          />
        )}
      </div>
    </div>
  );
};

export default TransactionTabPanel;
