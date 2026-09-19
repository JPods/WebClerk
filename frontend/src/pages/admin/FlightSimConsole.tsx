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
import { formatCurrency } from "@/utils/stringUtils";

const UiDetail = React.lazy(() => import("../../apps/transactions/components/TransactionDetail"));
const VCardImportDialog = React.lazy(() => import("../../components/common/VCardImportDialog"));

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface TransactionRow {
  id: string;
  type: "item" | "quote_line" | "order_line" | "invoice_line" | "purchase_line" | "workorder_line" | "pending";
  label: string;
  on_hand: number | string;
  on_qt: number | string;
  on_so: number | string;
  on_po: number | string;
  on_wo: number | string;
  available: number | string;
  gl_summary: string;
  model?: string;
  record_id?: number;
  processed?: boolean;
  /** Hover text: what the line carries, or why the pending record exists. */
  hint?: string;
  /** Parent document ida (line rows) */
  ida?: string;
  [key: string]: unknown;
}

interface CashRow {
  type: "cash" | "cash_application";
  label: string;
  model?: string;
  record_id?: number;
  values: {
    amount?: string;
    applied?: string;
    available?: string;
    method?: string;
    status?: string;
  };
  processed?: boolean;
}

interface GlRow {
  type: "gl_header" | "gl_entry";
  label: string;
  values: {
    debit?: string;
    credit?: string;
    source?: string;
  };
}

interface SimulationDef {
  id: string;
  label: string;
  description: string;
  /** Does this simulation track an item? The WHICH is the user's one chosen
   *  item (simItemIda), not a per-simulation literal. Phase 1 sims are false. */
  needsItem: boolean;
  firstModel: string;    // first transaction model to open on right
}

/** The simulator tracks one item at a time and the user picks it.
 *  There is deliberately NO default item. A literal here is a guess about
 *  someone else's data set — the previous one named a training item that no
 *  longer exists, so every panel sat empty with nothing saying why. */
const SIM_ITEM_KEY = "wc:flightsim:item_ida";
const DEFAULT_SIM_ITEM_IDA = "";

/** Items with this ida prefix are training items and may be reset.
 *  Anything else is real and is watched only. Mirrors TRAINING_IDA_PREFIX in
 *  backend/apps/products/services/inventory/inventory_flight_sim.py, which
 *  refuses the reset outright — this only keeps the UI from asking. */
const TRAINING_IDA_PREFIX = "qq";
const isTrainingItem = (ida: string) =>
  ida.trim().toLowerCase().startsWith(TRAINING_IDA_PREFIX);

/* ------------------------------------------------------------------ */
/*  Available simulations                                              */
/* ------------------------------------------------------------------ */

const SIMULATIONS: SimulationDef[] = [
  // ── Phase 1: Foundation ──
  {
    id: "first-customer",
    label: "1. Your First Customer",
    description: "Create a Contact, Customer Org, and set credit limit — the foundation for all transactions",
    needsItem: false,
    firstModel: "contact",
  },
  {
    id: "first-item",
    label: "2. Your First Item",
    description: "Create an Item with price ($10), cost ($6), GL accounts, and 100 units opening inventory",
    needsItem: true,
    firstModel: "item",
  },
  {
    id: "first-sale",
    label: "3. Your First Sale",
    description: "Create a Quote for 15 units, convert 9 to an Order — watch on_qt and on_so change",
    needsItem: true,
    firstModel: "quote",
  },
  // ── Phase 2: Sell Side ──
  {
    id: "inventory",
    label: "4. Inventory Quantity Tracking",
    description: "Quote → Order → Invoice → Purchase → Receive — watch on_hand, on_so, on_po, pending, and GL change at each step",
    needsItem: true,
    firstModel: "quote",
  },
  {
    id: "cash",
    label: "Cash Flow Tracking",
    description: "Invoice → Cash → Discount → Write-off — watch cash, AR, and bank reconciliation",
    needsItem: true,
    firstModel: "invoice",
  },
  {
    id: "cash-lifecycle",
    label: "Cash Lifecycle",
    description: "Order → partial Invoice → accept Cash → apply part to invoice → journal — watch amount, available, tendered, change, ledger, and GL",
    needsItem: true,
    firstModel: "order",
  },
  {
    id: "gl-audit",
    label: "GL Audit Trail",
    description: "Every business event creates balanced journal entries — trace any balance to its source",
    needsItem: true,
    firstModel: "invoice",
  },
  {
    id: "bom",
    label: "Bill of Materials",
    description: "BOM explosion, component availability, buildable quantity, cost rollup",
    needsItem: true,
    firstModel: "workorder",
  },
  {
    id: "p2p",
    label: "Purchase-to-Pay",
    description: "Requisition → PO → Receive → Three-way match → Pay vendor",
    needsItem: true,
    firstModel: "purchase",
  },
  {
    id: "commissions",
    label: "Commission Tracking",
    description: "Accrual at sale, split commissions, adjustments at cash, period-end reconciliation",
    needsItem: true,
    firstModel: "invoice",
  },
  {
    id: "currency",
    label: "Currency Variations",
    description: "Multi-currency transactions, exchange rate gains/losses, period-end revaluation",
    needsItem: true,
    firstModel: "invoice",
  },
  {
    id: "costing",
    label: "Costing Methods",
    description: "Same transactions, three different profit numbers — FIFO vs LIFO vs weighted average",
    needsItem: true,
    firstModel: "purchase",
  },
  {
    id: "company-profile",
    label: "Company Profile Setup",
    description: "Configure your company name, address, ship-to, logos, print defaults, receivables, and accounting — the foundation every document and report reads from",
    needsItem: false,
    firstModel: "setting",
  },
  {
    id: "admin-tools",
    label: "Admin Tools & Field Behaviors",
    description: "Run audit tools, review field behavior detection, Cmd+Shift+click to override — the incremental correction loop",
    needsItem: false,
    firstModel: "",
  },
];

interface SimDoc {
  model: string;
  record_id: number;
  ida: string;
}

/** A fresh run lists only its own documents. Resume replays the item's whole
 *  history, so keep the strip to the most recent few. */
const MAX_DOC_CHIPS = 6;

/** Documents that get a chip. The ida names the type (1023-inv), so the chip shows the ida. */
const DOC_MODELS = new Set(["quote", "order", "invoice", "purchase", "workorder"]);

/** Refresh control for a panel section. All three panels come from one call,
 *  so each button refreshes the same data. */
const SectionRefresh: React.FC<{ onClick: () => void; loading: boolean }> = ({ onClick, loading }) => (
  <button className="fs-btn fs-section-refresh" onClick={onClick} disabled={loading} title="Refresh">
    <FaSync size={9} className={loading ? "animate-spin" : ""} />
  </button>
);

/* ------------------------------------------------------------------ */
/*  Column definitions for transaction array                           */
/* ------------------------------------------------------------------ */

const QUANTITY_FIELDS = ["on_hand", "on_qt", "on_so", "on_po", "on_wo", "available"] as const;

const QUANTITY_LABELS: Record<string, string> = {
  on_hand: "On Hand",
  on_qt: "On Prop",
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
        .map((e: any) => `${e.side === "debit" ? "DR" : "CR"} ${e.account.split("-").slice(-2, -1)[0]} ${formatCurrency(e.amount)}`)
        .join(", ");
    }
    return {
      id: `${row.type}-${idx}`,
      type: row.type,
      label: row.label,
      on_hand: row.values?.on_hand ?? "",
      on_qt: row.values?.on_qt ?? "",
      on_so: row.values?.on_so ?? "",
      on_po: row.values?.on_po ?? "",
      on_wo: row.values?.on_wo ?? "",
      available: row.values?.available ?? "",
      gl_summary: glSummary,
      model: row.model,
      record_id: row.record_id,
      processed: row.processed,
      hint: row.hint,
      ida: row.ida,
    } as TransactionRow;
  });
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

/* ------------------------------------------------------------------ */
/*  Item picker — the simulator tracks ONE item and the user picks it   */
/* ------------------------------------------------------------------ */

const SimItemPicker: React.FC<{
  current: string;
  onPick: (ida: string) => void;
  onClose: () => void;
}> = ({ current, onPick, onClose }) => {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<any[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (query.trim().length < 2) { setResults([]); return; }
    const t = setTimeout(async () => {
      setBusy(true);
      try {
        const { getRecords } = await import("../../api/wcapi");
        const res: any = await getRecords("item", { keyword: query.trim(), limit: 10 });
        setResults(res?.results || []);
      } catch { setResults([]); }
      finally { setBusy(false); }
    }, 250);
    return () => clearTimeout(t);
  }, [query]);

  return (
    <div className="fs-item-picker">
      <div className="fs-item-picker-head">
        <span>Simulation item — one at a time</span>
        <button className="fs-btn" onClick={onClose}>Close</button>
      </div>
      <input
        autoFocus
        className="fs-item-picker-input"
        placeholder="Search items by ida, sku, or name…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <div className="fs-item-picker-results">
        {busy && <div className="fs-item-picker-empty">Searching…</div>}
        {!busy && query.trim().length >= 2 && results.length === 0 && (
          <div className="fs-item-picker-empty">No items match “{query}”.</div>
        )}
        {results.map((r) => {
          const training = isTrainingItem(r.ida || "");
          return (
            <button
              key={r.id}
              className={`fs-item-picker-row${r.ida === current ? " is-current" : ""}`}
              onClick={() => { onPick(r.ida); onClose(); }}
            >
              {/* ida and sku are different fields and are routinely confused —
                  the simulator matches on ida, so show both. */}
              <span className="fs-item-picker-ida">{r.ida}</span>
              {r.sku && r.sku !== r.ida && (
                <span className="fs-item-picker-sku">sku {r.sku}</span>
              )}
              <span className="fs-item-picker-name">{r.name}</span>
              <span className={`fs-item-picker-mode${training ? " is-training" : ""}`}>
                {training ? "training — resets each run" : "real — watch only"}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};

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

  // The simulator tracks exactly ONE item, and the user chooses which.
  // Every simulation that needs an item uses this one. Training items (ida
  // starting 'qq') get a fresh reset on each run; any other item is watched
  // only — never reset — so a simulation can never delete live records.
  const [simItemIda, setSimItemIda] = useState<string>(() => {
    try { return localStorage.getItem(SIM_ITEM_KEY) || DEFAULT_SIM_ITEM_IDA; }
    catch { return DEFAULT_SIM_ITEM_IDA; }
  });
  const [showItemPicker, setShowItemPicker] = useState(false);
  const [watchOnly, setWatchOnly] = useState(false);
  const [simError, setSimError] = useState<string | null>(null);

  const chooseSimItem = useCallback((ida: string) => {
    setSimItemIda(ida);
    try { localStorage.setItem(SIM_ITEM_KEY, ida); } catch { /* ignore */ }
  }, []);

  // Item quantities (opening state)
  const [itemQty, setItemQty] = useState<Record<string, number>>({});

  // vCard import dialog
  const [showVcardImport, setShowVcardImport] = useState(false);

  // Transaction array
  const [rows, setRows] = useState<TransactionRow[]>([]);
  const [cashRows, setCashRows] = useState<CashRow[]>([]);
  const [glRows, setGlRows] = useState<GlRow[]>([]);
  // Fresh start time (epoch ms, UTC). The panels show only what happens from
  // here on; null = full history (shift-click resume).
  const [simSince, setSimSince] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);

  // Section heights (percentages of left panel)
  const [sectionHeights, setSectionHeights] = useState<[number, number, number]>([50, 25, 25]);
  const [vDragging, setVDragging] = useState<number | null>(null); // which handle (0 or 1)

  // Right panel
  const [rightModel, setRightModel] = useState<string | null>(null);
  const [rightRecordId, setRightRecordId] = useState<number>(0);
  const [convertedLines, setConvertedLines] = useState<any[] | null>(null);

  const splitRef = useRef<HTMLDivElement>(null);
  const leftRef = useRef<HTMLDivElement>(null);
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

  // Vertical section drag
  useEffect(() => {
    if (vDragging === null) return;
    const onMove = (e: MouseEvent) => {
      const container = leftRef.current;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const totalHeight = rect.height;
      if (totalHeight <= 0) return;
      const y = e.clientY - rect.top;
      const pct = (y / totalHeight) * 100;

      setSectionHeights(prev => {
        const next: [number, number, number] = [...prev];
        if (vDragging === 0) {
          // Dragging between counts and money
          const newTop = Math.max(15, Math.min(pct, 100 - next[2] - 15));
          next[1] = 100 - newTop - next[2];
          next[0] = newTop;
        } else {
          // Dragging between money and GL
          const topFixed = next[0];
          const remaining = 100 - topFixed;
          const midPct = Math.max(15, Math.min(pct - topFixed, remaining - 15));
          next[1] = midPct;
          next[2] = remaining - midPct;
        }
        return next;
      });
    };
    const onUp = () => setVDragging(null);
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
    return () => { document.removeEventListener("mousemove", onMove); document.removeEventListener("mouseup", onUp); };
  }, [vDragging]);

  /** Refresh transaction array */
  const refreshArray = useCallback(async () => {
    if (!itemId) return;
    setLoading(true);
    try {
      const res = await manageAction("get_flight_transactions", simSince ? { item_id: itemId, since: simSince } : { item_id: itemId });
      const data = res?.data?.data ?? res?.data ?? res;
      // A section that could not be built reports itself rather than rendering
      // as "no events yet", which is indistinguishable from "nothing happened".
      if (data?.error) setSimError(String(data.error));
      else if (data?.warnings?.length) setSimError(data.warnings.join(" · "));
      if (data && !data.error) {
        setRows(transformRows(data));
        setCashRows(data.cash_rows || []);
        setGlRows(data.gl_rows || []);
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
  }, [itemId, simSince]);

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
  // itemIda: pass the ida just picked. setSimItemIda has not re-rendered yet,
  // so reading simItemIda here would look up the PREVIOUS item and report
  // the new one "not found".
  const startSimulation = async (sim: SimulationDef, resume = false, itemIda?: string) => {
    setActiveSim(sim);
    setLoading(true);
    setConvertedLines(null);
    // Small margin so browser/server clock skew cannot hide the first new line.
    setSimSince(resume ? null : Date.now() - 5000);
    setRows([]);
    setCashRows([]);
    setGlRows([]);
    // Phase 1 sims have no item — narrow the left panel to give the form more room
    if (!sim.needsItem) {
      setSplitWidth(280);
    }
    setSimError(null);
    setWatchOnly(false);
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
            { id: 'company', type: 'item' as const, label: 'Company Name & Address', on_hand: rec.config?.company?.name ? '✓' : '—', on_qt: '', on_so: '', on_po: '', on_wo: '', available: '', gl_summary: 'config.company' },
            { id: 'ship_to', type: 'item' as const, label: 'Ship-To Address', on_hand: rec.config?.company?.address_ship_to?.street1 ? '✓' : '—', on_qt: '', on_so: '', on_po: '', on_wo: '', available: '', gl_summary: 'config.company.address_ship_to' },
            { id: 'logos', type: 'item' as const, label: 'Logos', on_hand: rec.config?.logos?.primary ? '✓' : '—', on_qt: '', on_so: '', on_po: '', on_wo: '', available: '', gl_summary: 'config.logos' },
            { id: 'documents', type: 'item' as const, label: 'Document Templates', on_hand: rec.config?.documents?.invoice_template ? '✓' : '—', on_qt: '', on_so: '', on_po: '', on_wo: '', available: '', gl_summary: 'config.documents' },
            { id: 'print', type: 'item' as const, label: 'Print Defaults', on_hand: rec.config?.print_defaults?.paper_size ? '✓' : '—', on_qt: '', on_so: '', on_po: '', on_wo: '', available: '', gl_summary: 'config.print_defaults' },
            { id: 'receivables', type: 'item' as const, label: 'Receivables & Statements', on_hand: rec.config?.receivables?.finance_charge_pct !== undefined ? '✓' : '—', on_qt: '', on_so: '', on_po: '', on_wo: '', available: '', gl_summary: 'config.receivables' },
            { id: 'accounting', type: 'item' as const, label: 'Accounting Integration', on_hand: rec.config?.accounting?.package ? '✓' : '—', on_qt: '', on_so: '', on_po: '', on_wo: '', available: '', gl_summary: 'config.accounting' },
          ]);
        }
        setLoading(false);
        return;
      }

      // Phase 1 sims may not have an item — skip reset and item lookup
      let loadedItemId: number | null = null;

      if (sim.needsItem) {
        const ida = (itemIda ?? simItemIda).trim();

        // No item chosen yet — ask, rather than calling the backend with an
        // empty ida and landing back on an empty panel with no explanation.
        if (!ida) {
          setItemId(null);
          setSimError("Flight simulator limits you to one item");
          setShowItemPicker(true);
          setLoading(false);
          return;
        }

        const training = isTrainingItem(ida);
        setWatchOnly(!training);

        // Click = fresh start, but ONLY for a training item. Reset deletes the
        // item's transaction lines and any header they leave empty, so a real
        // item from the data set is watched as-is and never reset.
        if (!resume && training) {
          await manageAction("reset_flight_simulator", { ida });
        }

        const res = await manageAction("get_item_by_ida", { ida });
        const data = res?.data?.data ?? res?.data ?? res;
        if (data?.item?.id) {
          loadedItemId = data.item.id;
          setItemId(loadedItemId);
          setItemIda(data.item.ida || ida);
          setItemName(data.item.name || "");
          setItemQty(data.item.quantity || {});
        } else {
          // Say so. Without this the panels sit on "No count events yet",
          // which reads as "you have not done anything" rather than
          // "the item this simulation watches does not exist".
          setItemId(null);
          setItemIda(ida);
          setItemName("");
          setItemQty({});
          setSimError("Flight simulator limits you to one item");
          setShowItemPicker(true);
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
    // The right panel is a transaction form; a pending record opens only by double-click.
    if (row.model && row.record_id && row.model !== "pending") {
      setRightModel(row.model);
      setRightRecordId(row.record_id);
    }
  };

  /** Documents in this simulation, in the order they were added: every parent
   *  document with a line in the Counts panel, plus the record open on the right
   *  (a new header has no line yet). Reopen one to add more records to it. */
  const simDocs: SimDoc[] = [];
  for (const row of rows) {
    if (!row.type.endsWith("_line") || !row.model || !row.record_id) continue;
    if (simDocs.some((d) => d.model === row.model && d.record_id === row.record_id)) continue;
    simDocs.push({ model: row.model, record_id: row.record_id, ida: row.ida || `#${row.record_id}` });
  }
  if (rightModel && rightRecordId && DOC_MODELS.has(rightModel)
      && !simDocs.some((d) => d.model === rightModel && d.record_id === rightRecordId)) {
    simDocs.push({ model: rightModel, record_id: rightRecordId, ida: `#${rightRecordId}` });
  }

  /** Double-click: open the transaction or pending record on its own, so the
   *  trainee can see the two are separate records. */
  const openRowRecord = (row: TransactionRow) => {
    if (row.model && row.record_id) window.open(`/${row.model}/${row.record_id}`, "_blank");
  };

  /* ---------------------------------------------------------------- */
  /*  Simulation Select List (initial state)                           */
  /* ---------------------------------------------------------------- */

  /** Audit mode — enter an invoice number, load its full picture */
  const startAudit = async (invoiceIda: string) => {
    if (!invoiceIda.trim()) return;
    setLoading(true);
    setActiveSim({ id: "audit", label: `Audit: Invoice ${invoiceIda}`, description: "Transaction audit view", needsItem: false, firstModel: "invoice" });
    setConvertedLines(null);
    try {
      const res = await manageAction("get_flight_by_invoice", { invoice_ida: invoiceIda.trim() });
      const data = res?.data?.data ?? res?.data ?? res;
      if (data?.error) {
        setActiveSim(null);
        alert(data.error);
        return;
      }
      setRows(transformRows(data));
      setCashRows(data.cash_rows || []);
      setGlRows(data.gl_rows || []);
      if (data.item) {
        setItemId(data.item.id);
        setItemIda(data.item.ida || "");
        setItemName(data.item.name || "");
        setItemQty(data.item.quantity || {});
      }
      if (data.invoice) {
        setRightModel("invoice");
        setRightRecordId(data.invoice.id);
      }
    } catch (e) {
      console.error("Audit load failed:", e);
      setActiveSim(null);
    } finally {
      setLoading(false);
    }
  };

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

        {/* Audit mode — enter an invoice number */}
        <div className="fs-audit-bar">
          <span className="fs-audit-label">Audit</span>
          <input
            className="fs-audit-input"
            placeholder="Invoice # (e.g. 1023 or 1023-inv)"
            onKeyDown={(e) => {
              if (e.key === "Enter") startAudit((e.target as HTMLInputElement).value);
            }}
          />
          <button
            className="fs-btn"
            onClick={() => {
              const input = document.querySelector('.fs-audit-input') as HTMLInputElement;
              if (input) startAudit(input.value);
            }}
          >
            Look Up
          </button>
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
        {activeSim?.id === 'first-customer' && (
          <button className="fs-btn fs-btn-tx" onClick={() => setShowVcardImport(true)}>
            Import from Contacts
          </button>
        )}
        {activeSim?.needsItem && (
          <button
            className={`fs-btn${!itemId ? " fs-btn-unresolved" : ""}`}
            onClick={() => setShowItemPicker(true)}
            title={itemId
              ? "The simulator tracks one item. Click to choose which."
              : "This item was not found — the panels stay empty until one is chosen."}
          >
            Item: {simItemIda || "choose…"}
            {!itemId && simItemIda && <span className="fs-watch-badge is-missing">not found</span>}
            {itemId && watchOnly && <span className="fs-watch-badge">watch only</span>}
          </button>
        )}
        {simDocs.length > 0 && (
          <div className="fs-doc-strip">
            <span className="fs-doc-strip-label">Documents</span>
            {simDocs.slice(-MAX_DOC_CHIPS).map((d) => {
              const active = d.model === rightModel && d.record_id === rightRecordId;
              return (
                <button
                  key={`${d.model}-${d.record_id}`}
                  className={`fs-btn fs-doc-chip${active ? " is-active" : ""}`}
                  onClick={() => { setRightModel(d.model); setRightRecordId(d.record_id); setConvertedLines(null); }}
                  onDoubleClick={() => window.open(`/${d.model}/${d.record_id}`, "_blank")}
                  title={`Open ${d.model} ${d.ida} here to add more records · double-click for a new window`}
                >
                  {d.ida}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {showItemPicker && (
        <SimItemPicker
          current={simItemIda}
          onPick={(ida) => { chooseSimItem(ida); if (activeSim) startSimulation(activeSim, false, ida); }}
          onClose={() => setShowItemPicker(false)}
        />
      )}

      {simError && (
        <div className="fs-sim-error" role="alert">
          {simError}
          <button className="fs-btn" onClick={() => setSimError(null)}>Dismiss</button>
        </div>
      )}

      {/* Main content — left/right split */}
      <div className={`fs-split ${dragging ? "fs-split--dragging" : ""}`}>
        {/* Left panel — Item summary + Transaction Array (hidden for Phase 1 sims with no item) */}
        {activeSim?.needsItem && (<>
        <div className="fs-left" ref={leftRef} style={{ width: splitWidth }}>
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

          {/* Three vertically-stacked sections with drag handles */}
          <div className={`fs-left-sections ${vDragging !== null ? "fs-split--dragging" : ""}`}>
            {/* Section 1: Counts */}
            <div className="fs-section" style={{ height: `${sectionHeights[0]}%` }}>
              <div className="fs-section-header">
                Counts <span>{rows.length} rows</span>
              </div>
              <div className="fs-section-content">
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
                          onDoubleClick={() => openRowRecord(row)}
                          title={row.model && row.record_id ? `${row.hint ? row.hint + "\n" : ""}Double-click to open ${row.model} ${row.record_id} in a new window` : undefined}
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
                  <div className="fs-section-empty">
                    {loading ? "Loading..." : "No count events yet"}
                  </div>
                )}
              </div>
            </div>

            {/* Drag handle 1 */}
            <div
              className={`fs-vhandle ${vDragging === 0 ? "fs-vhandle--active" : ""}`}
              onMouseDown={() => setVDragging(0)}
            />

            {/* Section 2: Money */}
            <div className="fs-section" style={{ height: `${sectionHeights[1]}%` }}>
              <div className="fs-section-header">
                Money
                <span className="fs-section-header-tools">
                  {cashRows.length} rows
                  <SectionRefresh onClick={refreshArray} loading={loading} />
                </span>
              </div>
              <div className="fs-section-content">
                {cashRows.length > 0 ? (
                  <div className="fs-pay-table">
                    <div className="fs-pay-header">
                      <span className="fs-pay-cell fs-pay-label">Cash</span>
                      <span className="fs-pay-cell fs-pay-amount">Amount</span>
                      <span className="fs-pay-cell fs-pay-amount">Applied</span>
                      <span className="fs-pay-cell fs-pay-amount">Available</span>
                      <span className="fs-pay-cell fs-pay-status">Status</span>
                    </div>
                    {cashRows.map((row, idx) => {
                      const isApp = row.type === "cash_application";
                      return (
                        <div
                          key={`pay-${idx}`}
                          className={`fs-pay-row ${isApp ? "fs-pay-row--application" : "fs-pay-row--cash"}`}
                          onClick={() => {
                            if (row.model && row.record_id) {
                              setRightModel(row.model);
                              setRightRecordId(row.record_id);
                            }
                          }}
                        >
                          <span className="fs-pay-cell fs-pay-label">{row.label}</span>
                          <span className="fs-pay-cell fs-pay-amount">{row.values.amount || "—"}</span>
                          <span className="fs-pay-cell fs-pay-amount">{row.values.applied || "—"}</span>
                          <span className="fs-pay-cell fs-pay-amount">{row.values.available || "—"}</span>
                          <span className="fs-pay-cell fs-pay-status">{row.values.status || "—"}</span>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="fs-section-empty">No money events yet</div>
                )}
              </div>
            </div>

            {/* Drag handle 2 */}
            <div
              className={`fs-vhandle ${vDragging === 1 ? "fs-vhandle--active" : ""}`}
              onMouseDown={() => setVDragging(1)}
            />

            {/* Section 3: GL Journals */}
            <div className="fs-section" style={{ height: `${sectionHeights[2]}%` }}>
              <div className="fs-section-header">
                GL Journals
                <span className="fs-section-header-tools">
                  {glRows.length} rows
                  <SectionRefresh onClick={refreshArray} loading={loading} />
                </span>
              </div>
              <div className="fs-section-content">
                {glRows.length > 0 ? (
                  <div className="fs-gl-table">
                    <div className="fs-gl-header-row">
                      <span className="fs-gl-cell fs-gl-account">Account</span>
                      <span className="fs-gl-cell fs-gl-debit">Debit</span>
                      <span className="fs-gl-cell fs-gl-credit">Credit</span>
                      <span className="fs-gl-cell fs-gl-source">Source</span>
                    </div>
                    {glRows.map((row, idx) => {
                      const isHeader = row.type === "gl_header";
                      return (
                        <div
                          key={`gl-${idx}`}
                          className={`fs-gl-row ${isHeader ? "fs-gl-row--header" : "fs-gl-row--entry"}`}
                        >
                          <span className="fs-gl-cell fs-gl-account">{row.label}</span>
                          {isHeader ? (
                            <>
                              <span className="fs-gl-cell fs-gl-debit" />
                              <span className="fs-gl-cell fs-gl-credit" />
                              <span className="fs-gl-cell fs-gl-source" />
                            </>
                          ) : (
                            <>
                              <span className="fs-gl-cell fs-gl-debit">{row.values.debit || ""}</span>
                              <span className="fs-gl-cell fs-gl-credit">{row.values.credit || ""}</span>
                              <span className="fs-gl-cell fs-gl-source">{row.values.source || ""}</span>
                            </>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="fs-section-empty">No GL journals yet</div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Drag handle */}
        <div
          ref={splitRef}
          className={`fs-handle ${dragging ? "fs-handle--active" : ""}`}
          onMouseDown={handleMouseDown}
        />
        </>)}

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
                  } else if (result.cash_id) {
                    setRightModel("cash");
                    setRightRecordId(result.cash_id);
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

      {/* vCard import dialog */}
      {showVcardImport && (
        <Suspense fallback={null}>
          <VCardImportDialog
            isOpen={showVcardImport}
            onClose={() => setShowVcardImport(false)}
            onImported={(contactId) => {
              setShowVcardImport(false);
              setRightModel('contact');
              setRightRecordId(contactId);
            }}
          />
        </Suspense>
      )}
    </div>
  );
};

export default FlightSimConsole;
