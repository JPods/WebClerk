import React, { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getRecord } from '../../api/wcapi';

const InvoiceDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [invoice, setInvoice] = useState<any>(null);
  const [lines, setLines] = useState<any[]>([]);

  useEffect(() => {
    let mounted = true;
    async function load() {
      if (!id) return;
      try {
        setLoading(true);
        setError(null);
        const detail = await getRecord('invoice', Number(id));
        if (!mounted) return;
        setInvoice(detail?.record ?? null);
        const rel = detail?.related || {};
        const detected = rel['invoice_lines'] || rel['invoice_line'] || [];
        setLines(Array.isArray(detected) ? detected : []);
      } catch (e: any) {
        setError(e?.message || 'Failed to load invoice');
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => { mounted = false; };
  }, [id]);

  const lineColumns = useMemo(() => {
    if (!lines.length) return [] as string[];
    const preferred = ['line_no', 'item_id', 'description', 'qty', 'price', 'amount'];
    const keys = Object.keys(lines[0] || {});
    const cols = preferred.filter((k) => keys.includes(k));
    return cols.length ? cols : keys.slice(0, 8);
  }, [lines]);

  return (
    <div className="p-4 space-y-4">
      <nav className="text-sm text-gray-500">Home / Transactions / Invoices / {id}</nav>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {loading ? (
          <div className="text-sm text-gray-500">Loading...</div>
        ) : error ? (
          <div className="text-sm text-red-600">{error}</div>
        ) : !invoice ? (
          <div className="text-sm text-gray-500">No invoice found</div>
        ) : null}
        <div className="space-y-4">
          <div className="card p-4 border rounded">Customer Search (placeholder)</div>
          <div className="card p-4 border rounded">Invoice Form (placeholder)</div>
          <div className="card p-4 border rounded">Invoice Totals (placeholder)</div>
        </div>
        <div className="space-y-4">
          <div className="card p-4 border rounded">Product Tree (placeholder)</div>
          <div className="card p-4 border rounded">Items List (placeholder)</div>
          <div className="card p-4 border rounded">
            <div className="font-medium mb-2">Invoice Lines</div>
            {lines.length === 0 ? (
              <div className="text-sm text-gray-500">No lines</div>
            ) : (
              <div className="overflow-auto">
                <table className="min-w-full text-xs">
                  <thead className="bg-gray-50">
                    <tr>
                      {lineColumns.map((c) => (
                        <th key={c} className="text-left px-2 py-1 font-semibold text-gray-700 border-b">{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {lines.map((ln, idx) => (
                      <tr key={idx} className="odd:bg-white even:bg-gray-50">
                        {lineColumns.map((c) => (
                          <td key={c} className="px-2 py-1 border-b whitespace-nowrap">{String(ln?.[c] ?? '')}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          <div className="card p-4 border rounded">QA List & Form (placeholder)</div>
        </div>
      </div>
    </div>
  );
};

export default InvoiceDetailPage;
