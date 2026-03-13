import React, { useState, useEffect } from 'react';
import { useWCAPI } from '../../../hooks/useWCAPI';
import { useRealTimeCalculations } from '../../../hooks/useRealTimeCalculations';
import { useAuditTrail } from '../../../hooks/useAuditTrail';
import { TransactionHeader } from '../common/TransactionHeader';
import { TransactionTotals } from '../common/TransactionTotals';
import { AuditTrail } from '../common/AuditTrail';
import { TransactionLine } from '../../../hooks/useRealTimeCalculations';

export interface OrderFormProps {
  order_id?: number;
  onSave?: (order: any) => void;
  onCancel?: () => void;
}

export const OrderForm: React.FC<OrderFormProps> = ({
  order_id,
  onSave,
  onCancel,
}) => {
  const { get, create, update } = useWCAPI();
  const [loading, setLoading] = useState(false);
  const [order, setOrder] = useState({
    id: order_id || 0,
    uuid: '',
    ida: '',
    order_no: '',
    status: 'confirmed',
    customer_id: 0,
    vendor_id: 0,
    manufacturer_id: 0,
    priority: '',
    price_level: '',
    dt_created: '',
    dt_modified: '',
    dt_shipped: '',
    cost: {},
    sell: {},
    finance: {},
    flow: {},
    source: {},
    action: {},
  });

  const [lines, setLines] = useState<TransactionLine[]>([]);
  const totals = useRealTimeCalculations(lines, 0.08, 0, 0);
  const { addEntry } = useAuditTrail(order_id || 0, 'order');

  useEffect(() => {
    if (order_id) {
      loadOrder();
    } else {
      setOrder(prev => ({
        ...prev,
        dt_created: new Date().toISOString(),
        dt_modified: new Date().toISOString(),
      }));
    }
  }, [order_id]);

  const loadOrder = async () => {
    setLoading(true);
    try {
      const [orderRes, linesRes] = await Promise.all([
        get('order', { id: order_id }),
        get('order_line', { parent: order_id }),
      ]);

      if (orderRes?.record) {
        setOrder(orderRes.record);
      }

      if (linesRes?.results) {
        setLines(linesRes.results);
      }
    } catch (error) {
      console.error('Failed to load order:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleHeaderChange = (field: string, value: any) => {
    setOrder(prev => ({
      ...prev,
      [field]: value,
      dt_modified: new Date().toISOString(),
    }));
  };

  const handleSave = async () => {
    setLoading(true);
    try {
      let savedOrder;
      if (order_id) {
        const response = await update('order', order_id, order);
        savedOrder = response?.record;
        await addEntry('updated', { status: order.status });
      } else {
        const response = await create('order', order);
        savedOrder = response?.record;
        await addEntry('created', { status: order.status });
      }

      if (savedOrder) {
        // Save lines
        for (const line of lines) {
          if (line.id) {
            await update('order_line', line.id, {
              ...line,
              parent: savedOrder.id,
            });
          } else {
            await create('order_line', {
              ...line,
              parent: savedOrder.id,
            });
          }
        }

        onSave?.(savedOrder);
      }
    } catch (error) {
      console.error('Failed to save order:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2">Loading order...</span>
      </div>
    );
  }

  return (
    <div className="order-form max-w-6xl mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-800">
          {order_id ? `Edit Order #${order.order_no}` : 'New Order'}
        </h1>
        <div className="space-x-2">
          <button
            onClick={handleSave}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Saving...' : 'Save'}
          </button>
          <button
            onClick={onCancel}
            className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
          >
            Cancel
          </button>
        </div>
      </div>

      <TransactionHeader
        model="order"
        transactionId={order_id}
        data={order}
        onChange={handleHeaderChange}
      />

      {/* Lines Section */}
      <div className="bg-white p-6 rounded-lg shadow-sm border">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-gray-800">Order Lines</h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full table-auto">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left">Item</th>
                <th className="px-4 py-2 text-left">Description</th>
                <th className="px-4 py-2 text-right">Quantity</th>
                <th className="px-4 py-2 text-right">Price</th>
                <th className="px-4 py-2 text-right">Extended</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line, index) => (
                <tr key={index} className="border-t">
                  <td className="px-4 py-2">{line.item_name}</td>
                  <td className="px-4 py-2">{line.description}</td>
                  <td className="px-4 py-2 text-right">{line.quantity}</td>
                  <td className="px-4 py-2 text-right">${line.price.toFixed(2)}</td>
                  <td className="px-4 py-2 text-right font-medium">
                    ${(line.quantity * line.price).toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <TransactionTotals totals={totals} />

      {order_id && (
        <AuditTrail
          transactionId={order_id}
          model="order"
          className="mt-6"
        />
      )}
    </div>
  );
};