/**
 * WorkflowSelect — dropdown in the detail toolbar for workflow operations.
 *
 * Replaces the bottom ManageActionPanel. Shows available wcapi/manage
 * actions as a select list. Selecting an action executes it (with confirm
 * if needed) or opens a dialog for complex actions.
 */
import React, { useCallback, useState } from 'react';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';

interface ActionDef {
  key: string;
  label: string;
  icon?: string;
  confirm?: string;
  needsDialog?: boolean;
  params?: (record: any) => Record<string, unknown>;
}

const ACTION_CONFIGS: Record<string, ActionDef[]> = {
  order: [
    { key: 'convert_order_to_invoice', label: 'To Invoice',
      confirm: 'Post this order to an invoice?',
      params: (r) => ({ order_id: r.id }) },
    { key: 'convert_order_to_purchase', label: 'To Purchase',
      confirm: 'Post this order to a purchase order?',
      params: (r) => ({ order_id: r.id, vendor_id: r.vendor_id || r.vendor }) },
    { key: 'spawn_work_order', label: 'To Work Order',
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
    { key: 'journalize_invoice', label: 'Journalize Invoice',
      confirm: 'Post GL journal entries + accrue commission? This locks the invoice.',
      params: (r) => ({ invoice_id: r.id, ida_prefix: '' }) },
    { key: 'journalize_invoice_and_payments', label: 'Journalize Invoice + Payments',
      confirm: 'Post GL journals for this invoice AND all linked payments? This locks both.',
      params: (r) => ({ invoice_id: r.id, ida_prefix: '' }) },
    { key: 'consume_inventory', label: 'Consume Inventory', needsDialog: true },
    { key: 'assign_serial_on_ship', label: 'Assign Serial', needsDialog: true },
    { key: 'clone_record', label: 'Clone',
      confirm: 'Duplicate this invoice with fresh dates?',
      params: (r) => ({ model_name: 'invoice', record_id: r.id, include_children: true }) },
    { key: 'link_transaction_to_campaign', label: 'Link Campaign', needsDialog: true },
  ],
  purchase: [
    { key: 'receive_inventory', label: 'Receive Goods', needsDialog: true },
    { key: 'create_serial_on_receive', label: 'Create Serial', needsDialog: true },
  ],
  proposal: [
    { key: 'convert_proposal_to_order', label: 'To Order',
      confirm: 'Post this proposal to an order?',
      params: (r) => ({ proposal_id: r.id }) },
    { key: 'convert_proposal_to_invoice', label: 'To Invoice',
      confirm: 'Post directly to invoice (over-the-counter)?',
      params: (r) => ({ proposal_id: r.id }) },
    { key: 'clone_record', label: 'Clone',
      confirm: 'Duplicate this proposal with fresh dates?',
      params: (r) => ({ model_name: 'proposal', record_id: r.id, include_children: true }) },
    { key: 'link_transaction_to_campaign', label: 'Link Campaign', needsDialog: true },
  ],
  payment: [
    { key: 'journalize_payment', label: 'Journalize',
      confirm: 'Post GL journal entries for this payment? This locks the payment.',
      params: (r) => ({ payment_id: r.id, ida_prefix: '' }) },
  ],
  work_order: [
    { key: 'record_production_action', label: 'Add Production Note', needsDialog: true },
  ],
  item: [
    { key: 'get_inventory_summary', label: 'Inventory Summary',
      params: (r) => ({ item_id: r.id }) },
  ],
};

async function callManage(action: string, params: Record<string, unknown>): Promise<any> {
  const { default: apiClient } = await import('@/api/axios');
  const res = await apiClient.post('/wcapi/_manage/', { action, params });
  return res.data?.data;
}

interface WorkflowSelectProps {
  modelName: string;
  record?: any;
  onComplete?: (result?: any) => void;
}

const WorkflowSelect: React.FC<WorkflowSelectProps> = ({ modelName, record, onComplete }) => {
  const dispatch = useDispatch();
  const [loading, setLoading] = useState(false);
  const actions = ACTION_CONFIGS[modelName] || [];

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

    if (action.confirm && !confirm(action.confirm)) return;
    // Destructive actions require a second confirmation
    if (action.key === 'complete_order' && !confirm('CONFIRM: This will lock the order. Proceed?')) return;

    try {
      setLoading(true);
      const params = action.params ? action.params(record || {}) : {};
      const result = await callManage(action.key, params);
      dispatch(showToast({ message: `${action.label} completed`, type: 'success' }));
      onComplete?.({ ...result, _action: action.key });
    } catch (err: any) {
      dispatch(showToast({ message: err?.response?.data?.message || err?.message || `${action.label} failed`, type: 'error' }));
    } finally {
      setLoading(false);
    }
  }, [actions, record, dispatch, onComplete]);

  if (!actions.length) return null;

  return (
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
  );
};

export default WorkflowSelect;
export { WorkflowSelect };
