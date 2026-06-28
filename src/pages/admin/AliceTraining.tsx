/* Alice Training Window — Interactive inventory flow coaching
 *
 * Walks users through: Proposal → Order → Invoice → Payment → PO → Receive
 * Shows live inventory buckets (on_hand, on_so, on_po) as visual bars
 * Alice provides coaching text explaining what happened and why
 *
 * Uses zzitem + zzCustomer training fixtures (no real data impact)
 * All records flagged metadata.training=True
 */
import React, { useEffect, useState, useCallback } from "react";
import apiClient from "../../api/axios";
import {
  FaPlay, FaStepForward, FaTrash, FaSync, FaBoxOpen,
  FaFileInvoice, FaShoppingCart, FaTruck, FaDollarSign, FaClipboardList
} from "react-icons/fa";

type InventorySnapshot = {
  on_hand: number;
  on_so: number;
  on_po: number;
  reserved: number;
  available: number;
};

type StepResult = {
  step: number;
  action: string;
  expected: string;
  note?: string;
  inventory_before?: InventorySnapshot;
  inventory_after?: InventorySnapshot;
  inventory_changed?: boolean;
  record_id?: number;
  record_type?: string;
  invoice_balance?: number;
  invoice_status?: string;
  payment_applied?: boolean;
};

type TrainingReport = {
  customer: { id: number; name: string };
  item: { id: number; ida: string };
  steps: StepResult[];
  final_inventory: InventorySnapshot;
  records_created: Record<string, number | null>;
};

// Step definitions with Alice coaching text
const STEP_CONFIG = [
  {
    label: "Create Proposal",
    icon: <FaClipboardList />,
    coaching: "A proposal is a quote — no commitment, no inventory impact. The customer can review pricing before deciding. Watch: inventory doesn't change.",
    color: "bg-blue-500",
    param: "proposal_qty",
    defaultQty: 5,
  },
  {
    label: "Convert to Order",
    icon: <FaShoppingCart />,
    coaching: "Now it's a commitment. On Sales Order (on_so) increases — these units are spoken for. But on_hand doesn't change yet. The goods are still on the shelf, just promised.",
    color: "bg-indigo-500",
    param: "order_qty",
    defaultQty: 4,
  },
  {
    label: "Invoice (Ship)",
    icon: <FaFileInvoice />,
    coaching: "Invoicing means the goods shipped. On_hand DECREASES (goods left the warehouse). On_so DECREASES (the promise is fulfilled). The customer now owes money.",
    color: "bg-green-600",
    param: "invoice_qty",
    defaultQty: 3,
  },
  {
    label: "Record Payment",
    icon: <FaDollarSign />,
    coaching: "Payment reduces the invoice balance. No inventory effect — payment is financial, not physical. The invoice status changes to 'paid' or 'partially_paid'.",
    color: "bg-emerald-600",
    param: null,
    defaultQty: 0,
  },
  {
    label: "Purchase Order",
    icon: <FaTruck />,
    coaching: "We're ordering more from the vendor. On Purchase Order (on_po) INCREASES — units are on their way but haven't arrived yet. On_hand is unchanged.",
    color: "bg-orange-500",
    param: "po_qty",
    defaultQty: 10,
  },
  {
    label: "Receive Goods",
    icon: <FaBoxOpen />,
    coaching: "Goods arrived! On_hand INCREASES (physically received). On_po DECREASES (the PO is fulfilled). Available inventory is now higher.",
    color: "bg-teal-600",
    param: "receive_qty",
    defaultQty: 8,
  },
];

const BucketBar: React.FC<{
  label: string;
  value: number;
  maxValue: number;
  color: string;
  changed?: boolean;
  prevValue?: number;
}> = ({ label, value, maxValue, color, changed, prevValue }) => {
  const pct = maxValue > 0 ? Math.min(100, (value / maxValue) * 100) : 0;
  const delta = prevValue !== undefined ? value - prevValue : 0;
  return (
    <div className="mb-2">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-gray-600 font-medium">{label}</span>
        <span className={`font-mono font-bold ${changed ? "text-blue-600" : "text-gray-800"}`}>
          {value}
          {delta !== 0 && (
            <span className={delta > 0 ? "text-green-600 ml-1" : "text-red-600 ml-1"}>
              ({delta > 0 ? "+" : ""}{delta})
            </span>
          )}
        </span>
      </div>
      <div className="h-4 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
};

export default function AliceTraining() {
  const [trainingItem, setTrainingItem] = useState<{ id: number; ida: string } | null>(null);
  const [trainingCustomer, setTrainingCustomer] = useState<{ id: number } | null>(null);
  const [quantities, setQuantities] = useState<Record<string, number>>({
    proposal_qty: 5, order_qty: 4, invoice_qty: 3, po_qty: 10, receive_qty: 8,
  });
  const [currentStep, setCurrentStep] = useState(-1);
  const [steps, setSteps] = useState<StepResult[]>([]);
  const [running, setRunning] = useState(false);
  const [inventory, setInventory] = useState<InventorySnapshot | null>(null);
  const [prevInventory, setPrevInventory] = useState<InventorySnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const maxInventory = 150; // scale for bars

  // Find zzitem + zzCustomer on load
  useEffect(() => {
    const findFixtures = async () => {
      try {
        const itemRes = await apiClient.get("/wcapi/get/", { params: { model_name: "item", search: "zzitem" } });
        const items = itemRes.data?.data?.results || itemRes.data?.data?.items || [];
        const zz = items.find((i: any) => i.ida === "zzitem");
        if (zz) setTrainingItem({ id: zz.id, ida: zz.ida });

        const custRes = await apiClient.get("/wcapi/get/", { params: { model_name: "customer", search: "zzCustomer" } });
        const custs = custRes.data?.data?.results || custRes.data?.data?.items || [];
        const zzc = custs.find((c: any) => c.ida === "zzCustomer");
        if (zzc) setTrainingCustomer({ id: zzc.id });
      } catch (e) {
        setError("Could not find zzitem/zzCustomer. Run: manage.py seed_training_data");
      }
    };
    findFixtures();
  }, []);

  // Fetch current inventory for zzitem
  const refreshInventory = useCallback(async () => {
    if (!trainingItem) return;
    try {
      // Use the availability service via a simple GET
      const res = await apiClient.get("/wcapi/get/", {
        params: { model_name: "inventory_layer", search: "TRAINING" },
      });
      const layers = res.data?.data?.results || res.data?.data?.items || [];
      if (layers.length > 0) {
        const qty = layers[0].quantity || {};
        setInventory({
          on_hand: qty.on_hand || 0,
          on_so: qty.on_so || 0,
          on_po: qty.on_po || 0,
          reserved: qty.reserved || 0,
          available: (qty.on_hand || 0) - (qty.reserved || 0),
        });
      }
    } catch (e) {
      console.warn("Could not fetch inventory", e);
    }
  }, [trainingItem]);

  useEffect(() => {
    if (trainingItem) refreshInventory();
  }, [trainingItem, refreshInventory]);

  const runFullCycle = async () => {
    if (!trainingItem || !trainingCustomer) return;
    setRunning(true);
    setError(null);
    setSteps([]);
    setCurrentStep(-1);

    try {
      const res = await apiClient.post("/wcapi/manage/", {
        action: "run_training_flow",
        params: {
          customer_id: trainingCustomer.id,
          item_id: trainingItem.id,
          ...quantities,
        },
      });
      const report: TrainingReport = res.data?.data ?? res.data;
      setSteps(report.steps);
      setCurrentStep(report.steps.length - 1);
      if (report.final_inventory) setInventory(report.final_inventory);
    } catch (e: any) {
      setError(e?.response?.data?.message || e?.message || "Training flow failed");
    } finally {
      setRunning(false);
      refreshInventory();
    }
  };

  const cleanup = async () => {
    try {
      await apiClient.post("/wcapi/manage/", { action: "cleanup_training", params: {} });
      setSteps([]);
      setCurrentStep(-1);
      refreshInventory();
    } catch (e) {
      console.warn("Cleanup failed", e);
    }
  };

  const viewStep = (idx: number) => {
    setCurrentStep(idx);
    const step = steps[idx];
    if (step?.inventory_after) {
      setPrevInventory(step.inventory_before || null);
      setInventory(step.inventory_after);
    }
  };

  const activeStep = currentStep >= 0 && currentStep < steps.length ? steps[currentStep] : null;
  const coaching = currentStep >= 0 && currentStep < STEP_CONFIG.length ? STEP_CONFIG[currentStep] : null;

  if (!trainingItem || !trainingCustomer) {
    return (
      <div className="p-8 text-center">
        <h2 className="text-lg font-bold text-gray-700 mb-2">Alice Training Setup Required</h2>
        <p className="text-gray-500 mb-4">Training fixtures not found. Run this command first:</p>
        <code className="bg-gray-100 px-4 py-2 rounded text-sm font-mono">
          ./bin/python manage.py seed_training_data
        </code>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Alice — Inventory Training</h1>
          <p className="text-sm text-gray-500">
            Using: <span className="font-mono text-blue-600">zzitem</span> (id={trainingItem.id})
            + <span className="font-mono text-blue-600">zzCustomer</span> (id={trainingCustomer.id})
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={runFullCycle} disabled={running}
            className="flex items-center gap-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm font-medium">
            <FaPlay size={12} /> {running ? "Running..." : "Run Full Cycle"}
          </button>
          <button onClick={cleanup} className="flex items-center gap-1 px-3 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm">
            <FaTrash size={12} /> Cleanup
          </button>
          <button onClick={refreshInventory} className="flex items-center gap-1 px-3 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm">
            <FaSync size={12} />
          </button>
        </div>
      </div>

      {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">{error}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Left: Quantity inputs + step buttons */}
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-gray-700">Adjust Quantities</h3>
          {STEP_CONFIG.map((step, idx) => (
            <div key={idx}
              className={`p-3 rounded-lg border cursor-pointer transition-all ${
                currentStep === idx ? "border-blue-500 bg-blue-50 shadow" : "border-gray-200 bg-white hover:border-gray-300"
              } ${idx < steps.length ? "opacity-100" : "opacity-60"}`}
              onClick={() => idx < steps.length && viewStep(idx)}
            >
              <div className="flex items-center gap-2 text-sm font-medium text-gray-800">
                <span className={`p-1 rounded text-white ${step.color}`}>{step.icon}</span>
                <span>Step {idx + 1}: {step.label}</span>
                {idx < steps.length && <span className="ml-auto text-green-500 text-xs">done</span>}
              </div>
              {step.param && (
                <div className="mt-2 flex items-center gap-2">
                  <label className="text-xs text-gray-500">Qty:</label>
                  <input
                    type="number"
                    value={quantities[step.param] || step.defaultQty}
                    onChange={(e) => setQuantities(q => ({ ...q, [step.param!]: parseInt(e.target.value) || 0 }))}
                    className="w-16 px-2 py-1 text-sm border rounded text-center font-mono"
                    min={0}
                  />
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Center: Inventory visualization */}
        <div className="bg-white rounded-lg border border-gray-200 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Inventory Buckets — zzitem</h3>
          {inventory ? (
            <>
              <BucketBar label="On Hand" value={inventory.on_hand} maxValue={maxInventory}
                color="bg-green-500" changed={prevInventory?.on_hand !== inventory.on_hand}
                prevValue={prevInventory?.on_hand} />
              <BucketBar label="On Sales Order (on_so)" value={inventory.on_so} maxValue={maxInventory}
                color="bg-blue-500" changed={prevInventory?.on_so !== inventory.on_so}
                prevValue={prevInventory?.on_so} />
              <BucketBar label="On Purchase Order (on_po)" value={inventory.on_po} maxValue={maxInventory}
                color="bg-orange-500" changed={prevInventory?.on_po !== inventory.on_po}
                prevValue={prevInventory?.on_po} />
              <BucketBar label="Available" value={inventory.available} maxValue={maxInventory}
                color="bg-emerald-400" changed={prevInventory?.available !== inventory.available}
                prevValue={prevInventory?.available} />

              <div className="mt-4 pt-3 border-t text-xs text-gray-400">
                <div>Available = On Hand − Reserved</div>
                <div>On Hand changes only when goods physically move (ship or receive)</div>
              </div>
            </>
          ) : (
            <div className="text-gray-400 text-sm">Loading inventory...</div>
          )}
        </div>

        {/* Right: Alice coaching */}
        <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-lg border border-purple-200 p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-purple-700 mb-3">Alice says...</h3>
          {coaching ? (
            <>
              <p className="text-sm text-gray-700 leading-relaxed mb-4">{coaching.coaching}</p>
              {activeStep && (
                <div className="space-y-2 text-xs">
                  <div className="p-2 bg-white/70 rounded">
                    <span className="font-semibold text-gray-600">What happened:</span>
                    <div className="text-gray-700 mt-1">{activeStep.action}</div>
                  </div>
                  <div className="p-2 bg-white/70 rounded">
                    <span className="font-semibold text-gray-600">What to check:</span>
                    <div className="text-gray-700 mt-1">{activeStep.expected}</div>
                  </div>
                  {activeStep.note && (
                    <div className="p-2 bg-amber-50 rounded border border-amber-200">
                      <span className="font-semibold text-amber-700">Note:</span>
                      <div className="text-amber-800 mt-1">{activeStep.note}</div>
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            <div className="text-sm text-gray-500">
              <p className="mb-3">Welcome to inventory training!</p>
              <p className="mb-3">Click <strong>Run Full Cycle</strong> to see how transactions affect inventory. Adjust quantities on the left before running.</p>
              <p className="text-xs text-gray-400">All records use zzitem and zzCustomer — no impact on real data. Records are flagged metadata.training=True and excluded from reporting.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
