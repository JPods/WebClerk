/**
 * TransactionTabs - Second-row tab bar for navigating transaction sub-types
 *
 * Sits below DetailTabs on org detail pages (Customer, Vendor).
 * Each tab shows a filtered list of transactions for that sub-type.
 *
 * Customer tabs: Proposals · Orders · Invoices · Ledgers · Payments
 * Vendor tabs:   Proposals · Orders · Invoices · Ledgers · Payments · Purchases · Receipts
 *
 * @see readmes/tab-navigation.md — Tier 2 Org Tabs → transactions
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  FaClipboardList,
  FaChevronDown,
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
import { getRecord, getRecords } from "@/api/wcapi";
import {
  getModelDetailPath,
  getModelWindowTitle,
} from "@/apps/common/components/panels/getModelDetailPath";
import { formatDt } from '@/utils/fieldFormatters';

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
  return formatDt(ts, 'date');
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

// Safely extract a numeric quantity from possible structured quantity objects
const formatLineQuantity = (qty: any): string => {
  if (qty == null) return "";
  if (typeof qty === "number") return String(qty);
  if (typeof qty === "object") {
    const { remaining, placed, actioned, value } = qty as Record<string, any>;
    const candidate =
      remaining ?? placed ?? actioned ?? value ?? qty?.total ?? qty?.active;
    if (typeof candidate === "number") return String(candidate);
  }
  return String(qty);
};

// Normalize the common line fields for consistent accordion rendering
interface LineDisplay {
  lineNumber: string;
  itemCode?: string;
  itemId?: number;
  description?: string;
  uom?: string;
  qtyActive?: string;
  qtyRemaining?: string;
  unitPrice?: number;
  unitCost?: number;
  priceExtended?: number;
  costExtended?: number;
  extended?: number;
  status?: string;
}

const extractNumber = (...candidates: any[]): number | undefined => {
  for (const value of candidates) {
    if (value === null || value === undefined) continue;
    if (typeof value === "number" && Number.isFinite(value)) return value;
    if (typeof value === "string") {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) return parsed;
    }
  }
  return undefined;
};

const deriveLineDisplay = (
  line: any,
  fallbackLineNumber: number,
): LineDisplay => {
  const lineNumber =
    line?.line_number ?? line?.line_num ?? line?.id ?? fallbackLineNumber;

  const itemId =
    line?.item_id ?? line?.itemId ?? line?.item?.id ?? line?.item?.item_id;

  const itemCode =
    line?.ida_item ??
    line?.item_code ??
    line?.item_num ??
    line?.item_name ??
    line?.item?.ida_item ??
    line?.item?.item_code ??
    line?.item?.item_num;

  const description =
    line?.description ??
    line?.name ??
    line?.item_name ??
    line?.item?.description;

  const uom =
    line?.unit_measure ??
    line?.unit_of_measure ??
    line?.unitOfMeasure ??
    line?.uom ??
    line?.item?.unit_measure;

  const qtyActive = formatLineQuantity(
    line?.quantity?.active ?? line?.qty ?? line?.quantity ?? line?.active,
  );
  const qtyRemaining = formatLineQuantity(
    line?.quantity?.remaining ?? line?.remaining ?? line?.children_active?.sum,
  );

  const unitPrice = extractNumber(
    line?.price?.unit,
    line?.price?.sell,
    line?.price?.base,
    line?.price?.retail,
    line?.unit_price,
    line?.price,
  );
  const unitCost = extractNumber(
    line?.cost?.unit,
    line?.cost?.avg,
    line?.cost?.last,
    line?.unit_cost,
    line?.cost,
  );
  const priceExtended = extractNumber(
    line?.price?.extended,
    line?.extended,
    line?.total,
    typeof unitPrice === "number" && typeof line?.quantity?.active === "number"
      ? unitPrice * line.quantity.active
      : undefined,
  );
  const costExtended = extractNumber(
    line?.cost?.extended,
    typeof unitCost === "number" && typeof line?.quantity?.active === "number"
      ? unitCost * line.quantity.active
      : undefined,
  );
  const extended = priceExtended ?? costExtended;

  return {
    lineNumber: String(lineNumber ?? fallbackLineNumber),
    itemCode,
    itemId,
    description,
    uom,
    qtyActive: qtyActive || undefined,
    qtyRemaining: qtyRemaining || undefined,
    unitPrice,
    unitCost,
    priceExtended,
    costExtended,
    extended,
    status: line?.status ?? line?.line_status ?? line?.stage,
  };
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const TransactionTabs: React.FC<TransactionTabsProps> = ({
  orgType,
  orgId,
  className = "",
}) => {
  const [activeModel, setActiveModel] = useState<string | null>(null);
  const [data, setData] = useState<Record<string, TransactionRecord[]>>({});
  const [loading, setLoading] = useState(true);
  const [openKeys, setOpenKeys] = useState<Set<string>>(new Set());
  const [lineState, setLineState] = useState<
    Record<
      string,
      {
        status: "idle" | "loading" | "loaded" | "error";
        items: any[];
        error?: string;
      }
    >
  >({});

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

  useEffect(() => {
    const firstModel = tables[0]?.model ?? null;
    if (!firstModel) {
      setActiveModel(null);
      return;
    }
    if (!activeModel || !tables.some((t) => t.model === activeModel)) {
      setActiveModel(firstModel);
    }
  }, [tables, activeModel]);

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

  const toggleAccordion = useCallback(
    async (model: string, rec: TransactionRecord) => {
      const key = `${model}-${rec.id}`;
      setOpenKeys((prev) => {
        const next = new Set(prev);
        if (next.has(key)) {
          next.delete(key);
        } else {
          next.add(key);
        }
        return next;
      });

      const state = lineState[key];
      if (state && (state.status === "loaded" || state.status === "loading")) {
        return;
      }

      setLineState((prev) => ({
        ...prev,
        [key]: { status: "loading", items: [] },
      }));

      try {
        const detail = await getRecord(model, rec.id);
        const record = detail?.record ?? detail;
        const lines =
          record?.lines ??
          record?.line_items ??
          record?.items ??
          record?.data?.lines ??
          [];
        setLineState((prev) => ({
          ...prev,
          [key]: { status: "loaded", items: Array.isArray(lines) ? lines : [] },
        }));
      } catch (err: any) {
        setLineState((prev) => ({
          ...prev,
          [key]: {
            status: "error",
            items: [],
            error: err?.message || "Failed to load line items",
          },
        }));
      }
    },
    [lineState],
  );

  // Records for the active tab
  const visibleRecords = useMemo(() => {
    if (!activeModel) return [];
    const label = tables.find((t) => t.model === activeModel)?.label || "";
    return (data[activeModel] ?? []).map((r) => ({
      ...r,
      _model: activeModel,
      _label: label,
    }));
  }, [activeModel, data, tables]);

  return (
    <div
      className={`bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 ${className}`}
    >
      {/* Transaction Tab Bar */}
      <div className="border-b border-slate-200 dark:border-slate-700">
        <nav className="px-4">
          <div className="flex items-center justify-between py-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
            <span>
              Transactions -{" "}
              {tables.find((t) => t.model === activeModel)?.label || ""}
            </span>
            {activeModel && (
              <span className="text-xs text-slate-500 dark:text-slate-400">
                {visibleRecords.length} items
              </span>
            )}
          </div>
          <div className="flex items-center gap-1 py-2 overflow-x-auto">
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
            <FaSpinner className="animate-spin mr-2" /> Loading transactions...
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
                className="divide-y divide-slate-100 dark:divide-slate-700"
              >
                <div
                  className="flex items-center justify-between px-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-700/50 text-xs cursor-pointer"
                  onClick={() => toggleAccordion(rec._model, rec)}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <FaChevronDown
                      size={12}
                      className={`transition-transform ${
                        openKeys.has(`${rec._model}-${rec.id}`)
                          ? "rotate-180"
                          : ""
                      } text-slate-400`}
                    />
                    <span className="font-mono text-slate-500 dark:text-slate-400 shrink-0">
                      {rec.total}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 shrink-0">
                    <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-600 text-slate-600 dark:text-slate-300">
                      total
                    </span>
                    <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-600 text-slate-600 dark:text-slate-300">
                      balance
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

                {openKeys.has(`${rec._model}-${rec.id}`) && (
                  <div className="bg-slate-50 dark:bg-slate-800/50 px-3 py-3 text-xs text-slate-700 dark:text-slate-200">
                    {(() => {
                      const key = `${rec._model}-${rec.id}`;
                      const state = lineState[key];
                      if (!state || state.status === "loading") {
                        return (
                          <div className="flex items-center gap-2 text-slate-500">
                            <FaSpinner className="animate-spin" size={12} />
                            Loading line items...
                          </div>
                        );
                      }
                      if (state.status === "error") {
                        return (
                          <div className="text-red-500">
                            {state.error || "Failed to load line items"}
                          </div>
                        );
                      }
                      if (!state.items || state.items.length === 0) {
                        return (
                          <div className="text-slate-500">
                            No line items found.
                          </div>
                        );
                      }
                      return (
                        <div className="space-y-2">
                          {state.items.map((line: any, idx: number) => {
                            const display = deriveLineDisplay(line, idx + 1);
                            return (
                              <div
                                key={line.id ?? line.line_number ?? idx}
                                className="rounded border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 py-2"
                              >
                                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                                  <div className="flex items-start gap-3 min-w-0">
                                    <span className="font-mono text-slate-500 dark:text-slate-400 shrink-0">
                                      {display.itemId ?? display.lineNumber}
                                    </span>
                                    <div className="min-w-0 space-y-1">
                                      <div className="flex items-center gap-2 min-w-0">
                                        {display.itemCode && (
                                          <span className="font-semibold text-slate-800 dark:text-slate-100">
                                            {display.itemCode}
                                          </span>
                                        )}
                                        <span className="text-slate-700 dark:text-slate-200 truncate">
                                          {display.description || "Line"}
                                        </span>
                                      </div>
                                      <div className="flex flex-wrap gap-3 text-[11px] text-slate-500 dark:text-slate-400">
                                        {display.qtyActive && (
                                          <span>
                                            Active {display.qtyActive}
                                          </span>
                                        )}
                                        {display.qtyRemaining && (
                                          <span>
                                            Remaining {display.qtyRemaining}
                                          </span>
                                        )}
                                        {display.uom && (
                                          <span>UOM {display.uom}</span>
                                        )}
                                        {typeof display.unitPrice ===
                                          "number" && (
                                          <span>
                                            Price{" "}
                                            {formatCurrency(
                                              display.unitPrice,
                                              line.currency || rec.currency,
                                            )}
                                          </span>
                                        )}
                                        {typeof display.unitCost ===
                                          "number" && (
                                          <span>
                                            Cost{" "}
                                            {formatCurrency(
                                              display.unitCost,
                                              line.currency || rec.currency,
                                            )}
                                          </span>
                                        )}
                                        {display.status && (
                                          <span className="uppercase tracking-tight">
                                            {display.status}
                                          </span>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                  <div className="flex flex-col items-end gap-1 text-sm shrink-0">
                                    {display.priceExtended !== undefined && (
                                      <span className="font-semibold text-slate-900 dark:text-white">
                                        {formatCurrency(
                                          display.priceExtended,
                                          line.currency || rec.currency,
                                        )}
                                      </span>
                                    )}
                                    {display.costExtended !== undefined && (
                                      <span className="text-[11px] text-slate-500 dark:text-slate-300">
                                        Cost ext{" "}
                                        {formatCurrency(
                                          display.costExtended,
                                          line.currency || rec.currency,
                                        )}
                                      </span>
                                    )}
                                    {(display.unitPrice !== undefined ||
                                      display.unitCost !== undefined) && (
                                      <span className="text-[11px] text-slate-500 dark:text-slate-400">
                                        Line details
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      );
                    })()}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default TransactionTabs;
