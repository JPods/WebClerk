import React, { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getRecord } from '../../api/wcapi';

const PurchaseOrderDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [po, setPO] = useState<any>(null);
  const [lines, setLines] = useState<any[]>([]);
  const [vendors, setVendors] = useState<any[]>([]);
  const [addresses, setAddresses] = useState<any[]>([]);
  const [phones, setPhones] = useState<any[]>([]);
  const [emails, setEmails] = useState<any[]>([]);

  useEffect(() => {
    let mounted = true;
    async function load() {
      if (!id) return;
      try {
        setLoading(true);
        setError(null);
        const detail = await getRecord('purchase_order', Number(id));
        if (!mounted) return;
        setPO(detail?.record ?? null);
        const rel = detail?.related || {};
        const detected = rel['purchase_order_lines'] || rel['purchase_order_line'] || [];
        setLines(Array.isArray(detected) ? detected : []);
  setVendors(Array.isArray(rel['vendors']) ? rel['vendors'] : []);
  setAddresses(Array.isArray(rel['addresses']) ? rel['addresses'] : []);
  setPhones(Array.isArray(rel['phones']) ? rel['phones'] : []);
  setEmails(Array.isArray(rel['emails']) ? rel['emails'] : []);
      } catch (e: any) {
        setError(e?.message || 'Failed to load purchase order');
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
      <nav className="text-sm text-gray-500">Home / Transactions / Purchase Orders / {id}</nav>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {loading ? (
          <div className="text-sm text-gray-500">Loading...</div>
        ) : error ? (
          <div className="text-sm text-red-600">{error}</div>
        ) : !po ? (
          <div className="text-sm text-gray-500">No purchase order found</div>
        ) : null}
        <div className="space-y-4">
          <div className="card p-4 border rounded">Vendor Search (placeholder)</div>
          <div className="card p-4 border rounded">
            <div className="font-medium mb-2">PO Form (placeholder)</div>
            <pre className="text-xs overflow-auto">{JSON.stringify(po, null, 2)}</pre>
          </div>
          <div className="card p-4 border rounded">PO Totals (placeholder)</div>
          <div className="card p-4 border rounded">
            <div className="font-medium mb-2">Related Vendor & Contacts</div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <div className="text-gray-500 mb-1">Vendors</div>
                {vendors.length === 0 ? <div className="text-xs text-gray-400">None</div> : (
                  <ul className="list-disc list-inside text-xs">
                    {vendors.map((v, i) => <li key={i}>{v?.display_name || v?.name || v?.id}</li>)}
                  </ul>
                )}
              </div>
              <div>
                <div className="text-gray-500 mb-1">Phones</div>
                {phones.length === 0 ? <div className="text-xs text-gray-400">None</div> : (
                  <ul className="list-disc list-inside text-xs">
                    {phones.map((p, i) => <li key={i}>{p?.number || p?.name || p?.id}</li>)}
                  </ul>
                )}
              </div>
              <div>
                <div className="text-gray-500 mb-1">Emails</div>
                {emails.length === 0 ? <div className="text-xs text-gray-400">None</div> : (
                  <ul className="list-disc list-inside text-xs">
                    {emails.map((e, i) => <li key={i}>{e?.email || e?.name || e?.id}</li>)}
                  </ul>
                )}
              </div>
              <div>
                <div className="text-gray-500 mb-1">Addresses</div>
                {addresses.length === 0 ? <div className="text-xs text-gray-400">None</div> : (
                  <ul className="list-disc list-inside text-xs">
                    {addresses.map((a, i) => <li key={i}>{a?.display || a?.address1 || a?.id}</li>)}
                  </ul>
                )}
              </div>
            </div>
          </div>
        </div>
        <div className="space-y-4">
          <div className="card p-4 border rounded">Product Tree (placeholder)</div>
          <div className="card p-4 border rounded">Items List (placeholder)</div>
          <div className="card p-4 border rounded">
            <div className="font-medium mb-2">Purchase Order Lines</div>
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
        </div>
      </div>
    </div>
  );
};

export default PurchaseOrderDetailPage;
