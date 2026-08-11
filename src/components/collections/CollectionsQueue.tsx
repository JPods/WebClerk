/**
 * CollectionsQueue — live past-due invoice list for the accounting dashboard.
 *
 * Shows top customers by past-due amount. Click → opens invoice.
 * Shift-click → creates collection Action assigned to rep.
 *
 * Data source: POST /wcapi/manage/ { action: "get_collections_dashboard" }
 *
 * LastChecked: 2026-08-10 | WhereUsed: AccountingDashboard | WhoCreated: Bill+Claude
 */
import React, { useEffect, useState, useCallback } from 'react';
import apiClient from '@/api/axios';
import { FaSync, FaExclamationTriangle, FaPhoneAlt } from 'react-icons/fa';

interface PastDueCustomer {
  id: number;
  ida: string;
  company: string;
  balance_due: number;
  days_oldest: number;
  last_payment_date: string | null;
  last_payment_amount: number | null;
  open_invoice_count: number;
}

interface CollectionsData {
  top_past_due: PastDueCustomer[];
  dso_current: number;
  cash_this_week: { total: number; count: number; daily: { date: string; amount: number }[] };
  collection_actions: { open: number; overdue: number };
  promises_broken: number;
}

const fmt = (n: number) => n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtInt = (n: number) => n.toLocaleString('en-US');

function agingColor(days: number): string {
  if (days > 90) return 'text-red-700 bg-red-50';
  if (days > 60) return 'text-red-600 bg-red-50';
  if (days > 30) return 'text-amber-600 bg-amber-50';
  return 'text-gray-600';
}

const CollectionsQueue: React.FC = () => {
  const [data, setData] = useState<CollectionsData | null>(null);
  const [loading, setLoading] = useState(false);

  const fetch = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiClient.post('/wcapi/manage/', { action: 'get_collections_dashboard', params: {} });
      setData(res.data?.data ?? res.data);
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { fetch(); }, [fetch]);

  if (!data && loading) return <div className="p-6 text-gray-500 text-center">Loading collections...</div>;
  if (!data) return null;

  return (
    <div className="space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="rounded-lg border border-gray-200 bg-white p-3 text-center">
          <div className="text-2xl font-bold text-gray-900">{Math.round(data.dso_current)}</div>
          <div className="text-xs text-gray-500">DSO (days)</div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-3 text-center">
          <div className="text-2xl font-bold text-green-600">${fmt(data.cash_this_week.total)}</div>
          <div className="text-xs text-gray-500">Cash this week ({data.cash_this_week.count})</div>
        </div>
        <div className={`rounded-lg border p-3 text-center ${data.collection_actions.overdue > 0 ? 'border-red-300 bg-red-50' : 'border-gray-200 bg-white'}`}>
          <div className="text-2xl font-bold text-gray-900">{data.collection_actions.open}</div>
          <div className="text-xs text-gray-500">Open actions ({data.collection_actions.overdue} overdue)</div>
        </div>
        <div className={`rounded-lg border p-3 text-center ${data.promises_broken > 0 ? 'border-red-300 bg-red-50' : 'border-gray-200 bg-white'}`}>
          <div className="text-2xl font-bold text-red-600">{data.promises_broken}</div>
          <div className="text-xs text-gray-500">Promises broken</div>
        </div>
      </div>

      {/* Past-due customer list */}
      <div className="rounded-lg border border-gray-200 bg-white">
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100">
          <h3 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
            <FaExclamationTriangle className="text-amber-500" />
            Top Past Due — Click to open, Shift-click to create action
          </h3>
          <button onClick={fetch} disabled={loading} className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1">
            <FaSync className={loading ? 'animate-spin' : ''} size={10} /> Refresh
          </button>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-gray-500 uppercase border-b border-gray-100">
              <th className="text-left px-4 py-2">Customer</th>
              <th className="text-right px-4 py-2">Balance Due</th>
              <th className="text-right px-4 py-2">Days Late</th>
              <th className="text-right px-4 py-2">Invoices</th>
              <th className="text-right px-4 py-2">Last Payment</th>
              <th className="text-center px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {data.top_past_due.map(c => (
              <tr key={c.id}
                className="border-b border-gray-50 hover:bg-gray-50 cursor-pointer"
                onClick={(e) => {
                  if (e.shiftKey) {
                    // Create collection action
                    apiClient.post('/wcapi/save/', {
                      model_name: 'action',
                      data: {
                        name: `Collection: ${c.company} — $${fmt(c.balance_due)} past due`,
                        project_name: 'collection',
                        status: 'open',
                        parent_model: 'customer',
                        parent_id: c.id,
                      },
                    }).then(() => fetch());
                  } else {
                    window.open(`/customer?id=${c.id}`, '_blank');
                  }
                }}
              >
                <td className="px-4 py-2">
                  <div className="font-medium text-gray-900">{c.company}</div>
                  <div className="text-xs text-gray-400">{c.ida}</div>
                </td>
                <td className="px-4 py-2 text-right font-mono font-medium text-red-600">
                  ${fmt(c.balance_due)}
                </td>
                <td className="px-4 py-2 text-right">
                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${agingColor(c.days_oldest)}`}>
                    {c.days_oldest}d
                  </span>
                </td>
                <td className="px-4 py-2 text-right text-gray-600">
                  {c.open_invoice_count}
                </td>
                <td className="px-4 py-2 text-right text-gray-500 text-xs">
                  {c.last_payment_date
                    ? <>{new Date(c.last_payment_date).toLocaleDateString()} · ${fmt(c.last_payment_amount || 0)}</>
                    : <span className="text-red-400">No payments</span>
                  }
                </td>
                <td className="px-4 py-2 text-center">
                  <FaPhoneAlt className="text-gray-300 hover:text-blue-500" size={12} title="Shift-click to create collection action" />
                </td>
              </tr>
            ))}
            {data.top_past_due.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No past-due accounts</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default CollectionsQueue;
