/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * RelatedTransactions - Shows only parent/child related transactions
 *
 * Used on Transaction detail pages to show direct relationships:
 * - Parent transaction (via parent_id / parent_model)
 * - Child transactions (via flow.children)
 *
 * Does NOT show all transactions for the linked org — only direct relationships.
 *
 * @see TransactionTabPanel for org pages that show org transactions by selected type
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  FaArrowUp,
  FaArrowDown,
  FaExternalLinkAlt,
  FaLink,
  FaSpinner,
} from "react-icons/fa";
import { useWindowManager } from "@/context/WindowManagerContext";
import { getRecord } from "@/api/wcapi";
import {
  getModelDetailPath,
  getModelWindowTitle,
} from "@/apps/common/components/panels/getModelDetailPath";
import { formatDt } from '@/utils/fieldFormatters';
import { formatCurrency } from '@/utils/stringUtils';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface TransactionFlow {
  source?: Array<{ type: string; id: number }>;
  children?: Array<{ type: string; id: number }>;
}

interface TransactionData {
  id: number;
  ida?: string;
  name?: string;
  status?: string;
  total?: number;
  currency?: string;
  dt_created?: number;
  parent_id?: number | null;
  parent_model?: string | null;
  flow?: TransactionFlow;
}

interface RelatedRecord {
  model: string;
  record: TransactionData;
  relationship: "parent" | "child";
}

export interface RelatedTransactionsProps {
  /** The current transaction data */
  transaction: TransactionData;
  /** Optional CSS classes */
  className?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const formatDate = (ts?: number) => {
  if (!ts) return "—";
  return formatDt(ts, 'date');
};


const modelLabel = (model: string): string => {
  const labels: Record<string, string> = {
    order: "Order",
    invoice: "Invoice",
    proposal: "Proposal",
    purchase: "Purchase",
    receipt: "Receipt",
    payment: "Payment",
    ledger: "Ledger",
  };
  return labels[model] || model.charAt(0).toUpperCase() + model.slice(1);
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const RelatedTransactions: React.FC<RelatedTransactionsProps> = ({
  transaction,
  className = "",
}) => {
  const [relatedRecords, setRelatedRecords] = useState<RelatedRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const windowManager = useWindowManager();

  // Fetch parent and child transactions
  useEffect(() => {
    if (!transaction?.id) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);

    const fetchRelated = async () => {
      const records: RelatedRecord[] = [];

      // Fetch parent if exists
      if (transaction.parent_id && transaction.parent_model) {
        try {
          const parentData = await getRecord(
            transaction.parent_model,
            transaction.parent_id
          );
          if (parentData?.record) {
            records.push({
              model: transaction.parent_model,
              record: parentData.record,
              relationship: "parent",
            });
          }
        } catch (err) {
          console.warn("Failed to fetch parent transaction:", err);
        }
      }

      // Fetch children from flow.children
      const children = transaction.flow?.children ?? [];
      for (const child of children) {
        if (child.type && child.id && child.id > 0) {
          try {
            const childData = await getRecord(child.type, child.id);
            if (childData?.record) {
              records.push({
                model: child.type,
                record: childData.record,
                relationship: "child",
              });
            }
          } catch (err) {
            console.warn(`Failed to fetch child ${child.type}/${child.id}:`, err);
          }
        }
      }

      if (!cancelled) {
        setRelatedRecords(records);
        setLoading(false);
      }
    };

    fetchRelated();

    return () => {
      cancelled = true;
    };
  }, [transaction?.id, transaction?.parent_id, transaction?.parent_model, transaction?.flow]);

  const handleRowClick = useCallback(
    (model: string, rec: TransactionData) => {
      const path = getModelDetailPath(model, rec.id);
      const title = getModelWindowTitle(model, rec.id, rec.ida, rec.name);
      windowManager.ensureWindow(path, title, { maximized: false });
    },
    [windowManager]
  );

  // Separate parent and children
  const parentRecords = useMemo(
    () => relatedRecords.filter((r) => r.relationship === "parent"),
    [relatedRecords]
  );
  const childRecords = useMemo(
    () => relatedRecords.filter((r) => r.relationship === "child"),
    [relatedRecords]
  );

  // Don't render anything if no related transactions
  if (!loading && relatedRecords.length === 0) {
    return null;
  }

  return (
    <div
      className={`bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 ${className}`}
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-300">
          <FaLink size={14} />
          Related Transactions
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {loading ? (
          <div className="flex items-center justify-center py-4 text-slate-400">
            <FaSpinner className="animate-spin mr-2" /> Loading…
          </div>
        ) : (
          <div className="space-y-4">
            {/* Parent Section */}
            {parentRecords.length > 0 && (
              <div>
                <div className="flex items-center gap-2 text-xs font-medium text-slate-500 dark:text-slate-400 mb-2">
                  <FaArrowUp size={10} />
                  Parent
                </div>
                <div className="divide-y divide-slate-100 dark:divide-slate-700 border border-slate-200 dark:border-slate-700 rounded-md overflow-hidden">
                  {parentRecords.map((rel) => (
                    <div
                      key={`parent-${rel.model}-${rel.record.id}`}
                      className="flex items-center justify-between px-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-700/50 text-xs cursor-pointer"
                      onClick={() => handleRowClick(rel.model, rel.record)}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <span className="px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded shrink-0">
                          {modelLabel(rel.model)}
                        </span>
                        <span className="font-mono text-slate-500 dark:text-slate-400 shrink-0">
                          {rel.record.ida ?? `#${rel.record.id}`}
                        </span>
                        <span className="text-slate-800 dark:text-slate-200 truncate">
                          {rel.record.name ?? "—"}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 shrink-0">
                        {rel.record.status && (
                          <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-600 text-slate-600 dark:text-slate-300">
                            {rel.record.status}
                          </span>
                        )}
                        <span className="text-slate-600 dark:text-slate-300">
                          {formatCurrency(rel.record.totals?.total)}
                        </span>
                        <span className="text-slate-400">
                          {formatDate(rel.record.dt_created)}
                        </span>
                        <button
                          type="button"
                          title="Open in floating window"
                          className="p-1 rounded hover:bg-blue-100 dark:hover:bg-blue-900/30 text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRowClick(rel.model, rel.record);
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

            {/* Children Section */}
            {childRecords.length > 0 && (
              <div>
                <div className="flex items-center gap-2 text-xs font-medium text-slate-500 dark:text-slate-400 mb-2">
                  <FaArrowDown size={10} />
                  Children ({childRecords.length})
                </div>
                <div className="divide-y divide-slate-100 dark:divide-slate-700 border border-slate-200 dark:border-slate-700 rounded-md overflow-hidden">
                  {childRecords.map((rel) => (
                    <div
                      key={`child-${rel.model}-${rel.record.id}`}
                      className="flex items-center justify-between px-3 py-2 hover:bg-slate-50 dark:hover:bg-slate-700/50 text-xs cursor-pointer"
                      onClick={() => handleRowClick(rel.model, rel.record)}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <span className="px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400 rounded shrink-0">
                          {modelLabel(rel.model)}
                        </span>
                        <span className="font-mono text-slate-500 dark:text-slate-400 shrink-0">
                          {rel.record.ida ?? `#${rel.record.id}`}
                        </span>
                        <span className="text-slate-800 dark:text-slate-200 truncate">
                          {rel.record.name ?? "—"}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 shrink-0">
                        {rel.record.status && (
                          <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-600 text-slate-600 dark:text-slate-300">
                            {rel.record.status}
                          </span>
                        )}
                        <span className="text-slate-600 dark:text-slate-300">
                          {formatCurrency(rel.record.totals?.total)}
                        </span>
                        <span className="text-slate-400">
                          {formatDate(rel.record.dt_created)}
                        </span>
                        <button
                          type="button"
                          title="Open in floating window"
                          className="p-1 rounded hover:bg-blue-100 dark:hover:bg-blue-900/30 text-slate-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRowClick(rel.model, rel.record);
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
        )}
      </div>
    </div>
  );
};

export default RelatedTransactions;
