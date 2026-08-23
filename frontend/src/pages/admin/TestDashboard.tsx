/**
 * TestDashboard — Alice's testing and training dashboard.
 *
 * Shows all records from test sequences with live inventory state,
 * clickable links to each record, and a test journal.
 *
 * Route: /test-dashboard
 */
import React, { useCallback, useEffect, useState } from 'react';
import { getRecords, getRecord, manageAction } from '@/api/wcapi';
import { formatDt } from '@/utils/fieldFormatters';
import RecordLink from '@/components/common/RecordLink';
import { formatCurrency } from '@/utils/stringUtils';

interface InventoryImpact {
  type: string;        // 'invoice_line', 'order_line', 'purchase_line', 'proposal_line', 'inventory_layer', 'pending_adjustment'
  id: number;
  parentModel: string; // 'invoice', 'order', 'purchase', 'proposal'
  parentId: number;
  parentIda: string;
  lineNumber?: number;
  qtyField: string;    // which item.quantity field this impacts
  qtyDelta: number;    // +/- change
  description: string;
  dt: number;
}

interface TestRecord {
  model: string;
  id: number;
  ida: string;
  label: string;
  status?: string;
  amount?: number;
}

interface JournalEntry {
  dt: string;
  action: string;
  detail: string;
  pass?: boolean;
}

function GLJournalSection() {
  const [glEntries, setGlEntries] = useState<any[]>([]);
  const [journalResult, setJournalResult] = useState<any>(null);
  const [running, setRunning] = useState(false);

  const loadGLEntries = useCallback(async () => {
    try {
      const res = await getRecords('gl_journal', { ordering: '-dt_created', limit: 50 }) as any;
      setGlEntries(res?.results || []);
    } catch { setGlEntries([]); }
  }, []);

  useEffect(() => { loadGLEntries(); }, [loadGLEntries]);

  const handleBatchJournalize = async () => {
    setRunning(true);
    try {
      const res = await manageAction('batch_journalize', { ida_prefix: 'zzz-' });
      setJournalResult(res);
      await loadGLEntries();
    } catch (e: any) {
      setJournalResult({ error: e.message });
    }
    setRunning(false);
  };

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 mb-6">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-bold text-gray-700 dark:text-gray-300">GL Journal ({glEntries.length})</h2>
        <button
          onClick={handleBatchJournalize}
          disabled={running}
          className="px-3 py-1 text-xs font-bold rounded bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {running ? 'Journalizing...' : 'Batch Journalize (zzz-)'}
        </button>
      </div>

      {journalResult && (
        <div className={`mb-3 p-2 rounded text-xs ${journalResult.error ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}>
          {journalResult.error ? (
            <span>Error: {journalResult.error}</span>
          ) : (
            <span>
              Created {journalResult.total_created} journal entries —
              {' '}{journalResult.invoices?.length || 0} invoices,
              {' '}{journalResult.payments?.length || 0} payments,
              {' '}{journalResult.purchases?.length || 0} purchases
              {journalResult.errors?.length > 0 && (
                <span className="text-orange-600"> | Errors: {journalResult.errors.join('; ')}</span>
              )}
            </span>
          )}
        </div>
      )}

      {glEntries.length > 0 ? (
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-gray-200 dark:border-gray-700 text-left">
              <th className="py-2 pr-2 text-gray-500">IDA</th>
              <th className="py-2 pr-2 text-gray-500">Account</th>
              <th className="py-2 pr-2 text-gray-500 text-right">Debit</th>
              <th className="py-2 pr-2 text-gray-500 text-right">Credit</th>
              <th className="py-2 pr-2 text-gray-500">Type</th>
              <th className="py-2 pr-2 text-gray-500">Source</th>
              <th className="py-2 text-gray-500">When</th>
            </tr>
          </thead>
          <tbody>
            {glEntries.map((e: any) => (
              <tr key={e.id} className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800">
                <td className="py-1.5 pr-2 font-mono text-gray-600">{e.ida || '—'}</td>
                <td className="py-1.5 pr-2 font-mono font-semibold">{e.account}</td>
                <td className="py-1.5 pr-2 text-right font-mono text-green-600">{e.debit ? formatCurrency(e.debit) : ''}</td>
                <td className="py-1.5 pr-2 text-right font-mono text-red-600">{e.credit ? formatCurrency(e.credit) : ''}</td>
                <td className="py-1.5 pr-2">
                  <span className={`text-[9px] px-1 py-0.5 rounded font-bold uppercase ${
                    e.type === 'sales' ? 'bg-yellow-100 text-yellow-700' :
                    e.type === 'purchase' ? 'bg-red-100 text-red-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>{e.type}</span>
                </td>
                <td className="py-1.5 pr-2 text-gray-500">{e.source_model} #{e.source_id}</td>
                <td className="py-1.5 text-gray-400 text-[10px]">{e.dt_created ? formatDt(e.dt_created, 'datetime', 'dt_created') : '—'}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            {/* Admin audit tool — GL balance verification requires client-side sum */}
            <tr className="border-t-2 border-gray-300 dark:border-gray-600 font-bold">
              <td className="py-2 pr-2" colSpan={2}>Totals</td>
              <td className="py-2 pr-2 text-right font-mono text-green-700">
                ${glEntries.reduce((s: number, e: any) => s + (e.debit || 0), 0).toFixed(2)}
              </td>
              <td className="py-2 pr-2 text-right font-mono text-red-700">
                ${glEntries.reduce((s: number, e: any) => s + (e.credit || 0), 0).toFixed(2)}
              </td>
              <td colSpan={3} className="py-2 text-gray-400">
                {(() => {
                  const d = glEntries.reduce((s: number, e: any) => s + (e.debit || 0), 0);
                  const c = glEntries.reduce((s: number, e: any) => s + (e.credit || 0), 0);
                  const diff = Math.abs(d - c);
                  return diff < 0.01 ? '✓ Balanced' : `⚠ Out of balance by ${formatCurrency(diff)}`;
                })()}
              </td>
            </tr>
          </tfoot>
        </table>
      ) : (
        <div className="text-xs text-gray-400">No GL journal entries. Click "Batch Journalize" to post.</div>
      )}
    </div>
  );
}

export default function TestDashboard() {
  const [itemData, setItemData] = useState<any>(null);
  const [testRecords, setTestRecords] = useState<TestRecord[]>([]);
  const [journal, setJournal] = useState<JournalEntry[]>([]);
  const [impacts, setImpacts] = useState<InventoryImpact[]>([]);
  const [loading, setLoading] = useState(true);
  const [itemId, setItemId] = useState(308);

  // Period selection — default to last 24 hours
  // Snapshot the start time so it doesn't recalculate on every render
  const [periodHours, setPeriodHours] = useState(24);
  const [periodStart, setPeriodStart] = useState(() => Date.now() - (24 * 60 * 60 * 1000));

  // Update periodStart only when periodHours changes or Refresh is clicked
  const updatePeriod = useCallback(() => {
    setPeriodStart(Date.now() - (periodHours * 60 * 60 * 1000));
  }, [periodHours]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      // Load item
      const itemRes = await getRecord('item', itemId) as any;
      setItemData(itemRes?.record || itemRes);

      // Load inventory impacts — all lines referencing this item
      const impactList: InventoryImpact[] = [];

      // Invoice lines → on_hand decrease, on_so decrease
      // Query by both item_fk (Alice/shell) and item__item_id (UI-created)
      const invLines1 = await getRecords('invoice_line', { item_fk: itemId, dt_created__gte: periodStart, limit: 50 }) as any;
      const invLines2 = await getRecords('invoice_line', { item__item_id: itemId, dt_created__gte: periodStart, limit: 50 }) as any;
      const invLineIds = new Set<number>();
      const invLines = { results: [...(invLines1?.results || []), ...(invLines2?.results || [])].filter((r: any) => { if (invLineIds.has(r.id)) return false; invLineIds.add(r.id); return true; }) };
      for (const l of (invLines?.results || [])) {
        const qty = l.quantity?.active || l.quantity?.staged || 0;
        if (qty) {
          // Get parent invoice
          const parentId = l.invoice_id || l.invoice;
          let parentIda = '';
          try { const p = await getRecord('invoice', parentId) as any; parentIda = p?.record?.ida || `#${parentId}`; } catch {}
          impactList.push({ type: 'invoice_line', id: l.id, parentModel: 'invoice', parentId, parentIda, lineNumber: l.line_number, qtyField: 'on_hand / on_so', qtyDelta: -qty, description: `Shipped ${qty} → on_hand -${qty}, on_so -${qty}`, dt: l.dt_created });
        }
      }

      // Order lines → on_so increase
      const ordLines1 = await getRecords('order_line', { item_fk: itemId, dt_created__gte: periodStart, limit: 50 }) as any;
      const ordLines2 = await getRecords('order_line', { item__item_id: itemId, dt_created__gte: periodStart, limit: 50 }) as any;
      const ordLineIds = new Set<number>();
      const ordLines = { results: [...(ordLines1?.results || []), ...(ordLines2?.results || [])].filter((r: any) => { if (ordLineIds.has(r.id)) return false; ordLineIds.add(r.id); return true; }) };
      for (const l of (ordLines?.results || [])) {
        const qty = l.quantity?.active || l.quantity?.staged || 0;
        if (qty) {
          const parentId = l.order_id || l.order;
          let parentIda = '';
          try { const p = await getRecord('order', parentId) as any; parentIda = p?.record?.ida || `#${parentId}`; } catch {}
          impactList.push({ type: 'order_line', id: l.id, parentModel: 'order', parentId, parentIda, lineNumber: l.line_number, qtyField: 'on_so', qtyDelta: qty, description: `Ordered ${qty} → on_so +${qty}`, dt: l.dt_created });
        }
      }

      // Proposal lines → on_p increase
      const propLines1 = await getRecords('proposal_line', { item_fk: itemId, dt_created__gte: periodStart, limit: 50 }) as any;
      const propLines2 = await getRecords('proposal_line', { item__item_id: itemId, dt_created__gte: periodStart, limit: 50 }) as any;
      const propLineIds = new Set<number>();
      const propLines = { results: [...(propLines1?.results || []), ...(propLines2?.results || [])].filter((r: any) => { if (propLineIds.has(r.id)) return false; propLineIds.add(r.id); return true; }) };
      for (const l of (propLines?.results || [])) {
        const qty = l.quantity?.active || l.quantity?.staged || 0;
        if (qty) {
          const parentId = l.proposal_id || l.proposal;
          let parentIda = '';
          try { const p = await getRecord('proposal', parentId) as any; parentIda = p?.record?.ida || `#${parentId}`; } catch {}
          impactList.push({ type: 'proposal_line', id: l.id, parentModel: 'proposal', parentId, parentIda, lineNumber: l.line_number, qtyField: 'on_p', qtyDelta: qty, description: `Quoted ${qty} → on_p +${qty}`, dt: l.dt_created });
        }
      }

      // Purchase lines → on_po increase
      const poLines1 = await getRecords('purchase_line', { item_fk: itemId, dt_created__gte: periodStart, limit: 50 }) as any;
      const poLines2 = await getRecords('purchase_line', { item__item_id: itemId, dt_created__gte: periodStart, limit: 50 }) as any;
      const poLineIds = new Set<number>();
      const poLines = { results: [...(poLines1?.results || []), ...(poLines2?.results || [])].filter((r: any) => { if (poLineIds.has(r.id)) return false; poLineIds.add(r.id); return true; }) };
      for (const l of (poLines?.results || [])) {
        const qty = l.quantity?.active || l.quantity?.staged || 0;
        if (qty) {
          const parentId = l.purchase_id || l.purchase;
          let parentIda = '';
          try { const p = await getRecord('purchase', parentId) as any; parentIda = p?.record?.ida || `#${parentId}`; } catch {}
          impactList.push({ type: 'purchase_line', id: l.id, parentModel: 'purchase', parentId, parentIda, lineNumber: l.line_number, qtyField: 'on_po', qtyDelta: qty, description: `PO'd ${qty} → on_po +${qty}`, dt: l.dt_created });
        }
      }

      // Inventory layers → on_hand increase (receiving)
      const layers = await getRecords('inventory_layer', { item: itemId, dt_created__gte: periodStart, limit: 50 }) as any;
      for (const l of (layers?.results || [])) {
        const qty = l.quantity?.received || 0;
        const issued = l.quantity?.issued || 0;
        if (qty) {
          const srcId = l.source?.id;
          const srcType = l.source?.type || 'unknown';
          impactList.push({ type: 'inventory_layer', id: l.id, parentModel: srcType, parentId: srcId || 0, parentIda: `${srcType} #${srcId}`, qtyField: 'on_hand', qtyDelta: qty - issued, description: `Received ${qty}, issued ${issued} → net on_hand +${qty - issued}`, dt: l.dt_created });
        }
      }

      // Pending inventory adjustments
      // Pending inventory adjustments — query ALL then filter by item_id in request_ref
      const pending = await getRecords('pending_inventory_adjustment', { dt_created__gte: periodStart, limit: 100 }) as any;
      for (const p of (pending?.results || [])) {
        const ref = p.request_ref || {};
        const pendingItemId = ref.item_id;
        if (pendingItemId === itemId || !itemId) {
          const field = ref.field || 'on_hand';
          const delta = ref.delta || parseFloat(p.qty) || 0;
          const originalQty = parseFloat(p.qty) || delta;
          const stateLabel = p.state === 'applied' ? `✓ applied ${originalQty}` : p.state === 'pending' ? `⏳ pending ${originalQty}` : `✗ canceled ${originalQty}`;
          impactList.push({
            type: 'pending_adjustment',
            id: p.id,
            parentModel: ref.source_type || 'pending',
            parentId: ref.source_id || 0,
            parentIda: `${stateLabel} — ${p.reason || 'adjustment'}`,
            qtyField: field,
            qtyDelta: delta,
            description: `${stateLabel} (${field} ${delta >= 0 ? '+' : ''}${delta})`,
            dt: ref.dt_requested || p.dt_created,
          });
        }
      }

      impactList.sort((a, b) => (a.dt || 0) - (b.dt || 0));
      setImpacts(impactList);

      // Find test records by ida prefix patterns
      const records: TestRecord[] = [];
      const journalEntries: JournalEntry[] = [];

      // Customers
      const custRes = await getRecords('customer', { keyword: 'alice-test', limit: 10 }) as any;
      (custRes?.results || []).forEach((r: any) => {
        records.push({ model: 'customer', id: r.id, ida: r.ida || '', label: r.display_name || r.ida, status: r.status });
        journalEntries.push({ dt: formatDt(r.dt_created, 'datetime', 'dt_created'), action: 'Customer created', detail: `${r.display_name} (id=${r.id})` });
      });

      // Also check user-created test records
      const custRes2 = await getRecords('customer', { keyword: 'Test Cycle', limit: 10 }) as any;
      (custRes2?.results || []).forEach((r: any) => {
        if (!records.find(x => x.id === r.id)) {
          records.push({ model: 'customer', id: r.id, ida: r.ida || '', label: r.display_name || r.ida, status: r.status });
          journalEntries.push({ dt: formatDt(r.dt_created, 'datetime', 'dt_created'), action: 'Customer created (UI)', detail: `${r.display_name} (id=${r.id})` });
        }
      });

      // Proposals
      const propRes = await getRecords('proposal', { keyword: 'alice', limit: 10 }) as any;
      (propRes?.results || []).forEach((r: any) => {
        records.push({ model: 'proposal', id: r.id, ida: r.ida || '', label: `Proposal ${r.ida}`, status: r.status, amount: r.total });
        journalEntries.push({ dt: formatDt(r.dt_created, 'datetime', 'dt_created'), action: 'Proposal created', detail: `${r.ida} total=${r.total}` });
      });

      // Orders
      const ordRes = await getRecords('order', { keyword: 'alice', limit: 10 }) as any;
      (ordRes?.results || []).forEach((r: any) => {
        records.push({ model: 'order', id: r.id, ida: r.ida || '', label: `Order ${r.ida}`, status: r.status, amount: r.total });
        journalEntries.push({ dt: formatDt(r.dt_created, 'datetime', 'dt_created'), action: 'Order created', detail: `${r.ida} total=${r.total}` });
      });

      // Purchases
      const poRes = await getRecords('purchase', { keyword: 'alice', limit: 10 }) as any;
      (poRes?.results || []).forEach((r: any) => {
        records.push({ model: 'purchase', id: r.id, ida: r.ida || '', label: `PO ${r.ida}`, status: r.status, amount: r.total });
        journalEntries.push({ dt: formatDt(r.dt_created, 'datetime', 'dt_created'), action: 'PO created', detail: `${r.ida} total=${r.total}` });
      });

      // Invoices
      const invRes = await getRecords('invoice', { keyword: 'alice', limit: 10 }) as any;
      (invRes?.results || []).forEach((r: any) => {
        records.push({ model: 'invoice', id: r.id, ida: r.ida || '', label: `Invoice ${r.ida}`, status: r.status, amount: r.total });
        journalEntries.push({ dt: formatDt(r.dt_created, 'datetime', 'dt_created'), action: 'Invoice created', detail: `${r.ida} total=${r.total} balance=${r.balance}` });
      });

      // Contacts
      const contRes = await getRecords('contact', { keyword: 'alice-test', limit: 10 }) as any;
      (contRes?.results || []).forEach((r: any) => {
        records.push({ model: 'contact', id: r.id, ida: r.ida || '', label: `${r.name_first} ${r.name_last}` });
        journalEntries.push({ dt: formatDt(r.dt_created, 'datetime', 'dt_created'), action: 'Contact created', detail: `${r.email}` });
      });

      // Emails
      const emailRes = await getRecords('email', { keyword: 'alice-test', limit: 10 }) as any;
      (emailRes?.results || []).forEach((r: any) => {
        records.push({ model: 'email', id: r.id, ida: r.ida || '', label: r.email });
      });

      // Phones
      const phoneRes = await getRecords('phone', { keyword: 'ALICE', limit: 10 }) as any;
      (phoneRes?.results || []).forEach((r: any) => {
        records.push({ model: 'phone', id: r.id, ida: r.ida || '', label: r.number });
      });

      // Sort journal by date
      journalEntries.sort((a, b) => a.dt.localeCompare(b.dt));

      setTestRecords(records);
      setJournal(journalEntries);
    } catch (e) {
      console.error('TestDashboard load failed:', e);
    }
    finally { setLoading(false); }
  }, [itemId, periodStart]);

  useEffect(() => { loadData(); }, [loadData]);

  const q = itemData?.quantity || {};

  return (
    <div className="max-w-5xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Test Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">Alice's testing and training review tool</p>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500">Item:</label>
          <input type="number" value={itemId} onChange={(e) => setItemId(parseInt(e.target.value) || 308)}
            className="w-20 px-2 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800" />
          <label className="text-xs text-gray-500">Period:</label>
          <select value={periodHours} onChange={(e) => { setPeriodHours(parseInt(e.target.value)); setPeriodStart(Date.now() - (parseInt(e.target.value) * 60 * 60 * 1000)); }}
            className="px-2 py-1 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-800">
            <option value={1}>Last 1 hour</option>
            <option value={4}>Last 4 hours</option>
            <option value={24}>Last 24 hours</option>
            <option value={72}>Last 3 days</option>
            <option value={168}>Last 7 days</option>
            <option value={720}>Last 30 days</option>
            <option value={8760}>Last year</option>
            <option value={87600}>All time</option>
          </select>
          <button onClick={loadData} className="px-3 py-1 text-xs font-medium rounded bg-blue-600 text-white hover:bg-blue-700">Refresh</button>
        </div>
      </div>

      {loading && <div className="text-gray-500 py-8 text-center">Loading test data...</div>}

      {!loading && (
        <>
          {/* Item Inventory State */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 mb-6 bg-gray-50 dark:bg-gray-800">
            <h2 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-3">
              Item {itemId}: {itemData?.name || '?'} (ida: {itemData?.ida || '?'})
            </h2>
            <div className="grid grid-cols-5 gap-4">
              {[
                { key: 'on_hand', label: 'On Hand', color: 'blue' },
                { key: 'on_po', label: 'On PO', color: 'purple' },
                { key: 'on_so', label: 'On SO', color: 'green' },
                { key: 'on_p', label: 'On Proposal', color: 'yellow' },
                { key: 'available', label: 'Available', color: 'emerald' },
              ].map(({ key, label, color }) => (
                <div key={key} className={`text-center p-3 rounded-lg border border-${color}-200 dark:border-${color}-800 bg-${color}-50 dark:bg-${color}-900/20`}>
                  <div className={`text-2xl font-bold text-${color}-700 dark:text-${color}-400`}>{q[key] ?? '—'}</div>
                  <div className="text-[10px] font-semibold text-gray-500 uppercase mt-1">{label}</div>
                </div>
              ))}
            </div>
            <div className="mt-3 text-xs text-gray-500">
              Price: ${itemData?.price?.base ?? '?'} · Cost: ${itemData?.cost?.standard ?? '?'} · UOM: {itemData?.uom || '?'}
            </div>
          </div>

          {/* Inventory Impact — lines and layers that affected this item */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 mb-6">
            <h2 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-3">
              Inventory Impact — Transaction Lines & Layers ({impacts.length})
            </h2>
            {impacts.length === 0 ? (
              <div className="text-xs text-gray-400 py-4 text-center">No transaction lines found for this item.</div>
            ) : (
              <>{/* Flow path legend */}
              <div className="flex items-center gap-3 mb-3 text-[10px] text-gray-500">
                <span>Flow:</span>
                <span className="px-1.5 py-0.5 rounded bg-purple-100 text-purple-700 font-bold">Proposal</span>
                <span>→</span>
                <span className="px-1.5 py-0.5 rounded bg-green-100 text-green-700 font-bold">Order</span>
                <span>→</span>
                <span className="px-1.5 py-0.5 rounded bg-red-100 text-red-700 font-bold">Purchase</span>
                <span>→</span>
                <span className="px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-bold">Receive</span>
                <span>→</span>
                <span className="px-1.5 py-0.5 rounded bg-yellow-100 text-yellow-700 font-bold">Invoice/Ship</span>
              </div>

              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-gray-700 text-left">
                    <th className="py-2 pr-2 text-gray-500">Type</th>
                    <th className="py-2 pr-2 text-gray-500">Parent Transaction</th>
                    <th className="py-2 pr-2 text-gray-500">Line#</th>
                    <th className="py-2 pr-2 text-gray-500">Impact</th>
                    <th className="py-2 pr-2 text-gray-500 text-center">on_hand</th>
                    <th className="py-2 pr-2 text-gray-500 text-center">on_p</th>
                    <th className="py-2 pr-2 text-gray-500 text-center">on_so</th>
                    <th className="py-2 pr-2 text-gray-500 text-center">on_po</th>
                    <th className="py-2 text-gray-500">When</th>
                  </tr>
                </thead>
                <tbody>
                  {impacts.map((imp, i) => (
                    <tr key={`${imp.type}-${imp.id}-${i}`} className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800">
                      <td className="py-2 pr-2">
                        <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase ${
                          imp.type.includes('invoice') ? 'bg-yellow-100 text-yellow-700' :
                          imp.type.includes('order') ? 'bg-green-100 text-green-700' :
                          imp.type.includes('purchase') ? 'bg-red-100 text-red-700' :
                          imp.type.includes('proposal') ? 'bg-purple-100 text-purple-700' :
                          imp.type.includes('layer') ? 'bg-blue-100 text-blue-700' :
                          imp.type.includes('pending') ? 'bg-orange-100 text-orange-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>{imp.type.replace(/_/g, ' ')}</span>
                      </td>
                      <td className="py-2 pr-2">
                        {imp.parentId ? (
                          <button
                            onClick={() => {
                              const seg = imp.parentModel === 'purchase' ? 'purchase' : imp.parentModel;
                              window.open(`/transactions/${seg}/detail/${imp.parentId}`, `tx_${imp.parentModel}_${imp.parentId}`);
                            }}
                            className="text-left group"
                          >
                            <div className="text-blue-600 dark:text-blue-400 font-semibold group-hover:underline">
                              {imp.parentIda}
                            </div>
                            <div className="text-[10px] text-gray-400">
                              {imp.parentModel} #{imp.parentId} — click to open
                            </div>
                          </button>
                        ) : <span className="text-gray-400">—</span>}
                      </td>
                      <td className="py-2 pr-2 text-gray-600 text-center">{imp.lineNumber ?? '—'}</td>
                      <td className="py-2 pr-2 text-gray-600">{imp.description}</td>
                      {['on_hand', 'on_p', 'on_so', 'on_po'].map((col) => {
                        // Determine delta per column based on transaction type
                        let delta = 0;
                        const qty = Math.abs(imp.qtyDelta);
                        if (imp.type === 'proposal_line')    { if (col === 'on_p') delta = qty; }
                        else if (imp.type === 'order_line')  { if (col === 'on_so') delta = qty; }
                        else if (imp.type === 'purchase_line') { if (col === 'on_po') delta = qty; }
                        else if (imp.type === 'invoice_line') { if (col === 'on_hand') delta = -qty; if (col === 'on_so') delta = -qty; }
                        else if (imp.type === 'inventory_layer') { if (col === 'on_hand') delta = qty; if (col === 'on_po') delta = -qty; }
                        else if (imp.type === 'pending_adjustment') { if (col === imp.qtyField) delta = imp.qtyDelta; }
                        return (
                          <td key={col} className={`py-2 pr-2 font-mono font-bold text-center ${delta > 0 ? 'text-green-600' : delta < 0 ? 'text-red-600' : 'text-gray-300'}`}>
                            {delta !== 0 ? (delta > 0 ? `+${delta}` : delta) : '·'}
                          </td>
                        );
                      })}
                      <td className="py-2 text-gray-400 text-[10px]">{imp.dt ? formatDt(imp.dt, 'datetime') : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </>
            )}
          </div>

          {/* Test Records */}
          <div className="grid grid-cols-2 gap-6 mb-6">
            <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <h2 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-3">Test Records ({testRecords.length})</h2>
              <div className="space-y-1.5 max-h-80 overflow-auto">
                {testRecords.map((r, i) => (
                  <div key={`${r.model}-${r.id}-${i}`} className="flex items-center gap-2 py-1 px-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700">
                    <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold uppercase ${
                      r.model === 'customer' ? 'bg-blue-100 text-blue-700' :
                      r.model === 'order' ? 'bg-green-100 text-green-700' :
                      r.model === 'invoice' ? 'bg-yellow-100 text-yellow-700' :
                      r.model === 'proposal' ? 'bg-purple-100 text-purple-700' :
                      r.model === 'purchase' ? 'bg-red-100 text-red-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>{r.model}</span>
                    <RecordLink model={r.model} id={r.id} label={r.label} />
                    {r.status && <span className="text-[10px] text-gray-400">{r.status}</span>}
                    {r.amount != null && <span className="text-[10px] text-gray-400 ml-auto">${r.amount}</span>}
                  </div>
                ))}
                {testRecords.length === 0 && <div className="text-xs text-gray-400">No test records found. Run test_sequence_001.py first.</div>}
              </div>
            </div>

            {/* Journal */}
            <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
              <h2 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-3">Test Journal ({journal.length})</h2>
              <div className="space-y-1 max-h-80 overflow-auto font-mono">
                {journal.map((j, i) => (
                  <div key={i} className="flex gap-2 py-0.5 text-[10px]">
                    <span className="text-gray-400 whitespace-nowrap">{j.dt}</span>
                    <span className="font-semibold text-gray-700 dark:text-gray-300 whitespace-nowrap">{j.action}</span>
                    <span className="text-gray-500 truncate">{j.detail}</span>
                  </div>
                ))}
                {journal.length === 0 && <div className="text-xs text-gray-400">No journal entries.</div>}
              </div>
            </div>
          </div>

          {/* GL Journal */}
          <GLJournalSection />

          {/* Inventory Math Check */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
            <h2 className="text-sm font-bold text-gray-700 dark:text-gray-300 mb-3">Inventory Math Verification</h2>
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="py-2 text-left text-gray-500">Field</th>
                  <th className="py-2 text-right text-gray-500">Value</th>
                  <th className="py-2 text-left text-gray-500 pl-4">Formula</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-gray-100 dark:border-gray-800">
                  <td className="py-2 font-medium">On Hand</td>
                  <td className="py-2 text-right font-mono">{q.on_hand ?? '—'}</td>
                  <td className="py-2 pl-4 text-gray-500">Start − shipped + received</td>
                </tr>
                <tr className="border-b border-gray-100 dark:border-gray-800">
                  <td className="py-2 font-medium">On PO</td>
                  <td className="py-2 text-right font-mono">{q.on_po ?? '—'}</td>
                  <td className="py-2 pl-4 text-gray-500">Ordered from vendor − received</td>
                </tr>
                <tr className="border-b border-gray-100 dark:border-gray-800">
                  <td className="py-2 font-medium">On SO</td>
                  <td className="py-2 text-right font-mono">{q.on_so ?? '—'}</td>
                  <td className="py-2 pl-4 text-gray-500">Customer ordered − shipped</td>
                </tr>
                <tr className="border-b border-gray-100 dark:border-gray-800">
                  <td className="py-2 font-medium">On Proposal</td>
                  <td className="py-2 text-right font-mono">{q.on_p ?? '—'}</td>
                  <td className="py-2 pl-4 text-gray-500">Quoted − transferred to order</td>
                </tr>
                <tr>
                  <td className="py-2 font-medium">Available</td>
                  <td className="py-2 text-right font-mono">{q.available ?? '—'}</td>
                  <td className="py-2 pl-4 text-gray-500">On Hand − allocated</td>
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
