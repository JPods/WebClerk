/**
 * RelatedTransactionsPanel — the documents around this one, a tab per kind (Bill, 2026-10-25:
 * an order shows its quote, invoices, purchases and payments).
 *
 * Related means linked: up the parent_model/parent_id chain (the quote an order came from),
 * down it (what was converted from this document, and from those — a quote's orders'
 * invoices, an order's invoices' payments), and payments by their own document link
 * (cash.invoice / .purchase / .receipt). Reads go through the one read channel.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { getRecord, getRecords } from '@/api/wcapi';
import { useWindowManager } from '@/context/WindowManagerContext';
import { formatCurrency } from '@/utils/stringUtils';

type Rec = Record<string, any>;

/** The tabs each document shows, in order. */
const RELATED_TABS: Record<string, string[]> = {
  quote: ['order', 'invoice'],
  order: ['quote', 'invoice', 'purchase', 'workorder', 'cash'],
  invoice: ['cash', 'order', 'quote'],     // payments first: what settled it (Bill, 2026-10-27)
  purchase: ['order', 'receipt', 'cash'],
  receipt: ['purchase', 'cash'],
  workorder: ['order'],
};

const LABELS: Record<string, string> = {
  quote: 'Quote', order: 'Order', invoice: 'Invoice', purchase: 'Purchase',
  workorder: 'Work Order', receipt: 'Receipt', cash: 'Payment',
};

/** The documents a payment names directly (cash.<field> = id). */
const CASH_LINK_FIELDS = new Set(['invoice', 'purchase', 'receipt']);

const amountOf = (model: string, r: Rec) =>
  model === 'cash' ? Number(r.amount ?? 0) : Number(r.totals?.total ?? 0);

// dt_ fields are UTC epoch ms; cash.dt_cash is still a datetime (ISO string), so read both.
const dateOf = (r: Rec) => {
  const v = r.dt_cash || r.dt_created;
  const d = v ? new Date(typeof v === 'string' && !/^\d+$/.test(v) ? v : Number(v)) : null;
  return d && !isNaN(d.getTime()) ? d.toLocaleDateString() : '—';
};

async function childrenOf(model: string, id: number, childModel: string): Promise<Rec[]> {
  const res: any = await getRecords(childModel, { parent_model: model, parent_id: id, limit: 100 });
  return res?.results || [];
}

async function paymentsNaming(model: string, id: number): Promise<Rec[]> {
  if (!CASH_LINK_FIELDS.has(model)) return [];
  const res: any = await getRecords('cash', { [model]: id, limit: 100 });
  return res?.results || [];
}

async function ancestorsOf(record: Rec): Promise<{ model: string; rec: Rec }[]> {
  const found: { model: string; rec: Rec }[] = [];
  let model = record.parent_model, id = record.parent_id;
  for (let hops = 0; model && id && hops < 5; hops++) {
    const resp: any = await getRecord(model, id);
    const rec = resp?.record || resp;
    if (!rec?.id) break;
    found.push({ model, rec });
    model = rec.parent_model; id = rec.parent_id;
  }
  return found;
}

/** Every related document, grouped by model. */
async function loadRelated(modelName: string, record: Rec, tabs: string[]): Promise<Record<string, Rec[]>> {
  const byModel: Record<string, Map<number, Rec>> = Object.fromEntries(tabs.map((t) => [t, new Map()]));
  const add = (m: string, recs: Rec[]) => { if (byModel[m]) recs.forEach((r) => byModel[m].set(r.id, r)); };

  for (const { model, rec } of await ancestorsOf(record)) add(model, [rec]);

  // Down two levels: this document's children, and theirs.
  const docTabs = tabs.filter((t) => t !== 'cash');
  const childModels = ['order', 'invoice', 'purchase', 'workorder', 'receipt'];
  const level1 = await Promise.all(childModels.map(async (m) => ({ m, recs: await childrenOf(modelName, record.id, m) })));
  for (const { m, recs } of level1) add(m, recs);
  for (const { m, recs } of level1.filter((x) => x.recs.length)) {
    for (const r of recs) {
      for (const g of docTabs) add(g, await childrenOf(m, r.id, g));
    }
  }

  if (byModel.cash) {
    add('cash', await childrenOf(modelName, record.id, 'cash'));
    add('cash', await paymentsNaming(modelName, record.id));
    for (const m of ['invoice', 'purchase', 'receipt']) {
      for (const r of byModel[m]?.values() || []) add('cash', await paymentsNaming(m, r.id));
    }
  }
  return Object.fromEntries(Object.entries(byModel).map(([m, map]) => [m, [...map.values()]]));
}

interface Props {
  modelName: string;
  record: Rec;
  /** Stay in-panel (flight simulator); otherwise a window opens. */
  onNavigate?: (model: string, id: number) => void;
}

const RelatedTransactionsPanel: React.FC<Props> = ({ modelName, record, onNavigate }) => {
  const tabs = RELATED_TABS[modelName] || [];
  const windowManager = useWindowManager();
  const [related, setRelated] = useState<Record<string, Rec[]> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState(tabs[0]);

  const load = useCallback(async () => {
    if (!record?.id || !tabs.length) return;
    setError(null);
    try {
      const found = await loadRelated(modelName, record, tabs);
      setRelated(found);
      setActive((a) => (found[a]?.length ? a : tabs.find((t) => found[t]?.length) || a));
    } catch (err: any) {
      setError(err?.message || 'Related documents could not be read');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modelName, record?.id, record?.parent_id, record?.parent_model]);

  useEffect(() => { load(); }, [load]);

  if (!tabs.length || !record?.id) return null;

  const open = (model: string, r: Rec) => {
    if (onNavigate) { onNavigate(model, r.id); return; }
    windowManager.ensureWindow(`/${model}/${r.id}`, `${LABELS[model] || model} ${r.ida || `#${r.id}`}`);
  };

  const rows = related?.[active] || [];
  return (
    <div data-wc="related-transactions" className="rounded-lg border overflow-hidden db-panel no-print">
      <div className="flex items-center gap-1 px-3 pt-2 border-b db-section-bg">
        <span className="text-sm font-semibold db-text mr-2">Related</span>
        {tabs.map((t) => {
          const n = related?.[t]?.length ?? 0;
          return (
            <button key={t} onClick={() => setActive(t)}
              className={`px-3 py-1 text-xs rounded-t ${t === active ? 'db-bg-row-active db-text-accent font-semibold' : 'db-text-muted'}`}>
              {LABELS[t]} <span className="db-text-dim">({related ? n : '…'})</span>
            </button>
          );
        })}
        <button onClick={load} title="Reload" className="ml-auto text-xs db-text-dim px-2">↻</button>
      </div>
      {error ? (
        <div className="p-3 text-xs db-text-red">{error}</div>
      ) : !related ? (
        <div className="p-3 text-xs db-text-dim">Loading…</div>
      ) : !rows.length ? (
        <div className="p-3 text-xs db-text-dim">No {LABELS[active].toLowerCase()} linked to this {modelName}.</div>
      ) : (
        <table className="w-full text-xs">
          <thead>
            <tr className="db-text-muted text-left">
              <th className="px-3 py-1 font-medium">{LABELS[active]}</th>
              <th className="px-3 py-1 font-medium">status</th>
              <th className="px-3 py-1 font-medium">date</th>
              <th className="px-3 py-1 font-medium text-right">{active === 'cash' ? 'amount' : 'total'}</th>
              {active !== 'cash' && <th className="px-3 py-1 font-medium text-right">balance</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} onClick={() => open(active, r)} className="cursor-pointer hover:db-bg-row-active border-t db-border-color">
                <td className="px-3 py-1 font-mono db-text-accent">{r.ida || `#${r.id}`}</td>
                <td className="px-3 py-1">{r.status || '—'}</td>
                <td className="px-3 py-1">{dateOf(r)}</td>
                <td className="px-3 py-1 text-right font-mono">{formatCurrency(amountOf(active, r))}</td>
                {active !== 'cash' && <td className="px-3 py-1 text-right font-mono">{formatCurrency(Number(r.totals?.balance ?? 0))}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default RelatedTransactionsPanel;
