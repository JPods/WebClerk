/**
 * FlightSimConsole -- Flight Simulator training page.
 *
 * Left:  Inventory ledger — columns are quantity buckets, rows grow as user
 *        creates transactions. Shows transaction delta → pending → item.quantity.
 * Right: UiDetail — the actual transaction form. User picks which transaction
 *        to create via buttons at top. After save, ledger refreshes from DB.
 *
 * The user drives — buttons at top let them choose: Add Proposal, Add Order,
 * Add Invoice, Add Purchase, Add Work Order, Add Payment. The scripted scenario
 * provides coaching guidance, not rigid control.
 *
 * LastChecked: 2026-08-16 | WhereUsed: /flight-sim/* | WhoCreated: Bill+Claude
 */
import React, { useEffect, useState, useCallback, useRef, Suspense } from "react";
import PageMeta from "@/components/common/PageMeta";
import { manageAction, saveRecord } from "../../api/wcapi";
import {
  FaPlus, FaSync, FaClipboardList, FaShoppingCart, FaFileInvoice,
  FaTruck, FaWrench, FaDollarSign, FaBoxOpen,
} from "react-icons/fa";

const UiDetail = React.lazy(() => import("../../apps/transactions/components/TransactionDetail"));

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface GlEntry {
  account: string;
  side: "debit" | "credit";
  amount: number;
  purpose: string;
}

/** One row in the ledger */
interface LedgerRow {
  type: "state" | "transaction" | "pending";
  label: string;
  values: Record<string, number | string>;
  gl?: GlEntry[];
  model?: string;
  record_id?: number;
}

interface LiveLedger {
  columns: string[];
  rows: LedgerRow[];
  item: {
    id: number;
    ida: string;
    name: string;
    quantity: Record<string, number>;
  };
  line_count: number;
  pending_count: number;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const COLUMNS = ["on_hand", "on_so", "on_po", "on_p", "on_wo", "available"];

const COLUMN_LABELS: Record<string, string> = {
  on_hand: "On Hand",
  on_so: "On SO",
  on_po: "On PO",
  on_p: "On Prop",
  on_wo: "On WO",
  available: "Available",
};

/** Transaction types the user can create */
const TRANSACTION_BUTTONS = [
  { model: "proposal", label: "Proposal", icon: <FaClipboardList size={11} />, color: "bg-blue-600 hover:bg-blue-700" },
  { model: "order", label: "Order", icon: <FaShoppingCart size={11} />, color: "bg-indigo-600 hover:bg-indigo-700" },
  { model: "invoice", label: "Invoice", icon: <FaFileInvoice size={11} />, color: "bg-green-600 hover:bg-green-700" },
  { model: "purchase", label: "Purchase", icon: <FaTruck size={11} />, color: "bg-orange-600 hover:bg-orange-700" },
  { model: "receipt", label: "Receive", icon: <FaBoxOpen size={11} />, color: "bg-teal-600 hover:bg-teal-700" },
  { model: "work_order", label: "Work Order", icon: <FaWrench size={11} />, color: "bg-purple-600 hover:bg-purple-700" },
  { model: "payment", label: "Payment", icon: <FaDollarSign size={11} />, color: "bg-emerald-600 hover:bg-emerald-700" },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatCell(v: number | string | undefined): string {
  if (v === undefined || v === null) return "";
  if (typeof v === "number") return v.toString();
  return String(v);
}

/* ------------------------------------------------------------------ */
/*  Item Picker                                                        */
/* ------------------------------------------------------------------ */

const ItemPicker: React.FC<{
  itemId: number | null;
  onSelect: (id: number, ida: string) => void;
}> = ({ itemId, onSelect }) => {
  const [search, setSearch] = useState("");
  const [searching, setSearching] = useState(false);

  const handleSearch = async () => {
    if (!search.trim()) return;
    setSearching(true);
    try {
      const res = await manageAction("get_item_flight_state", { item_id: parseInt(search) || 0 });
      const data = res?.data?.data ?? res?.data ?? res;
      if (data?.item?.id) {
        onSelect(data.item.id, data.item.ida);
      }
    } catch { /* ignore */ }
    finally { setSearching(false); }
  };

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-500">Item ID:</span>
      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && handleSearch()}
        placeholder="Enter item ID"
        className="w-24 px-2 py-1 text-sm border border-gray-300 rounded font-mono focus:outline-none focus:ring-1 focus:ring-blue-400"
      />
      <button onClick={handleSearch} disabled={searching}
        className="px-2 py-1 text-xs bg-gray-200 rounded hover:bg-gray-300 transition-colors">
        {searching ? "..." : "Load"}
      </button>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  Ledger Table                                                       */
/* ------------------------------------------------------------------ */

const LedgerTable: React.FC<{
  rows: LedgerRow[];
  onClickRow?: (row: LedgerRow) => void;
}> = ({ rows, onClickRow }) => {
  return (
    <div className="overflow-y-auto h-full">
      <table className="w-full text-xs border-collapse">
        <thead className="sticky top-0 z-10">
          <tr className="bg-gray-800 text-white">
            <th className="text-left p-2 min-w-[140px] font-medium">Event</th>
            {COLUMNS.map((col) => (
              <th key={col} className="p-2 text-right min-w-[60px] font-medium">
                {COLUMN_LABELS[col] || col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => {
            let bgClass = "";
            let borderClass = "";
            let textClass = "text-gray-700";

            if (row.type === "state") {
              bgClass = "bg-white";
              borderClass = "border-l-3 border-l-gray-300";
              textClass = "text-gray-900 font-semibold";
            } else if (row.type === "transaction") {
              bgClass = "bg-blue-50";
              borderClass = "border-l-3 border-l-blue-500";
              textClass = "text-blue-800";
            } else if (row.type === "pending") {
              bgClass = "bg-amber-50";
              borderClass = "border-l-3 border-l-amber-400";
              textClass = "text-amber-800";
            }

            const clickable = row.type === "transaction" && row.record_id;

            return (
              <React.Fragment key={idx}>
                <tr
                  className={`${bgClass} ${borderClass} border-b border-gray-100
                    ${clickable ? "cursor-pointer hover:brightness-90" : "hover:brightness-95"} transition-colors`}
                  onClick={() => clickable && onClickRow?.(row)}
                >
                  <td className={`p-2 ${textClass} whitespace-nowrap`}>
                    <div className="flex items-center gap-1">
                      {row.type === "pending" && <span className="text-amber-400 text-[10px]">&#9679;</span>}
                      {row.type === "state" && <span className="text-gray-300 text-[10px]">&#9632;</span>}
                      {row.label}
                    </div>
                  </td>
                  {COLUMNS.map((col) => {
                    const val = row.values[col];
                    const display = formatCell(val);
                    const isPositive = typeof val === "string" && val.startsWith("+");
                    const isNegative = typeof val === "string" && val.startsWith("-");
                    const cellColor = isPositive ? "text-green-700 font-bold"
                      : isNegative ? "text-red-600 font-bold"
                      : row.type === "state" ? "text-gray-900 font-mono"
                      : "text-gray-500";

                    return (
                      <td key={col} className={`p-2 text-right font-mono ${cellColor}`}>
                        {display}
                      </td>
                    );
                  })}
                </tr>

                {/* GL entries — compact line under transaction rows */}
                {row.gl && row.gl.length > 0 && (
                  <tr className="bg-slate-50">
                    <td colSpan={COLUMNS.length + 1} className="px-4 py-1">
                      <div className="flex flex-wrap gap-3 text-[10px] text-gray-500">
                        {row.gl.map((e, gi) => (
                          <span key={gi} className="font-mono">
                            <span className={e.side === "debit" ? "text-blue-600" : "text-green-600"}>
                              {e.side === "debit" ? "DR" : "CR"}
                            </span>
                            {" "}{e.account.split("-").slice(-2, -1)[0]} ${e.amount.toFixed(2)}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

interface FlightSimConsoleProps {
  scenarioAction?: string;
  title?: string;
  description?: string;
}

const FlightSimConsole: React.FC<FlightSimConsoleProps> = ({
  title = "Flight Simulator: Transaction Lifecycle",
  description = "Pick an item, create transactions, watch inventory and GL change in real time.",
}) => {
  // Split position (left panel width in pixels)
  const [splitWidth, setSplitWidth] = useState(480);
  const [dragging, setDragging] = useState(false);

  // Item being tracked
  const [itemId, setItemId] = useState<number | null>(null);
  const [itemIda, setItemIda] = useState<string>("");

  // Ledger data from backend
  const [ledger, setLedger] = useState<LiveLedger | null>(null);
  const [ledgerLoading, setLedgerLoading] = useState(false);

  // Right panel — which transaction is being viewed/edited
  const [rightModel, setRightModel] = useState<string | null>(null);
  const [rightRecordId, setRightRecordId] = useState<number>(0);
  const [creating, setCreating] = useState<string | null>(null); // model being created

  /** Drag-to-resize split */
  const splitRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = useCallback(() => {
    setDragging(true);
  }, []);

  useEffect(() => {
    if (!dragging) return;
    const handleMouseMove = (e: MouseEvent) => {
      const container = splitRef.current?.parentElement;
      if (!container) return;
      const rect = container.getBoundingClientRect();
      const newWidth = Math.max(200, Math.min(e.clientX - rect.left, rect.width - 200));
      setSplitWidth(newWidth);
    };
    const handleMouseUp = () => setDragging(false);
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [dragging]);

  /** Fetch ledger from backend */
  const refreshLedger = useCallback(async () => {
    if (!itemId) return;
    setLedgerLoading(true);
    try {
      const res = await manageAction("get_flight_ledger", { item_id: itemId });
      const data = res?.data?.data ?? res?.data ?? res;
      if (data && !data.error) {
        setLedger(data as LiveLedger);
      }
    } catch (e) {
      console.error("Ledger refresh failed:", e);
    } finally {
      setLedgerLoading(false);
    }
  }, [itemId]);

  // Refresh ledger when item changes
  useEffect(() => { if (itemId) refreshLedger(); }, [itemId, refreshLedger]);

  /** Create a new transaction record and open it on the right */
  const handleAddTransaction = async (model: string) => {
    setCreating(model);
    try {
      const blank: any = {
        model_name: model,
        is_active: true,
        metadata: { training: true },
        status: 'draft',
      };
      const result = await saveRecord(model, blank) as any;
      const newId = result?.data?.id || result?.id || result?.data?.record?.id;
      if (newId) {
        setRightModel(model);
        setRightRecordId(newId);
      }
    } catch (e) {
      console.error(`Failed to create ${model}:`, e);
    } finally {
      setCreating(null);
    }
  };

  /** When user clicks a transaction row in the ledger, open it on the right */
  const handleLedgerRowClick = (row: LedgerRow) => {
    if (row.model && row.record_id) {
      setRightModel(row.model);
      setRightRecordId(row.record_id);
    }
  };

  /** Item selected */
  const handleItemSelect = (id: number, ida: string) => {
    setItemId(id);
    setItemIda(ida);
    setRightModel(null);
    setRightRecordId(0);
  };

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <>
      <PageMeta title={title} description={description} />

      <div className="flex flex-col h-screen">
        {/* Header */}
        <div className="bg-gray-800 text-white px-6 py-3 flex items-center justify-between shrink-0">
          <h1 className="text-lg font-semibold">{title}</h1>
          {ledger && (
            <span className="text-gray-300 text-sm">
              {ledger.item.ida} — {ledger.line_count} transactions, {ledger.pending_count} pending
            </span>
          )}
        </div>

        {/* Toolbar */}
        <div className="shrink-0 border-b border-gray-300 bg-gray-50 px-4 py-2.5">
          <div className="flex items-center gap-3 flex-wrap">
            {/* Item picker */}
            <ItemPicker itemId={itemId} onSelect={handleItemSelect} />

            {itemId && (
              <>
                <div className="w-px h-5 bg-gray-300" />

                {/* Transaction buttons */}
                {TRANSACTION_BUTTONS.map((btn) => (
                  <button
                    key={btn.model}
                    onClick={() => handleAddTransaction(btn.model)}
                    disabled={creating !== null}
                    className={`px-2.5 py-1 rounded text-xs font-medium text-white transition-colors
                      flex items-center gap-1 ${btn.color}
                      ${creating === btn.model ? "opacity-50" : ""}`}
                  >
                    {creating === btn.model ? "..." : btn.icon}
                    {btn.label}
                  </button>
                ))}

                <div className="w-px h-5 bg-gray-300" />

                {/* Refresh */}
                <button onClick={refreshLedger} disabled={ledgerLoading}
                  className="px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-100 transition-colors flex items-center gap-1 text-gray-600">
                  <FaSync size={10} className={ledgerLoading ? "animate-spin" : ""} /> Refresh
                </button>
              </>
            )}
          </div>
        </div>

        {/* Main content — left/right split with draggable divider */}
        <div className={`flex flex-1 min-h-0 ${dragging ? "select-none cursor-col-resize" : ""}`}>

          {/* Left panel — Inventory Ledger */}
          <div className="shrink-0 flex flex-col" style={{ width: splitWidth }}>
            {ledger && ledger.rows.length > 0 ? (
              <LedgerTable rows={ledger.rows} onClickRow={handleLedgerRowClick} />
            ) : itemId ? (
              <div className="flex items-center justify-center h-full text-gray-400 text-sm">
                {ledgerLoading ? "Loading ledger..." : "No transactions yet — create one above"}
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400 text-sm">
                Enter an item ID to begin
              </div>
            )}
          </div>

          {/* Drag handle */}
          <div
            ref={splitRef}
            onMouseDown={handleMouseDown}
            className={`w-1.5 shrink-0 cursor-col-resize transition-colors
              ${dragging ? "bg-blue-400" : "bg-gray-200 hover:bg-blue-300"}`}
          />

          {/* Right panel — Transaction Form */}
          <div className="flex-1 min-w-0 overflow-y-auto bg-white">
            {rightModel && rightRecordId > 0 ? (
              <Suspense fallback={<div className="p-8 text-gray-400">Loading {rightModel}...</div>}>
                <UiDetail
                  modelName={rightModel}
                  recordId={rightRecordId}
                  inline
                />
              </Suspense>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400">
                <div className="text-center max-w-md">
                  {itemId ? (
                    <>
                      <p className="text-lg mb-2">Create a transaction</p>
                      <p className="text-sm">
                        Use the buttons above to add a Proposal, Order, Invoice, or other transaction.
                        The ledger on the left will show how each transaction affects inventory quantities and GL accounts.
                      </p>
                    </>
                  ) : (
                    <>
                      <p className="text-lg mb-2">Flight Simulator</p>
                      <p className="text-sm">{description}</p>
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
};

export default FlightSimConsole;
