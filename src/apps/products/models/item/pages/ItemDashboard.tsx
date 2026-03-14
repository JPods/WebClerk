/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { Item } from '../../../../../model/item';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

export default function ItemDashboard() {
  const { id } = useParams();
  const [item, setItem] = useState<Item | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    console.log('ItemDashboard route param id:', id);
    if (!id) return;
    setLoading(true);
    setError(null);
    fetch(`/wcapi/get/?model_name=item&id=${id}`)
      .then((res) => {
        console.log('API response status:', res.status);
        if (!res.ok) throw new Error('Failed to fetch item');
        return res.json();
      })
      .then((data) => {
        console.log('API response data:', data);
        const itemData = data?.data?.item || data?.data || data?.item || data;
        setItem(itemData as Item);
      })
      .catch((err) => {
        console.error('API error:', err);
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return <div className="p-8 text-center text-gray-500">Loading item...</div>;
  }
  if (error) {
    return <div className="p-8 text-center text-red-500">Error: {error}</div>;
  }
  if (!item) {
    return <div className="p-8 text-center text-gray-500">No item data loaded.</div>;
  }

  return (
    <div className="p-6 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
      {/* Core Info */}
      <section className="col-span-1 md:col-span-2 xl:col-span-3 bg-white rounded shadow p-4">
        <h2 className="text-xl font-bold mb-2">{item.name} <span className="text-sm text-gray-400">({item.sku})</span></h2>
        <div className="text-gray-600 mb-2">{item.description}</div>
        <div className="flex flex-wrap gap-4 text-xs text-gray-500">
          <span>Kind: {item.kind}</span>
          <span>UOM: {item.uom}</span>
          <span>Base UOM: {item.base_uom}</span>
          <span>Row Version: {item.row_version}</span>
        </div>
      </section>
      {/* Metrics/Stats */}
      <section className="bg-white rounded shadow p-4">
        <h3 className="font-semibold mb-2">Metrics</h3>
        <div className="text-gray-400">No metrics available.</div>
      </section>
      {/* Quantity/Inventory */}
      <section className="bg-white rounded shadow p-4">
        <h3 className="font-semibold mb-2">Inventory</h3>
        <pre className="text-xs bg-gray-50 rounded p-2 overflow-x-auto">{JSON.stringify(item.quantity, null, 2)}</pre>
      </section>
      {/* Price */}
      <section className="bg-white rounded shadow p-4">
        <h3 className="font-semibold mb-2">Price</h3>
        <pre className="text-xs bg-gray-50 rounded p-2 overflow-x-auto">{JSON.stringify(item.price, null, 2)}</pre>
      </section>
      {/* Cost */}
      <section className="bg-white rounded shadow p-4">
        <h3 className="font-semibold mb-2">Cost</h3>
        <pre className="text-xs bg-gray-50 rounded p-2 overflow-x-auto">{JSON.stringify(item.cost, null, 2)}</pre>
      </section>
      {/* Flags */}
      <section className="bg-white rounded shadow p-4">
        <h3 className="font-semibold mb-2">Flags</h3>
        <pre className="text-xs bg-gray-50 rounded p-2 overflow-x-auto">{JSON.stringify(item.flags, null, 2)}</pre>
      </section>
      {/* Tax */}
      <section className="bg-white rounded shadow p-4">
        <h3 className="font-semibold mb-2">Tax</h3>
        <pre className="text-xs bg-gray-50 rounded p-2 overflow-x-auto">{JSON.stringify(item.tax_code, null, 2)}</pre>
      </section>
      {/* Catalog */}
      <section className="bg-white rounded shadow p-4">
        <h3 className="font-semibold mb-2">Catalog</h3>
        <pre className="text-xs bg-gray-50 rounded p-2 overflow-x-auto">{JSON.stringify(item.catalog, null, 2)}</pre>
      </section>
      {/* Specification */}
      <section className="bg-white rounded shadow p-4">
        <h3 className="font-semibold mb-2">Specification</h3>
        <div className="text-gray-400">Spec ID: {item.specification_id || 'N/A'}</div>
      </section>
      {/* Serial Tracking */}
      <section className="bg-white rounded shadow p-4">
        <h3 className="font-semibold mb-2">Serial Tracking</h3>
        <div className="text-gray-400">{item.flags?.serialized ? 'Serialized' : 'Not serialized'}</div>
      </section>
      {/* Bill of Material */}
      <section className="bg-white rounded shadow p-4">
        <h3 className="font-semibold mb-2">Bill of Material</h3>
        <div className="text-gray-400">No BOM data (link or embed as needed).</div>
      </section>
      {/* Pending Inventory */}
      <section className="bg-white rounded shadow p-4">
        <h3 className="font-semibold mb-2">Pending Inventory</h3>
        <div className="text-gray-400">No pending inventory records.</div>
      </section>
      {/* Usage */}
      <section className="bg-white rounded shadow p-4">
        <h3 className="font-semibold mb-2">Usage</h3>
        <div className="text-gray-400">No usage data.</div>
      </section>
      {/* Variant */}
      <section className="bg-white rounded shadow p-4">
        <h3 className="font-semibold mb-2">Variant</h3>
        <div className="text-gray-400">No variant data.</div>
      </section>
      {/* Warehouse */}
      <section className="bg-white rounded shadow p-4">
        <h3 className="font-semibold mb-2">Warehouse</h3>
        <div className="text-gray-400">No warehouse data.</div>
      </section>
    </div>
  );
}
