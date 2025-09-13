import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { getModelDetail, getRecords } from '../../api/wcapi';
import { PageRoutes } from '../../routes/Routes';

const MODEL = 'sales_order';

const OrdersListPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<any[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [q, setQ] = useState('');

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        setLoading(true);
        setError(null);
        const [detail, list] = await Promise.all([
          getModelDetail(MODEL),
          getRecords(MODEL),
        ]);
        if (!mounted) return;
        const cols = (detail?.model?.fields || []).map((f: any) => f.name);
        setColumns(cols);
        setRows(Array.isArray(list?.results) ? list.results : []);
      } catch (e: any) {
        setError(e?.message || 'Failed to load orders');
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => {
      mounted = false;
    };
  }, []);

  const filtered = useMemo(() => {
    if (!q) return rows;
    const needle = q.toLowerCase();
    return rows.filter((r) =>
      Object.values(r).some((v) => String(v ?? '').toLowerCase().includes(needle))
    );
  }, [rows, q]);

  return (
    <div className="p-4 space-y-4">
      <nav className="text-sm text-gray-500">Home / Transactions / Orders</nav>
      <div className="card p-4 border rounded">
        <div className="flex items-center gap-3 mb-3">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search orders..."
            className="w-full border rounded px-3 py-2 text-sm"
          />
        </div>
        {loading ? (
          <div className="text-sm text-gray-500">Loading...</div>
        ) : error ? (
          <div className="text-sm text-red-600">{error}</div>
        ) : (
          <div className="overflow-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {columns.slice(0, 6).map((c) => (
                    <th key={c} className="text-left px-3 py-2 font-semibold text-gray-700 border-b">{c}</th>
                  ))}
                  <th className="px-3 py-2 border-b">Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r, idx) => (
                  <tr key={idx} className="odd:bg-white even:bg-gray-50">
                    {columns.slice(0, 6).map((c) => (
                      <td key={c} className="px-3 py-2 border-b whitespace-nowrap">{String(r?.[c] ?? '')}</td>
                    ))}
                    <td className="px-3 py-2 border-b whitespace-nowrap">
                      {r?.id != null ? (
                        <Link className="text-brand-600 hover:underline" to={PageRoutes.transactionsOrders + '/' + r.id}>View</Link>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td className="px-3 py-4 text-center text-gray-500" colSpan={Math.max(2, columns.slice(0,6).length + 1)}>
                      No orders found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default OrdersListPage;
