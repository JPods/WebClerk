import React, { useEffect, useMemo, useState } from 'react';
import { getModelDetail, getRecords, getRecord } from '../../api/wcapi';

type Row = Record<string, any>;

const MODEL = 'item';

const ProductsPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [q, setQ] = useState('');
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<any | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

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
        setError(e?.message || 'Failed to load products');
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

  async function openDetail(id: number) {
    try {
      setSelectedId(id);
      setDrawerOpen(true);
      const d = await getRecord(MODEL, id);
      setDetail(d?.record ?? null);
    } catch (e) {
      // keep drawer open, but indicate no detail
      setDetail(null);
    }
  }

  function closeDrawer() {
    setDrawerOpen(false);
    setSelectedId(null);
    setDetail(null);
  }

  return (
    <div className="p-4 space-y-4">
      <nav className="text-sm text-gray-500">Home / Products</nav>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-1 space-y-3">
          <div className="card p-4 border rounded">
            <div className="font-medium mb-2">Product Key/Tag Search</div>
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search products..."
              className="w-full border rounded px-3 py-2 text-sm"
            />
            <p className="text-xs text-gray-500 mt-2">Filters client-side for now; server-side filters can be added.</p>
          </div>
        </div>
        <div className="lg:col-span-2">
          <div className="card p-0 border rounded overflow-auto">
            {loading ? (
              <div className="p-4 text-sm text-gray-500">Loading...</div>
            ) : error ? (
              <div className="p-4 text-sm text-red-600">{error}</div>
            ) : (
              <table className="min-w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {columns.slice(0, 8).map((c) => (
                      <th key={c} className="text-left px-3 py-2 font-semibold text-gray-700 border-b">{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((r, idx) => (
                    <tr
                      key={idx}
                      className="odd:bg-white even:bg-gray-50 cursor-pointer hover:bg-brand-50"
                      onClick={() => r?.id != null && openDetail(Number(r.id))}
                    >
                      {columns.slice(0, 8).map((c) => (
                        <td key={c} className="px-3 py-2 border-b whitespace-nowrap">{String(r?.[c] ?? '')}</td>
                      ))}
                    </tr>
                  ))}
                  {filtered.length === 0 && (
                    <tr>
                      <td className="px-3 py-4 text-center text-gray-500" colSpan={Math.max(1, columns.slice(0,8).length)}>
                        No products found
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {/* Side drawer for detail */}
      {drawerOpen && (
        <div className="fixed inset-0 z-40">
          <div className="absolute inset-0 bg-black/30" onClick={closeDrawer} />
          <div className="absolute right-0 top-0 h-full w-full sm:w-[480px] bg-white shadow-xl p-4 overflow-auto">
            <div className="flex items-center justify-between mb-3">
              <div className="font-semibold">Product Detail {selectedId ? `#${selectedId}` : ''}</div>
              <button onClick={closeDrawer} className="text-gray-500 hover:text-gray-700">Close</button>
            </div>
            {!detail ? (
              <div className="text-sm text-gray-500">Loading...</div>
            ) : (
              <pre className="text-xs">{JSON.stringify(detail, null, 2)}</pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default ProductsPage;
