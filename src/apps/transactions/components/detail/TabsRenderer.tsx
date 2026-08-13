/* LastChecked: 2026-08-02 | WhereUsed: TransactionDetail | WhoCreated: Claude */
import React from 'react';
import { useAppSelector } from '@/store/hooks';
import { getRecords } from '@/api/wcapi';
import { formatDt } from '@/utils/fieldFormatters';
import CommentsPanel from '@/apps/common/components/panels/CommentsPanel';
import FinancialsPanel from '@/apps/common/components/panels/FinancialsPanel';
import { PanelTable, type PanelColumnDef } from '@/apps/common/components/panels/PanelTable';
import type { TabsSection } from '@/hooks/useDetailLayout';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TabsRendererProps {
  section: TabsSection;
  data: any;
  isEditing: boolean;
  modelName: string;
  activeTab: string;
  onTabChange: (tab: string) => void;
  onChange: (field: string, value: unknown) => void;
  onRefresh: () => void;
  loggedInUserName?: string;
}

// ---------------------------------------------------------------------------
// TabsRenderer
// ---------------------------------------------------------------------------

/** Render tabbed sections */
const TabsRenderer: React.FC<TabsRendererProps> = ({ section, data, isEditing, modelName, activeTab, onTabChange, onChange, onRefresh, loggedInUserName }) => {
  const authUser = useAppSelector((s) => s.auth.user);
  const isStaff = authUser?.is_staff || authUser?.is_superuser || false;
  // Default to first tab if activeTab not in this section
  const tabIds = section.tabs.map(t => t.content);
  const currentTab = tabIds.includes(activeTab) ? activeTab : tabIds[0] || 'summary';

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
      {/* Tab bar */}
      <div className="flex border-b border-slate-200 dark:border-slate-700 overflow-x-auto no-print">
        {section.tabs.map((tab) => (
          <button
            key={tab.content}
            onClick={() => onTabChange(tab.content)}
            className={`px-4 py-2 text-xs font-medium whitespace-nowrap border-b-2 transition-colors ${
              currentTab === tab.content
                ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="p-4">
        <TabContent
          tabId={currentTab}
          data={data}
          isEditing={isEditing}
          modelName={modelName}
          onChange={onChange}
          onRefresh={onRefresh}
          loggedInUserName={loggedInUserName}
        />
      </div>
    </div>
  );
};

export default TabsRenderer;

// ---------------------------------------------------------------------------
// Tab Content -- renders the right component for each tab type
// ---------------------------------------------------------------------------

export const TabContent: React.FC<{
  tabId: string;
  data: any;
  isEditing: boolean;
  modelName: string;
  onChange: (field: string, value: unknown) => void;
  onRefresh: () => void;
  loggedInUserName?: string;
}> = ({ tabId, data, isEditing, modelName, onChange, onRefresh, loggedInUserName }) => {
  switch (tabId) {
    case 'summary':
      return <SummaryTabContent data={data} modelName={modelName} />;

    case 'payments':
    case 'financials':
    case 'margins':
      return (
        <FinancialsPanel
          transactionId={data?.id}
          modelName={modelName}
          isEditing={false}
        />
      );

    case 'contacts': {
      const rawContacts = data?.refs?.links?.contact ?? [];
      const contactRows = Array.isArray(rawContacts) ? rawContacts.map((c: any) => {
        const ct = c.contact || c;
        return {
          id: ct.id || ct.contact_id || 0,
          ida: ct.ida || '',
          role: c.purpose || ct.role || '',
          name: ct.attention || ct.display_name || '',
          email: Array.isArray(ct.email) ? ct.email[0] : (ct.email || ''),
          phone: Array.isArray(ct.phone) ? ct.phone[0] : (ct.phone || ''),
          address: Array.isArray(ct.address) ? ct.address[0]?.full : (ct.address?.full || ct.address || ''),
        };
      }) : [];

      if (!contactRows.length) {
        return <div className="text-center py-8 text-slate-400 text-sm">No contacts linked</div>;
      }

      const contactCols: PanelColumnDef<Record<string, unknown>>[] = [
        { key: 'role', label: 'role', cellClassName: 'w-[70px] text-slate-600 dark:text-slate-300', render: (r) => String(r.role ?? '—') },
        { key: 'name', label: 'name', cellClassName: 'w-[150px] text-slate-800 dark:text-slate-200', render: (r) => String(r.name ?? '—') },
        { key: 'email', label: 'email', cellClassName: 'w-[200px] text-slate-600 dark:text-slate-300', render: (r) => String(r.email ?? '—') },
        { key: 'phone', label: 'phone', cellClassName: 'w-[140px] text-slate-600 dark:text-slate-300', render: (r) => String(r.phone ?? '—') },
        { key: 'address', label: 'address', cellClassName: 'min-w-[200px] flex-1 text-slate-600 dark:text-slate-300', render: (r) => String(r.address ?? '—') },
      ];

      return (
        <PanelTable
          storageKey={`panel:${modelName}:contacts`}
          columns={contactCols}
          data={contactRows}
          rowKey={(r: any) => r.id}
          compact
        />
      );
    }

    case 'comments':
      return (
        <CommentsPanel
          comments={data?.comments}
          isEditing={isEditing}
          onChange={(comments: any) => onChange('comments', comments)}
        />
      );

    case 'documents': {
      const docs = data?.refs?.links?.document ?? [];
      const docRows = Array.isArray(docs) ? docs.map((d: any) => {
        const doc = d.document || d;
        return { id: doc.id || 0, ida: doc.ida || '', name: doc.name || doc.display_name || '', status: doc.status || d.purpose || '' };
      }) : [];
      if (!docRows.length) return <div className="text-center py-8 text-slate-400 text-sm">No documents attached</div>;

      const docCols: PanelColumnDef<Record<string, unknown>>[] = [
        { key: 'ida', label: 'ida', cellClassName: 'w-[100px] font-mono text-slate-500 dark:text-slate-400', render: (r) => String(r.ida ?? '—') },
        { key: 'name', label: 'name', cellClassName: 'min-w-[200px] flex-1 text-slate-800 dark:text-slate-200', render: (r) => String(r.name ?? '—') },
        { key: 'status', label: 'status', cellClassName: 'w-[80px] text-slate-600 dark:text-slate-300', render: (r) => String(r.status ?? '—') },
      ];

      return (
        <PanelTable
          storageKey={`panel:${modelName}:documents`}
          columns={docCols}
          data={docRows}
          rowKey={(r: any) => r.id}
          compact
        />
      );
    }

    case 'actions': {
      const actionItems = (data?.actions?.items ?? []) as any[];
      if (!actionItems.length) return <div className="text-center py-8 text-slate-400 text-sm">No actions on this {modelName}</div>;

      const actionCols: PanelColumnDef<Record<string, unknown>>[] = [
        { key: 'action', label: 'action', cellClassName: 'min-w-[200px] flex-1 text-slate-800 dark:text-slate-200', render: (r) => {
          const v = r.action;
          return String(typeof v === 'object' && v !== null ? (v as any).en ?? JSON.stringify(v) : v ?? '—');
        }},
        { key: 'status', label: 'status', cellClassName: 'w-[90px]', render: (r) => {
          const s = String(r.status ?? 'pending');
          const done = s === 'done' || s === 'completed';
          return <span className={`px-1.5 py-0.5 rounded text-xs ${done ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-slate-100 text-slate-600 dark:bg-slate-600 dark:text-slate-300'}`}>{s}</span>;
        }},
      ];

      return (
        <PanelTable
          storageKey={`panel:${modelName}:actions`}
          columns={actionCols}
          data={actionItems}
          rowKey={(r: any) => r.id ?? Math.random()}
          compact
        />
      );
    }

    case 'related_transactions': {
      const links = data?.refs?.links || {};
      const relatedRows: any[] = [];
      for (const [linkType, items] of Object.entries(links)) {
        if (!Array.isArray(items)) continue;
        for (const item of items as any[]) {
          const obj = item.contact || item.customer || item;
          relatedRows.push({
            id: obj.id || 0,
            type: linkType,
            ida: obj.ida || '',
            name: obj.display_name || obj.company || obj.name || obj.attention || '',
          });
        }
      }
      if (!relatedRows.length) return <div className="text-center py-8 text-slate-400 text-sm">No related records</div>;

      const relCols: PanelColumnDef<Record<string, unknown>>[] = [
        { key: 'type', label: 'type', cellClassName: 'w-[90px] font-semibold text-slate-600 dark:text-slate-300', render: (r) => String(r.type ?? '—') },
        { key: 'ida', label: 'ida', cellClassName: 'w-[120px] font-mono text-slate-500 dark:text-slate-400', render: (r) => String(r.ida ?? '—') },
        { key: 'name', label: 'name', cellClassName: 'min-w-[200px] flex-1 text-slate-800 dark:text-slate-200', render: (r) => String(r.name ?? '—') },
      ];

      return (
        <PanelTable
          storageKey={`panel:${modelName}:related`}
          columns={relCols}
          data={relatedRows}
          rowKey={(r: any) => `${r.type}-${r.id}`}
          compact
        />
      );
    }

    case 'qa': {
      const [qaRecords, setQaRecords] = React.useState<any[]>([]);
      React.useEffect(() => {
        if (!data?.id) return;
        getRecords('qa', { parent_id: data.id, parent_model: modelName, limit: 50 })
          .then(res => setQaRecords((res?.results || []).map((q: any) => ({
            id: q.id, ida: q.ida || '', question: q.question || '', answer: q.answer || '', status: q.status || '',
          }))))
          .catch(() => setQaRecords([]));
      }, [data?.id, modelName]);

      if (!qaRecords.length) return <div className="text-center py-8 text-slate-400 text-sm">No QA records</div>;

      const qaCols: PanelColumnDef<Record<string, unknown>>[] = [
        { key: 'ida', label: 'ida', cellClassName: 'w-[80px] font-mono text-slate-500 dark:text-slate-400', render: (r) => String(r.ida ?? '—') },
        { key: 'question', label: 'question', cellClassName: 'min-w-[200px] flex-1 text-slate-800 dark:text-slate-200', render: (r) => String(r.question ?? '—') },
        { key: 'answer', label: 'answer', cellClassName: 'min-w-[150px] flex-1 text-slate-600 dark:text-slate-300', render: (r) => String(r.answer ?? '—') },
        { key: 'status', label: 'status', cellClassName: 'w-[70px] text-slate-600 dark:text-slate-300', render: (r) => String(r.status ?? '—') },
      ];

      return (
        <PanelTable
          storageKey={`panel:${modelName}:qa`}
          columns={qaCols}
          data={qaRecords}
          rowKey={(r: any) => r.id}
          compact
        />
      );
    }

    case 'shipping':
      return <ShippingTabContent data={data} />;

    case 'notes':
      return <NotesTabContent data={data} isEditing={isEditing} onChange={onChange} userName={loggedInUserName || 'User'} />;

    case 'history':
      return (
        <div className="text-xs text-slate-500 dark:text-slate-400">
          <pre className="whitespace-pre-wrap">{JSON.stringify(data?.metadata?.history ?? [], null, 2)}</pre>
        </div>
      );

    default:
      return (
        <div className="text-center py-8 text-slate-400 text-sm">
          Tab "{tabId}" not implemented
        </div>
      );
  }
};

// ---------------------------------------------------------------------------
// Built-in Tab Content Components
// ---------------------------------------------------------------------------

export const SummaryTabContent: React.FC<{ data: any; modelName: string }> = ({ data, modelName }) => {
  const authUser = useAppSelector((s) => s.auth.user);
  const isStaff = authUser?.is_staff || authUser?.is_superuser || false;
  const lines = data?.lines || [];
  const isSellSide = ['order', 'invoice', 'proposal'].includes(modelName);
  const totals = data?.totals || {};
  const sell = data?.sell || {};
  const cost = data?.cost || {};

  const totalExtended = lines.reduce((sum: number, line: any) => {
    if (isSellSide) return sum + Number(line.price?.extended ?? 0);
    return sum + Number(line.cost?.extended ?? 0);
  }, 0);
  const totalCost = lines.reduce((sum: number, line: any) => sum + Number(line.cost?.extended ?? 0), 0);
  const margin = totalExtended - totalCost;
  const marginPct = totalExtended > 0 ? (margin / totalExtended) * 100 : 0;

  const fmt = (v: number | null | undefined) => v == null ? '—' : `$${Number(v).toFixed(2)}`;

  // Customer data from refs links OR from the record's customer config
  const customerLink = data?.refs?.links?.customer?.[0] || {};
  const customerConfig = data?.customer_config || {};
  const customerData = { ...customerConfig, ...customerLink };

  // Payment and invoice data for third column
  const [payments, setPayments] = React.useState<any[]>([]);
  const [invoices, setInvoices] = React.useState<any[]>([]);
  React.useEffect(() => {
    if (!data?.id) return;
    (async () => {
      try {
        // Invoices linked via parent_id; payments by customer (no parent_id on payment model)
        const custId = data.customer_id || data.customer;
        const [payRes, invRes] = await Promise.all([
          custId ? getRecords('payment', { customer_id: custId, limit: 20 }).catch(() => null) : null,
          getRecords('invoice', { parent_id: data.id, parent_model: modelName, limit: 20 }).catch(() => null),
        ]);
        // Filter out demo/test records (ida starting with qq or zz)
        const filterReal = (recs: any[]) => (recs || []).filter((r: any) => {
          const ida = String(r.ida || '').toLowerCase();
          return !ida.startsWith('qq') && !ida.startsWith('zz') && !ida.startsWith('dev-');
        });
        setPayments(filterReal(payRes?.results));
        setInvoices(filterReal(invRes?.results));
      } catch { /* nothing yet */ }
    })();
  }, [data?.id]);

  const totalPayments = payments.reduce((s: number, d: any) => s + Number(d.total ?? d.totals?.total ?? 0), 0);
  const totalInvoiced = invoices.reduce((s: number, d: any) => s + Number(d.total ?? d.totals?.total ?? 0), 0);
  const totalUnapplied = invoices.reduce((s: number, d: any) => s + Number(d.balance ?? d.totals?.balance ?? 0), 0);

  return (
    <div className="grid grid-cols-3 gap-6 text-xs">
      {/* Left: Order Totals */}
      <div>
        <div className="text-xs font-bold text-slate-700 dark:text-slate-200 mb-2">Order Totals</div>
        <div className="space-y-0.5">
          <div className="flex justify-between"><span className="text-slate-500">Lines</span><span className="font-mono">{lines.length}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Sell Amount</span><span className="font-mono">{fmt(sell.line_sum_goods || totalExtended)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Discount</span><span className="font-mono">{fmt(sell.discount || totals.discount)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Sell Total</span><span className="font-mono font-medium">{fmt(sell.total || totalExtended)}</span></div>
          <div className="border-t border-slate-100 dark:border-slate-700 my-1" />
          <div className="flex justify-between"><span className="text-slate-500">Taxable</span><span className="font-mono">{fmt(totals.taxable)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Tax</span><span className="font-mono">{fmt(totals.tax)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Shipping</span><span className="font-mono">{fmt(totals.shipping)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Other</span><span className="font-mono">{fmt(totals.other)}</span></div>
          <div className="border-t border-slate-200 dark:border-slate-700 my-1" />
          <div className="flex justify-between font-bold"><span>Total</span><span className="font-mono">{fmt(totals.total || totalExtended)}</span></div>
          <div className="border-t border-slate-100 dark:border-slate-700 my-1" />
          <div className="flex justify-between"><span className="text-slate-500">Cost</span><span className="font-mono">{fmt(cost.line_sum_goods || totalCost)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Freight</span><span className="font-mono">{fmt(cost.freight)}</span></div>
          {isStaff && <div className="flex justify-between"><span className="text-slate-500">Commissions</span><span className="font-mono">{fmt(cost.commissions)}</span></div>}
          <div className="flex justify-between"><span className="text-slate-500">Cost Total</span><span className="font-mono">{fmt(cost.total || totalCost)}</span></div>
          <div className="border-t border-slate-200 dark:border-slate-700 my-1" />
          <div className="flex justify-between">
            <span className="text-slate-500">Margin</span>
            <span className="font-mono text-green-700 dark:text-green-400">{fmt(margin)} ({marginPct.toFixed(1)}%)</span>
          </div>
          <div className="border-t border-slate-100 dark:border-slate-700 my-1" />
          <div className="flex justify-between"><span className="text-slate-500">Payments</span><span className="font-mono">{data?.finance?.payment_count ?? totals.payment_count ?? 0}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Received</span><span className="font-mono">{fmt(totals.received)}</span></div>
          <div className="flex justify-between font-medium"><span>Balance</span><span className="font-mono">{fmt(totals.balance || data?.balance)}</span></div>
        </div>
      </div>

      {/* Right: Customer */}
      <div>
        <div className="text-xs font-bold text-slate-700 dark:text-slate-200 mb-2">Customer</div>
        <div className="space-y-0.5">
          <div className="flex justify-between"><span className="text-slate-500">Company</span><span className="font-mono">{data?.company || data?.customer_company || customerData.company || customerData.display_name || '—'}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Price Level</span><span className="font-mono">{data?.price_level || '—'}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Terms</span><span className="font-mono">{data?.terms || '—'}</span></div>
          <div className="border-t border-slate-100 dark:border-slate-700 my-1" />
          <div className="text-[10px] font-medium text-slate-400 mb-1">Credit</div>
          <div className="flex justify-between"><span className="text-slate-500">Credit Limit</span><span className="font-mono">{fmt(customerData.credit_limit)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Available</span><span className="font-mono">{fmt(customerData.credit_available)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Balance Due</span><span className="font-mono">{fmt(customerData.balance_due)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Current</span><span className="font-mono">{fmt(customerData.balance_current)}</span></div>
          <div className="border-t border-slate-100 dark:border-slate-700 my-1" />
          <div className="text-[10px] font-medium text-slate-400 mb-1">Sales History</div>
          <div className="flex justify-between"><span className="text-slate-500">MTD</span><span className="font-mono">{fmt(customerData.sales_mtd)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">YTD</span><span className="font-mono">{fmt(customerData.sales_ytd)}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Lifetime</span><span className="font-mono">{fmt(customerData.sales_lifetime)}</span></div>
          <div className="border-t border-slate-100 dark:border-slate-700 my-1" />
          <div className="text-[10px] font-medium text-slate-400 mb-1">Payment</div>
          <div className="flex justify-between"><span className="text-slate-500">Avg Days</span><span className="font-mono">{customerData.avg_pay_days ?? '—'}</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Last Payment</span><span className="font-mono">{fmt(customerData.last_payment_amount)}</span></div>
        </div>
      </div>

      {/* Right: Payments then Invoices */}
      <div>
        <div className="text-xs font-bold text-slate-700 dark:text-slate-200 mb-2">Flow</div>
        <div className="space-y-0.5">
          <div className="flex justify-between font-medium"><span>Total</span><span className="font-mono">{fmt(totalInvoiced || totals.total || totalExtended)}</span></div>
          <div className="flex justify-between font-medium">
            <span className={totalUnapplied > 0 ? 'text-red-600' : 'text-slate-500'}>Unapplied</span>
            <span className={`font-mono ${totalUnapplied > 0 ? 'text-red-600 font-bold' : ''}`}>{fmt(totalUnapplied || totals.balance || data?.balance)}</span>
          </div>
          <div className="border-t border-slate-200 dark:border-slate-700 my-1" />

          {/* Payments first */}
          <div className="text-[10px] font-medium text-slate-400 mb-0.5">Payments</div>
          {payments.length > 0 ? (
            <div className="space-y-0.5 mb-2">
              {payments.map((doc: any, i: number) => (
                <div
                  key={doc.id || i}
                  className="flex justify-between py-0.5 cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded px-1 -mx-1"
                  onDoubleClick={() => { if (doc.id) window.open(`/td/payment/${doc.id}`, '_blank'); }}
                  title="Double-click to open"
                >
                  <span className="font-mono text-slate-700 dark:text-slate-300">{doc.ida || `#${doc.id}`}</span>
                  <span className="font-mono text-green-700 dark:text-green-400">{fmt(doc.total ?? doc.totals?.total)}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-slate-400 mb-2">No payments</div>
          )}

          {/* Invoices second */}
          <div className="text-[10px] font-medium text-slate-400 mb-0.5">Invoices</div>
          {invoices.length > 0 ? (
            <div className="space-y-0.5">
              {invoices.map((doc: any, i: number) => (
                <div
                  key={doc.id || i}
                  className="flex justify-between py-0.5 cursor-pointer hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded px-1 -mx-1"
                  onDoubleClick={() => { if (doc.id) window.open(`/td/invoice/${doc.id}`, '_blank'); }}
                  title="Double-click to open"
                >
                  <span className="font-mono text-slate-700 dark:text-slate-300">{doc.ida || `#${doc.id}`}</span>
                  <span className="font-mono">{fmt(doc.total ?? doc.totals?.total)}</span>
                  <span className={`font-mono ${Number(doc.balance ?? doc.totals?.balance ?? 0) > 0 ? 'text-red-500' : 'text-green-600'}`}>
                    {fmt(doc.balance ?? doc.totals?.balance)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-slate-400">No invoices</div>
          )}
        </div>
      </div>
    </div>
  );
};

export const ActionsTabContent: React.FC<{ data: any; modelName: string }> = ({ data, modelName }) => {
  const actions = (data?.actions?.items ?? []) as any[];

  if (!actions.length) {
    return (
      <div className="text-center py-8 text-slate-400 text-sm">
        No actions on this {modelName}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {actions.map((action: any, idx: number) => (
        <div
          key={action.id ?? idx}
          className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 flex justify-between items-center"
        >
          <span className="font-medium text-sm text-slate-900 dark:text-white">
            {typeof action.action === 'object' ? action.action?.en : action.action ?? action.what ?? '—'}
          </span>
          <span className={`px-2 py-0.5 text-xs rounded-full ${
            action.status === 'done' || action.status === 'completed'
              ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
              : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400'
          }`}>
            {action.status ?? 'pending'}
          </span>
        </div>
      ))}
    </div>
  );
};

export const ShippingTabContent: React.FC<{ data: any }> = ({ data }) => {
  const shipments = (data?.metadata?.shipping ?? []) as any[];

  if (!shipments.length) {
    return (
      <div className="text-center py-8 text-slate-400 text-sm">
        No shipments recorded
      </div>
    );
  }

  return (
    <table className="w-full text-xs border-collapse">
      <thead>
        <tr className="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
          <th className="text-left px-2 py-1.5 font-medium">Carrier</th>
          <th className="text-left px-2 py-1.5 font-medium">Shipment ID</th>
          <th className="text-right px-2 py-1.5 font-medium">Mass</th>
          <th className="text-left px-2 py-1.5 font-medium">Status</th>
        </tr>
      </thead>
      <tbody>
        {shipments.map((s: any, i: number) => (
          <tr key={i} className="border-b border-slate-100 dark:border-slate-700">
            <td className="px-2 py-1">{s.carrier ?? '—'}</td>
            <td className="px-2 py-1 font-mono">{s.shipment_id ?? '—'}</td>
            <td className="px-2 py-1 text-right">{s.mass != null ? `${s.mass} lbs` : '—'}</td>
            <td className="px-2 py-1">{s.status ?? '—'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export const NotesTabContent: React.FC<{
  data: any;
  isEditing: boolean;
  onChange: (field: string, value: unknown) => void;
  userName?: string;
}> = ({ data, isEditing, onChange, userName }) => {
  const notes = data?.notes || data?.comments || {};
  const currentUser = userName || 'User';

  const textareaRefs = React.useRef<Record<string, HTMLTextAreaElement | null>>({});

  const handleLabelClick = (key: string) => {
    // Click on label inserts timestamp + username, then focuses textarea with cursor at end of header
    const existing = notes[key] || '';
    const ts = formatDt(new Date(), 'datetime');
    const header = `${ts} — ${currentUser}\n`;
    const newVal = header + (existing ? '\n' + existing : '');
    onChange('comments', { ...notes, [key]: newVal });

    // Focus textarea and place cursor at end of the header line
    setTimeout(() => {
      const ta = textareaRefs.current[key];
      if (ta) {
        ta.focus();
        ta.setSelectionRange(header.length, header.length);
      }
    }, 50);
  };

  return (
    <div className="space-y-3">
      {['public', 'process', 'partner'].map((key) => (
        <div key={key}>
          <label
            className={`text-xs font-medium capitalize mb-1 block ${
              isEditing
                ? 'text-blue-600 dark:text-blue-400 cursor-pointer hover:underline'
                : 'text-slate-500 dark:text-slate-400'
            }`}
            onClick={isEditing ? () => handleLabelClick(key) : undefined}
            title={isEditing ? `Click to add timestamped entry to ${key}` : undefined}
          >
            {key}
          </label>
          {isEditing ? (
            <textarea
              ref={(el) => { textareaRefs.current[key] = el; }}
              value={notes[key] ?? ''}
              onChange={(e) => onChange('comments', { ...notes, [key]: e.target.value })}
              className="w-full text-xs p-2 border border-slate-200 dark:border-slate-700 rounded bg-white dark:bg-slate-900 text-slate-900 dark:text-white min-h-[80px] font-mono"
              placeholder={`Click "${key}" label above to add a timestamped entry`}
            />
          ) : (
            <div className="text-xs text-slate-600 dark:text-slate-300 p-2 bg-slate-50 dark:bg-slate-900/50 rounded min-h-[30px] whitespace-pre-wrap font-mono">
              {notes[key] || '—'}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
