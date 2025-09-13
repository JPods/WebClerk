import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getRecord } from '../../api/wcapi';

const OrderDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [order, setOrder] = useState<any>(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      if (!id) return;
      try {
        setLoading(true);
        setError(null);
        const detail = await getRecord('sales_order', Number(id));
        if (!mounted) return;
        setOrder(detail?.record ?? null);
      } catch (e: any) {
        setError(e?.message || 'Failed to load order');
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => { mounted = false; };
  }, [id]);
  return (
    <div className="p-4 space-y-4">
      <nav className="text-sm text-gray-500">Home / Transactions / Orders / {id}</nav>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {loading ? (
          <div className="text-sm text-gray-500">Loading...</div>
        ) : error ? (
          <div className="text-sm text-red-600">{error}</div>
        ) : !order ? (
          <div className="text-sm text-gray-500">No order found</div>
        ) : null}
        <div className="space-y-4">
          <div className="card p-4 border rounded">Customer Search (placeholder)</div>
          <div className="card p-4 border rounded">
            <div className="font-medium mb-2">Order</div>
            <pre className="text-xs overflow-auto">{JSON.stringify(order, null, 2)}</pre>
          </div>
          <div className="card p-4 border rounded">
            <div className="font-medium mb-2">Order Totals</div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="text-gray-500">Amount</div>
              <div>{String(order?.amount ?? '')}</div>
              <div className="text-gray-500">Sales Tax</div>
              <div>{String(order?.sales_tax ?? '')}</div>
              <div className="text-gray-500">Freight</div>
              <div>{String(order?.ship_total ?? '')}</div>
              <div className="text-gray-500">Total</div>
              <div>{String(order?.total ?? '')}</div>
            </div>
          </div>
        </div>
        <div className="space-y-4">
          <div className="card p-4 border rounded">Product Tree (placeholder)</div>
          <div className="card p-4 border rounded">Items List (placeholder)</div>
          <div className="card p-4 border rounded">Order Lines (placeholder)</div>
          <div className="card p-4 border rounded">QA List & Form (placeholder)</div>
        </div>
      </div>
    </div>
  );
};

export default OrderDetailPage;
