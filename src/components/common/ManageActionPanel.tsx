/**
 * ManageActionPanel — config-driven operations panel for transaction detail pages.
 *
 * Drops into any detail page. Shows available wcapi/manage actions for the
 * current model + record. Click an action → calls wcapi/manage → shows result.
 *
 * Some actions open a dialog for input (partial ship, serial assign, etc.).
 * Simple actions execute immediately with confirmation.
 *
 * Usage:
 *   <ManageActionPanel modelName="order" recordId={123} record={orderData} />
 */
import { useCallback, useState, lazy, Suspense } from 'react';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';

const PackingPanel = lazy(() => import('@/apps/transactions/components/detail/PackingPanel'));

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ActionDef {
  key: string;           // wcapi/manage action name
  label: string;         // button label
  icon?: string;         // emoji icon
  variant?: 'primary' | 'default' | 'danger' | 'success';
  confirm?: string;      // if set, show confirm before executing
  needsDialog?: boolean; // if true, opens a dialog instead of immediate execute
  params?: (record: any) => Record<string, unknown>; // build params from record
}

interface ManageActionPanelProps {
  modelName: string;
  recordId: number | string;
  record?: any;
  onActionComplete?: () => void; // refresh after action
}

// ---------------------------------------------------------------------------
// Action configs per model
// ---------------------------------------------------------------------------

const ACTION_CONFIGS: Record<string, ActionDef[]> = {
  order: [
    { key: 'convert_order_to_invoice', label: 'Convert to Invoice', icon: '📄', variant: 'primary',
      confirm: 'Convert this order to an invoice?',
      params: (r) => ({ order_id: r.id }) },
    { key: 'convert_order_to_purchase', label: 'Convert to PO', icon: '🛒', variant: 'success',
      confirm: 'Create a purchase order from this order?',
      params: (r) => ({ order_id: r.id, vendor_id: r.vendor_id || r.vendor }) },
    { key: 'spawn_work_order', label: 'Create Work Order', icon: '🔧',
      confirm: 'Create a work order from this order?',
      params: (r) => ({ order_id: r.id }) },
    { key: 'ship_order', label: 'Ship Order', icon: '📦', variant: 'success', needsDialog: true },
    { key: 'complete_order', label: 'Complete Order', icon: '✓',
      confirm: 'Mark this order as complete?',
      params: (r) => ({ order_id: r.id }) },
    { key: 'clone_record', label: 'Clone', icon: '📋',
      confirm: 'Duplicate this order with fresh dates?',
      params: (r) => ({ model_name: 'order', record_id: r.id, include_children: true }) },
    { key: 'link_transaction_to_campaign', label: 'Link Campaign', icon: '📣', needsDialog: true },
  ],
  invoice: [
    { key: 'journalize_invoice', label: 'Journalize', icon: '📒', variant: 'success',
      confirm: 'Post GL journal entries + accrue commission? This locks the invoice.',
      params: (r) => ({ invoice_id: r.id, ida_prefix: '' }) },
    { key: 'consume_inventory', label: 'Ship (Consume Inventory)', icon: '📦', variant: 'primary', needsDialog: true },
    { key: 'assign_serial_on_ship', label: 'Assign Serial', icon: '🏷', needsDialog: true },
    { key: 'clone_record', label: 'Clone', icon: '📋',
      confirm: 'Duplicate this invoice with fresh dates?',
      params: (r) => ({ model_name: 'invoice', record_id: r.id, include_children: true }) },
    { key: 'link_transaction_to_campaign', label: 'Link Campaign', icon: '📣', needsDialog: true },
  ],
  purchase: [
    { key: 'receive_inventory', label: 'Receive Goods', icon: '📥', variant: 'primary', needsDialog: true },
    { key: 'create_serial_on_receive', label: 'Create Serial', icon: '🏷', needsDialog: true },
  ],
  proposal: [
    { key: 'convert_proposal_to_order', label: 'Convert to Order', icon: '📋', variant: 'primary',
      confirm: 'Convert this proposal to an order?',
      params: (r) => ({ proposal_id: r.id }) },
    { key: 'convert_proposal_to_invoice', label: 'Convert to Invoice', icon: '📄', variant: 'success',
      confirm: 'Convert directly to invoice (over-the-counter)?',
      params: (r) => ({ proposal_id: r.id }) },
    { key: 'clone_record', label: 'Clone', icon: '📋',
      confirm: 'Duplicate this proposal with fresh dates?',
      params: (r) => ({ model_name: 'proposal', record_id: r.id, include_children: true }) },
    { key: 'link_transaction_to_campaign', label: 'Link Campaign', icon: '📣', needsDialog: true },
  ],
  item: [
    { key: 'get_inventory_summary', label: 'Inventory Summary', icon: '📊', variant: 'default',
      params: (r) => ({ item_id: r.id }) },
  ],
  work_order: [
    { key: 'record_production_action', label: 'Add Production Note', icon: '📝', needsDialog: true },
  ],
};

// ---------------------------------------------------------------------------
// API caller
// ---------------------------------------------------------------------------

async function callManage(action: string, params: Record<string, unknown>): Promise<any> {
  const { default: apiClient } = await import('@/api/axios');
  const res = await apiClient.post('/wcapi/manage/', { action, params });
  return res.data?.data;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ManageActionPanel({ modelName, recordId, record, onActionComplete }: ManageActionPanelProps) {
  const dispatch = useDispatch();
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState<string | null>(null);
  const [result, setResult] = useState<any>(null);
  const [dialogAction, setDialogAction] = useState<ActionDef | null>(null);
  const [showPacking, setShowPacking] = useState(false);

  // Dialog state for various input forms
  const [dialogInputs, setDialogInputs] = useState<Record<string, any>>({});

  const actions = ACTION_CONFIGS[modelName] || [];
  if (!actions.length) return null;

  const executeAction = useCallback(async (action: ActionDef, extraParams?: Record<string, unknown>) => {
    try {
      setLoading(action.key);
      const params = {
        ...(action.params ? action.params(record || { id: recordId }) : { order_id: recordId }),
        ...extraParams,
      };
      const data = await callManage(action.key, params);
      setResult({ action: action.label, data });
      dispatch(showToast({ message: `${action.label} completed`, type: 'success' }));
      onActionComplete?.();
    } catch (e: any) {
      dispatch(showToast({ message: e?.response?.data?.message || e?.message || `${action.label} failed`, type: 'error' }));
    } finally {
      setLoading(null);
    }
  }, [record, recordId, dispatch, onActionComplete]);

  const handleClick = useCallback((action: ActionDef) => {
    // Ship Order opens the PackingPanel instead of the generic dialog
    if (action.key === 'ship_order') {
      setShowPacking(true);
      return;
    }
    if (action.needsDialog) {
      setDialogAction(action);
      setDialogInputs({});
      return;
    }
    if (action.confirm && !confirm(action.confirm)) return;
    executeAction(action);
  }, [executeAction]);

  const handleDialogSubmit = useCallback(() => {
    if (!dialogAction) return;

    let extraParams: Record<string, unknown> = {};

    // Build params based on action type
    if (dialogAction.key === 'partial_ship') {
      extraParams = { order_id: recordId, shipped_lines: dialogInputs.shipped_lines || [] };
    } else if (dialogAction.key === 'record_production_action') {
      extraParams = { order_id: recordId, action_text: dialogInputs.action_text || '' };
    } else if (dialogAction.key === 'link_transaction_to_campaign') {
      extraParams = { model_name: modelName, record_id: recordId, campaign_id: parseInt(dialogInputs.campaign_id) };
    } else if (dialogAction.key === 'receive_inventory') {
      extraParams = {
        item_id: parseInt(dialogInputs.item_id),
        warehouse_id: parseInt(dialogInputs.warehouse_id),
        qty_received: parseInt(dialogInputs.qty_received),
        unit_cost: dialogInputs.unit_cost || '0',
        source_type: 'purchase', source_id: recordId,
      };
    } else if (dialogAction.key === 'consume_inventory') {
      extraParams = {
        item_id: parseInt(dialogInputs.item_id),
        qty_to_consume: parseInt(dialogInputs.qty_to_consume),
        method: dialogInputs.method || 'fifo',
        source_type: 'invoice', source_id: recordId,
      };
    } else if (dialogAction.key === 'create_serial_on_receive') {
      extraParams = {
        item_id: parseInt(dialogInputs.item_id),
        serial_number: dialogInputs.serial_number || '',
        purchase_id: recordId,
        unit_cost: dialogInputs.unit_cost || '0',
        warehouse_id: parseInt(dialogInputs.warehouse_id || '0'),
      };
    } else if (dialogAction.key === 'assign_serial_on_ship') {
      extraParams = {
        serial_id: parseInt(dialogInputs.serial_id),
        customer_id: parseInt(dialogInputs.customer_id || record?.customer_id),
        invoice_id: recordId,
        warranty_months: parseInt(dialogInputs.warranty_months || '12'),
      };
    }

    executeAction(dialogAction, extraParams);
    setDialogAction(null);
  }, [dialogAction, dialogInputs, executeAction, recordId, modelName, record]);

  const variantClass = (v?: string) => {
    if (v === 'primary') return 'bg-blue-600 text-white hover:bg-blue-700';
    if (v === 'success') return 'bg-green-600 text-white hover:bg-green-700';
    if (v === 'danger') return 'bg-red-600 text-white hover:bg-red-700';
    return 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600';
  };

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-2 text-xs font-semibold transition"
        style={{ background: 'var(--db-surface-alt, #f8f9fa)', color: 'var(--db-text-muted, #6c757d)' }}
      >
        <span>⚡ Workflow ({actions.length})</span>
        <span>{expanded ? '▼' : '▶'}</span>
      </button>

      {expanded && (
        <div className="p-3 space-y-2">
          {/* Action buttons */}
          <div className="flex flex-wrap gap-2">
            {actions.map((action) => (
              <button
                key={action.key}
                onClick={() => handleClick(action)}
                disabled={loading === action.key}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition ${variantClass(action.variant)} ${loading === action.key ? 'opacity-50' : ''}`}
              >
                {action.icon && <span className="mr-1">{action.icon}</span>}
                {loading === action.key ? 'Working...' : action.label}
              </button>
            ))}
          </div>

          {/* Result display */}
          {result && (
            <div className="mt-2 p-2 bg-green-50 dark:bg-green-900/20 rounded text-xs">
              <div className="font-semibold text-green-700 dark:text-green-400 mb-1">{result.action} — Result:</div>
              <pre className="text-[10px] text-gray-600 dark:text-gray-400 overflow-auto max-h-32">{JSON.stringify(result.data, null, 2)}</pre>
            </div>
          )}
        </div>
      )}

      {/* Packing Panel — full pick/pack/ship workflow */}
      {showPacking && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setShowPacking(false)}>
          <div style={{ width: 720, maxWidth: '90vw' }} onClick={(e) => e.stopPropagation()}>
            <Suspense fallback={<div style={{ padding: 32, color: '#999', textAlign: 'center' }}>Loading...</div>}>
              <PackingPanel
                orderId={typeof recordId === 'number' ? recordId : parseInt(String(recordId))}
                orderIda={record?.ida}
                onComplete={() => { setShowPacking(false); onActionComplete?.(); }}
                onClose={() => setShowPacking(false)}
              />
            </Suspense>
          </div>
        </div>
      )}

      {/* Dialog overlay */}
      {dialogAction && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setDialogAction(null)}>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl w-96 max-h-[80vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
            <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{dialogAction.icon} {dialogAction.label}</h3>
            </div>
            <div className="p-4 space-y-3">
              {/* Dynamic form based on action type */}
              {dialogAction.key === 'partial_ship' && (
                <>
                  <p className="text-xs text-gray-500">Enter shipped lines as JSON array: [{'{'}order_line_id, qty_shipped{'}'}]</p>
                  <textarea
                    className="w-full px-3 py-2 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 font-mono"
                    rows={4}
                    placeholder='[{"order_line_id": 1, "qty_shipped": 5}]'
                    value={dialogInputs.shipped_lines_raw || ''}
                    onChange={(e) => {
                      setDialogInputs((d: any) => ({ ...d, shipped_lines_raw: e.target.value }));
                      try { setDialogInputs((d: any) => ({ ...d, shipped_lines: JSON.parse(e.target.value) })); } catch {}
                    }}
                  />
                </>
              )}
              {dialogAction.key === 'record_production_action' && (
                <input type="text" placeholder="Production note..." className="w-full px-3 py-2 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                  value={dialogInputs.action_text || ''} onChange={(e) => setDialogInputs((d: any) => ({ ...d, action_text: e.target.value }))} />
              )}
              {dialogAction.key === 'link_transaction_to_campaign' && (
                <input type="number" placeholder="Campaign Setting ID" className="w-full px-3 py-2 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                  value={dialogInputs.campaign_id || ''} onChange={(e) => setDialogInputs((d: any) => ({ ...d, campaign_id: e.target.value }))} />
              )}
              {(dialogAction.key === 'receive_inventory' || dialogAction.key === 'consume_inventory') && (
                <>
                  <input type="number" placeholder="Item ID" className="w-full px-3 py-2 text-xs rounded border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                    value={dialogInputs.item_id || ''} onChange={(e) => setDialogInputs((d: any) => ({ ...d, item_id: e.target.value }))} />
                  {dialogAction.key === 'receive_inventory' && (
                    <>
                      <input type="number" placeholder="Warehouse ID" className="w-full px-3 py-2 text-xs rounded border" value={dialogInputs.warehouse_id || ''} onChange={(e) => setDialogInputs((d: any) => ({ ...d, warehouse_id: e.target.value }))} />
                      <input type="number" placeholder="Qty Received" className="w-full px-3 py-2 text-xs rounded border" value={dialogInputs.qty_received || ''} onChange={(e) => setDialogInputs((d: any) => ({ ...d, qty_received: e.target.value }))} />
                      <input type="text" placeholder="Unit Cost" className="w-full px-3 py-2 text-xs rounded border" value={dialogInputs.unit_cost || ''} onChange={(e) => setDialogInputs((d: any) => ({ ...d, unit_cost: e.target.value }))} />
                    </>
                  )}
                  {dialogAction.key === 'consume_inventory' && (
                    <>
                      <input type="number" placeholder="Qty to Consume" className="w-full px-3 py-2 text-xs rounded border" value={dialogInputs.qty_to_consume || ''} onChange={(e) => setDialogInputs((d: any) => ({ ...d, qty_to_consume: e.target.value }))} />
                      <select className="w-full px-3 py-2 text-xs rounded border" value={dialogInputs.method || 'fifo'} onChange={(e) => setDialogInputs((d: any) => ({ ...d, method: e.target.value }))}>
                        <option value="fifo">FIFO</option>
                        <option value="lifo">LIFO</option>
                      </select>
                    </>
                  )}
                </>
              )}
              {dialogAction.key === 'create_serial_on_receive' && (
                <>
                  <input type="number" placeholder="Item ID" className="w-full px-3 py-2 text-xs rounded border" value={dialogInputs.item_id || ''} onChange={(e) => setDialogInputs((d: any) => ({ ...d, item_id: e.target.value }))} />
                  <input type="text" placeholder="Serial Number" className="w-full px-3 py-2 text-xs rounded border" value={dialogInputs.serial_number || ''} onChange={(e) => setDialogInputs((d: any) => ({ ...d, serial_number: e.target.value }))} />
                  <input type="number" placeholder="Warehouse ID" className="w-full px-3 py-2 text-xs rounded border" value={dialogInputs.warehouse_id || ''} onChange={(e) => setDialogInputs((d: any) => ({ ...d, warehouse_id: e.target.value }))} />
                  <input type="text" placeholder="Unit Cost" className="w-full px-3 py-2 text-xs rounded border" value={dialogInputs.unit_cost || ''} onChange={(e) => setDialogInputs((d: any) => ({ ...d, unit_cost: e.target.value }))} />
                </>
              )}
              {dialogAction.key === 'assign_serial_on_ship' && (
                <>
                  <input type="number" placeholder="Serial ID" className="w-full px-3 py-2 text-xs rounded border" value={dialogInputs.serial_id || ''} onChange={(e) => setDialogInputs((d: any) => ({ ...d, serial_id: e.target.value }))} />
                  <input type="number" placeholder="Warranty Months (default 12)" className="w-full px-3 py-2 text-xs rounded border" value={dialogInputs.warranty_months || ''} onChange={(e) => setDialogInputs((d: any) => ({ ...d, warranty_months: e.target.value }))} />
                </>
              )}
            </div>
            <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-2">
              <button onClick={() => setDialogAction(null)} className="px-3 py-1.5 text-xs rounded border border-gray-300 text-gray-600 hover:bg-gray-100">Cancel</button>
              <button onClick={handleDialogSubmit} className="px-3 py-1.5 text-xs rounded bg-blue-600 text-white hover:bg-blue-700 font-medium">Execute</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
