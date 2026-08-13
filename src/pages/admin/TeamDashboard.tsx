/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * TeamDashboard.tsx — Per-team-member insight dashboard.
 *
 * Fetches contacts grouped by `name_prefix` (each team member tags their
 * 3 contacts — customer/vendor/employee — with their first name).
 *
 * Shows four insight categories per member:
 *   1. Record Completeness — filled fields, linked records
 *   2. Activity & Actions  — last modified, version, recent actions
 *   3. API Usage           — UserDailyLog stats (calls, errors, hints)
 *   4. Org Health          — linked org summary
 *
 * Route: /core/team-dashboard
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bot,
  Briefcase,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Code2,
  Factory,
  Loader2,
  RefreshCw,
  ShieldCheck,
  Store,
  Truck,
  User,
  Users,
  XCircle,
  Zap,
} from "lucide-react";
import { getRecords } from "@/api/wcapi";
import { formatDt } from '@/utils/fieldFormatters';
import { fetchUserDailyLogs } from "../../apps/core/services/userDailyLogApi";
import type { UserDailyLog } from "../../apps/core/models/log/UserDailyLog";
import type { ContactApiTask } from "../../apps/core/models/contact/types/contactType";

/* ------------------------------------------------------------------ */
/*  Constants & Types                                                  */
/* ------------------------------------------------------------------ */

/** Fields checked for completeness scoring. */
const COMPLETENESS_FIELDS: (keyof ContactApiTask)[] = [
  "name_first",
  "name_last",
  "name_middle",
  "name_prefix",
  "name_suffix",
  "email",
  "company",
  "title",
  "department",
  "comment",
  "role",
];

/** Map FK field → human label + icon + colour */
const ORG_ROLE_MAP: Record<
  string,
  { label: string; purpose: string; color: string; bg: string }
> = {
  customer_id: {
    label: "Customer",
    purpose: "Testing",
    color: "text-blue-600 dark:text-blue-400",
    bg: "bg-blue-50 dark:bg-blue-900/30",
  },
  vendor_id: {
    label: "Vendor",
    purpose: "Testing",
    color: "text-amber-600 dark:text-amber-400",
    bg: "bg-amber-50 dark:bg-amber-900/30",
  },
  employee_id: {
    label: "Employee",
    purpose: "Development",
    color: "text-emerald-600 dark:text-emerald-400",
    bg: "bg-emerald-50 dark:bg-emerald-900/30",
  },
  manufacturer_id: {
    label: "Manufacturer",
    purpose: "Testing",
    color: "text-purple-600 dark:text-purple-400",
    bg: "bg-purple-50 dark:bg-purple-900/30",
  },
  rep_id: {
    label: "Rep",
    purpose: "Testing",
    color: "text-rose-600 dark:text-rose-400",
    bg: "bg-rose-50 dark:bg-rose-900/30",
  },
};

const ORG_ICON: Record<string, typeof Store> = {
  customer_id: Store,
  vendor_id: Truck,
  employee_id: Briefcase,
  manufacturer_id: Factory,
  rep_id: Users,
};

interface MemberGroup {
  name: string;
  contacts: ContactApiTask[];
  isAI: boolean;
}

interface OrgSummary {
  id: number;
  display_name?: string;
  org_type?: string;
  status?: string;
  is_active?: boolean;
  health_rating?: number;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function computeCompleteness(c: ContactApiTask): number {
  let filled = 0;
  for (const f of COMPLETENESS_FIELDS) {
    const val = c[f];
    if (val !== undefined && val !== null && val !== "") filled++;
  }
  // Bonus: check org FK links
  const orgFks = [
    "customer_id",
    "vendor_id",
    "employee_id",
    "manufacturer_id",
    "rep_id",
  ] as const;
  const hasOrg = orgFks.some(
    (k) => c[k as keyof ContactApiTask] !== null && c[k as keyof ContactApiTask] !== undefined,
  );
  if (hasOrg) filled++;

  // Bonus: check refs.links count
  const linksCount = countRefsLinks(c);
  if (linksCount > 0) filled++;

  const total = COMPLETENESS_FIELDS.length + 2; // +2 for org + links bonuses
  return Math.round((filled / total) * 100);
}

function countRefsLinks(c: ContactApiTask): number {
  const refs = c.refs as Record<string, unknown> | undefined;
  if (!refs) return 0;
  const links = refs.links as Record<string, unknown[]> | undefined;
  if (!links || typeof links !== "object") return 0;
  return Object.values(links).reduce(
    (sum, arr) => sum + (Array.isArray(arr) ? arr.length : 0),
    0,
  );
}

function getOrgAssociations(
  c: ContactApiTask,
): { fk: string; orgId: number }[] {
  const result: { fk: string; orgId: number }[] = [];
  const fks = [
    "customer_id",
    "vendor_id",
    "employee_id",
    "manufacturer_id",
    "rep_id",
  ];
  for (const fk of fks) {
    const val = c[fk as keyof ContactApiTask] as number | null | undefined;
    if (val) result.push({ fk, orgId: val });
  }
  return result;
}

function formatEpochMs(epoch?: number): string {
  if (!epoch) return "Never";
  return formatDt(epoch, 'datetime');
}

function completenessColor(pct: number): string {
  if (pct >= 80) return "text-emerald-600 dark:text-emerald-400";
  if (pct >= 50) return "text-amber-600 dark:text-amber-400";
  return "text-red-600 dark:text-red-400";
}

function completenessBg(pct: number): string {
  if (pct >= 80) return "bg-emerald-500";
  if (pct >= 50) return "bg-amber-500";
  return "bg-red-500";
}

const AI_NAMES = new Set(["copilot", "deepseek", "ollama", "ai"]);

/* ------------------------------------------------------------------ */
/*  Sub-Components                                                     */
/* ------------------------------------------------------------------ */

/** Single contact card within a member section */
function ContactCard({
  contact,
  orgMap,
  dailyLogs,
}: {
  contact: ContactApiTask;
  orgMap: Map<number, OrgSummary>;
  dailyLogs: UserDailyLog[];
}) {
  const [expanded, setExpanded] = useState(false);
  const pct = computeCompleteness(contact);
  const orgs = getOrgAssociations(contact);
  const linksCount = countRefsLinks(contact);

  // Actions summary
  const actions = contact.actions as Record<string, unknown> | undefined;
  const actionCount =
    actions && typeof actions === "object"
      ? Object.keys(actions).length
      : 0;

  // Health
  const health = contact.health_rating ?? 0;

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg bg-white dark:bg-gray-800 shadow-sm">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors rounded-t-lg"
      >
        <div className="flex items-center gap-3 min-w-0">
          {/* Org badge */}
          {orgs.map(({ fk }) => {
            const Icon = ORG_ICON[fk] ?? User;
            const meta = ORG_ROLE_MAP[fk];
            return (
              <span
                key={fk}
                className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${meta?.bg ?? ""} ${meta?.color ?? ""}`}
              >
                <Icon size={12} />
                {meta?.label}
                <span className="opacity-60">({meta?.purpose})</span>
              </span>
            );
          })}
          {orgs.length === 0 && (
            <span className="text-xs text-gray-400">No org link</span>
          )}

          <span className="font-medium text-gray-900 dark:text-gray-100 truncate">
            {contact.name_first} {contact.name_last}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {contact.email}
          </span>
        </div>

        <div className="flex items-center gap-4">
          {/* Completeness bar */}
          <div className="flex items-center gap-2">
            <div className="w-20 h-2 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${completenessBg(pct)}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className={`text-xs font-semibold ${completenessColor(pct)}`}>
              {pct}%
            </span>
          </div>

          {expanded ? (
            <ChevronDown size={16} className="text-gray-400" />
          ) : (
            <ChevronRight size={16} className="text-gray-400" />
          )}
        </div>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-gray-200 dark:border-gray-700 p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
          {/* 1. Record Completeness */}
          <div className="space-y-2">
            <h4 className="font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-1">
              <CheckCircle2 size={14} /> Record Completeness
            </h4>
            <div className="space-y-1 text-xs">
              {COMPLETENESS_FIELDS.map((f) => {
                const val = contact[f];
                const filled =
                  val !== undefined && val !== null && val !== "";
                return (
                  <div
                    key={f}
                    className="flex items-center justify-between"
                  >
                    <span className="text-gray-500 dark:text-gray-400">
                      {String(f)}
                    </span>
                    {filled ? (
                      <CheckCircle2
                        size={12}
                        className="text-emerald-500"
                      />
                    ) : (
                      <XCircle size={12} className="text-gray-300" />
                    )}
                  </div>
                );
              })}
              <div className="flex items-center justify-between pt-1 border-t border-gray-100 dark:border-gray-700">
                <span className="text-gray-500">Linked records</span>
                <span className="font-mono">{linksCount}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Health rating</span>
                <span className="font-mono">{health}/100</span>
              </div>
            </div>
          </div>

          {/* 2. Activity & Actions */}
          <div className="space-y-2">
            <h4 className="font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-1">
              <Activity size={14} /> Activity
            </h4>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-gray-500">Version</span>
                <span className="font-mono">{contact.version ?? 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Created</span>
                <span>{formatEpochMs(contact.dt_created)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Modified</span>
                <span>{formatEpochMs(contact.dt_modified)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Last login</span>
                <span>
                  {contact.last_login
                    ? formatDt(contact.last_login, 'date')
                    : "Never"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Actions</span>
                <span className="font-mono">{actionCount}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Status</span>
                <span
                  className={
                    contact.is_active
                      ? "text-emerald-600"
                      : "text-red-500"
                  }
                >
                  {contact.is_active ? "Active" : "Inactive"}
                </span>
              </div>
            </div>
          </div>

          {/* 3. API Usage (from UserDailyLog) */}
          <div className="space-y-2">
            <h4 className="font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-1">
              <BarChart3 size={14} /> API Usage (7 days)
            </h4>
            {dailyLogs.length === 0 ? (
              <p className="text-xs text-gray-400 italic">
                No API activity recorded
              </p>
            ) : (
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-500">Total calls</span>
                  <span className="font-mono font-semibold">
                    {dailyLogs.reduce((s, d) => s + d.total_calls, 0)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Total errors</span>
                  <span className="font-mono text-red-500">
                    {dailyLogs.reduce((s, d) => s + d.total_errors, 0)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Avg duration</span>
                  <span className="font-mono">
                    {Math.round(
                      dailyLogs.reduce(
                        (s, d) => s + d.avg_duration_ms,
                        0,
                      ) / dailyLogs.length,
                    )}{" "}
                    ms
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Days active</span>
                  <span className="font-mono">{dailyLogs.length}</span>
                </div>
                {/* Hint summary */}
                {dailyLogs.some((d) => d.hints?.length > 0) && (
                  <div className="pt-1 border-t border-gray-100 dark:border-gray-700">
                    <span className="text-gray-500">Hints:</span>
                    {dailyLogs
                      .flatMap((d) => d.hints ?? [])
                      .slice(0, 3)
                      .map((h, i) => (
                        <div
                          key={i}
                          className={`mt-1 px-2 py-1 rounded text-xs ${
                            h.level === "error"
                              ? "bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300"
                              : h.level === "warning"
                                ? "bg-amber-50 text-amber-700 dark:bg-amber-900/20 dark:text-amber-300"
                                : "bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300"
                          }`}
                        >
                          {h.message}
                        </div>
                      ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* 4. Org Health */}
          <div className="space-y-2">
            <h4 className="font-semibold text-gray-700 dark:text-gray-300 flex items-center gap-1">
              <ShieldCheck size={14} /> Linked Orgs
            </h4>
            {orgs.length === 0 ? (
              <p className="text-xs text-gray-400 italic">
                No org associations
              </p>
            ) : (
              <div className="space-y-2">
                {orgs.map(({ fk, orgId }) => {
                  const org = orgMap.get(orgId);
                  const meta = ORG_ROLE_MAP[fk];
                  const Icon = ORG_ICON[fk] ?? User;
                  return (
                    <div
                      key={fk}
                      className={`p-2 rounded-md border ${meta?.bg ?? ""} border-gray-200 dark:border-gray-600`}
                    >
                      <div className="flex items-center gap-1">
                        <Icon size={12} className={meta?.color ?? ""} />
                        <span
                          className={`text-xs font-semibold ${meta?.color ?? ""}`}
                        >
                          {meta?.label ?? fk}
                        </span>
                      </div>
                      {org ? (
                        <div className="mt-1 space-y-0.5 text-xs text-gray-600 dark:text-gray-400">
                          <div className="font-medium text-gray-800 dark:text-gray-200">
                            {org.display_name ?? `Org #${orgId}`}
                          </div>
                          {org.status && (
                            <div>
                              Status:{" "}
                              <span className="font-mono">{org.status}</span>
                            </div>
                          )}
                          {org.health_rating !== undefined && (
                            <div>
                              Health:{" "}
                              <span className="font-mono">
                                {org.health_rating}/100
                              </span>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="mt-1 text-xs text-gray-400">
                          Org #{orgId}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/** Section for a single team member */
function MemberSection({
  member,
  orgMap,
  dailyLogsMap,
}: {
  member: MemberGroup;
  orgMap: Map<number, OrgSummary>;
  dailyLogsMap: Map<number, UserDailyLog[]>;
}) {
  const avgCompleteness = Math.round(
    member.contacts.reduce((s, c) => s + computeCompleteness(c), 0) /
      (member.contacts.length || 1),
  );

  return (
    <section className="space-y-3">
      {/* Member header */}
      <div className="flex items-center gap-3">
        {member.isAI ? (
          <Bot size={20} className="text-purple-500" />
        ) : (
          <User size={20} className="text-indigo-500" />
        )}
        <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">
          {member.name}
        </h3>
        <span className="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded-full">
          {member.contacts.length} contact{member.contacts.length !== 1 ? "s" : ""}
        </span>
        <span
          className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
            avgCompleteness >= 80
              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
              : avgCompleteness >= 50
                ? "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
          }`}
        >
          {avgCompleteness}% complete
        </span>
        {member.isAI && (
          <span className="text-xs bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 px-2 py-0.5 rounded-full">
            AI Agent
          </span>
        )}
      </div>

      {/* Contact cards */}
      <div className="space-y-2 pl-2">
        {member.contacts.map((c) => (
          <ContactCard
            key={c.id}
            contact={c}
            orgMap={orgMap}
            dailyLogs={dailyLogsMap.get(c.id) ?? []}
          />
        ))}
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Page Component                                                */
/* ------------------------------------------------------------------ */

export default function TeamDashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [contacts, setContacts] = useState<ContactApiTask[]>([]);
  const [orgMap, setOrgMap] = useState<Map<number, OrgSummary>>(new Map());
  const [dailyLogsMap, setDailyLogsMap] = useState<
    Map<number, UserDailyLog[]>
  >(new Map());

  /* ---- Data fetching ---- */

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Fetch contacts that have a name_prefix (team-tagged)
      const res = await getRecords("contact", {
        limit: 200,
        ordering: "name_prefix,name_last",
      });
      const allContacts = (res?.results ?? []) as ContactApiTask[];
      const teamContacts = allContacts.filter(
        (c) => c.name_prefix && c.name_prefix.trim() !== "",
      );
      setContacts(teamContacts);

      // 2. Collect unique org IDs and batch-fetch
      const orgIds = new Set<number>();
      for (const c of teamContacts) {
        for (const fk of [
          "customer_id",
          "vendor_id",
          "employee_id",
          "manufacturer_id",
          "rep_id",
        ]) {
          const v = c[fk as keyof ContactApiTask] as number | null;
          if (v) orgIds.add(v);
        }
      }
      if (orgIds.size > 0) {
        const orgRes = await getRecords("orgbase", {
          id__in: Array.from(orgIds).join(","),
          limit: orgIds.size,
        });
        const map = new Map<number, OrgSummary>();
        for (const o of (orgRes?.results ?? []) as OrgSummary[]) {
          map.set(o.id, o);
        }
        setOrgMap(map);
      }

      // 3. Fetch last 7 days of UserDailyLog for each team contact
      const since = new Date();
      since.setDate(since.getDate() - 7);
      const sinceStr = since.toISOString().split("T")[0];

      const logMap = new Map<number, UserDailyLog[]>();
      // Batch — one call for all, then distribute
      const userIds = teamContacts.map((c) => c.id);
      if (userIds.length > 0) {
        const logRes = await fetchUserDailyLogs({
          log_date__gte: sinceStr,
          ordering: "-log_date",
          limit: userIds.length * 7,
        });
        for (const log of logRes.results) {
          const uid =
            (log as unknown as Record<string, unknown>).user_id ??
            (log as unknown as Record<string, unknown>).user;
          if (typeof uid === "number") {
            if (!logMap.has(uid)) logMap.set(uid, []);
            logMap.get(uid)!.push(log);
          }
        }
      }
      setDailyLogsMap(logMap);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load team data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  /* ---- Group contacts by name_prefix ---- */

  const memberGroups: MemberGroup[] = useMemo(() => {
    const map = new Map<string, ContactApiTask[]>();
    for (const c of contacts) {
      const key = (c.name_prefix ?? "").trim();
      if (!key) continue;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(c);
    }
    return Array.from(map.entries())
      .map(([name, cts]) => ({
        name,
        contacts: cts,
        isAI: AI_NAMES.has(name.toLowerCase()),
      }))
      .sort((a, b) => {
        // Humans first, then AI
        if (a.isAI !== b.isAI) return a.isAI ? 1 : -1;
        return a.name.localeCompare(b.name);
      });
  }, [contacts]);

  /* ---- Summary stats ---- */

  const stats = useMemo(() => {
    const totalContacts = contacts.length;
    const totalMembers = memberGroups.length;
    const avgCompleteness =
      totalContacts > 0
        ? Math.round(
            contacts.reduce((s, c) => s + computeCompleteness(c), 0) /
              totalContacts,
          )
        : 0;
    const withOrg = contacts.filter(
      (c) => getOrgAssociations(c).length > 0,
    ).length;
    const totalApiCalls = Array.from(dailyLogsMap.values())
      .flat()
      .reduce((s, d) => s + d.total_calls, 0);
    const totalErrors = Array.from(dailyLogsMap.values())
      .flat()
      .reduce((s, d) => s + d.total_errors, 0);
    return {
      totalMembers,
      totalContacts,
      avgCompleteness,
      withOrg,
      totalApiCalls,
      totalErrors,
    };
  }, [contacts, memberGroups, dailyLogsMap]);

  /* ---- Render ---- */

  return (
    <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
      {/* Title */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <Code2 size={24} className="text-indigo-500" />
            Team Dashboard
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Per-member insight report — contacts grouped by{" "}
            <code className="px-1 bg-gray-100 dark:bg-gray-700 rounded text-xs">
              name_prefix
            </code>
          </p>
        </div>
        <button
          onClick={loadData}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 transition-colors text-sm"
        >
          {loading ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <RefreshCw size={16} />
          )}
          Refresh
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm">
          <AlertTriangle size={16} />
          {error}
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard
          icon={<Users size={18} />}
          label="Team Members"
          value={stats.totalMembers}
          color="text-indigo-600 dark:text-indigo-400"
        />
        <StatCard
          icon={<User size={18} />}
          label="Contacts"
          value={stats.totalContacts}
          color="text-blue-600 dark:text-blue-400"
        />
        <StatCard
          icon={<CheckCircle2 size={18} />}
          label="Avg Completeness"
          value={`${stats.avgCompleteness}%`}
          color={completenessColor(stats.avgCompleteness)}
        />
        <StatCard
          icon={<Briefcase size={18} />}
          label="With Org Link"
          value={stats.withOrg}
          color="text-emerald-600 dark:text-emerald-400"
        />
        <StatCard
          icon={<Zap size={18} />}
          label="API Calls (7d)"
          value={stats.totalApiCalls}
          color="text-amber-600 dark:text-amber-400"
        />
        <StatCard
          icon={<XCircle size={18} />}
          label="Errors (7d)"
          value={stats.totalErrors}
          color="text-red-600 dark:text-red-400"
        />
      </div>

      {/* Loading indicator */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 size={32} className="animate-spin text-indigo-500" />
        </div>
      )}

      {/* Empty state */}
      {!loading && memberGroups.length === 0 && (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          <Users size={48} className="mx-auto mb-4 opacity-40" />
          <p className="text-lg font-medium">No team contacts found</p>
          <p className="text-sm mt-1">
            Create contacts with a <code>name_prefix</code> matching your first
            name to appear here.
          </p>
          <p className="text-xs mt-3 text-gray-400">
            Each member should have 3 contacts: one linked to a Customer (testing),
            one to a Vendor (testing), and one to an Employee (development).
          </p>
        </div>
      )}

      {/* Member sections */}
      {!loading && memberGroups.length > 0 && (
        <div className="space-y-8">
          {memberGroups.map((m) => (
            <MemberSection
              key={m.name}
              member={m}
              orgMap={orgMap}
              dailyLogsMap={dailyLogsMap}
            />
          ))}
        </div>
      )}

      {/* Legend */}
      {!loading && memberGroups.length > 0 && (
        <div className="border-t border-gray-200 dark:border-gray-700 pt-4 text-xs text-gray-500 dark:text-gray-400">
          <div className="flex flex-wrap gap-4">
            <span className="flex items-center gap-1">
              <Store size={12} className="text-blue-500" /> Customer = Testing
            </span>
            <span className="flex items-center gap-1">
              <Truck size={12} className="text-amber-500" /> Vendor = Testing
            </span>
            <span className="flex items-center gap-1">
              <Briefcase size={12} className="text-emerald-500" /> Employee =
              Development
            </span>
            <span className="flex items-center gap-1">
              <Bot size={12} className="text-purple-500" /> AI Agent
            </span>
            <span className="flex items-center gap-1">
              <Clock size={12} /> API data = last 7 days
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

/* ---- Stat card ---- */

function StatCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  color: string;
}) {
  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
      <div className={`flex items-center gap-2 ${color}`}>{icon}</div>
      <div className="mt-2 text-2xl font-bold text-gray-900 dark:text-gray-100">
        {value}
      </div>
      <div className="text-xs text-gray-500 dark:text-gray-400">{label}</div>
    </div>
  );
}
