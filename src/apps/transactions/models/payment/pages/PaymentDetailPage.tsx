/**
 * PaymentDetailPage — View/edit a single Payment record.
 *
 * Unlike orders/invoices, Payment is NOT a TransactionBaseModel,
 * so it does NOT extend TransactionDetailBase. Instead it renders
 * its own standalone detail layout inspired by the legacy wc2
 * Table 28 Input form (pages 1 & 2).
 *
 * Legacy reference:
 *   Page 1 — customer info, invoice/order refs, status flags, banking
 *   Page 2 — core payment fields, currency, credit-card, check, address, comment/history
 */
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useDispatch } from 'react-redux';
import {
  FaSave,
  FaSpinner,
  FaArrowLeft,
  FaFileInvoice,
  FaClipboardList,
  FaTrash,
} from 'react-icons/fa';
import PageBreadcrumb from '@/components/common/PageBreadCrumb';
import ComponentCard from '@/components/common/ComponentCard';
import { showToast } from '@/store/slices/toastSlice';
import {
  fetchPayment,
  createPayment,
  updatePayment,
  deletePayment,
  fetchPaymentMethods,
  fetchPaymentApplications,
} from '../services/paymentApi';
import type {
  Payment,
  PaymentMethod,
  PaymentApplication,
  PaymentStatus,
  PaymentGateway,
} from '../types/Payment';
import { PageRoutes } from '@/routes/Routes';
import { getModelDetailPath } from '@/apps/common/components/panels';

type Mode = 'view' | 'edit' | 'add';

const STATUS_OPTIONS: PaymentStatus[] = [
  'pending',
  'processing',
  'completed',
  'failed',
  'cancelled',
  'refunded',
  'partially_refunded',
];

const GATEWAY_OPTIONS: PaymentGateway[] = ['manual', 'stripe', 'paypal'];

const STATUS_STYLES: Record<string, string> = {
  completed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  processing: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  cancelled: 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200',
  refunded: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  partially_refunded: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
};

const formatCurrency = (v: number | undefined | null) => {
  if (v == null) return '$0.00';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(v);
};

const formatDate = (d?: string | null) => {
  if (!d) return '--';
  return new Date(d).toLocaleDateString();
};

export default function PaymentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const stateMode = (location.state as any)?.mode as Mode | undefined;
  const isNew = !id;
  const [mode, setMode] = useState<Mode>(stateMode || (isNew ? 'add' : 'edit'));

  // Data
  const [payment, setPayment] = useState<Payment | null>(null);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [applications, setApplications] = useState<PaymentApplication[]>([]);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);

  // Form fields
  const [amount, setAmount] = useState('');
  const [status, setStatus] = useState<PaymentStatus>('pending');
  const [gateway, setGateway] = useState<PaymentGateway>('manual');
  const [paymentMethodId, setPaymentMethodId] = useState<number | null>(null);
  const [referenceNumber, setReferenceNumber] = useState('');
  const [notes, setNotes] = useState('');
  const [paymentDate, setPaymentDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [contactId, setContactId] = useState<string>('');
  const [invoiceId, setInvoiceId] = useState<string>('');
  const [feeAmount, setFeeAmount] = useState('');
  const [reconciled, setReconciled] = useState(false);

  // Load data
  useEffect(() => {
    fetchPaymentMethods().then(setPaymentMethods).catch(console.error);
  }, []);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([
      fetchPayment(Number(id)),
      fetchPaymentApplications(Number(id)),
    ])
      .then(([pay, apps]) => {
        setPayment(pay);
        setApplications(apps);
        // Populate form
        setAmount(String(pay.amount ?? ''));
        setStatus(pay.status || 'pending');
        setGateway(pay.gateway || 'manual');
        setPaymentMethodId(pay.paymentmethod_id ?? null);
        setReferenceNumber(pay.reference_number || '');
        setNotes(pay.notes || '');
        setPaymentDate(pay.dt_payment ? pay.dt_payment.split('T')[0] : '');
        setContactId(String(pay.contact_id ?? ''));
        setInvoiceId(String(pay.invoice_id ?? ''));
        setFeeAmount(String(pay.fee_amount ?? ''));
        setReconciled(pay.reconciled ?? false);
      })
      .catch((err) => {
        console.error('Failed to load payment:', err);
        dispatch(showToast({ message: 'Failed to load payment', type: 'error' }));
      })
      .finally(() => setLoading(false));
  }, [id, dispatch]);

  // Save handler
  const handleSave = useCallback(async () => {
    const parsedAmount = parseFloat(amount);
    if (!parsedAmount || parsedAmount <= 0) {
      dispatch(showToast({ message: 'Enter a valid amount', type: 'error' }));
      return;
    }
    if (!contactId) {
      dispatch(showToast({ message: 'Contact is required', type: 'error' }));
      return;
    }

    setSaving(true);
    try {
      const payload: any = {
        amount: parsedAmount,
        contact_id: Number(contactId),
        status,
        gateway,
        paymentmethod_id: paymentMethodId,
        reference_number: referenceNumber,
        notes,
        dt_payment: paymentDate ? new Date(paymentDate).toISOString() : undefined,
        fee_amount: feeAmount ? parseFloat(feeAmount) : undefined,
        reconciled,
      };
      if (invoiceId) payload.invoice_id = Number(invoiceId);

      if (isNew) {
        const created = await createPayment(payload);
        dispatch(showToast({ message: 'Payment created', type: 'success' }));
        const newId = created?.id ?? created?.record?.id;
        if (newId) {
          navigate(
            PageRoutes.transactionsPaymentDetail.replace(':id?', String(newId)),
            { state: { mode: 'edit' }, replace: true },
          );
        }
      } else {
        await updatePayment(Number(id), { ...payload, id: Number(id), version: payment?.version });
        dispatch(showToast({ message: 'Payment updated', type: 'success' }));
        // Re-fetch
        const updated = await fetchPayment(Number(id));
        setPayment(updated);
      }
    } catch (error: any) {
      const msg =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        'Failed to save payment';
      dispatch(showToast({ message: msg, type: 'error' }));
    } finally {
      setSaving(false);
    }
  }, [
    amount, contactId, status, gateway, paymentMethodId, referenceNumber,
    notes, paymentDate, invoiceId, feeAmount, reconciled,
    isNew, id, payment, dispatch, navigate,
  ]);

  // Delete handler
  const handleDelete = useCallback(async () => {
    if (!id) return;
    if (!window.confirm('Delete this payment?')) return;
    try {
      await deletePayment(Number(id));
      dispatch(showToast({ message: 'Payment deleted', type: 'success' }));
      navigate(PageRoutes.transactionsPaymentList);
    } catch {
      dispatch(showToast({ message: 'Failed to delete payment', type: 'error' }));
    }
  }, [id, dispatch, navigate]);

  // Navigate to linked entities
  const goToInvoice = (invId: number) =>
    navigate(getModelDetailPath('invoice', invId));
  const goToOrder = (ordId: number) =>
    navigate(getModelDetailPath('order', ordId));

  const isEditable = mode !== 'view';

  const inputClass =
    'w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-60 disabled:cursor-not-allowed';

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <FaSpinner className="animate-spin text-blue-500 text-2xl" />
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4 max-w-5xl mx-auto">
      <PageBreadcrumb pageTitle={isNew ? 'New Payment' : `Payment #${id}`} />

      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => navigate(PageRoutes.transactionsPaymentList)}
          className="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white"
        >
          <FaArrowLeft /> Back to list
        </button>

        <div className="flex items-center gap-2">
          {mode === 'view' && (
            <button
              onClick={() => setMode('edit')}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            >
              Edit
            </button>
          )}
          {isEditable && (
            <>
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg transition-colors disabled:opacity-50"
              >
                {saving ? (
                  <FaSpinner className="animate-spin" size={14} />
                ) : (
                  <FaSave size={14} />
                )}
                Save
              </button>
              {!isNew && (
                <button
                  onClick={() => setMode('view')}
                  className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
                >
                  Cancel
                </button>
              )}
            </>
          )}
          {!isNew && (
            <button
              onClick={handleDelete}
              className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
              title="Delete"
            >
              <FaTrash size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Status badge */}
      {payment && (
        <div className="flex items-center gap-3">
          <span
            className={`px-3 py-1 rounded-full text-sm font-medium ${
              STATUS_STYLES[payment.status] || STATUS_STYLES.pending
            }`}
          >
            {payment.status}
          </span>
          <span className="text-2xl font-bold text-green-600 dark:text-green-400">
            {formatCurrency(payment.amount)}
          </span>
          {payment.amount_available != null && payment.amount_available !== payment.amount && (
            <span className="text-sm text-slate-500 dark:text-slate-400">
              ({formatCurrency(payment.amount_available)} available)
            </span>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left Column — Core Payment */}
        <ComponentCard title="Payment Details">
          <div className="p-4 space-y-4">
            {/* Amount */}
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                amount *
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">$</span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  disabled={!isEditable}
                  className={`${inputClass} pl-7`}
                />
              </div>
            </div>

            {/* Status */}
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                status
              </label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as PaymentStatus)}
                disabled={!isEditable}
                className={inputClass}
              >
                {STATUS_OPTIONS.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            {/* Payment Method */}
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                payment_method
              </label>
              <select
                value={paymentMethodId ?? ''}
                onChange={(e) =>
                  setPaymentMethodId(e.target.value ? parseInt(e.target.value) : null)
                }
                disabled={!isEditable}
                className={inputClass}
              >
                <option value="">Select method...</option>
                {paymentMethods.map((m) => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
            </div>

            {/* Gateway */}
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                gateway
              </label>
              <select
                value={gateway}
                onChange={(e) => setGateway(e.target.value as PaymentGateway)}
                disabled={!isEditable}
                className={inputClass}
              >
                {GATEWAY_OPTIONS.map((g) => (
                  <option key={g} value={g}>{g}</option>
                ))}
              </select>
            </div>

            {/* Payment Date */}
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                dt_payment
              </label>
              <input
                type="date"
                value={paymentDate}
                onChange={(e) => setPaymentDate(e.target.value)}
                disabled={!isEditable}
                className={inputClass}
              />
            </div>

            {/* Reference Number */}
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                reference_number
              </label>
              <input
                type="text"
                value={referenceNumber}
                onChange={(e) => setReferenceNumber(e.target.value)}
                disabled={!isEditable}
                placeholder="Check #, transaction ID, etc."
                className={inputClass}
              />
            </div>

            {/* Fee Amount */}
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                fee_amount
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={feeAmount}
                onChange={(e) => setFeeAmount(e.target.value)}
                disabled={!isEditable}
                className={inputClass}
              />
            </div>

            {/* Reconciled */}
            <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
              <input
                type="checkbox"
                checked={reconciled}
                onChange={(e) => setReconciled(e.target.checked)}
                disabled={!isEditable}
                className="rounded"
              />
              reconciled
            </label>
          </div>
        </ComponentCard>

        {/* Right Column — References & Notes */}
        <div className="space-y-4">
          <ComponentCard title="References">
            <div className="p-4 space-y-4">
              {/* Contact ID */}
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  contact_id *
                </label>
                <input
                  type="number"
                  value={contactId}
                  onChange={(e) => setContactId(e.target.value)}
                  disabled={!isEditable}
                  className={inputClass}
                />
                {payment?.contact_name && (
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    {payment.contact_name}
                  </p>
                )}
              </div>

              {/* Invoice ID */}
              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                  invoice_id
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    value={invoiceId}
                    onChange={(e) => setInvoiceId(e.target.value)}
                    disabled={!isEditable}
                    className={inputClass}
                  />
                  {invoiceId && (
                    <button
                      onClick={() => goToInvoice(Number(invoiceId))}
                      className="p-2 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded"
                      title="Go to invoice"
                    >
                      <FaFileInvoice />
                    </button>
                  )}
                </div>
              </div>

              {/* Customer name (read-only) */}
              {payment?.customer_name && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    customer_name
                  </label>
                  <p className="px-3 py-2 text-slate-900 dark:text-white">
                    {payment.customer_name}
                  </p>
                </div>
              )}

              {/* Linked Orders from refs */}
              {payment?.refs?.order_ids && payment.refs.order_ids.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    .order_ids
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {payment.refs.order_ids.map((oid) => (
                      <button
                        key={oid}
                        onClick={() => goToOrder(oid)}
                        className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 rounded hover:underline"
                      >
                        <FaClipboardList size={10} /> Order #{oid}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Linked Invoices from refs */}
              {payment?.refs?.invoice_ids && payment.refs.invoice_ids.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                    .invoice_ids
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {payment.refs.invoice_ids.map((iid) => (
                      <button
                        key={iid}
                        onClick={() => goToInvoice(iid)}
                        className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 rounded hover:underline"
                      >
                        <FaFileInvoice size={10} /> Invoice #{iid}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </ComponentCard>

          <ComponentCard title="Notes">
            <div className="p-4">
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                disabled={!isEditable}
                rows={4}
                placeholder="Payment notes..."
                className={`${inputClass} resize-none`}
              />
            </div>
          </ComponentCard>

          {/* Gateway / Processing info (read-only) */}
          {payment && (payment.id_gateway_transaction || payment.dt_processed) && (
            <ComponentCard title="Processing">
              <div className="p-4 space-y-2 text-sm">
                {payment.id_gateway_transaction && (
                  <div className="flex justify-between">
                    <span className="text-slate-500 dark:text-slate-400">id_gateway_transaction</span>
                    <span className="font-mono text-slate-900 dark:text-white">
                      {payment.id_gateway_transaction}
                    </span>
                  </div>
                )}
                {payment.id_gateway_payment_intent && (
                  <div className="flex justify-between">
                    <span className="text-slate-500 dark:text-slate-400">id_gateway_payment_intent</span>
                    <span className="font-mono text-slate-900 dark:text-white">
                      {payment.id_gateway_payment_intent}
                    </span>
                  </div>
                )}
                {payment.dt_processed && (
                  <div className="flex justify-between">
                    <span className="text-slate-500 dark:text-slate-400">dt_processed</span>
                    <span className="text-slate-900 dark:text-white">
                      {formatDate(payment.dt_processed)}
                    </span>
                  </div>
                )}
                {payment.dt_reconciliation && (
                  <div className="flex justify-between">
                    <span className="text-slate-500 dark:text-slate-400">dt_reconciliation</span>
                    <span className="text-slate-900 dark:text-white">
                      {formatDate(payment.dt_reconciliation)}
                    </span>
                  </div>
                )}
              </div>
            </ComponentCard>
          )}

          {/* Timestamps (always read-only) */}
          {payment && (
            <ComponentCard title="Timestamps">
              <div className="p-4 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-500 dark:text-slate-400">dt_created</span>
                  <span className="text-slate-900 dark:text-white">{formatDate(payment.dt_created)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500 dark:text-slate-400">dt_modified</span>
                  <span className="text-slate-900 dark:text-white">{formatDate(payment.dt_modified)}</span>
                </div>
                {payment.version != null && (
                  <div className="flex justify-between">
                    <span className="text-slate-500 dark:text-slate-400">version</span>
                    <span className="text-slate-900 dark:text-white">{payment.version}</span>
                  </div>
                )}
              </div>
            </ComponentCard>
          )}
        </div>
      </div>

      {/* Applications Table */}
      {applications.length > 0 && (
        <ComponentCard title={`Applications (${applications.length})`}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700 text-left text-slate-500 dark:text-slate-400">
                  <th className="px-4 py-2">invoice_id</th>
                  <th className="px-4 py-2">amount</th>
                  <th className="px-4 py-2">applied_at</th>
                  <th className="px-4 py-2">notes</th>
                </tr>
              </thead>
              <tbody>
                {applications.map((app) => (
                  <tr
                    key={app.id}
                    className="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50"
                  >
                    <td className="px-4 py-2">
                      <button
                        onClick={() => goToInvoice(app.invoice_id)}
                        className="text-blue-600 dark:text-blue-400 hover:underline"
                      >
                        {app.invoice_number || `#${app.invoice_id}`}
                      </button>
                    </td>
                    <td className="px-4 py-2 font-medium text-green-600 dark:text-green-400">
                      {formatCurrency(app.amount)}
                    </td>
                    <td className="px-4 py-2">{formatDate(app.applied_at)}</td>
                    <td className="px-4 py-2 text-slate-500 dark:text-slate-400">
                      {app.notes || '--'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </ComponentCard>
      )}

      {/* Raw Refs JSON (view mode) */}
      {mode === 'view' && payment?.refs && (
        <ComponentCard title="refs (JSON)">
          <pre className="p-4 text-xs font-mono text-slate-700 dark:text-slate-300 overflow-x-auto">
            {JSON.stringify(payment.refs, null, 2)}
          </pre>
        </ComponentCard>
      )}

      {mode === 'view' && payment?.metadata && Object.keys(payment.metadata).length > 0 && (
        <ComponentCard title="metadata (JSON)">
          <pre className="p-4 text-xs font-mono text-slate-700 dark:text-slate-300 overflow-x-auto">
            {JSON.stringify(payment.metadata, null, 2)}
          </pre>
        </ComponentCard>
      )}
    </div>
  );
}
