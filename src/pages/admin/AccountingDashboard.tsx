/* Accounting Dashboard — admin system health overview
 *
 * Data source: POST /wcapi/manage/ { action: "get_accounting_dashboard" }
 *
 * Sections:
 *   - Journal Status: last journalized, pending journal counts
 *   - GL Balance: total debits vs credits, imbalance detection
 *   - Transaction Volume: counts by type and status
 *   - Locked Records: journalized vs editable
 *   - Aging Summary: AR aging buckets
 *   - Pending Inventory: unprocessed pending count + age
 *   - Orphan Detection: FK integrity check (separate action)
 */
import React, { useEffect, useState, useCallback } from "react";
import apiClient from "../../api/axios";
import { FaSync, FaExclamationTriangle, FaCheckCircle, FaLock, FaUnlock, FaClock, FaExternalLinkAlt } from "react-icons/fa";

type DashboardData = {
  journal_status: {
    last_invoice_journalized: { source_id: number; dt_created: number } | null;
    last_payment_journalized: { source_id: number; dt_created: number } | null;
    pending_invoices: number;
    pending_payments: number;
    total_journal_entries: number;
  };
  gl_balance: {
    total_debit: number;
    total_credit: number;
    imbalance: number;
    balanced: boolean;
    source_imbalances: { source_model: string; debits: number; credits: number; imbalance: number }[];
  };
  transaction_volume: Record<string, { total: number; by_status: Record<string, number> }>;
  locked_records: Record<string, { locked: number; unlocked: number }>;
  aging_summary: {
    current: number;
    period_1_30: number;
    period_2_60: number;
    period_3_90_plus: number;
    total_ar: number;
    customers_with_balance: number;
  };
  pending_inventory: {
    unprocessed_count: number;
    oldest_age_minutes: number;
  };
  dt_generated: number;
};

type OrphanData = {
  orphans: { model: string; fk_field: string; parent_model: string; null_count: number; dangling_count: number; total_orphans: number }[];
  total_orphans: number;
  tables_with_orphans: number;
};

const fmt = (n: number) => n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtInt = (n: number) => n.toLocaleString("en-US");
const fmtDate = (ms: number) => ms ? new Date(ms).toLocaleString() : "—";

const Card: React.FC<{ title: string; icon?: React.ReactNode; alert?: boolean; children: React.ReactNode }> = ({ title, icon, alert, children }) => (
  <div className={`rounded-lg border p-4 shadow-sm ${alert ? "border-red-300 bg-red-50" : "border-gray-200 bg-white"}`}>
    <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-3">
      {icon} {title}
    </h3>
    {children}
  </div>
);

const Stat: React.FC<{ label: string; value: string | number; alert?: boolean }> = ({ label, value, alert }) => (
  <div className="flex justify-between py-1 text-sm">
    <span className="text-gray-500">{label}</span>
    <span className={`font-mono font-medium ${alert ? "text-red-600" : "text-gray-900"}`}>{value}</span>
  </div>
);

export default function AccountingDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [orphans, setOrphans] = useState<OrphanData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dashRes, orphanRes] = await Promise.all([
        apiClient.post("/wcapi/manage/", { action: "get_accounting_dashboard", params: {} }),
        apiClient.post("/wcapi/manage/", { action: "get_orphan_counts", params: {} }),
      ]);
      setData(dashRes.data?.data ?? dashRes.data);
      setOrphans(orphanRes.data?.data ?? orphanRes.data);
    } catch (err: any) {
      setError(err?.message || "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchDashboard(); }, [fetchDashboard]);

  if (loading && !data) return <div className="p-8 text-center text-gray-500">Loading accounting dashboard...</div>;
  if (error) return <div className="p-8 text-center text-red-600">{error}</div>;
  if (!data) return null;

  const { journal_status, gl_balance, transaction_volume, locked_records, aging_summary, pending_inventory } = data;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-900">Accounting Dashboard</h1>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400">Generated: {fmtDate(data.dt_generated)}</span>
          <button onClick={fetchDashboard} disabled={loading} className="flex items-center gap-1 px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50">
            <FaSync className={loading ? "animate-spin" : ""} size={12} /> Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

        {/* GL Balance */}
        <Card title="GL Balance" icon={gl_balance.balanced ? <FaCheckCircle className="text-green-500" /> : <FaExclamationTriangle className="text-red-500" />} alert={!gl_balance.balanced}>
          <Stat label="Total Debits" value={`$${fmt(gl_balance.total_debit)}`} />
          <Stat label="Total Credits" value={`$${fmt(gl_balance.total_credit)}`} />
          <Stat label="Imbalance" value={`$${fmt(gl_balance.imbalance)}`} alert={!gl_balance.balanced} />
          <Stat label="Status" value={gl_balance.balanced ? "Balanced" : "IMBALANCED"} alert={!gl_balance.balanced} />
          {gl_balance.source_imbalances.length > 0 && (
            <div className="mt-2 text-xs text-red-600">
              {gl_balance.source_imbalances.map((s, i) => (
                <div key={i}>{s.source_model}: ${fmt(s.imbalance)} imbalance</div>
              ))}
            </div>
          )}
        </Card>

        {/* Journal Status */}
        <Card title="Journal Status" icon={<FaLock className="text-gray-400" />}>
          <Stat label="Total GL Entries" value={fmtInt(journal_status.total_journal_entries)} />
          <Stat label="Pending Invoices" value={fmtInt(journal_status.pending_invoices)} alert={journal_status.pending_invoices > 10} />
          <Stat label="Pending Payments" value={fmtInt(journal_status.pending_payments)} alert={journal_status.pending_payments > 10} />
          <div className="mt-2 text-xs text-gray-400">
            Last Invoice GL: {journal_status.last_invoice_journalized ? fmtDate(journal_status.last_invoice_journalized.dt_created) : "None"}
          </div>
          <div className="text-xs text-gray-400">
            Last Payment GL: {journal_status.last_payment_journalized ? fmtDate(journal_status.last_payment_journalized.dt_created) : "None"}
          </div>
        </Card>

        {/* Aging Summary */}
        <Card title="Accounts Receivable Aging" icon={<FaClock className="text-gray-400" />}>
          <Stat label="Current" value={`$${fmt(aging_summary.current)}`} />
          <Stat label="1-30 Days" value={`$${fmt(aging_summary.period_1_30)}`} alert={aging_summary.period_1_30 > 0} />
          <Stat label="31-60 Days" value={`$${fmt(aging_summary.period_2_60)}`} alert={aging_summary.period_2_60 > 0} />
          <Stat label="60+ Days" value={`$${fmt(aging_summary.period_3_90_plus)}`} alert={aging_summary.period_3_90_plus > 0} />
          <div className="border-t mt-2 pt-2">
            <Stat label="Total AR" value={`$${fmt(aging_summary.total_ar)}`} />
            <Stat label="Customers w/ Balance" value={fmtInt(aging_summary.customers_with_balance)} />
          </div>
        </Card>

        {/* Transaction Volume */}
        <Card title="Transaction Volume" icon={<FaCheckCircle className="text-gray-400" />}>
          {Object.entries(transaction_volume).map(([type, info]) => (
            <Stat key={type} label={type.charAt(0).toUpperCase() + type.slice(1)} value={fmtInt(info.total)} />
          ))}
        </Card>

        {/* Locked Records */}
        <Card title="Locked Records (Journalized)" icon={<FaLock className="text-gray-400" />}>
          {Object.entries(locked_records).map(([type, info]) => (
            <div key={type} className="flex justify-between py-1 text-sm">
              <span className="text-gray-500">{type.charAt(0).toUpperCase() + type.slice(1)}</span>
              <span className="font-mono">
                <span className="text-green-600">{info.locked} locked</span>
                {" / "}
                <span className="text-gray-500">{info.unlocked} unlocked</span>
              </span>
            </div>
          ))}
        </Card>

        {/* Pending Inventory */}
        <Card title="Pending Inventory" icon={pending_inventory.unprocessed_count > 0 ? <FaClock className="text-amber-500" /> : <FaCheckCircle className="text-green-500" />} alert={pending_inventory.oldest_age_minutes > 5}>
          <Stat label="Unprocessed" value={fmtInt(pending_inventory.unprocessed_count)} alert={pending_inventory.unprocessed_count > 0} />
          <Stat label="Oldest Age" value={`${pending_inventory.oldest_age_minutes} min`} alert={pending_inventory.oldest_age_minutes > 5} />
          <div className="text-xs text-gray-400 mt-2">Celery processes every 30s. Age &gt; 5 min = investigate.</div>
        </Card>

        {/* Orphan Detection */}
        {orphans && (
          <Card title="Data Integrity (Orphans)" icon={orphans.total_orphans > 0 ? <FaExclamationTriangle className="text-amber-500" /> : <FaCheckCircle className="text-green-500" />} alert={orphans.total_orphans > 0}>
            <Stat label="Total Orphans" value={fmtInt(orphans.total_orphans)} alert={orphans.total_orphans > 0} />
            <Stat label="Tables Affected" value={fmtInt(orphans.tables_with_orphans)} alert={orphans.tables_with_orphans > 0} />
            {orphans.orphans.length > 0 && (
              <div className="mt-2 space-y-1">
                {orphans.orphans.slice(0, 5).map((o, i) => (
                  <div key={i} className="flex justify-between text-xs">
                    <span className="text-gray-600">{o.model}.{o.fk_field}</span>
                    <span className="text-red-600 font-mono">{o.total_orphans}</span>
                  </div>
                ))}
                {orphans.orphans.length > 5 && (
                  <div className="text-xs text-gray-400">+ {orphans.orphans.length - 5} more</div>
                )}
              </div>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}
