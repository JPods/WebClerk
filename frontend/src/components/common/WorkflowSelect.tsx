/**
 * WorkflowSelect — dropdown in the detail toolbar for workflow operations.
 *
 * Replaces the bottom ManageActionPanel. Shows available wcapi/manage
 * actions as a select list. Selecting an action executes it (with confirm
 * if needed) or opens a dialog for complex actions.
 */
import React, { useCallback, useState } from 'react';
import { createPortal } from 'react-dom';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';

interface ActionDef {
  key: string;
  label: string;
  icon?: string;
  confirm?: string;
  needsDialog?: boolean;
  params?: (record: any) => Record<string, unknown>;
  /** A command on this record: POST /wcapi/<model>/<id>/<command>/ with params as the body. */
  command?: string;
}

const ACTION_CONFIGS: Record<string, ActionDef[]> = {
  order: [
    { key: 'convert_to_invoice', label: 'To Invoice', command: 'convert',
      confirm: 'Post this order to an invoice?',
      params: () => ({ to: 'invoice' }) },
    { key: 'convert_to_purchase', label: 'To Purchase', command: 'convert',
      confirm: 'Post this order to a purchase order?',
      params: (r) => ({ to: 'purchase', vendor_id: r.vendor_id || r.vendor }) },
    { key: 'spawn_workorder', label: 'To Work Order',
      confirm: 'Post this order to a work order?',
      params: (r) => ({ order_id: r.id }) },
    { key: 'complete_order', label: 'Complete',
      confirm: 'Mark this order as complete?',
      params: (r) => ({ order_id: r.id }) },
    { key: 'clone_record', label: 'Clone',
      confirm: 'Duplicate this order with fresh dates?',
      params: (r) => ({ model_name: 'order', record_id: r.id, include_children: true }) },
    { key: 'link_transaction_to_campaign', label: 'Link Campaign', needsDialog: true },
  ],
  invoice: [
    // One door: the journalize command refuses an incomplete or unreleased invoice with coaching.
    { key: 'journalize', label: 'Journalize', command: 'journalize',
      confirm: 'Post this invoice to the GL (revenue, tax, COGS) and accrue its commission? This locks the invoice.',
      params: () => ({}) },
    { key: 'assign_serial_on_ship', label: 'Assign Serial', needsDialog: true },
    { key: 'clone_record', label: 'Clone',
      confirm: 'Duplicate this invoice with fresh dates?',
      params: (r) => ({ model_name: 'invoice', record_id: r.id, include_children: true }) },
    { key: 'link_transaction_to_campaign', label: 'Link Campaign', needsDialog: true },
  ],
  purchase: [
    { key: 'convert_to_receipt', label: 'To Receipt', command: 'convert',
      confirm: 'Receive what is left on this purchase?',
      params: () => ({ to: 'receipt' }) },
    { key: 'create_serial_on_receive', label: 'Create Serial', needsDialog: true },
  ],
  quote: [
    { key: 'convert_to_order', label: 'To Order', command: 'convert',
      confirm: 'Post this quote to an order?',
      params: () => ({ to: 'order' }) },
    { key: 'convert_to_invoice', label: 'To Invoice', command: 'convert',
      confirm: 'Post directly to invoice (over-the-counter)?',
      params: () => ({ to: 'invoice' }) },
    { key: 'clone_record', label: 'Clone',
      confirm: 'Duplicate this quote with fresh dates?',
      params: (r) => ({ model_name: 'quote', record_id: r.id, include_children: true }) },
    { key: 'link_transaction_to_campaign', label: 'Link Campaign', needsDialog: true },
  ],
  receipt: [
    // Bill, 2026-11-11 (readme 108): saving a receipt receives its goods; this is the way off
    // hold, for a receipt converted with Hold ticked.
    { key: 'receive', label: 'Receive', command: 'receive',
      confirm: "Put this held receipt's goods on the shelf? Their cost is fixed from then on.",
      params: () => ({}) },
    { key: 'journalize', label: 'Journalize', command: 'journalize',
      confirm: 'Post what this receipt received (inventory) and what it owes the vendor (payable)? This locks the receipt.',
      params: () => ({}) },
  ],
  cash: [
    { key: 'journalize', label: 'Journalize', command: 'journalize',
      confirm: 'Post this cash to the GL? This locks the cash.',
      params: () => ({}) },
  ],
  workorder: [
    { key: 'record_production_action', label: 'Add Production Note', needsDialog: true },
    // Bill, 2026-09-28: a workorder journalizes on command, each event once.
    { key: 'journalize', label: 'Journalize', command: 'journalize',
      confirm: "Post this workorder's stock moves (parts, build, scrap, counts) to the GL? This locks it.",
      params: () => ({}) },
  ],
  item: [
    // One name, one meaning: the commerce dashboard's get_inventory_summary is the company's; this is the item's.
    { key: 'get_item_inventory_summary', label: 'Inventory Summary',
      params: (r) => ({ item_id: r.id }) },
  ],
};

async function callCommand(model: string, id: number, command: string,
                           body: Record<string, unknown>): Promise<any> {
  const { default: apiClient } = await import('@/api/axios');
  const res = await apiClient.post(`/wcapi/${model}/${id}/${command}/`, body);
  return res.data?.data?.result;
}

async function callManage(action: string, params: Record<string, unknown>): Promise<any> {
  const { default: apiClient } = await import('@/api/axios');
  const res = await apiClient.post('/wcapi/_manage/', { action, params });
  return res.data?.data;
}

/** One source line offered to a conversion: what is left, and how much of it to take. */
interface ConvertRow { line_id: number; label: string; left: number; qty: string }

/** The lines a conversion can take: saved, not removed, with something left. */
export function convertRows(record: any): ConvertRow[] {
  return (Array.isArray(record?.lines) ? record.lines : [])
    .filter((l: any) => l && l.id && !l._removed && !l._new && l.line_type !== 'discount')
    .map((l: any) => {
      const left = Number(l.quantity?.remaining ?? 0) || 0;
      const item = l.item || {};
      return { line_id: l.id, left, qty: String(left),
               label: [item.ida_item, item.description].filter(Boolean).join(' — ') || `line ${l.line_number ?? l.id}` };
    })
    .filter((r: ConvertRow) => r.left > 0);
}

/** The `lines` a conversion sends: nothing when every quantity is what is left (the server
 *  takes everything left, as before); otherwise each line with a quantity above 0. */
export function convertLines(rows: ConvertRow[]): { line_id: number; qty: number }[] | null {
  if (rows.every((r) => Number(r.qty) === r.left)) return null;
  return rows.map((r) => ({ line_id: r.line_id, qty: Number(r.qty) || 0 })).filter((r) => r.qty > 0);
}

interface WorkflowSelectProps {
  modelName: string;
  record?: any;
  onComplete?: (result?: any) => void;
}

const WorkflowSelect: React.FC<WorkflowSelectProps> = ({ modelName, record, onComplete }) => {
  const dispatch = useDispatch();
  const [loading, setLoading] = useState(false);
  // A conversion asks its quantities first (Bill, 2026-11-11): one save at the number meant.
  const [asking, setAsking] = useState<{ action: ActionDef; rows: ConvertRow[]; toReceipt: boolean; hold: boolean } | null>(null);
  const actions = ACTION_CONFIGS[modelName] || [];

  const run = useCallback(async (action: ActionDef, extra: Record<string, unknown> = {}) => {
    try {
      setLoading(true);
      const params = { ...(action.params ? action.params(record || {}) : {}), ...extra };
      const result = action.command
        ? await callCommand(modelName, record.id, action.command, params)
        : await callManage(action.key, params);
      // The server's coaching rides on the result (a purchase born without a vendor, 2026-11-08).
      const notes = Array.isArray(result?.messages) ? result.messages.filter(Boolean) : [];
      dispatch(showToast({ message: [`${action.label} completed`, ...notes].join('. '), type: 'success' }));
      onComplete?.({ ...result, _action: action.key });
    } catch (err: any) {
      dispatch(showToast({ message: err?.response?.data?.message || err?.message || `${action.label} failed`, type: 'error' }));
    } finally {
      setLoading(false);
    }
  }, [record, modelName, dispatch, onComplete]);

  const confirmAsked = useCallback(() => {
    if (!asking) return;
    const lines = convertLines(asking.rows);
    if (lines && !lines.length) {
      dispatch(showToast({ message: 'Enter a quantity above 0 on at least one line.', type: 'info' }));
      return;
    }
    const { action, hold } = asking;
    setAsking(null);
    // Hold is a positive act (Bill, 2026-11-11, R2): sent only when ticked.
    void run(action, { ...(lines ? { lines } : {}), ...(hold ? { hold: true } : {}) });
  }, [asking, run, dispatch]);

  const handleChange = useCallback(async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const key = e.target.value;
    if (!key) return;
    e.target.value = ''; // reset select

    const action = actions.find(a => a.key === key);
    if (!action) return;

    if (action.needsDialog) {
      dispatch(showToast({ message: `${action.label}: dialog not yet implemented in toolbar`, type: 'info' }));
      return;
    }

    if (action.command === 'convert') {
      // The lines and what is left of each, editable; Enter takes them as shown. A record
      // loaded without its lines falls back to the plain question.
      const rows = convertRows(record);
      if (rows.length) {
        const toReceipt = (action.params ? action.params(record || {}) : {}).to === 'receipt';
        setAsking({ action, rows, toReceipt, hold: false });
        return;
      }
    }
    if (action.confirm && !confirm(action.confirm)) return;
    // Destructive actions require a second confirmation
    if (action.key === 'complete_order' && !confirm('CONFIRM: This will lock the order. Proceed?')) return;
    await run(action);
  }, [actions, record, dispatch, run]);

  if (!actions.length) return null;

  return (
    <>
    {asking && createPortal(
      <div data-wc="convert-ask" role="dialog" aria-label={asking.action.label}
        style={{ position: 'fixed', inset: 0, zIndex: 10000, background: 'rgba(0,0,0,0.35)',
                 display: 'flex', alignItems: 'flex-start', justifyContent: 'center', paddingTop: '12vh' }}
        onKeyDown={(e) => { if (e.key === 'Escape') setAsking(null); }}>
        <form onSubmit={(e) => { e.preventDefault(); confirmAsked(); }}
          style={{ background: 'var(--db-surface, #fff)', color: 'var(--db-text, #212529)',
                   border: '1px solid var(--db-border, #dee2e6)', borderRadius: 6, padding: 16,
                   minWidth: 420, maxWidth: '90vw', maxHeight: '70vh', overflow: 'auto', fontSize: 13 }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>{asking.action.label}</div>
          <div style={{ color: 'var(--db-text-dim, #6c757d)', marginBottom: 10 }}>
            {asking.action.confirm} Change a quantity to take less; 0 leaves the line out.
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr>
              <th style={{ textAlign: 'right', width: 90, padding: '2px 6px' }}>Qty</th>
              <th style={{ textAlign: 'right', width: 70, padding: '2px 6px' }}>Left</th>
              <th style={{ textAlign: 'left', padding: '2px 6px' }}>Item</th>
            </tr></thead>
            <tbody>
              {asking.rows.map((r, i) => (
                <tr key={r.line_id}>
                  <td style={{ padding: '2px 6px', textAlign: 'right' }}>
                    <input type="text" inputMode="decimal" value={r.qty} autoFocus={i === 0}
                      onFocus={(e) => e.currentTarget.select()}
                      onChange={(e) => setAsking({ ...asking, rows: asking.rows.map((x) =>
                        x.line_id === r.line_id ? { ...x, qty: e.target.value.replace(/[^0-9.]/g, '') } : x) })}
                      className="db-input" style={{ width: 72, textAlign: 'right', fontSize: 'inherit' }} />
                  </td>
                  <td style={{ padding: '2px 6px', textAlign: 'right' }}>{r.left.toLocaleString()}</td>
                  <td style={{ padding: '2px 6px' }}>{r.label}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {asking.toReceipt && (
            <label data-wc="convert-hold" style={{ display: 'flex', gap: 6, alignItems: 'center', marginTop: 10 }}>
              <input type="checkbox" checked={asking.hold}
                onChange={(e) => setAsking({ ...asking, hold: e.target.checked })} />
              <span>Hold: the goods are not here yet. On hand does not move until Workflow → Receive.</span>
            </label>
          )}
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 12 }}>
            <button type="button" onClick={() => setAsking(null)} className="px-3 py-1 rounded"
              style={{ border: '1px solid var(--db-border, #dee2e6)', fontSize: 'inherit' }}>Cancel</button>
            <button type="submit" className="px-3 py-1 rounded font-medium text-white bg-green-600 hover:bg-green-700"
              style={{ fontSize: 'inherit' }}>{asking.action.label}</button>
          </div>
        </form>
      </div>, document.body)}
    <select
      onChange={handleChange}
      disabled={loading || !record?.id}
      className="text-xs px-1 py-0.5 rounded cursor-pointer"
      style={{
        background: 'var(--db-surface-alt, #f1f3f5)',
        color: 'var(--db-text, #212529)',
        border: '1px solid var(--db-border, #dee2e6)',
      }}
      title="Workflow operations"
    >
      <option value="">Workflow</option>
      {actions.map(a => (
        <option key={a.key} value={a.key}>{a.label}</option>
      ))}
    </select>
    </>
  );
};

export default WorkflowSelect;
export { WorkflowSelect };
