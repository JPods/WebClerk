/**
 * TransactionFlowIndicator — horizontal lineage strip for transaction detail pages.
 *
 * Shows the document chain: Proposal → Order → Invoice → Payment
 * Walks up via parent_id/parent_model, down via flow.children.
 * Current document highlighted. Clickable nodes open in WindowManager.
 */
import { useEffect, useState, useCallback } from 'react';
import { useWindowManager } from '@/context/WindowManagerContext';
import { getRecord } from '@/api/wcapi';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FlowNode {
  model: string;
  id: number;
  ida?: string;
  status?: string;
  isCurrent: boolean;
}

interface TransactionFlowIndicatorProps {
  modelName: string;
  record: {
    id: number;
    ida?: string;
    status?: string;
    parent_id?: number | null;
    parent_model?: string | null;
    refs?: { source?: Record<string, unknown> };
    flow?: { children?: Array<{ type: string; id: number }> };
  };
  /** If provided, clicking a node calls this instead of opening a new window.
   *  Used by flight simulator to stay in-panel. */
  onNavigate?: (model: string, id: number) => void;
}

// Canonical order for the flow strip
const FLOW_ORDER: Record<string, number> = {
  proposal: 0,
  order: 1,
  invoice: 2,
  payment: 3,
};

const MODEL_LABELS: Record<string, string> = {
  proposal: 'Proposal',
  order: 'Order',
  invoice: 'Invoice',
  payment: 'Payment',
  purchase: 'Purchase',
  receipt: 'Receipt',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function TransactionFlowIndicator({ modelName, record, onNavigate }: TransactionFlowIndicatorProps) {
  const [nodes, setNodes] = useState<FlowNode[]>([]);
  const [loading, setLoading] = useState(true);
  const windowManager = useWindowManager();

  const buildChain = useCallback(async () => {
    if (!record?.id) return;
    setLoading(true);

    const chain: FlowNode[] = [];
    const seen = new Set<string>();
    const key = (m: string, id: number) => `${m}:${id}`;

    // Add current node
    chain.push({
      model: modelName,
      id: record.id,
      ida: record.ida,
      status: record.status,
      isCurrent: true,
    });
    seen.add(key(modelName, record.id));

    // Walk UP via parent_id/parent_model
    let walkModel = record.parent_model;
    let walkId = record.parent_id;

    // Fallback: check refs.source if no parent_id
    if (!walkId && record.refs?.source) {
      const src = record.refs.source;
      if (src.proposal_id) { walkModel = 'proposal'; walkId = src.proposal_id as number; }
      else if (src.order_id) { walkModel = 'order'; walkId = src.order_id as number; }
    }

    let safety = 5;
    while (walkModel && walkId && safety-- > 0) {
      const k = key(walkModel, walkId);
      if (seen.has(k)) break;
      seen.add(k);

      try {
        const resp = await getRecord(walkModel, walkId);
        const rec = resp?.record || resp;
        chain.push({
          model: walkModel,
          id: walkId,
          ida: rec?.ida,
          status: rec?.status,
          isCurrent: false,
        });

        // Continue up
        const nextModel = rec?.parent_model;
        const nextId = rec?.parent_id;
        if (nextModel && nextId) {
          walkModel = nextModel;
          walkId = nextId;
        } else if (rec?.refs?.source) {
          const src = rec.refs.source;
          if (src.proposal_id) { walkModel = 'proposal'; walkId = src.proposal_id; }
          else if (src.order_id) { walkModel = 'order'; walkId = src.order_id; }
          else break;
        } else break;
      } catch {
        break;
      }
    }

    // Walk DOWN via flow.children
    if (record.flow?.children?.length) {
      for (const child of record.flow.children) {
        const k = key(child.type, child.id);
        if (seen.has(k)) continue;
        seen.add(k);
        try {
          const resp = await getRecord(child.type, child.id);
          const rec = resp?.record || resp;
          chain.push({
            model: child.type,
            id: child.id,
            ida: rec?.ida,
            status: rec?.status,
            isCurrent: false,
          });
        } catch { /* child not accessible */ }
      }
    }

    // Sort by canonical flow order
    chain.sort((a, b) => (FLOW_ORDER[a.model] ?? 99) - (FLOW_ORDER[b.model] ?? 99));

    setNodes(chain);
    setLoading(false);
  }, [modelName, record?.id, record?.parent_id, record?.parent_model]);

  useEffect(() => { buildChain(); }, [buildChain]);

  // Don't render if only current node (no chain to show)
  if (!loading && nodes.length <= 1) return null;
  if (loading) return null;

  const handleClick = (node: FlowNode) => {
    if (node.isCurrent) return;
    if (onNavigate) {
      // Stay in-panel (flight simulator)
      onNavigate(node.model, node.id);
    } else {
      // Open in new window (normal mode)
      const path = `/${node.model}/${node.id}`;
      const label = MODEL_LABELS[node.model] || node.model;
      const title = `${label} ${node.ida || `#${node.id}`}`;
      windowManager.ensureWindow(path, title);
    }
  };

  return (
    <div data-wc="transaction-flow-indicator" className="flex items-center gap-1 px-1 py-1.5 text-xs no-print">
      {nodes.map((node, i) => {
        const label = MODEL_LABELS[node.model] || node.model;
        const display = node.ida || `#${node.id}`;

        return (
          <div key={`${node.model}-${node.id}`} className="flex items-center gap-1">
            {i > 0 && (
              <span className="text-slate-400 dark:text-slate-500 text-[10px]">→</span>
            )}
            <button
              onClick={() => handleClick(node)}
              disabled={node.isCurrent}
              className={`
                px-2 py-0.5 rounded text-[11px] font-medium transition
                ${node.isCurrent
                  ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 ring-1 ring-blue-300 dark:ring-blue-700 cursor-default'
                  : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600 cursor-pointer'
                }
              `}
              title={`${label} ${display} — ${node.status || 'unknown'}`}
            >
              {label} {display}
              {node.status && (
                <span className={`ml-1 text-[9px] opacity-70`}>
                  ({node.status})
                </span>
              )}
            </button>
          </div>
        );
      })}
    </div>
  );
}
