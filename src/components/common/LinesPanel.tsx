/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import React, { useEffect, useMemo, useState } from "react";
import { FaSpinner, FaStream } from "react-icons/fa";
import { getRecord } from "@/api/wcapi";
import LinesCard from "@/apps/transactions/components/LinesCard";

export interface LinesPanelSelection {
  model: string;
  id: number;
  ida?: string;
  name?: string;
}

interface LinesPanelProps {
  selection: LinesPanelSelection | null;
  className?: string;
}

function toArray(value: unknown): any[] {
  return Array.isArray(value) ? value : [];
}

const LinesPanel: React.FC<LinesPanelProps> = ({ selection, className = "" }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lines, setLines] = useState<any[]>([]);

  useEffect(() => {
    let cancelled = false;

    if (!selection?.id || !selection?.model) {
      setLines([]);
      setError(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    getRecord(selection.model, selection.id)
      .then((res: any) => {
        if (cancelled) return;
        const record = res?.record ?? res;
        setLines(toArray(record?.lines));
      })
      .catch((err: any) => {
        if (cancelled) return;
        setLines([]);
        setError(err?.message || "Failed to load lines.");
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selection?.id, selection?.model]);

  const selectionLabel = useMemo(() => {
    if (!selection) return "";
    return selection.ida || selection.name || `#${selection.id}`;
  }, [selection]);

  return (
    <div
      className={`bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 ${className}`}
    >
      <div className="border-b border-slate-200 dark:border-slate-700 px-4 py-2 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 dark:text-slate-200">
          <FaStream size={12} />
          LinesPanel
        </div>
        {selection && (
          <div className="text-xs text-slate-500 dark:text-slate-400 truncate">
            {selection.model} {selectionLabel}
          </div>
        )}
      </div>

      <div className="p-4 max-h-[420px] overflow-y-auto">
        {!selection ? (
          <p className="text-sm text-slate-400 text-center py-6">
            cmd/ctrl-click a transaction row above to load lines.
          </p>
        ) : loading ? (
          <div className="flex items-center justify-center py-8 text-slate-400">
            <FaSpinner className="animate-spin mr-2" /> Loading lines...
          </div>
        ) : error ? (
          <p className="text-sm text-rose-500 text-center py-6">{error}</p>
        ) : lines.length === 0 ? (
          <p className="text-sm text-slate-400 text-center py-6">
            No lines found for this transaction.
          </p>
        ) : (
          <LinesCard
            lines={lines}
            isEditing={false}
            transactionType={selection.model}
          />
        )}
      </div>
    </div>
  );
};

export default LinesPanel;
