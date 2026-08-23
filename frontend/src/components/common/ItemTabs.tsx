/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * ItemTabs - Third-row tab bar for navigating item sub-types (lines & serials)
 *
 * Sits below TransactionTabPanel on org detail pages (Customer, Vendor).
 * Shows a filterable list of line items and serial records linked to the org.
 *
 * Tabs: All · Line Items · Serials
 *
 * @see readmes/tab-navigation.md — Tier 2 Org Tabs → items
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  FaBoxes,
  FaBoxOpen,
  FaBarcode,
  FaExternalLinkAlt,
  FaSpinner,
} from "react-icons/fa";
import { useWindowManager } from "@/context/WindowManagerContext";
import { getModelNames, getRecords } from "@/api/wcapi";
import {
  getModelDetailPath,
  getModelWindowTitle,
} from "@/apps/common/components/panels/getModelDetailPath";
import { formatCurrency } from "@/utils/stringUtils";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type OrgType = "customer" | "vendor";

interface LineItemRecord {
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

interface SerialRecord {
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

type ActiveView = "all" | "lines" | "serials";

export interface ItemTabsProps {
  /** The org type — determines the filter field */
  orgType: OrgType;
  /** Parent org ID to filter items */
  orgId: number;
  /** Additional CSS classes */
  className?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------


const formatQty = (value?: number) =>
  value != null ? value.toLocaleString() : "—";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const ItemTabs: React.FC<ItemTabsProps> = ({
  orgType,
  orgId,
  className = "",
}) => {
  const [activeView, setActiveView] = useState<ActiveView>("all");
  const [lines, setLines] = useState<LineItemRecord[]>([]);
  const [serials, setSerials] = useState<SerialRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [canFetchLines, setCanFetchLines] = useState<boolean | null>(null);

  const windowManager = useWindowManager();

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

  // Fetch lines and serials in parallel
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

  const totalCount = lines.length + serials.length;

  const handleItemClick = useCallback(
    (line: LineItemRecord) => {
      if (!line.item_id) return;
      const path = getModelDetailPath("item", line.item_id);
      const title = getModelWindowTitle(
        "item",
        line.item_id,
        line.item_ida,
        line.item_name,
      );
      windowManager.ensureWindow(path, title, { maximized: false });
    },
    [windowManager],
  );

  const handleSerialClick = useCallback(
    (serial: SerialRecord) => {
      const path = getModelDetailPath("serial", serial.id);
      const title = getModelWindowTitle(
        "serial",
        serial.id,
        serial.ida,
        serial.serial_number,
      );
      windowManager.ensureWindow(path, title, { maximized: false });
    },
    [windowManager],
  );

  // Tab definitions
  const tabs = useMemo(
    () => [
      {
        id: "all" as ActiveView,
        label: "All",
        icon: <FaBoxes size={12} />,
        count: totalCount,
      },
      {
        id: "lines" as ActiveView,
        label: "Line Items",
        icon: <FaBoxOpen size={12} />,
        count: lines.length,
      },
      {
        id: "serials" as ActiveView,
        label: "Serials",
        icon: <FaBarcode size={12} />,
        count: serials.length,
      },
    ],
    [totalCount, lines.length, serials.length],
  );

  // Determine which rows to render
  const showLines = activeView === "all" || activeView === "lines";
  const showSerials = activeView === "all" || activeView === "serials";

  return (
    <div
      className={`bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 ${className}`}
    >
      {/* Item Tab Bar */}
      <div className="border-b border-slate-200 dark:border-slate-700">
        <nav className="px-4">
          <div className="flex items-center gap-1 py-2 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveView(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-md whitespace-nowrap transition-all duration-200 ${
                  activeView === tab.id
                    ? "text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-900/20 border-b-2 border-indigo-600"
                    : "text-slate-500 hover:text-slate-700 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-700"
                }`}
              >
                {tab.icon}
                {tab.label}
                {!loading && tab.count > 0 && (
                  <span className="ml-1 px-1.5 py-0.5 text-xs bg-slate-200 dark:bg-slate-600 rounded-full">
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>
        </nav>
      </div>

      {/* Tab Content — item list */}
      <div className="p-4 max-h-[500px] overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-8 text-slate-400">
            <FaSpinner className="animate-spin mr-2" /> Loading items…
          </div>
        ) : totalCount === 0 ? (
          <p className="text-sm text-slate-400 text-center py-6">
            No items found.
          </p>
        ) : (
          <div className="divide-y divide-slate-100 dark:divide-slate-700 border border-slate-200 dark:border-slate-700 rounded-md overflow-hidden">
            {/* Line Items */}
            {showLines &&
              lines.map((line) => (
                <div
                  key={`line-${line.id}`}
                  className="flex items-center justify-between px-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-700/50 text-xs cursor-pointer"
                  onClick={() => handleItemClick(line)}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    {/* Type badge in "All" view */}
                    {activeView === "all" && (
                      <span className="px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 rounded shrink-0">
                        Line
                      </span>
                    )}
                    <span className="font-mono text-slate-500 dark:text-slate-400 shrink-0">
                      {line.item_ida ?? line.ida ?? `#${line.id}`}
                    </span>
                    <span className="text-slate-800 dark:text-slate-200 truncate">
                      {line.item_name ?? line.description ?? "—"}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 shrink-0">
                    <span className="text-slate-600 dark:text-slate-300">
                      {formatQty(line.quantity)}
                    </span>
                    <span className="text-slate-600 dark:text-slate-300">
                      {formatCurrency(line.unit_price)}
                    </span>
                    <span className="font-medium text-slate-700 dark:text-slate-200">
                      {formatCurrency(line.total)}
                    </span>
                    {line.source_ida && (
                      <span className="text-slate-400 font-mono">
                        {line.source_ida}
                      </span>
                    )}
                    <button
                      type="button"
                      title="Open in floating window"
                      className="p-1 rounded hover:bg-blue-100 dark:hover:bg-blue-900/30 text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                      disabled={!line.item_id}
                      onClick={(e) => {
                        e.stopPropagation();
                        handleItemClick(line);
                      }}
                    >
                      <FaExternalLinkAlt size={10} />
                    </button>
                  </div>
                </div>
              ))}

            {/* Serials */}
            {showSerials &&
              serials.map((serial) => (
                <div
                  key={`serial-${serial.id}`}
                  className="flex items-center justify-between px-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-700/50 text-xs cursor-pointer"
                  onClick={() => handleSerialClick(serial)}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    {/* Type badge in "All" view */}
                    {activeView === "all" && (
                      <span className="px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide bg-violet-50 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400 rounded shrink-0">
                        Serial
                      </span>
                    )}
                    <span className="font-mono text-slate-500 dark:text-slate-400 shrink-0">
                      {serial.serial_number ?? serial.ida ?? `#${serial.id}`}
                    </span>
                    <span className="text-slate-800 dark:text-slate-200 truncate">
                      {serial.item_name ?? "—"}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 shrink-0">
                    {serial.status && (
                      <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-600 text-slate-600 dark:text-slate-300">
                        {serial.status}
                      </span>
                    )}
                    {serial.location && (
                      <span className="text-slate-500 dark:text-slate-400">
                        {serial.location}
                      </span>
                    )}
                    <button
                      type="button"
                      title="Open in floating window"
                      className="p-1 rounded hover:bg-blue-100 dark:hover:bg-blue-900/30 text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleSerialClick(serial);
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

export default ItemTabs;
