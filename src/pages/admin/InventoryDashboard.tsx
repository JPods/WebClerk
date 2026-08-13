/**
 * Inventory Dashboard — consolidated inventory management.
 *
 * Replaces 4 separate wc2 forms (InShipGoods, InventoryAdjustment,
 * ItemWarehouse, InshipAdj) with one page, five tabs.
 *
 * Tabs:
 *   1. Receive   — PO receiving into inventory layers
 *   2. Adjust    — manual quantity adjustments with reason codes
 *   3. Warehouse — inventory by warehouse with reorder alerts
 *   4. Reconcile — physical count vs system, variance adjustments
 *   5. Training  — Alice's guided Proposal→Order→Invoice→Payment→PO→Receive cycle
 *
 * All mutations go through manageAction → backend services:
 *   - receive_inventory (inventory_stacks.py)
 *   - adjust_item_quantity (inventory_pending.py)
 *   - get_item_inventory_summary (inventory_stacks.py)
 *   - get_items_below_reorder (suggest_purchase.py)
 */
import React, { useCallback, useEffect, useState } from "react";
import apiClient from "../../api/axios";
import { getRecords, manageAction } from "../../api/wcapi";
import AliceHintBar from "../../components/common/AliceHintBar";
import { formatDt } from '@/utils/fieldFormatters';
import {
  FaSync,
  FaBoxOpen,
  FaExchangeAlt,
  FaWarehouse,
  FaClipboardCheck,
  FaExclamationTriangle,
  FaCheckCircle,
  FaSearch,
  FaGraduationCap,
  FaFileInvoice,
  FaShoppingCart,
  FaTruck,
  FaClipboardList,
} from "react-icons/fa";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type TabKey = "receive" | "adjust" | "warehouse" | "reconcile" | "training";

interface POLine {
  id: number;
  item_fk_id: number;
  item_ida: string;
  item_name: string;
  qty_ordered: number;
  qty_received: number;
  qty_remaining: number;
  unit_cost: number;
}

interface PurchaseOrder {
  id: number;
  ida: string;
  vendor_name: string;
  status: string;
  lines: POLine[];
}

interface ItemQuantity {
  on_hand: number;
  on_po: number;
  on_so: number;
  on_p: number;
  available: number;
  [key: string]: number;
}

interface ItemRecord {
  id: number;
  ida: string;
  name: string;
  quantity: ItemQuantity;
}

interface AdjustmentRecord {
  pending_id: number;
  field: string;
  delta: number;
  reason: string;
  state: string;
  source_type: string;
  source_id: number | null;
  dt_requested: number | null;
  dt_applied: string | null;
}

interface WarehouseItem {
  id: number;
  item_id: number;
  item_ida: string;
  item_name: string;
  warehouse_id: number;
  warehouse_name: string;
  on_hand: number;
  on_po: number;
  on_so: number;
  available: number;
  reorder_point: number | null;
  below_reorder: boolean;
}

interface ReconcileRow {
  item_id: number;
  item_ida: string;
  item_name: string;
  system_on_hand: number;
  physical_count: number | null;
  variance: number | null;
}

// ---------------------------------------------------------------------------
// Reason codes for adjustments
// ---------------------------------------------------------------------------

const REASON_CODES = [
  { value: "count_correction", label: "Count Correction" },
  { value: "damage", label: "Damage" },
  { value: "return", label: "Return" },
  { value: "sample", label: "Sample" },
  { value: "write_off", label: "Write Off" },
  { value: "found", label: "Found" },
  { value: "transfer_in", label: "Transfer In" },
  { value: "transfer_out", label: "Transfer Out" },
];

const QTY_FIELDS = [
  { value: "on_hand", label: "On Hand" },
  { value: "on_po", label: "On PO" },
  { value: "on_so", label: "On SO" },
  { value: "on_p", label: "On Proposal" },
  { value: "available", label: "Available" },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const fmtInt = (n: number) => n.toLocaleString("en-US");
const fmtDec = (n: number) =>
  n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtDate = (ms: number | null) =>
  ms ? formatDt(ms, 'datetime') : "\u2014";

// ---------------------------------------------------------------------------
// Shared components
// ---------------------------------------------------------------------------

const Card: React.FC<{
  title: string;
  icon?: React.ReactNode;
  alert?: boolean;
  children: React.ReactNode;
}> = ({ title, icon, alert, children }) => (
  <div
    data-wc="inv-card"
    className={`rounded-lg border p-4 shadow-sm ${
      alert ? "border-red-300 bg-red-50" : "border-gray-200 bg-white"
    }`}
  >
    <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-3">
      {icon} {title}
    </h3>
    {children}
  </div>
);

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const colors: Record<string, string> = {
    applied: "bg-green-100 text-green-800",
    pending: "bg-yellow-100 text-yellow-800",
    rejected: "bg-red-100 text-red-800",
  };
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
        colors[status] || "bg-gray-100 text-gray-700"
      }`}
    >
      {status}
    </span>
  );
};

const TabButton: React.FC<{
  active: boolean;
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}> = ({ active, icon, label, onClick }) => (
  <button
    data-wc={`inv-tab-${label.toLowerCase()}`}
    onClick={onClick}
    className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 transition-colors ${
      active
        ? "border-blue-600 text-blue-600 bg-blue-50"
        : "border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50"
    }`}
  >
    {icon} {label}
  </button>
);

// ---------------------------------------------------------------------------
// Tab 1: Receive
// ---------------------------------------------------------------------------

function ReceiveTab() {
  const [purchases, setPurchases] = useState<{ id: number; ida: string; vendor_name: string; status: string }[]>([]);
  const [selectedPO, setSelectedPO] = useState<PurchaseOrder | null>(null);
  const [receiveQtys, setReceiveQtys] = useState<Record<number, number>>({});
  const [loading, setLoading] = useState(false);
  const [receiving, setReceiving] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");

  // Fetch open purchase orders
  const fetchPurchases = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getRecords("purchase", {
        status__in: "planned,ordered,partial",
        limit: 200,
        ordering: "-dt_created",
      });
      setPurchases(
        (data.results || []).map((p: any) => ({
          id: p.id,
          ida: p.ida || `PO-${p.id}`,
          vendor_name: p.vendor?.display_name || p.refs?.vendor_name || `Vendor #${p.vendor_id || "?"}`,
          status: p.status || "planned",
        }))
      );
    } catch (err: any) {
      setError(err?.message || "Failed to load purchase orders");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPurchases();
  }, [fetchPurchases]);

  // Fetch PO detail with lines
  const selectPO = async (poId: number) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setReceiveQtys({});
    try {
      const res = await apiClient.get(`/wcapi/get/`, {
        params: { model_name: "purchase", id: poId },
      });
      const record = res.data?.data?.record || res.data?.record;
      const lines = record?.lines || [];

      const poLines: POLine[] = lines.map((line: any) => {
        const qty = line.quantity || {};
        const ordered = qty.active || qty.staged || 0;
        const received = qty.received || 0;
        const remaining = ordered - received;
        const itemInfo = line.item || {};
        return {
          id: line.id,
          item_fk_id: line.item_fk_id || line.item_fk || itemInfo.item_id,
          item_ida: itemInfo.ida_item || line.ida || "",
          item_name: itemInfo.description || line.name || "",
          qty_ordered: ordered,
          qty_received: received,
          qty_remaining: Math.max(0, remaining),
          unit_cost: line.cost?.unit || 0,
        };
      });

      setSelectedPO({
        id: record.id,
        ida: record.ida || `PO-${record.id}`,
        vendor_name: record.vendor?.display_name || "",
        status: record.status || "",
        lines: poLines,
      });
    } catch (err: any) {
      setError(err?.message || "Failed to load PO details");
    } finally {
      setLoading(false);
    }
  };

  // Receive inventory for all lines with entered quantities
  const handleReceive = async () => {
    if (!selectedPO) return;
    const linesToReceive = selectedPO.lines.filter(
      (l) => (receiveQtys[l.id] || 0) > 0
    );
    if (linesToReceive.length === 0) {
      setError("Enter a quantity to receive for at least one line.");
      return;
    }

    setReceiving(true);
    setError(null);
    setResult(null);

    const results: string[] = [];
    let hasError = false;

    for (const line of linesToReceive) {
      const qty = receiveQtys[line.id] || 0;
      if (qty <= 0) continue;

      try {
        // Create inventory layer via receive_inventory
        await manageAction("receive_inventory", {
          item_id: line.item_fk_id,
          warehouse_id: 1, // default warehouse
          qty_received: qty,
          unit_cost: line.unit_cost,
          source_type: "purchase",
          source_id: selectedPO.id,
        });

        // Adjust on_hand up
        await manageAction("adjust_item_quantity", {
          item_id: line.item_fk_id,
          field: "on_hand",
          delta: qty,
          reason: "po_receive",
          source_type: "purchase",
          source_id: selectedPO.id,
          source_line_id: line.id,
        });

        // Adjust on_po down
        await manageAction("adjust_item_quantity", {
          item_id: line.item_fk_id,
          field: "on_po",
          delta: -qty,
          reason: "po_receive",
          source_type: "purchase",
          source_id: selectedPO.id,
          source_line_id: line.id,
        });

        results.push(`${line.item_ida || line.item_name}: received ${qty}`);
      } catch (err: any) {
        hasError = true;
        results.push(
          `${line.item_ida || line.item_name}: FAILED - ${err?.message || "unknown error"}`
        );
      }
    }

    setReceiving(false);
    setResult(results.join("\n"));
    if (!hasError) {
      // Refresh PO to show updated quantities
      selectPO(selectedPO.id);
    }
  };

  const filteredPurchases = purchases.filter(
    (p) =>
      p.ida.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.vendor_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div data-wc="inv-receive" className="space-y-4">
      {/* PO Selection */}
      <Card title="Select Purchase Order" icon={<FaBoxOpen />}>
        <div className="flex items-center gap-2 mb-3">
          <div className="relative flex-1">
            <FaSearch className="absolute left-3 top-2.5 text-gray-400" size={12} />
            <input
              data-wc="inv-receive-search"
              type="text"
              placeholder="Search PO number or vendor..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-2 text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          <button
            onClick={fetchPurchases}
            disabled={loading}
            className="flex items-center gap-1 px-3 py-2 text-sm bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-50"
          >
            <FaSync className={loading ? "animate-spin" : ""} size={11} /> Refresh
          </button>
        </div>

        {loading && !selectedPO && (
          <p className="text-sm text-gray-500">Loading purchase orders...</p>
        )}

        <div className="max-h-48 overflow-y-auto border rounded">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 sticky top-0">
              <tr>
                <th className="text-left px-3 py-1.5 font-medium text-gray-600">PO #</th>
                <th className="text-left px-3 py-1.5 font-medium text-gray-600">Vendor</th>
                <th className="text-left px-3 py-1.5 font-medium text-gray-600">Status</th>
                <th className="px-3 py-1.5"></th>
              </tr>
            </thead>
            <tbody>
              {filteredPurchases.map((po) => (
                <tr
                  key={po.id}
                  className={`border-t hover:bg-blue-50 cursor-pointer ${
                    selectedPO?.id === po.id ? "bg-blue-50" : ""
                  }`}
                  onClick={() => selectPO(po.id)}
                >
                  <td className="px-3 py-1.5 font-mono">{po.ida}</td>
                  <td className="px-3 py-1.5">{po.vendor_name}</td>
                  <td className="px-3 py-1.5">
                    <StatusBadge status={po.status} />
                  </td>
                  <td className="px-3 py-1.5 text-blue-600 text-xs">Select</td>
                </tr>
              ))}
              {filteredPurchases.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-3 py-4 text-center text-gray-400">
                    No open purchase orders found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* PO Lines — enter quantities to receive */}
      {selectedPO && (
        <Card title={`Receive: ${selectedPO.ida} — ${selectedPO.vendor_name}`} icon={<FaBoxOpen />}>
          <table className="w-full text-sm mb-4">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-3 py-1.5 font-medium text-gray-600">Item</th>
                <th className="text-left px-3 py-1.5 font-medium text-gray-600">Name</th>
                <th className="text-right px-3 py-1.5 font-medium text-gray-600">Ordered</th>
                <th className="text-right px-3 py-1.5 font-medium text-gray-600">Received</th>
                <th className="text-right px-3 py-1.5 font-medium text-gray-600">Remaining</th>
                <th className="text-right px-3 py-1.5 font-medium text-gray-600">Unit Cost</th>
                <th className="text-right px-3 py-1.5 font-medium text-gray-600">Receive Qty</th>
              </tr>
            </thead>
            <tbody>
              {selectedPO.lines.map((line) => (
                <tr key={line.id} className="border-t">
                  <td className="px-3 py-1.5 font-mono text-xs">{line.item_ida}</td>
                  <td className="px-3 py-1.5">{line.item_name}</td>
                  <td className="px-3 py-1.5 text-right font-mono">{fmtInt(line.qty_ordered)}</td>
                  <td className="px-3 py-1.5 text-right font-mono">{fmtInt(line.qty_received)}</td>
                  <td className="px-3 py-1.5 text-right font-mono">{fmtInt(line.qty_remaining)}</td>
                  <td className="px-3 py-1.5 text-right font-mono">{fmtDec(line.unit_cost)}</td>
                  <td className="px-3 py-1.5 text-right">
                    <input
                      data-wc={`inv-receive-qty-${line.id}`}
                      type="number"
                      min={0}
                      max={line.qty_remaining}
                      value={receiveQtys[line.id] || ""}
                      onChange={(e) =>
                        setReceiveQtys((prev) => ({
                          ...prev,
                          [line.id]: Math.min(
                            parseInt(e.target.value) || 0,
                            line.qty_remaining
                          ),
                        }))
                      }
                      className="w-20 px-2 py-1 text-right text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="flex items-center justify-between">
            <div>
              {error && <p className="text-sm text-red-600">{error}</p>}
              {result && (
                <pre className="text-xs text-green-700 whitespace-pre-wrap bg-green-50 p-2 rounded">
                  {result}
                </pre>
              )}
            </div>
            <button
              data-wc="inv-receive-submit"
              onClick={handleReceive}
              disabled={receiving}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              <FaBoxOpen size={12} />
              {receiving ? "Receiving..." : "Receive"}
            </button>
          </div>
        </Card>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 2: Adjust
// ---------------------------------------------------------------------------

function AdjustTab() {
  const [searchTerm, setSearchTerm] = useState("");
  const [items, setItems] = useState<ItemRecord[]>([]);
  const [selectedItem, setSelectedItem] = useState<ItemRecord | null>(null);
  const [adjField, setAdjField] = useState("on_hand");
  const [adjDelta, setAdjDelta] = useState<number>(0);
  const [adjReason, setAdjReason] = useState("count_correction");
  const [pending, setPending] = useState<AdjustmentRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Search items
  const searchItems = async () => {
    if (!searchTerm.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getRecords("item", {
        keyword: searchTerm,
        limit: 50,
      });
      setItems(
        (data.results || []).map((i: any) => ({
          id: i.id,
          ida: i.ida || "",
          name: i.name || "",
          quantity: i.quantity || { on_hand: 0, on_po: 0, on_so: 0, on_p: 0, available: 0 },
        }))
      );
    } catch (err: any) {
      setError(err?.message || "Search failed");
    } finally {
      setLoading(false);
    }
  };

  // Select item and load pending adjustments
  const selectItem = async (item: ItemRecord) => {
    setSelectedItem(item);
    setResult(null);
    setError(null);
    setAdjDelta(0);

    try {
      const data = await manageAction("get_pending_for_item", {
        item_id: item.id,
      });
      setPending(Array.isArray(data) ? data : []);
    } catch {
      setPending([]);
    }
  };

  // Submit adjustment
  const handleAdjust = async () => {
    if (!selectedItem || adjDelta === 0) {
      setError("Select an item and enter a non-zero adjustment.");
      return;
    }

    setSubmitting(true);
    setError(null);
    setResult(null);

    try {
      const res = await manageAction("adjust_item_quantity", {
        item_id: selectedItem.id,
        field: adjField,
        delta: adjDelta,
        reason: adjReason,
        source_type: "manual_adjustment",
      });

      setResult(
        `Adjustment ${res.applied ? "applied" : "queued as pending"}: ${adjField} ${
          adjDelta > 0 ? "+" : ""
        }${adjDelta} (${adjReason})`
      );

      // Refresh item data
      const data = await getRecords("item", { id: selectedItem.id });
      if (data.results?.[0]) {
        const updated = data.results[0];
        setSelectedItem({
          id: updated.id,
          ida: updated.ida || "",
          name: updated.name || "",
          quantity: updated.quantity || {},
        });
      }

      // Refresh pending
      const pendingData = await manageAction("get_pending_for_item", {
        item_id: selectedItem.id,
      });
      setPending(Array.isArray(pendingData) ? pendingData : []);

      setAdjDelta(0);
    } catch (err: any) {
      setError(err?.message || "Adjustment failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div data-wc="inv-adjust" className="space-y-4">
      {/* Item Search */}
      <Card title="Search Item" icon={<FaSearch />}>
        <div className="flex items-center gap-2">
          <input
            data-wc="inv-adjust-search"
            type="text"
            placeholder="Item ID, name, or keyword..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && searchItems()}
            className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
          />
          <button
            onClick={searchItems}
            disabled={loading}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Searching..." : "Search"}
          </button>
        </div>

        {items.length > 0 && (
          <div className="mt-3 max-h-40 overflow-y-auto border rounded">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="text-left px-3 py-1.5 font-medium text-gray-600">ID</th>
                  <th className="text-left px-3 py-1.5 font-medium text-gray-600">Name</th>
                  <th className="text-right px-3 py-1.5 font-medium text-gray-600">On Hand</th>
                  <th className="text-right px-3 py-1.5 font-medium text-gray-600">Available</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.id}
                    className={`border-t hover:bg-blue-50 cursor-pointer ${
                      selectedItem?.id === item.id ? "bg-blue-50" : ""
                    }`}
                    onClick={() => selectItem(item)}
                  >
                    <td className="px-3 py-1.5 font-mono text-xs">{item.ida}</td>
                    <td className="px-3 py-1.5">{item.name}</td>
                    <td className="px-3 py-1.5 text-right font-mono">
                      {fmtInt(item.quantity.on_hand || 0)}
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono">
                      {fmtInt(item.quantity.available || 0)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Adjustment Form */}
      {selectedItem && (
        <>
          <Card title={`${selectedItem.ida} — ${selectedItem.name}`} icon={<FaExchangeAlt />}>
            {/* Current quantities */}
            <div className="grid grid-cols-5 gap-3 mb-4">
              {QTY_FIELDS.map(({ value, label }) => (
                <div
                  key={value}
                  className={`p-2 rounded text-center ${
                    value === adjField ? "bg-blue-100 border border-blue-300" : "bg-gray-50"
                  }`}
                >
                  <div className="text-xs text-gray-500">{label}</div>
                  <div className="text-lg font-mono font-semibold">
                    {fmtInt(selectedItem.quantity[value] || 0)}
                  </div>
                </div>
              ))}
            </div>

            {/* Adjustment inputs */}
            <div className="grid grid-cols-3 gap-3 mb-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Field to Adjust
                </label>
                <select
                  data-wc="inv-adjust-field"
                  value={adjField}
                  onChange={(e) => setAdjField(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                >
                  {QTY_FIELDS.map(({ value, label }) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Quantity (+/-)
                </label>
                <input
                  data-wc="inv-adjust-delta"
                  type="number"
                  value={adjDelta}
                  onChange={(e) => setAdjDelta(parseInt(e.target.value) || 0)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Reason
                </label>
                <select
                  data-wc="inv-adjust-reason"
                  value={adjReason}
                  onChange={(e) => setAdjReason(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                >
                  {REASON_CODES.map(({ value, label }) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex items-center justify-between">
              {error && <p className="text-sm text-red-600">{error}</p>}
              {result && (
                <p className="text-sm text-green-700 flex items-center gap-1">
                  <FaCheckCircle size={12} /> {result}
                </p>
              )}
              {!error && !result && <span />}
              <button
                data-wc="inv-adjust-submit"
                onClick={handleAdjust}
                disabled={submitting || adjDelta === 0}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                <FaExchangeAlt size={12} />
                {submitting ? "Adjusting..." : "Adjust"}
              </button>
            </div>
          </Card>

          {/* Adjustment History */}
          {pending.length > 0 && (
            <Card title="Adjustment History" icon={<FaClipboardCheck />}>
              <div className="max-h-60 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 sticky top-0">
                    <tr>
                      <th className="text-left px-3 py-1.5 font-medium text-gray-600">Field</th>
                      <th className="text-right px-3 py-1.5 font-medium text-gray-600">Delta</th>
                      <th className="text-left px-3 py-1.5 font-medium text-gray-600">Reason</th>
                      <th className="text-left px-3 py-1.5 font-medium text-gray-600">Status</th>
                      <th className="text-left px-3 py-1.5 font-medium text-gray-600">Requested</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pending.map((adj) => (
                      <tr key={adj.pending_id} className="border-t">
                        <td className="px-3 py-1.5">{adj.field}</td>
                        <td
                          className={`px-3 py-1.5 text-right font-mono ${
                            adj.delta > 0 ? "text-green-600" : "text-red-600"
                          }`}
                        >
                          {adj.delta > 0 ? "+" : ""}
                          {adj.delta}
                        </td>
                        <td className="px-3 py-1.5 text-xs">{adj.reason}</td>
                        <td className="px-3 py-1.5">
                          <StatusBadge status={adj.state} />
                        </td>
                        <td className="px-3 py-1.5 text-xs text-gray-500">
                          {fmtDate(adj.dt_requested)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 3: Warehouse
// ---------------------------------------------------------------------------

function WarehouseTab() {
  const [items, setItems] = useState<WarehouseItem[]>([]);
  const [warehouses, setWarehouses] = useState<{ id: number; name: string }[]>([]);
  const [selectedWarehouse, setSelectedWarehouse] = useState<number | null>(null);
  const [sortField, setSortField] = useState<string>("item_ida");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Fetch warehouses
      const whData = await getRecords("warehouse", { limit: 100 });
      const whs = (whData.results || []).map((w: any) => ({
        id: w.id,
        name: w.name || w.ida || `WH-${w.id}`,
      }));
      setWarehouses(whs);

      // Fetch items with inventory
      const itemData = await getRecords("item", {
        limit: 500,
        is_active: true,
        ordering: "ida",
      });

      // Fetch items below reorder for flagging
      let belowReorder: Set<number> = new Set();
      try {
        const reorderData = await manageAction("get_items_below_reorder", {
          warehouse_id: selectedWarehouse || undefined,
        });
        if (Array.isArray(reorderData)) {
          belowReorder = new Set(reorderData.map((r: any) => r.item_id));
        }
      } catch {
        // Non-critical — just won't highlight
      }

      const mapped: WarehouseItem[] = (itemData.results || []).map((item: any) => {
        const qty = item.quantity || {};
        return {
          id: item.id,
          item_id: item.id,
          item_ida: item.ida || "",
          item_name: item.name || "",
          warehouse_id: item.warehouse_id || 1,
          warehouse_name:
            whs.find((w: any) => w.id === (item.warehouse_id || 1))?.name || "Default",
          on_hand: qty.on_hand || 0,
          on_po: qty.on_po || 0,
          on_so: qty.on_so || 0,
          available: qty.available || 0,
          reorder_point: null,
          below_reorder: belowReorder.has(item.id),
        };
      });

      setItems(mapped);
    } catch (err: any) {
      setError(err?.message || "Failed to load warehouse data");
    } finally {
      setLoading(false);
    }
  }, [selectedWarehouse]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  };

  const sortedItems = [...items]
    .filter((i) => !selectedWarehouse || i.warehouse_id === selectedWarehouse)
    .sort((a, b) => {
      const aVal = (a as any)[sortField];
      const bVal = (b as any)[sortField];
      if (typeof aVal === "number" && typeof bVal === "number") {
        return sortDir === "asc" ? aVal - bVal : bVal - aVal;
      }
      return sortDir === "asc"
        ? String(aVal).localeCompare(String(bVal))
        : String(bVal).localeCompare(String(aVal));
    });

  const SortHeader: React.FC<{ field: string; label: string; right?: boolean }> = ({
    field,
    label,
    right,
  }) => (
    <th
      className={`px-3 py-1.5 font-medium text-gray-600 cursor-pointer hover:bg-gray-100 select-none ${
        right ? "text-right" : "text-left"
      }`}
      onClick={() => handleSort(field)}
    >
      {label} {sortField === field ? (sortDir === "asc" ? "\u25B2" : "\u25BC") : ""}
    </th>
  );

  return (
    <div data-wc="inv-warehouse" className="space-y-4">
      <Card title="Inventory by Warehouse" icon={<FaWarehouse />}>
        <div className="flex items-center gap-3 mb-3">
          <select
            data-wc="inv-warehouse-filter"
            value={selectedWarehouse || ""}
            onChange={(e) =>
              setSelectedWarehouse(e.target.value ? parseInt(e.target.value) : null)
            }
            className="px-3 py-2 text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">All Warehouses</option>
            {warehouses.map((wh) => (
              <option key={wh.id} value={wh.id}>
                {wh.name}
              </option>
            ))}
          </select>
          <button
            onClick={fetchData}
            disabled={loading}
            className="flex items-center gap-1 px-3 py-2 text-sm bg-gray-100 rounded hover:bg-gray-200 disabled:opacity-50"
          >
            <FaSync className={loading ? "animate-spin" : ""} size={11} /> Refresh
          </button>
          <span className="text-xs text-gray-400 ml-auto">
            {sortedItems.length} items
            {sortedItems.filter((i) => i.on_hand === 0).length > 0 &&
              ` | ${sortedItems.filter((i) => i.on_hand === 0).length} zero stock`}
            {sortedItems.filter((i) => i.below_reorder).length > 0 &&
              ` | ${sortedItems.filter((i) => i.below_reorder).length} below reorder`}
          </span>
        </div>

        {error && <p className="text-sm text-red-600 mb-2">{error}</p>}

        <div className="max-h-[500px] overflow-y-auto border rounded">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 sticky top-0">
              <tr>
                <SortHeader field="item_ida" label="Item ID" />
                <SortHeader field="item_name" label="Name" />
                <SortHeader field="warehouse_name" label="Warehouse" />
                <SortHeader field="on_hand" label="On Hand" right />
                <SortHeader field="on_po" label="On PO" right />
                <SortHeader field="on_so" label="On SO" right />
                <SortHeader field="available" label="Available" right />
              </tr>
            </thead>
            <tbody>
              {sortedItems.map((item) => {
                const rowClass = item.below_reorder
                  ? "bg-red-50 border-t"
                  : item.on_hand === 0
                  ? "bg-orange-50 border-t"
                  : "border-t";
                return (
                  <tr key={item.id} className={`${rowClass} hover:bg-gray-50`}>
                    <td className="px-3 py-1.5 font-mono text-xs">{item.item_ida}</td>
                    <td className="px-3 py-1.5">{item.item_name}</td>
                    <td className="px-3 py-1.5 text-xs">{item.warehouse_name}</td>
                    <td
                      className={`px-3 py-1.5 text-right font-mono ${
                        item.on_hand === 0 ? "text-orange-600 font-semibold" : ""
                      }`}
                    >
                      {fmtInt(item.on_hand)}
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono">{fmtInt(item.on_po)}</td>
                    <td className="px-3 py-1.5 text-right font-mono">{fmtInt(item.on_so)}</td>
                    <td
                      className={`px-3 py-1.5 text-right font-mono ${
                        item.below_reorder ? "text-red-600 font-semibold" : ""
                      }`}
                    >
                      {fmtInt(item.available)}
                      {item.below_reorder && (
                        <FaExclamationTriangle
                          className="inline ml-1 text-red-500"
                          size={11}
                          title="Below reorder point"
                        />
                      )}
                    </td>
                  </tr>
                );
              })}
              {sortedItems.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-3 py-6 text-center text-gray-400">
                    {loading ? "Loading..." : "No inventory data"}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 bg-red-50 border border-red-200 rounded" />
            Below reorder point
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 bg-orange-50 border border-orange-200 rounded" />
            Zero on hand
          </span>
        </div>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 4: Reconcile
// ---------------------------------------------------------------------------

function ReconcileTab() {
  const [searchTerm, setSearchTerm] = useState("");
  const [rows, setRows] = useState<ReconcileRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Search items for reconciliation
  const searchItems = async () => {
    if (!searchTerm.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await getRecords("item", {
        keyword: searchTerm,
        limit: 100,
        is_active: true,
      });
      setRows(
        (data.results || []).map((item: any) => ({
          item_id: item.id,
          item_ida: item.ida || "",
          item_name: item.name || "",
          system_on_hand: item.quantity?.on_hand || 0,
          physical_count: null,
          variance: null,
        }))
      );
    } catch (err: any) {
      setError(err?.message || "Search failed");
    } finally {
      setLoading(false);
    }
  };

  // Update physical count for a row
  const updateCount = (itemId: number, count: number | null) => {
    setRows((prev) =>
      prev.map((r) => {
        if (r.item_id !== itemId) return r;
        const variance = count !== null ? count - r.system_on_hand : null;
        return { ...r, physical_count: count, variance };
      })
    );
  };

  // Apply all variance adjustments
  const applyAdjustments = async () => {
    const withVariance = rows.filter(
      (r) => r.variance !== null && r.variance !== 0
    );
    if (withVariance.length === 0) {
      setError("No variances to apply. Enter physical counts that differ from system.");
      return;
    }

    setApplying(true);
    setError(null);
    setResult(null);

    const results: string[] = [];
    let hasError = false;

    for (const row of withVariance) {
      try {
        await manageAction("adjust_item_quantity", {
          item_id: row.item_id,
          field: "on_hand",
          delta: row.variance,
          reason: "physical_count",
          source_type: "reconciliation",
        });
        results.push(
          `${row.item_ida}: adjusted ${row.variance! > 0 ? "+" : ""}${row.variance}`
        );
      } catch (err: any) {
        hasError = true;
        results.push(
          `${row.item_ida}: FAILED - ${err?.message || "unknown error"}`
        );
      }
    }

    setApplying(false);
    setResult(results.join("\n"));

    if (!hasError) {
      // Refresh items to show updated on_hand
      searchItems();
    }
  };

  const totalVariance = rows.reduce((sum, r) => sum + (r.variance || 0), 0);
  const countedRows = rows.filter((r) => r.physical_count !== null);
  const varianceRows = rows.filter((r) => r.variance !== null && r.variance !== 0);

  return (
    <div data-wc="inv-reconcile" className="space-y-4">
      <Card title="Physical Count Reconciliation" icon={<FaClipboardCheck />}>
        <div className="flex items-center gap-2 mb-3">
          <input
            data-wc="inv-reconcile-search"
            type="text"
            placeholder="Search items to count (ID, name, keyword)..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && searchItems()}
            className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
          />
          <button
            onClick={searchItems}
            disabled={loading}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Loading..." : "Load Items"}
          </button>
        </div>

        {rows.length > 0 && (
          <>
            <div className="max-h-[400px] overflow-y-auto border rounded mb-4">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="text-left px-3 py-1.5 font-medium text-gray-600">Item ID</th>
                    <th className="text-left px-3 py-1.5 font-medium text-gray-600">Name</th>
                    <th className="text-right px-3 py-1.5 font-medium text-gray-600">
                      System On Hand
                    </th>
                    <th className="text-right px-3 py-1.5 font-medium text-gray-600">
                      Physical Count
                    </th>
                    <th className="text-right px-3 py-1.5 font-medium text-gray-600">Variance</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr
                      key={row.item_id}
                      className={`border-t ${
                        row.variance && row.variance !== 0
                          ? row.variance > 0
                            ? "bg-green-50"
                            : "bg-red-50"
                          : ""
                      }`}
                    >
                      <td className="px-3 py-1.5 font-mono text-xs">{row.item_ida}</td>
                      <td className="px-3 py-1.5">{row.item_name}</td>
                      <td className="px-3 py-1.5 text-right font-mono">
                        {fmtInt(row.system_on_hand)}
                      </td>
                      <td className="px-3 py-1.5 text-right">
                        <input
                          data-wc={`inv-reconcile-count-${row.item_id}`}
                          type="number"
                          min={0}
                          value={row.physical_count ?? ""}
                          onChange={(e) =>
                            updateCount(
                              row.item_id,
                              e.target.value === "" ? null : parseInt(e.target.value) || 0
                            )
                          }
                          placeholder="--"
                          className="w-24 px-2 py-1 text-right text-sm border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
                        />
                      </td>
                      <td
                        className={`px-3 py-1.5 text-right font-mono font-semibold ${
                          row.variance === null
                            ? "text-gray-300"
                            : row.variance === 0
                            ? "text-gray-500"
                            : row.variance > 0
                            ? "text-green-600"
                            : "text-red-600"
                        }`}
                      >
                        {row.variance !== null
                          ? `${row.variance > 0 ? "+" : ""}${row.variance}`
                          : "--"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Summary and apply button */}
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">
                <span className="mr-4">
                  Counted: {countedRows.length} / {rows.length}
                </span>
                <span className="mr-4">
                  With variance: {varianceRows.length}
                </span>
                <span
                  className={`font-mono font-semibold ${
                    totalVariance === 0
                      ? "text-gray-500"
                      : totalVariance > 0
                      ? "text-green-600"
                      : "text-red-600"
                  }`}
                >
                  Net: {totalVariance > 0 ? "+" : ""}
                  {totalVariance}
                </span>
              </div>
              <button
                data-wc="inv-reconcile-apply"
                onClick={applyAdjustments}
                disabled={applying || varianceRows.length === 0}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                <FaClipboardCheck size={12} />
                {applying
                  ? "Applying..."
                  : `Apply ${varianceRows.length} Adjustment${
                      varianceRows.length !== 1 ? "s" : ""
                    }`}
              </button>
            </div>

            {error && <p className="text-sm text-red-600 mt-2">{error}</p>}
            {result && (
              <pre className="text-xs text-green-700 whitespace-pre-wrap bg-green-50 p-2 rounded mt-2">
                {result}
              </pre>
            )}
          </>
        )}
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab 5: Training — observation panel for manual transaction walkthrough
// ---------------------------------------------------------------------------

// The guided steps: user does each in the real UI, comes back here to see results
const TRAINING_INSTRUCTIONS = [
  {
    step: 1,
    action: "Create a Proposal for 15 zz-fake-item",
    effect: "+15 on_p",
    detail: "Products > New Proposal. Add 15 × zz-fake-item for zzCustomer. Save. Print it.",
    icon: <FaClipboardList />,
    color: "text-blue-600",
  },
  {
    step: 2,
    action: "Transfer 11 from Proposal to Order",
    effect: "-11 on_p, +11 on_so",
    detail: "Go to Open Proposals. Open your proposal. Transfer 11 of the 15 to Order. Come back here — see the quantities change.",
    icon: <FaShoppingCart />,
    color: "text-indigo-600",
  },
  {
    step: 3,
    action: "Order → Purchase 10",
    effect: "+10 on_po",
    detail: "Open the Order. Create a Purchase Order for 10 units. This tells the vendor to ship.",
    icon: <FaTruck />,
    color: "text-orange-600",
  },
  {
    step: 4,
    action: "Purchase → Receive 8",
    effect: "+8 on_hand, -8 on_po (2 still on_po)",
    detail: "Open the Purchase. Receive 8 of the 10. Partial receipt — 2 remain on PO.",
    icon: <FaBoxOpen />,
    color: "text-teal-600",
  },
  {
    step: 5,
    action: "Order → Invoice 6",
    effect: "-6 on_hand, -6 on_so (5 still on_so)",
    detail: "Open the Order. Invoice 6 of the 11. Goods shipped, customer owes money.",
    icon: <FaFileInvoice />,
    color: "text-green-600",
  },
];

type ActivityRow = {
  dt: number;
  type: string;
  record_type: string;
  parent_ida: string;
  parent_status: string;
  qty_staged?: number;
  qty_remaining?: number;
  unit_price?: number;
  unit_cost?: number;
  extended?: number;
  line_id?: number;
  line_status?: string;
  detail?: string;
  delta?: number;
  reason?: string;
  pending_id?: number;
};

type TrainingData = {
  item: { id: number; ida: string; description: string };
  inventory: { on_hand: number; on_so: number; on_po: number; on_p: number; available: number };
  activity: ActivityRow[];
  count: number;
  error?: string;
};

const TYPE_COLORS: Record<string, string> = {
  proposal: "bg-blue-100 text-blue-800",
  order: "bg-indigo-100 text-indigo-800",
  invoice: "bg-green-100 text-green-800",
  purchase: "bg-orange-100 text-orange-800",
  pending: "bg-yellow-100 text-yellow-800",
};

function TrainingTab() {
  const [data, setData] = useState<TrainingData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchActivity = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await manageAction("get_training_activity", { item_ida: "zz-fake-item" });
      if (res.error) {
        setError(res.error);
      } else {
        setData(res);
      }
    } catch (e: any) {
      setError(e?.message || "Failed to load training activity");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchActivity();
  }, [fetchActivity]);

  const inv = data?.inventory;
  const activity = data?.activity || [];

  return (
    <div data-wc="inv-training" className="space-y-4">
      {/* Instructions */}
      <Card title="Transaction Training — zz-fake-item" icon={<FaGraduationCap />}>
        <p className="text-sm text-gray-600 mb-4">
          Follow these steps in the real WC3 UI, then come back here and hit{" "}
          <strong>Refresh</strong> to see your changes in the activity table below.
          The objective: see how item data, transaction lines, and pending records
          record and manage each change.
        </p>
        <div className="space-y-2">
          {TRAINING_INSTRUCTIONS.map((inst) => (
            <div key={inst.step} className="flex items-start gap-3 p-2 rounded hover:bg-gray-50">
              <span className={`mt-0.5 ${inst.color}`}>{inst.icon}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-gray-800">
                    {inst.step}. {inst.action}
                  </span>
                  <span className="text-xs font-mono bg-gray-100 px-2 py-0.5 rounded text-gray-600">
                    {inst.effect}
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">{inst.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Inventory buckets + refresh */}
      <div className="flex items-center gap-4">
        <Card title="Current Inventory — zz-fake-item" icon={<FaBoxOpen />}>
          {inv ? (
            <div className="flex gap-4">
              {[
                { label: "On Hand", value: inv.on_hand, color: "text-green-700 bg-green-50" },
                { label: "On SO", value: inv.on_so, color: "text-blue-700 bg-blue-50" },
                { label: "On PO", value: inv.on_po, color: "text-orange-700 bg-orange-50" },
                { label: "On Proposal", value: inv.on_p, color: "text-purple-700 bg-purple-50" },
                { label: "Available", value: inv.available, color: "text-emerald-700 bg-emerald-50" },
              ].map((b) => (
                <div key={b.label} className={`px-4 py-2 rounded text-center ${b.color}`}>
                  <div className="text-xs font-medium">{b.label}</div>
                  <div className="text-2xl font-mono font-bold">{b.value}</div>
                </div>
              ))}
              <div className="flex items-center ml-auto">
                <button
                  onClick={fetchActivity}
                  disabled={loading}
                  className="flex items-center gap-1 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm font-medium"
                >
                  <FaSync className={loading ? "animate-spin" : ""} size={12} />
                  {loading ? "Loading..." : "Refresh"}
                </button>
              </div>
            </div>
          ) : (
            <div className="text-sm text-gray-400">
              {loading ? "Loading..." : "No inventory data — run seed_training_data"}
            </div>
          )}
        </Card>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Activity table — transaction lines + pending records in dt sequence */}
      <Card title={`Today's Activity (${activity.length} records)`} icon={<FaClipboardCheck />}>
        {activity.length > 0 ? (
          <div className="max-h-[500px] overflow-y-auto border rounded">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="text-left px-3 py-1.5 font-medium text-gray-600">Time</th>
                  <th className="text-left px-3 py-1.5 font-medium text-gray-600">Type</th>
                  <th className="text-left px-3 py-1.5 font-medium text-gray-600">Document</th>
                  <th className="text-left px-3 py-1.5 font-medium text-gray-600">Status</th>
                  <th className="text-right px-3 py-1.5 font-medium text-gray-600">Qty</th>
                  <th className="text-right px-3 py-1.5 font-medium text-gray-600">Price</th>
                  <th className="text-right px-3 py-1.5 font-medium text-gray-600">Extended</th>
                  <th className="text-left px-3 py-1.5 font-medium text-gray-600">Detail</th>
                </tr>
              </thead>
              <tbody>
                {activity.map((row, idx) => {
                  const time = row.dt
                    ? formatDt(row.dt, 'datetime')
                    : "--";
                  const isPending = row.record_type === "pending";
                  return (
                    <tr key={idx} className="border-t hover:bg-gray-50">
                      <td className="px-3 py-1.5 text-xs font-mono text-gray-500">{time}</td>
                      <td className="px-3 py-1.5">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                            TYPE_COLORS[row.type] || "bg-gray-100 text-gray-700"
                          }`}
                        >
                          {row.type}
                        </span>
                      </td>
                      <td className="px-3 py-1.5 font-mono text-xs">{row.parent_ida}</td>
                      <td className="px-3 py-1.5">
                        <StatusBadge status={isPending ? row.parent_status : (row.line_status || row.parent_status)} />
                      </td>
                      <td className="px-3 py-1.5 text-right font-mono">
                        {isPending
                          ? row.delta !== undefined
                            ? `${row.delta > 0 ? "+" : ""}${row.delta}`
                            : "--"
                          : fmtInt(row.qty_staged || 0)}
                      </td>
                      <td className="px-3 py-1.5 text-right font-mono">
                        {isPending ? "--" : fmtDec(row.unit_price || 0)}
                      </td>
                      <td className="px-3 py-1.5 text-right font-mono">
                        {isPending ? "--" : fmtDec(row.extended || 0)}
                      </td>
                      <td className="px-3 py-1.5 text-xs text-gray-500">
                        {isPending
                          ? `${row.detail || ""} ${row.reason || ""}`.trim()
                          : row.qty_remaining
                          ? `${row.qty_remaining} remaining`
                          : ""}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="py-8 text-center text-gray-400 text-sm">
            {loading
              ? "Loading activity..."
              : "No activity yet today. Follow the steps above, then Refresh."}
          </div>
        )}
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Dashboard
// ---------------------------------------------------------------------------

export default function InventoryDashboard() {
  const [activeTab, setActiveTab] = useState<TabKey>("receive");

  const TABS: { key: TabKey; label: string; icon: React.ReactNode }[] = [
    { key: "receive", label: "Receive", icon: <FaBoxOpen size={14} /> },
    { key: "adjust", label: "Adjust", icon: <FaExchangeAlt size={14} /> },
    { key: "warehouse", label: "Warehouse", icon: <FaWarehouse size={14} /> },
    { key: "reconcile", label: "Reconcile", icon: <FaClipboardCheck size={14} /> },
    { key: "training", label: "Training", icon: <FaGraduationCap size={14} /> },
  ];

  return (
    <div data-wc="inventory-dashboard" className="p-6 max-w-7xl mx-auto">
      <AliceHintBar model="inventory" />

      <div className="flex items-center justify-between mb-2 mt-2">
        <h1 className="text-xl font-bold text-gray-900">Inventory Dashboard</h1>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-gray-200 mb-4">
        {TABS.map((tab) => (
          <TabButton
            key={tab.key}
            active={activeTab === tab.key}
            icon={tab.icon}
            label={tab.label}
            onClick={() => setActiveTab(tab.key)}
          />
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "receive" && <ReceiveTab />}
      {activeTab === "adjust" && <AdjustTab />}
      {activeTab === "warehouse" && <WarehouseTab />}
      {activeTab === "reconcile" && <ReconcileTab />}
      {activeTab === "training" && <TrainingTab />}
    </div>
  );
}
