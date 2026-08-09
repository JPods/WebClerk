import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAppSelector } from "../../store/hooks";
import { getRecords } from "../../api/wcapi";
import DataGrid from "@/components/common/DataGrid";
import ToolbarIcon from "@/components/common/ToolbarIcon";
import { TB } from "@/components/common/toolbarActions";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

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
  { label: "+ Order", to: "/order?action=new", accent: "bg-blue-600 text-white" },
  { label: "+ Proposal", to: "/proposal?action=new", accent: "bg-indigo-600 text-white" },
  { label: "+ Purchase", to: "/purchase?action=new", accent: "bg-emerald-600 text-white" },
  { label: "+ Customer", to: "/customer?action=new", accent: "bg-amber-600 text-white" },
  { label: "+ Contact", to: "/contact?action=new", accent: "bg-purple-600 text-white" },
  { label: "Payments", to: "/payment", accent: "bg-teal-600 text-white" },
  { label: "Expenses", to: "/payment?filter=type:expense", accent: "bg-rose-600 text-white" },
  { label: "Statements", to: "/statement_line", accent: "bg-orange-600 text-white" },
];

// Models to count for the signed-in user
const COUNT_MODELS: Omit<RecordCount, "count">[] = [
  { model: "contact", label: "Contacts", link: "/contact" },
  { model: "customer", label: "Customers", link: "/customer" },
  { model: "proposal", label: "Proposals", link: "/proposal" },
  { model: "order", label: "Orders", link: "/order" },
  { model: "invoice", label: "Invoices", link: "/invoice" },
  { model: "purchase", label: "Purchases", link: "/purchase" },
];

// Action list columns — action with related entity detail
const ACTION_COLUMNS = [
  "ida",
  "action_en",
  "status",
  "kanban_column",
  "priority",
  "project_name",
  "contact_name",
  "company",
  "dt_deadline",
  "percent_complete",
];

// ---------------------------------------------------------------------------
// StaffPicker — compact multi-select for staff members
// ---------------------------------------------------------------------------

function StaffPicker({
  members,
  selected,
  onToggle,
  onSelectAll,
  onSelectNone,
}: {
  members: { id: number; name: string }[];
  selected: Set<number>;
  onToggle: (id: number) => void;
  onSelectAll: () => void;
  onSelectNone: () => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const count = selected.size;
  const label = count === 0
    ? "Nobody"
    : count === members.length
      ? "Everyone"
      : count <= 2
        ? members.filter((m) => selected.has(m.id)).map((m) => m.name.split(" ")[0]).join(", ")
        : `${count} people`;

  // Hover preview — show names as tooltip
  const hoverText = members
    .filter((m) => selected.has(m.id))
    .map((m) => m.name)
    .join("\n") || "No one selected";

  return (
    <div ref={ref} style={{ position: "relative", display: "inline-flex" }}>
      <button
        onClick={() => setOpen(!open)}
        title={hoverText}
        style={{
          fontSize: 11, padding: "2px 8px", cursor: "pointer",
          background: open ? "var(--db-accent, #4a9eff)" : "var(--db-surface-alt, #f8f9fa)",
          color: open ? "#fff" : "var(--db-text, #495057)",
          border: `1px solid ${open ? "var(--db-accent, #4a9eff)" : "var(--db-border, #dee2e6)"}`,
          borderRadius: 3, whiteSpace: "nowrap",
        }}
      >
        {label} ▾
      </button>
      {open && (
        <div style={{
          position: "absolute", top: "100%", left: 0, zIndex: 100,
          marginTop: 2, minWidth: 180, maxHeight: 300, overflowY: "auto",
          background: "var(--db-surface, #fff)", border: "1px solid var(--db-border, #dee2e6)",
          borderRadius: 4, boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
        }}>
          {/* All / None header */}
          <div style={{
            display: "flex", gap: 8, padding: "4px 8px",
            borderBottom: "1px solid var(--db-border, #dee2e6)",
            fontSize: 10, color: "var(--db-text-muted, #6c757d)",
          }}>
            <button onClick={onSelectAll}
              style={{ background: "none", border: "none", cursor: "pointer", color: "inherit", textDecoration: "underline", fontSize: 10 }}>
              all
            </button>
            <button onClick={onSelectNone}
              style={{ background: "none", border: "none", cursor: "pointer", color: "inherit", textDecoration: "underline", fontSize: 10 }}>
              none
            </button>
            <span style={{ flex: 1 }} />
            <span>{count}/{members.length}</span>
          </div>
          {/* Staff list */}
          {members.map((s) => {
            const active = selected.has(s.id);
            return (
              <label
                key={s.id}
                style={{
                  display: "flex", alignItems: "center", gap: 6,
                  padding: "3px 8px", cursor: "pointer", fontSize: 11,
                  background: active ? "var(--db-accent-bg, #e8f0fe)" : "transparent",
                  color: "var(--db-text, #495057)",
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = active ? "var(--db-accent-bg, #d0e3fc)" : "var(--db-surface-alt, #f8f9fa)")}
                onMouseLeave={(e) => (e.currentTarget.style.background = active ? "var(--db-accent-bg, #e8f0fe)" : "transparent")}
              >
                <input
                  type="checkbox"
                  checked={active}
                  onChange={() => onToggle(s.id)}
                  style={{ margin: 0, accentColor: "var(--db-accent, #4a9eff)" }}
                />
                {s.name}
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Date range presets
// ---------------------------------------------------------------------------

type DatePreset = "today" | "yesterday" | "tomorrow" | "this_week" | "last_week" | "next_week" | "between" | "all";

const DATE_PRESETS: { value: DatePreset; label: string }[] = [
  { value: "all", label: "All" },
  { value: "today", label: "Today" },
  { value: "yesterday", label: "Yesterday" },
  { value: "tomorrow", label: "Tomorrow" },
  { value: "this_week", label: "This Week" },
  { value: "last_week", label: "Last Week" },
  { value: "next_week", label: "Next Week" },
  { value: "between", label: "Between..." },
];

function startOfDay(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

function dateRangeForPreset(preset: DatePreset): { from: number; to: number } | null {
  const now = new Date();
  const today = startOfDay(now);
  const oneDay = 86400000;
  const dow = now.getDay(); // 0=Sun
  const mondayOffset = dow === 0 ? -6 : 1 - dow;

  switch (preset) {
    case "today":
      return { from: today, to: today + oneDay - 1 };
    case "yesterday":
      return { from: today - oneDay, to: today - 1 };
    case "tomorrow":
      return { from: today + oneDay, to: today + 2 * oneDay - 1 };
    case "this_week": {
      const mon = today + mondayOffset * oneDay;
      return { from: mon, to: mon + 7 * oneDay - 1 };
    }
    case "last_week": {
      const mon = today + (mondayOffset - 7) * oneDay;
      return { from: mon, to: mon + 7 * oneDay - 1 };
    }
    case "next_week": {
      const mon = today + (mondayOffset + 7) * oneDay;
      return { from: mon, to: mon + 7 * oneDay - 1 };
    }
    case "all":
    case "between":
    default:
      return null;
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Extract action title from the multilingual action JSON */
function actionTitle(action: any): string {
  if (!action) return "";
  if (typeof action === "string") return action;
  if (typeof action === "object") return action.en || action.bn || action.ar || "";
  return String(action);
}

/** Flatten an action record for grid display — denormalize related entity info from refs.links */
function flattenAction(rec: any): any {
  const action_en = actionTitle(rec.action);
  const refs = rec.refs || {};
  const links = refs.links || {};

  // Collect related entity summaries from refs.links
  const related: string[] = [];
  for (const [model, ids] of Object.entries(links)) {
    if (!Array.isArray(ids) || ids.length === 0) continue;
    if (model === "contact" || model === "item") continue; // skip standard link buckets
    const count = ids.length;
    const label = model.charAt(0).toUpperCase() + model.slice(1);
    related.push(count === 1 ? `${label} #${ids[0]}` : `${count} ${label}s`);
  }

  // Contact name from assigned_to
  let contact_name = "";
  if (rec.assigned_to && Array.isArray(rec.assigned_to) && rec.assigned_to.length > 0) {
    const first = rec.assigned_to[0];
    contact_name = typeof first === "object" ? (first.name || first.email || "") : String(first);
  }

  // Company from project or first linked customer/org
  const company = rec.project_name || rec.company || "";

  return {
    ...rec,
    action_en,
    contact_name,
    company,
    related: related.join(", "),
  };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function Home() {
  const { user } = useAppSelector((state) => state.auth);
  const navigate = useNavigate();
  const [actions, setActions] = useState<any[]>([]);
  const [counts, setCounts] = useState<RecordCount[]>([]);
  const [loadingActions, setLoadingActions] = useState(false);
  const [loadingCounts, setLoadingCounts] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [datePreset, setDatePreset] = useState<DatePreset>("all");
  const [customFrom, setCustomFrom] = useState(() => {
    const d = new Date(); d.setDate(d.getDate() - 1);
    return d.toISOString().slice(0, 10);
  });
  const [customTo, setCustomTo] = useState(() => {
    const d = new Date(); d.setDate(d.getDate() + 7);
    return d.toISOString().slice(0, 10);
  });
  const [selectedStaffIds, setSelectedStaffIds] = useState<Set<number>>(() => new Set(user?.id ? [user.id] : []));
  const [staffMembers, setStaffMembers] = useState<{ id: number; name: string }[]>([]);
  const [projects, setProjects] = useState<{ id: number; name: string }[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [subsetMode, setSubsetMode] = useState<"all" | "show" | "omit">("all");

  // Fetch staff members and active projects
  const fetchStaff = useCallback(async () => {
    try {
      const res = await getRecords("contact", { is_staff: true, is_active: true, limit: 100, ordering: "attention" });
      const members = (res?.results ?? []).map((c: any) => ({
        id: c.id,
        name: c.attention || c.name_first || c.email || `#${c.id}`,
      }));
      setStaffMembers(members);
    } catch { /* silent */ }
  }, []);

  const fetchProjects = useCallback(async () => {
    try {
      const res = await getRecords("project", { is_active: true, limit: 100, ordering: "name" });
      const items = (res?.results ?? []).map((p: any) => ({
        id: p.id,
        name: p.name || p.ida || `#${p.id}`,
      }));
      setProjects(items);
    } catch { /* silent */ }
  }, []);

  useEffect(() => { fetchStaff(); fetchProjects(); }, [fetchStaff, fetchProjects]);

  const toggleStaff = useCallback((id: number) => {
    setSelectedStaffIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }, []);

  const selectAllStaff = useCallback(() => {
    setSelectedStaffIds(new Set(staffMembers.map((s) => s.id)));
  }, [staffMembers]);

  const selectNone = useCallback(() => {
    setSelectedStaffIds(new Set());
  }, []);

  // Fetch active actions with optional date filtering on dt_deadline
  const fetchActions = useCallback(async () => {
    setLoadingActions(true);
    try {
      const params: Record<string, any> = {
        is_active: true,
        ordering: "-priority,-dt_deadline",
        limit: 500,
      };

      // Owner filter — selected staff ids
      if (selectedStaffIds.size === 1) {
        params.contact_id = Array.from(selectedStaffIds)[0];
      } else if (selectedStaffIds.size > 1) {
        params.contact_id__in = Array.from(selectedStaffIds).join(",");
      }
      // size 0 = show all (no filter)

      // Project filter
      if (selectedProjectId) {
        params.project_id = selectedProjectId;
      }

      // Apply date range filter on dt_deadline
      if (datePreset === "between" && customFrom && customTo) {
        params.dt_deadline__gte = new Date(customFrom).getTime();
        params.dt_deadline__lte = new Date(customTo).getTime() + 86400000 - 1;
      } else if (datePreset !== "all") {
        const range = dateRangeForPreset(datePreset);
        if (range) {
          params.dt_deadline__gte = range.from;
          params.dt_deadline__lte = range.to;
        }
      }

      const res = await getRecords("action", params);
      setActions((res?.results ?? []).map(flattenAction));
    } catch (err) {
      console.error("[Dashboard] Failed to fetch actions:", err);
    } finally {
      setLoadingActions(false);
    }
  }, [datePreset, customFrom, customTo, selectedStaffIds, selectedProjectId]);

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
    fetchActions();
    fetchCounts();
  }, [fetchActions, fetchCounts]);

  const gridColumns = useMemo(() => ACTION_COLUMNS, []);

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

      {/* Actions list — standard db.list toolbar + DataGrid */}
      <section className="min-h-0 flex-1 rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-900">
        <div className="flex h-full flex-col">
          {/* Standard db.list toolbar */}
          <div className="db-toolbar-row" style={{ display: "flex", alignItems: "center", gap: 4, padding: "2px 6px", borderBottom: "1px solid var(--db-border, #dee2e6)" }}>
            <div className="db-list-toolbar" style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <ToolbarIcon action={TB.filter} title="Filter" active={showFilters} onClick={() => setShowFilters(!showFilters)} />
              <ToolbarIcon action={TB.showAll} title="Show All" onClick={() => { setSubsetMode("all"); selectAllStaff(); setDatePreset("all"); }} />
              <ToolbarIcon action={TB.showSubset} title="Show Selected" active={subsetMode === "show"} onClick={() => setSubsetMode(subsetMode === "show" ? "all" : "show")} />
              <ToolbarIcon action={TB.omit} title="Omit Selected" active={subsetMode === "omit"} onClick={() => setSubsetMode(subsetMode === "omit" ? "all" : "omit")} />
              <ToolbarIcon action={TB.sort} title="Sort" onClick={() => {}} />
              <ToolbarIcon action={TB.print} title="Reports" onClick={() => window.print()} />
            </div>
            {/* Period */}
            <span style={{ width: 1, height: 16, background: "var(--db-border, #dee2e6)", margin: "0 2px" }} />
            <select
              value={datePreset}
              onChange={(e) => setDatePreset(e.target.value as DatePreset)}
              style={{ fontSize: 11, padding: "2px 4px", background: "var(--db-surface-alt, #f8f9fa)", color: "var(--db-text, #495057)", border: "1px solid var(--db-border, #dee2e6)", borderRadius: 3, cursor: "pointer" }}
            >
              {DATE_PRESETS.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>
            {datePreset === "between" && (
              <>
                <input type="date" value={customFrom} onChange={(e) => setCustomFrom(e.target.value)}
                  style={{ fontSize: 11, padding: "2px 4px", border: "1px solid var(--db-border, #dee2e6)", borderRadius: 3 }} />
                <span style={{ fontSize: 11, color: "var(--db-text-muted, #6c757d)" }}>to</span>
                <input type="date" value={customTo} onChange={(e) => setCustomTo(e.target.value)}
                  style={{ fontSize: 11, padding: "2px 4px", border: "1px solid var(--db-border, #dee2e6)", borderRadius: 3 }} />
              </>
            )}

            {/* Project */}
            <span style={{ width: 1, height: 16, background: "var(--db-border, #dee2e6)", margin: "0 2px" }} />
            <select
              value={selectedProjectId ?? ""}
              onChange={(e) => setSelectedProjectId(e.target.value ? Number(e.target.value) : null)}
              style={{ fontSize: 11, padding: "2px 4px", background: "var(--db-surface-alt, #f8f9fa)", color: "var(--db-text, #495057)", border: "1px solid var(--db-border, #dee2e6)", borderRadius: 3, cursor: "pointer" }}
            >
              <option value="">All Projects</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>

            {/* People */}
            <span style={{ width: 1, height: 16, background: "var(--db-border, #dee2e6)", margin: "0 2px" }} />
            <StaffPicker
              members={staffMembers}
              selected={selectedStaffIds}
              onToggle={toggleStaff}
              onSelectAll={selectAllStaff}
              onSelectNone={selectNone}
            />

            <span style={{ flex: 1 }} />
            <span style={{ fontSize: 11, color: "var(--db-text-muted, #6c757d)" }}>
              {loadingActions ? "Loading..." : `${actions.length} actions`}
            </span>
          </div>
          <DataGrid
            records={actions}
            columns={gridColumns}
            selectedId={selectedId}
            hideToolbar
            onSelectRecord={(id) => {
              setSelectedId(id);
              navigate(`/action/${id}`);
            }}
            sort={{ field: "priority", direction: "desc" }}
          />
        </div>
      </section>
    </div>
  );
}
