/**
 * FlightSimConsole -- Flight Simulator training page.
 *
 * Renders inside the standard app shell (sidebar, topbar).
 *
 * Initial state: simulation select list — user picks which sim to run.
 * After selection: left panel shows transaction array (db.column via DbColumns),
 * right panel shows transaction form (db.form via UiDetail).
 *
 * Data-driven: transaction array from manage action (get_flight_transactions).
 * Form from existing TransactionDetail (form layout Settings).
 *
 * LastChecked: 2026-08-18 | WhereUsed: /flight-simulator | WhoCreated: Bill+Claude
 */
import React, { useEffect, useState, useCallback, useRef, Suspense } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { manageAction, saveRecord } from "../../api/wcapi";
import { FaSync } from "react-icons/fa";
import "./FlightSimConsole.css";

const UiDetail = React.lazy(() => import("../../apps/transactions/components/TransactionDetail"));

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface TransactionRow {
  id: string;
  type: "item" | "proposal_line" | "order_line" | "invoice_line" | "purchase_line" | "workorder_line" | "pending";
  label: string;
  on_hand: number | string;
  on_p: number | string;
  on_so: number | string;
  on_po: number | string;
  on_wo: number | string;
  available: number | string;
  gl_summary: string;
  model?: string;
  record_id?: number;
  processed?: boolean;
  [key: string]: unknown;
}

interface SimulationDef {
  id: string;
  label: string;
  description: string;
  itemIda: string;       // training item to load
  firstModel: string;    // first transaction model to open on right
}

/* ------------------------------------------------------------------ */
/*  Available simulations                                              */
/* ------------------------------------------------------------------ */

const SIMULATIONS: SimulationDef[] = [
  // ── Phase 1: Foundation ──
  {
    id: "first-customer",
    label: "1. Your First Customer",
    description: "Create a Contact, Customer Org, and set credit limit — the foundation for all transactions",
    itemIda: "",
    firstModel: "contact",
  },
  {
    id: "first-item",
    label: "2. Your First Item",
    description: "Create an Item with price ($10), cost ($6), GL accounts, and 100 units opening inventory",
    itemIda: "qqBB200",
    firstModel: "item",
  },
  {
    id: "first-sale",
    label: "3. Your First Sale",
    description: "Create a Proposal for 15 units, convert 9 to an Order — watch on_p and on_so change",
    itemIda: "qqBB200",
    firstModel: "proposal",
  },
  // ── Phase 2: Sell Side ──
  {
    id: "inventory",
    label: "4. Inventory Quantity Tracking",
    description: "Proposal → Order → Invoice → Purchase → Receive — watch on_hand, on_so, on_po, pending, and GL change at each step",
    itemIda: "qqBB200",
    firstModel: "proposal",
  },
  {
    id: "cash",
    label: "Cash Flow Tracking",
    description: "Invoice → Payment → Discount → Write-off — watch cash, AR, and bank reconciliation",
    itemIda: "qqBB200",
    firstModel: "invoice",
  },
  {
    id: "payment",
    label: "Payment Lifecycle",
    description: "Order → partial Invoice → accept Payment → apply part to invoice → journal — watch amount, available, tendered, change, ledger, and GL",
    itemIda: "qqBB200",
    firstModel: "order",
  },
  {
    id: "gl-audit",
    label: "GL Audit Trail",
    description: "Every business event creates balanced journal entries — trace any balance to its source",
    itemIda: "qqBB200",
    firstModel: "invoice",
  },
  {
    id: "bom",
    label: "Bill of Materials",
    description: "BOM explosion, component availability, buildable quantity, cost rollup",
    itemIda: "qqBB200",
    firstModel: "work_order",
  },
  {
    id: "p2p",
    label: "Purchase-to-Pay",
    description: "Requisition → PO → Receive → Three-way match → Pay vendor",
    itemIda: "qqBB200",
    firstModel: "purchase",
  },
  {
    id: "commissions",
    label: "Commission Tracking",
    description: "Accrual at sale, split commissions, adjustments at payment, period-end reconciliation",
    itemIda: "qqBB200",
    firstModel: "invoice",
  },
  {
    id: "currency",
    label: "Currency Variations",
    description: "Multi-currency transactions, exchange rate gains/losses, period-end revaluation",
    itemIda: "qqBB200",
    firstModel: "invoice",
  },
  {
    id: "costing",
    label: "Costing Methods",
    description: "Same transactions, three different profit numbers — FIFO vs LIFO vs weighted average",
    itemIda: "qqBB200",
    firstModel: "purchase",
  },
  {
    id: "company-profile",
    label: "Company Profile Setup",
    description: "Configure your company name, address, ship-to, logos, print defaults, receivables, and accounting — the foundation every document and report reads from",
    itemIda: "",
    firstModel: "setting",
  },
  {
    id: "admin-tools",
    label: "Admin Tools & Field Behaviors",
    description: "Run audit tools, review field behavior detection, Cmd+Shift+click to override — the incremental correction loop",
    itemIda: "",
    firstModel: "",
  },
];

/* ------------------------------------------------------------------ */
/*  Column definitions for transaction array                           */
/* ------------------------------------------------------------------ */

const QUANTITY_FIELDS = ["on_hand", "on_p", "on_so", "on_po", "on_wo", "available"] as const;

const QUANTITY_LABELS: Record<string, string> = {
  on_hand: "On Hand",
  on_p: "On Prop",
  on_so: "On SO",
  on_po: "On PO",
  on_wo: "On WO",
  available: "Available",
};


/* ------------------------------------------------------------------ */
/*  Transform backend data → TransactionRow[]                          */
/* ------------------------------------------------------------------ */

function transformRows(data: any): TransactionRow[] {
  if (!data?.rows) return [];
  return data.rows.map((row: any, idx: number) => {
    let glSummary = "";
    if (row.gl && row.gl.length > 0) {
      glSummary = row.gl
        .map((e: any) => `${e.side === "debit" ? "DR" : "CR"} ${e.account.split("-").slice(-2, -1)[0]} $${e.amount.toFixed(2)}`)
        .join(", ");
    }
    return {
      id: `${row.type}-${idx}`,
      type: row.type,
      label: row.label,
      on_hand: row.values?.on_hand ?? "",
      on_p: row.values?.on_p ?? "",
      on_so: row.values?.on_so ?? "",
      on_po: row.values?.on_po ?? "",
      on_wo: row.values?.on_wo ?? "",
      available: row.values?.available ?? "",
      gl_summary: glSummary,
      model: row.model,
      record_id: row.record_id,
      processed: row.processed,
    } as TransactionRow;
  });
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

const FlightSimConsole: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  // Active simulation
  const [activeSim, setActiveSim] = useState<SimulationDef | null>(null);

  // Split position
  const [splitWidth, setSplitWidth] = useState(640);
  const [dragging, setDragging] = useState(false);

  // Item being tracked
  const [itemId, setItemId] = useState<number | null>(null);
  const [itemIda, setItemIda] = useState("");
  const [itemName, setItemName] = useState("");

  // Item quantities (opening state)
  const [itemQty, setItemQty] = useState<Record<string, number>>({});

  // Transaction array
  const [rows, setRows] = useState<TransactionRow[]>([]);
  const [loading, setLoading] = useState(false);

  // Right panel
  const [rightModel, setRightModel] = useState<string | null>(null);
  const [rightRecordId, setRightRecordId] = useState<number>(0);
  const [convertedLines, setConvertedLines] = useState<any[] | null>(null);

  const splitRef = useRef<HTMLDivElement>(null);
  const handleMouseDown = useCallback(() => setDragging(true), []);

  // Auto-start simulation from URL path (e.g., /flight-sim/inventory)
  const autoStarted = useRef(false);
  useEffect(() => {
    if (autoStarted.current) return;
    const pathParts = location.pathname.split('/');
    const simId = pathParts[pathParts.length - 1]; // last segment
    const sim = SIMULATIONS.find(s => s.id === simId);
    if (sim) {
      autoStarted.current = true;
      startSimulation(sim, false);
    }
  }, [location.pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!dragging) return;
    const onMove = (e: MouseEvent) => {
      const container = splitRef.current?.parentElement;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      setSplitWidth(Math.max(300, Math.min(e.clientX - rect.left, rect.width - 300)));
    };
    const onUp = () => setDragging(false);
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
    return () => { document.removeEventListener("mousemove", onMove); document.removeEventListener("mouseup", onUp); };
  }, [dragging]);

  /** Refresh transaction array */
  const refreshArray = useCallback(async () => {
    if (!itemId) return;
    setLoading(true);
    try {
      const res = await manageAction("get_flight_transactions", { item_id: itemId });
      const data = res?.data?.data ?? res?.data ?? res;
      if (data && !data.error) {
        setRows(transformRows(data));
        if (data.item) {
          setItemIda(data.item.ida || "");
          setItemName(data.item.name || "");
          setItemQty(data.item.quantity || {});
        }
      }
    } catch (e) {
      console.error("Transaction array refresh failed:", e);
    } finally {
      setLoading(false);
    }
  }, [itemId]);

  useEffect(() => { if (itemId) refreshArray(); }, [itemId, refreshArray]);

  /** Create a blank transaction record with simple qq ida */
  const createSimRecord = async (model: string): Promise<number | null> => {
    try {
      const result = await saveRecord(model, {
        is_active: true,
        status: "planned",
        metadata: { training: true, flight_sim: true },
      }) as any;
      const newId = result?.data?.id || result?.id || result?.data?.record?.id;
      return newId || null;
    } catch (e) {
      console.error(`Failed to create ${model}:`, e);
      return null;
    }
  };

  /** Start a simulation.
   *  Click = always fresh — reset item + all training data, then create new record.
   *  Shift-click = resume last (find most recent from transaction data).
   */
  const startSimulation = async (sim: SimulationDef, resume = false) => {
    setActiveSim(sim);
    setLoading(true);
    setConvertedLines(null);
    try {
      // Company profile sim — find the Setting by ida and open it
      if (sim.id === 'company-profile') {
        const { getRecords } = await import('../../api/wcapi');
        const res = await getRecords('setting', { ida: 'company-profile', limit: 1 }) as any;
        const rec = (res?.results || [])[0];
        if (rec?.id) {
          setRightModel('setting');
          setRightRecordId(rec.id);
          setRows([
            { id: 'company', type: 'item' as const, label: 'Company Name & Address', on_hand: rec.config?.company?.name ? '✓' : '—', on_p: '', on_so: '', on_po: '', on_wo: '', available: '', gl_summary: 'config.company' },
            { id: 'ship_to', type: 'item' as const, label: 'Ship-To Address', on_hand: rec.config?.company?.address_ship_to?.street1 ? '✓' : '—', on_p: '', on_so: '', on_po: '', on_wo: '', available: '', gl_summary: 'config.company.address_ship_to' },
            { id: 'logos', type: 'item' as const, label: 'Logos', on_hand: rec.config?.logos?.primary ? '✓' : '—', on_p: '', on_so: '', on_po: '', on_wo: '', available: '', gl_summary: 'config.logos' },
            { id: 'documents', type: 'item' as const, label: 'Document Templates', on_hand: rec.config?.documents?.invoice_template ? '✓' : '—', on_p: '', on_so: '', on_po: '', on_wo: '', available: '', gl_summary: 'config.documents' },
            { id: 'print', type: 'item' as const, label: 'Print Defaults', on_hand: rec.config?.print_defaults?.paper_size ? '✓' : '—', on_p: '', on_so: '', on_po: '', on_wo: '', available: '', gl_summary: 'config.print_defaults' },
            { id: 'receivables', type: 'item' as const, label: 'Receivables & Statements', on_hand: rec.config?.receivables?.finance_charge_pct !== undefined ? '✓' : '—', on_p: '', on_so: '', on_po: '', on_wo: '', available: '', gl_summary: 'config.receivables' },
            { id: 'accounting', type: 'item' as const, label: 'Accounting Integration', on_hand: rec.config?.accounting?.package ? '✓' : '—', on_p: '', on_so: '', on_po: '', on_wo: '', available: '', gl_summary: 'config.accounting' },
          ]);
        }
        setLoading(false);
        return;
      }

      // Phase 1 sims may not have an item — skip reset and item lookup
      let loadedItemId: number | null = null;

      if (sim.itemIda) {
        // Click = fresh start: reset everything for this item first
        if (!resume) {
          await manageAction("reset_flight_simulator", { ida: sim.itemIda });
        }

        // Look up training item by ida (fresh state after reset)
        const res = await manageAction("get_item_by_ida", { ida: sim.itemIda });
        const data = res?.data?.data ?? res?.data ?? res;
        if (data?.item?.id) {
          loadedItemId = data.item.id;
          setItemId(loadedItemId);
          setItemIda(data.item.ida || sim.itemIda);
          setItemName(data.item.name || "");
          setItemQty(data.item.quantity || {});
        }
      }

      let recordId: number | null = null;

      // Shift-click: find most recent existing record
      if (resume && loadedItemId) {
        const txRes = await manageAction("get_flight_transactions", { item_id: loadedItemId });
        const txData = txRes?.data?.data ?? txRes?.data ?? txRes;
        if (txData && !txData.error) {
          setRows(transformRows(txData));
          const txRows = txData.rows || [];
          for (let i = txRows.length - 1; i >= 0; i--) {
            const row = txRows[i];
            if (row.model === sim.firstModel && row.record_id) {
              recordId = row.record_id;
              break;
            }
          }
        }
      }

      // Click (or no existing found): always create fresh
      if (!recordId) {
        setRows([]);
        recordId = await createSimRecord(sim.firstModel);
      }

      if (recordId) {
        setRightModel(sim.firstModel);
        setRightRecordId(recordId);
      }
    } catch (e) {
      console.error("Start simulation failed:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleRowSelect = (row: TransactionRow) => {
    if (row.model && row.record_id) {
      setRightModel(row.model);
      setRightRecordId(row.record_id);
    }
  };

  /* ---------------------------------------------------------------- */
  /*  Simulation Select List (initial state)                           */
  /* ---------------------------------------------------------------- */

  if (!activeSim) {
    return (
      <div className="fs-select-root">
        <div className="fs-select-header">
          <h2 className="fs-select-title">Flight Simulator</h2>
          <p className="fs-select-desc">
            Choose a simulation to learn how transactions flow through WebClerk.
            Each simulation uses a training item and walks you through creating
            real transactions while watching quantities, pending records, and GL accounts change.
          </p>
        </div>
        <div className="fs-select-grid">
          {SIMULATIONS.map((sim) => (
            <button
              key={sim.id}
              className="fs-sim-card"
              onClick={(e) => {
                if (sim.id === 'admin-tools') {
                  navigate('/admin-tools');
                  return;
                }
                startSimulation(sim, e.shiftKey);
              }}
            >
              <span className="fs-sim-label">{sim.label}</span>
              <span className="fs-sim-desc">{sim.description}</span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  /* ---------------------------------------------------------------- */
  /*  Active Simulation (db.list + db.form)                            */
  /* ---------------------------------------------------------------- */

  return (
    <div className="fs-root db-root" data-theme="dark">
      {/* Sim info bar */}
      <div className="fs-sim-bar">
        <button className="fs-btn" onClick={() => { setActiveSim(null); setItemId(null); setRows([]); setRightModel(null); }}>
          &larr; Simulations
        </button>
        <span className="fs-sim-bar-title">{activeSim.label}</span>
        {itemId && (
          <span className="fs-header-meta">
            {itemIda} &mdash; {itemName} &mdash; {rows.length} rows
          </span>
        )}
        <button className="fs-btn" onClick={refreshArray} disabled={loading}>
          <FaSync size={10} className={loading ? "animate-spin" : ""} /> Refresh
        </button>
      </div>

      {/* Main content — left/right split */}
      <div className={`fs-split ${dragging ? "fs-split--dragging" : ""}`}>
        {/* Left panel — Item summary + Transaction Array */}
        <div className="fs-left" style={{ width: splitWidth }}>
          {/* Item opening quantities */}
          {itemId && (
            <div className="fs-item-summary">
              <div className="fs-item-header">
                <span className="fs-item-ida">{itemIda}</span>
                <span className="fs-item-name">{itemName}</span>
              </div>
              <div className="fs-item-quantities">
                {QUANTITY_FIELDS.map((field) => (
                  <div key={field} className="fs-item-qty-cell">
                    <span className="fs-item-qty-label">{QUANTITY_LABELS[field]}</span>
                    <span className="fs-item-qty-value">{itemQty[field] ?? 0}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {rows.length > 0 ? (
            <div className="fs-transaction-table">
              <div className="fs-tx-header">
                <span className="fs-tx-cell fs-tx-event">Event</span>
                {QUANTITY_FIELDS.map((f) => (
                  <span key={f} className="fs-tx-cell fs-tx-qty">{QUANTITY_LABELS[f]}</span>
                ))}
                <span className="fs-tx-cell fs-tx-gl">GL Impact</span>
              </div>
              {rows.map((row) => {
                const isItem = row.type === "item";
                const isPending = row.type === "pending";
                const isLine = row.type.endsWith("_line");
                const rowClass = isItem ? "fs-tx-row--item"
                  : isPending && row.processed ? "fs-tx-row--pending-applied"
                  : isPending ? "fs-tx-row--pending-unapplied"
                  : "fs-tx-row--line";
                return (
                  <div
                    key={row.id}
                    className={`fs-tx-row ${rowClass}`}
                    onClick={() => handleRowSelect(row)}
                  >
                    <span className="fs-tx-cell fs-tx-event">
                      {isItem ? "■ " : isPending ? "● " : isLine ? "▶ " : ""}
                      {row.label}
                    </span>
                    {QUANTITY_FIELDS.map((f) => {
                      const val = row[f];
                      if (val === undefined || val === null || val === "" || val === 0) {
                        return <span key={f} className="fs-tx-cell fs-tx-qty fs-tx-empty">—</span>;
                      }
                      const s = String(val);
                      const cls = s.startsWith("+") ? "fs-qty-positive"
                        : s.startsWith("-") ? "fs-qty-negative"
                        : "fs-qty-static";
                      return <span key={f} className={`fs-tx-cell fs-tx-qty ${cls}`}>{s}</span>;
                    })}
                    <span className="fs-tx-cell fs-tx-gl">
                      {row.gl_summary || "—"}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="fs-empty">
              {loading ? "Loading item..." : "Waiting for training item..."}
            </div>
          )}
        </div>

        {/* Drag handle */}
        <div
          ref={splitRef}
          className={`fs-handle ${dragging ? "fs-handle--active" : ""}`}
          onMouseDown={handleMouseDown}
        />

        {/* Right panel — Transaction Form */}
        <div className="fs-right">
          {rightModel ? (
            <Suspense fallback={<div className="fs-empty">Loading {rightModel}...</div>}>
              <UiDetail
                modelName={rightModel}
                recordId={rightRecordId}
                initialLines={convertedLines}
                onNavigate={(model: string, id: number) => { setRightModel(model); setRightRecordId(id); setConvertedLines(null); refreshArray(); }}
                onAfterSave={() => { setConvertedLines(null); refreshArray(); }}
                onWorkflowComplete={(result: any) => {
                  refreshArray();
                  if (!result) return;
                  // Switch right panel to the created record
                  // Pass converted lines for user review before save
                  const lines = result.lines || null;
                  if (result.order_id) {
                    setRightModel("order");
                    setRightRecordId(result.order_id);
                    setConvertedLines(lines);
                  } else if (result.invoice_id) {
                    setRightModel("invoice");
                    setRightRecordId(result.invoice_id);
                    setConvertedLines(lines);
                  } else if (result.purchase_id) {
                    setRightModel("purchase");
                    setRightRecordId(result.purchase_id);
                    setConvertedLines(lines);
                  } else if (result.payment_id) {
                    setRightModel("payment");
                    setRightRecordId(result.payment_id);
                    setConvertedLines(null);
                  }
                }}
              />
            </Suspense>
          ) : (
            <div className="fs-empty">
              <div className="fs-empty-box">
                <p className="fs-empty-title">Ready</p>
                <p className="fs-empty-desc">{activeSim.description}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FlightSimConsole;
