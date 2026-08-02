import { useEffect, useState, useCallback, useMemo } from "react";
import { Link } from "react-router-dom";
import { useAppSelector } from "../../store/hooks";
import { getRecords } from "../../api/wcapi";
import DataGrid from "@/components/common/DataGrid";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ServiceRecord {
  id: number;
  tableName: string;
  actionBy?: string;
  action?: string;
  action_en?: string;
  actionDate?: string;
  due_date?: string;
  company?: string;
  attention?: string;
  contact_name?: string;
  variable?: string;
  notes?: string;
  priority?: string;
  status?: string;
  project_name?: string;
  [k: string]: any;
}

interface RecordCount {
  model: string;
  label: string;
  count: number;
  link: string;
}

// ---------------------------------------------------------------------------
// Quick Add shortcuts
// ---------------------------------------------------------------------------

const QUICK_ADDS = [
  { label: "+ Order", to: "/admin-wb?model=order&action=new", accent: "bg-blue-600 text-white" },
  { label: "+ Proposal", to: "/admin-wb?model=proposal&action=new", accent: "bg-indigo-600 text-white" },
  { label: "+ Purchase", to: "/admin-wb?model=purchase&action=new", accent: "bg-emerald-600 text-white" },
  { label: "+ Customer", to: "/admin-wb?model=customer&action=new", accent: "bg-amber-600 text-white" },
  { label: "+ Contact", to: "/admin-wb?model=contact&action=new", accent: "bg-purple-600 text-white" },
  { label: "Payments", to: "/db/payment", accent: "bg-teal-600 text-white" },
  { label: "Expenses", to: "/db/payment?filter=type:expense", accent: "bg-rose-600 text-white" },
  { label: "Statements", to: "/db/statement_line", accent: "bg-orange-600 text-white" },
];

// Tables to query for the user's action records (mirrors wc2 Cal_SearchMySales)
const ACTION_TABLES = [
  { model: "order", label: "Orders" },
  { model: "invoice", label: "Invoices" },
  { model: "proposal", label: "Proposals" },
  { model: "customer", label: "Customers" },
  { model: "purchase", label: "Purchases" },
  { model: "contact", label: "Contacts" },
];

// Models to count for the signed-in user
const COUNT_MODELS: Omit<RecordCount, "count">[] = [
  { model: "contact", label: "Contacts", link: "/admin-wb?model=contact" },
  { model: "customer", label: "Customers", link: "/admin-wb?model=customer" },
  { model: "proposal", label: "Proposals", link: "/admin-wb?model=proposal" },
  { model: "order", label: "Orders", link: "/admin-wb?model=order" },
  { model: "invoice", label: "Invoices", link: "/admin-wb?model=invoice" },
  { model: "purchase", label: "Purchases", link: "/admin-wb?model=purchase" },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function daysAgoISO(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function Home() {
  const { user } = useAppSelector((state) => state.auth);
  const [serviceRecords, setServiceRecords] = useState<ServiceRecord[]>([]);
  const [counts, setCounts] = useState<RecordCount[]>([]);
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [loadingCounts, setLoadingCounts] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [dateRange, setDateRange] = useState({ begin: daysAgoISO(7), end: todayISO() });

  // Fetch action records across all tables for the current user
  const fetchServiceRecords = useCallback(async () => {
    if (!user?.id) return;
    setLoadingRecords(true);
    try {
      const results = await Promise.all(
        ACTION_TABLES.map(async (table) => {
          try {
            const res = await getRecords(table.model, {
              contact_id: user.id,
              is_active: true,
              action_date__gte: dateRange.begin,
              action_date__lte: dateRange.end,
              limit: 200,
            });
            const records = (res?.results ?? []).map((r: any) => ({
              ...r,
              tableName: table.label,
              actionDate: r.action_date || r.due_date || r.created_at || "",
              company: r.company || r.contact_name || r.customer_name || "",
              attention: r.attention || r.contact_name || "",
              variable: r.notes || r.description || r.comment || "",
            }));
            return records;
          } catch {
            return [];
          }
        })
      );
      const merged = results.flat().sort((a, b) => {
        const da = a.actionDate || "";
        const db = b.actionDate || "";
        return db.localeCompare(da); // newest first
      });
      setServiceRecords(merged);
    } catch (err) {
      console.error("[Dashboard] Failed to fetch service records:", err);
    } finally {
      setLoadingRecords(false);
    }
  }, [user?.id, dateRange]);

  // Also fetch open actions specifically assigned to user
  const [myActions, setMyActions] = useState<ServiceRecord[]>([]);
  const fetchMyActions = useCallback(async () => {
    if (!user?.id) return;
    try {
      const res = await getRecords("action", {
        contact_id: user.id,
        is_active: true,
        limit: 500,
      });
      setMyActions(res?.results ?? []);
    } catch (err) {
      console.error("[Dashboard] Failed to fetch actions:", err);
    }
  }, [user?.id]);

  // Fetch record counts for models where user appears
  const fetchCounts = useCallback(async () => {
    if (!user?.id) return;
    setLoadingCounts(true);
    try {
      const results = await Promise.all(
        COUNT_MODELS.map(async (m) => {
          try {
            const res = await getRecords(m.model, {
              contact_id: user.id,
              is_active: true,
              limit: 1,
            });
            return { ...m, count: res?.total ?? 0 };
          } catch {
            return { ...m, count: 0 };
          }
        })
      );
      setCounts(results);
    } catch (err) {
      console.error("[Dashboard] Failed to fetch counts:", err);
    } finally {
      setLoadingCounts(false);
    }
  }, [user?.id]);

  useEffect(() => {
    fetchServiceRecords();
    fetchMyActions();
    fetchCounts();
  }, [fetchServiceRecords, fetchMyActions, fetchCounts]);

  // Columns for the bottom DataGrid (mirrors wc2 LB_Service listbox)
  const gridColumns = useMemo(() => [
    "tableName",
    "actionBy",
    "action_en",
    "actionDate",
    "company",
    "attention",
    "variable",
    "id",
  ], []);

  // Combine actions + service records for the grid
  const gridRecords = useMemo(() => {
    const actionRows = myActions.map((a: any) => ({
      ...a,
      tableName: "Action",
      actionDate: a.due_date || a.action_date || a.created_at || "",
      company: a.project_name || "",
      attention: a.contact_name || "",
      variable: a.notes || a.action_en || "",
      actionBy: a.assignee_name || a.contact_name || "",
    }));
    return [...actionRows, ...serviceRecords];
  }, [myActions, serviceRecords]);

  const getActionTitle = (a: any): string => {
    if (a.action_en) return a.action_en;
    if (typeof a.action === "string") return a.action;
    if (a.action?.value?.en) return a.action.value.en;
    return `#${a.id}`;
  };

  return (
    <div className="flex h-full flex-col gap-4 p-4 lg:p-6">
      {/* Header row: greeting + quick adds */}
      <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
          {user?.name_first ? `${user.name_first}'s Sales & Service` : "Sales & Service"}
        </h1>
        <div className="flex flex-wrap gap-2">
          {QUICK_ADDS.map((qa) => (
            <Link
              key={qa.label}
              to={qa.to}
              className={`rounded-lg px-3 py-1.5 text-sm font-semibold shadow-sm transition hover:-translate-y-[1px] hover:shadow-md ${qa.accent}`}
            >
              {qa.label}
            </Link>
          ))}
        </div>
      </header>

      {/* Record counts row */}
      <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {(loadingCounts ? COUNT_MODELS.map((m) => ({ ...m, count: -1 })) : counts).map((item) => (
          <Link
            key={item.model}
            to={item.link}
            className="group rounded-xl border border-gray-200 bg-white p-3 text-center shadow-sm transition hover:-translate-y-[1px] hover:border-blue-300 hover:shadow-md dark:border-gray-700 dark:bg-gray-900 dark:hover:border-blue-500"
          >
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {item.count < 0 ? "…" : item.count}
            </p>
            <p className="text-xs font-medium text-gray-500 group-hover:text-blue-600 dark:text-gray-400">
              {item.label}
            </p>
          </Link>
        ))}
      </section>

      {/* Filter bar: date range */}
      <div className="flex flex-wrap items-center gap-3 rounded-lg border border-gray-200 bg-gray-50 px-4 py-2 dark:border-gray-700 dark:bg-gray-800">
        <label className="text-xs font-semibold text-gray-600 dark:text-gray-400">From</label>
        <input
          type="date"
          value={dateRange.begin}
          onChange={(e) => setDateRange((d) => ({ ...d, begin: e.target.value }))}
          className="rounded border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-white"
        />
        <label className="text-xs font-semibold text-gray-600 dark:text-gray-400">To</label>
        <input
          type="date"
          value={dateRange.end}
          onChange={(e) => setDateRange((d) => ({ ...d, end: e.target.value }))}
          className="rounded border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-900 dark:text-white"
        />
        <button
          onClick={() => { fetchServiceRecords(); fetchMyActions(); }}
          className="rounded-lg bg-blue-600 px-3 py-1 text-xs font-semibold text-white hover:bg-blue-700"
        >
          Refresh
        </button>
        <span className="ml-auto text-xs text-gray-500 dark:text-gray-400">
          {gridRecords.length} records
        </span>
      </div>

      {/* My Actions — link to standard DataBrowser */}
      <Link
        to="/db/action"
        className="flex items-center justify-between rounded-xl border border-gray-200 bg-white px-4 py-3 shadow-sm transition hover:-translate-y-[1px] hover:border-blue-300 hover:shadow-md dark:border-gray-700 dark:bg-gray-900 dark:hover:border-blue-500"
      >
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold text-gray-900 dark:text-white">My Actions</span>
          <span className="rounded-full bg-blue-100 px-2.5 py-0.5 text-sm font-semibold text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
            {myActions.length} open
          </span>
        </div>
        <span className="text-sm text-gray-400">Open in DataBrowser →</span>
      </Link>

      {/* DataBrowser (DataGrid) — bottom section, shows all action records across tables */}
      <section className="min-h-0 flex-1 rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-900">
        <div className="flex h-full flex-col">
          <div className="border-b border-gray-100 px-4 py-2 dark:border-gray-700">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              All Records — Sales & Service
            </h2>
          </div>
          <div className="flex-1 overflow-auto px-2 py-1">
            <DataGrid
              records={gridRecords}
              columns={gridColumns}
              selectedId={selectedId}
              onSelectRecord={(id) => setSelectedId(id)}
              sort={null}
            />
          </div>
        </div>
      </section>
    </div>
  );
}
