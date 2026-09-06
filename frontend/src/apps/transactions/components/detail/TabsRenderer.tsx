/* LastChecked: 2026-08-02 | WhereUsed: UiDetail | WhoCreated: Claude */
import React from 'react';
import { useAppSelector } from '@/store/hooks';
import { getRecords, saveRecord, getModelNames } from '@/api/wcapi';
import { formatDt } from '@/utils/fieldFormatters';
import CommentsPanel from '@/apps/common/components/panels/CommentsPanel';
import FinancialsPanel from '@/apps/common/components/panels/FinancialsPanel';
import { PanelTable, type PanelColumnDef } from '@/apps/common/components/panels/PanelTable';
import { LinkedRecordsPanel } from '@/apps/common/components/panels/LinkedRecordsPanel';
import type { TabsSection } from '@/hooks/useDetailLayout';
import { formatCurrency, formatPercent } from '@/utils/stringUtils';

/** Tabs that should render as LinkedRecordsPanel with db.columns header */
const LINKED_TAB_MODELS: Record<string, string> = {
  contacts: 'contact',
  documents: 'document',
  actions: 'action',
  touches: 'touch',
  qa: 'qa',
};

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
  const currentTab = tabIds.includes(activeTab) || activeTab === '_link' ? activeTab : tabIds[0] || 'summary';

  return (
    <div className="bg-[var(--db-surface,#fff)] rounded-lg border border-[var(--db-border,#dee2e6)]">
      {/* Tab bar */}
      <div className="flex border-b border-[var(--db-border,#dee2e6)] overflow-x-auto no-print">
        {section.tabs.map((tab) => (
          <button
            key={tab.content}
            onClick={() => onTabChange(tab.content)}
            className={`px-4 py-2 db-font-xs font-medium whitespace-nowrap border-b-2 transition-colors ${
              currentTab === tab.content
                ? 'border-blue-600 text-blue-600 '
                : 'border-transparent text-[var(--db-text-muted,#6c757d)] hover:text-[var(--db-text,#212529)]'
            }`}
          >
            {tab.label}
          </button>
        ))}
        <button
          onClick={() => onTabChange('_link')}
          className={`px-4 py-2 db-font-xs font-medium whitespace-nowrap border-b-2 transition-colors ${
            currentTab === '_link'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-[var(--db-text-muted,#6c757d)] hover:text-[var(--db-text,#212529)]'
          }`}
        >
          + link
        </button>
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

    case 'contacts':
    case 'documents':
    case 'actions':
    case 'touches': {
      const linkedModel = LINKED_TAB_MODELS[tabId];
      if (linkedModel && data?.id) {
        return (
          <LinkedRecordsPanel
            linkedModel={linkedModel}
            parentModel={modelName}
            parentId={data.id}
            defaultCollapsed={false}
          />
        );
      }
      return <div className="text-center py-8 text-[var(--db-text-dim,#adb5bd)] db-font-sm">No {tabId} linked</div>;
    }

    case 'comments':
      return (
        <CommentsPanel
          comments={data?.comments}
          isEditing={isEditing}
          onChange={(comments: any) => onChange('comments', comments)}
        />
      );

    case '_link':
      return <LinkPickerContent data={data} modelName={modelName} onTabChange={onRefresh} />;

    /* qa handled by the combined linked-model case above */

    case 'shipping':
      return <ShippingTabContent data={data} />;

    case 'notes':
      return <NotesTabContent data={data} isEditing={isEditing} onChange={onChange} userName={loggedInUserName || 'User'} />;

    case 'history':
      return (
        <div className="db-font-xs text-[var(--db-text-muted,#6c757d)]">
          <pre className="whitespace-pre-wrap">{JSON.stringify(data?.metadata?.history ?? [], null, 2)}</pre>
        </div>
      );

    default: {
      // Dynamic linked model tab — any model added via + link
      if (data?.id) {
        return (
          <LinkedRecordsPanel
            linkedModel={tabId}
            parentModel={modelName}
            parentId={data.id}
            defaultCollapsed={false}
          />
        );
      }
      return (
        <div className="text-center py-8 text-[var(--db-text-dim,#adb5bd)] db-font-sm">
          No {tabId} linked
        </div>
      );
    }
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

  // All values from json.path.value — never compute independently
  const totalExtended = Number(totals.total ?? 0);
  const totalCost = Number(totals.cost ?? 0);
  const margin = Number(totals.margin ?? 0);
  const marginPct = Number(totals.margin_pc ?? 0);

  const fmt = (v: number | null | undefined) => formatCurrency(v) || '—';

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

  // Aggregate of server-provided envelope values — no server-side cross-record aggregate available
  const totalPayments = payments.reduce((s: number, d: any) => s + Number(d.totals?.total ?? 0), 0);
  const totalInvoiced = invoices.reduce((s: number, d: any) => s + Number(d.totals?.total ?? 0), 0);
  const totalUnapplied = invoices.reduce((s: number, d: any) => s + Number(d.totals?.balance ?? 0), 0);

  return (
    <div className="grid grid-cols-3 gap-6 db-font-xs">
      {/* Left: Order Totals */}
      <div>
        <div className="db-font-xs font-bold text-[var(--db-text,#212529)] mb-2">order totals</div>
        <div className="space-y-0.5">
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">lines</span><span className="font-mono">{lines.length}</span></div>
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">sell amount</span><span className="font-mono">{fmt(sell.line_sum_goods ?? 0)}</span></div>
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">discount</span><span className="font-mono">{fmt(totals.discount)}</span></div>
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">sell total</span><span className="font-mono font-medium">{fmt(sell.total ?? 0)}</span></div>
          <div className="border-t border-[var(--db-border,#dee2e6)] my-1" />
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">taxable</span><span className="font-mono">{fmt(totals.taxable)}</span></div>
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">tax</span><span className="font-mono">{fmt(totals.tax)}</span></div>
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">shipping</span><span className="font-mono">{fmt(totals.shipping)}</span></div>
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">other</span><span className="font-mono">{fmt(totals.other)}</span></div>
          <div className="border-t border-[var(--db-border,#dee2e6)] my-1" />
          <div className="flex justify-between font-bold"><span>total</span><span className="font-mono">{fmt(totals.total)}</span></div>
          <div className="border-t border-[var(--db-border,#dee2e6)] my-1" />
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">cost</span><span className="font-mono">{fmt(cost.line_sum_goods ?? 0)}</span></div>
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">freight</span><span className="font-mono">{fmt(cost.freight)}</span></div>
          {isStaff && <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">commissions</span><span className="font-mono">{fmt(cost.commissions)}</span></div>}
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">cost total</span><span className="font-mono">{fmt(cost.total ?? 0)}</span></div>
          <div className="border-t border-[var(--db-border,#dee2e6)] my-1" />
          <div className="flex justify-between">
            <span className="text-[var(--db-text-muted,#6c757d)]">margin</span>
            <span className="font-mono text-green-600">{fmt(margin)} ({formatPercent(marginPct)})</span>
          </div>
          <div className="border-t border-[var(--db-border,#dee2e6)] my-1" />
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">payments</span><span className="font-mono">{data?.finance?.payment_count ?? totals.payment_count ?? 0}</span></div>
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">received</span><span className="font-mono">{fmt(totals.received)}</span></div>
          <div className="flex justify-between font-medium"><span>balance</span><span className="font-mono">{fmt(totals.balance)}</span></div>
        </div>
      </div>

      {/* Right: Customer */}
      <div>
        <div className="db-font-xs font-bold text-[var(--db-text,#212529)] mb-2">customer</div>
        <div className="space-y-0.5">
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">company</span><span className="font-mono">{data?.company || data?.customer_company || customerData.company || customerData.display_name || '—'}</span></div>
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">price level</span><span className="font-mono">{data?.price_level || '—'}</span></div>
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">terms</span><span className="font-mono">{data?.terms || '—'}</span></div>
          <div className="border-t border-[var(--db-border,#dee2e6)] my-1" />
          <div className="db-font-xs font-medium text-[var(--db-text-dim,#adb5bd)] mb-1">Credit</div>
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">credit limit</span><span className="font-mono">{fmt(customerData.credit_limit)}</span></div>
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">available</span><span className="font-mono">{fmt(customerData.credit_available)}</span></div>
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">balance due</span><span className="font-mono">{fmt(customerData.balance_due)}</span></div>
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">current</span><span className="font-mono">{fmt(customerData.balance_current)}</span></div>
          <div className="border-t border-[var(--db-border,#dee2e6)] my-1" />
          <div className="db-font-xs font-medium text-[var(--db-text-dim,#adb5bd)] mb-1">Sales History</div>
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">mtd</span><span className="font-mono">{fmt(customerData.sales_mtd)}</span></div>
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">ytd</span><span className="font-mono">{fmt(customerData.sales_ytd)}</span></div>
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">lifetime</span><span className="font-mono">{fmt(customerData.sales_lifetime)}</span></div>
          <div className="border-t border-[var(--db-border,#dee2e6)] my-1" />
          <div className="db-font-xs font-medium text-[var(--db-text-dim,#adb5bd)] mb-1">Payment</div>
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">avg days</span><span className="font-mono">{customerData.avg_pay_days ?? '—'}</span></div>
          <div className="flex justify-between"><span className="text-[var(--db-text-muted,#6c757d)]">last payment</span><span className="font-mono">{fmt(customerData.last_payment_amount)}</span></div>
        </div>
      </div>

      {/* Right: Payments then Invoices */}
      <div>
        <div className="db-font-xs font-bold text-[var(--db-text,#212529)] mb-2">flow</div>
        <div className="space-y-0.5">
          <div className="flex justify-between font-medium"><span>total</span><span className="font-mono">{fmt(totalInvoiced || totals.total)}</span></div>
          <div className="flex justify-between font-medium">
            <span className={totalUnapplied > 0 ? 'text-red-600' : 'text-[var(--db-text-muted,#6c757d)]'}>unapplied</span>
            <span className={`font-mono ${totalUnapplied > 0 ? 'text-red-600 font-bold' : ''}`}>{fmt(totalUnapplied || totals.balance)}</span>
          </div>
          <div className="border-t border-[var(--db-border,#dee2e6)] my-1" />

          {/* Payments first */}
          <div className="db-font-xs font-medium text-[var(--db-text-dim,#adb5bd)] mb-0.5">Payments</div>
          {payments.length > 0 ? (
            <div className="space-y-0.5 mb-2">
              {payments.map((doc: any, i: number) => (
                <div
                  key={doc.id || i}
                  className="flex justify-between py-0.5 cursor-pointer hover:bg-blue-50/50 rounded px-1 -mx-1"
                  onDoubleClick={() => { if (doc.id) window.open(`/td/payment/${doc.id}`, '_blank'); }}
                  title="Double-click to open"
                >
                  <span className="font-mono text-[var(--db-text,#212529)]">{doc.ida || `#${doc.id}`}</span>
                  <span className="font-mono text-green-600">{fmt(doc.totals?.total ?? 0)}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-[var(--db-text-dim,#adb5bd)] mb-2">No payments</div>
          )}

          {/* Invoices second */}
          <div className="db-font-xs font-medium text-[var(--db-text-dim,#adb5bd)] mb-0.5">Invoices</div>
          {invoices.length > 0 ? (
            <div className="space-y-0.5">
              {invoices.map((doc: any, i: number) => (
                <div
                  key={doc.id || i}
                  className="flex justify-between py-0.5 cursor-pointer hover:bg-blue-50/50 rounded px-1 -mx-1"
                  onDoubleClick={() => { if (doc.id) window.open(`/td/invoice/${doc.id}`, '_blank'); }}
                  title="Double-click to open"
                >
                  <span className="font-mono text-[var(--db-text,#212529)]">{doc.ida || `#${doc.id}`}</span>
                  <span className="font-mono">{fmt(doc.totals?.total ?? 0)}</span>
                  <span className={`font-mono ${Number(doc.totals?.balance ?? 0) > 0 ? 'text-red-500' : 'text-green-600'}`}>
                    {fmt(doc.totals?.balance ?? 0)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-[var(--db-text-dim,#adb5bd)]">No invoices</div>
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
      <div className="text-center py-8 text-[var(--db-text-dim,#adb5bd)] db-font-sm">
        No actions on this {modelName}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {actions.map((action: any, idx: number) => (
        <div
          key={action.id ?? idx}
          className="p-3 bg-[var(--db-surface-alt,#f1f3f5)] rounded-lg border border-[var(--db-border,#dee2e6)] flex justify-between items-center"
        >
          <span className="font-medium db-font-sm text-[var(--db-text,#212529)]">
            {typeof action.action === 'object' ? action.action?.en : action.action ?? action.what ?? '—'}
          </span>
          <span className={`px-2 py-0.5 db-font-xs rounded-full ${
            action.status === 'done' || action.status === 'completed'
              ? 'bg-green-100 text-green-600'
              : 'bg-amber-100 text-amber-700 '
          }`}>
            {action.status ?? 'pending'}
          </span>
        </div>
      ))}
    </div>
  );
};

/** + link tab — shows all available models as clickable buttons */
const LinkPickerContent: React.FC<{ data: any; modelName: string; onTabChange: () => void }> = ({ data, modelName, onTabChange }) => {
  const [models, setModels] = React.useState<string[]>([]);
  React.useEffect(() => {
    getModelNames().then((res: any) => {
      setModels(Array.isArray(res?.model_names) ? res.model_names.sort() : []);
    }).catch(() => {});
  }, []);

  // Already-linked models from refs.links
  const linked = new Set(Object.keys(data?.refs?.links || {}));

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
      {models
        .filter(m => m !== modelName && !linked.has(m))
        .map(m => (
          <button
            key={m}
            onClick={() => {
              saveRecord(modelName, {
                id: data.id,
                [`refs.links.${m}`]: [],
              }).then(() => onTabChange()).catch(() => {});
            }}
            className="px-2 py-0.5 rounded db-font-xs transition-colors"
            style={{ border: '1px solid var(--db-border)', color: 'var(--db-text-dim)', background: 'var(--db-surface-alt)' }}
          >{m}</button>
        ))
      }
    </div>
  );
};

export const ShippingTabContent: React.FC<{ data: any }> = ({ data }) => {
  const shipments = (data?.metadata?.shipping ?? []) as any[];

  if (!shipments.length) {
    return (
      <div className="text-center py-8 text-[var(--db-text-dim,#adb5bd)] db-font-sm">
        No shipments recorded
        <div className="font-mono db-font-xs mt-1" style={{ color: 'var(--db-text-dim, #adb5bd)' }}>metadata.shipping</div>
      </div>
    );
  }

  return (
    <table className="w-full db-font-xs border-collapse">
      <thead>
        <tr className="bg-[var(--db-surface-alt,#f1f3f5)] text-[var(--db-text,#212529)]">
          <th className="text-left px-2 py-1.5 font-medium">carrier</th>
          <th className="text-left px-2 py-1.5 font-medium">shipment id</th>
          <th className="text-right px-2 py-1.5 font-medium">mass</th>
          <th className="text-left px-2 py-1.5 font-medium">status</th>
        </tr>
      </thead>
      <tbody>
        {shipments.map((s: any, i: number) => (
          <tr key={i} className="border-b border-[var(--db-border,#dee2e6)]">
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
            className={`db-font-xs font-medium capitalize mb-1 block ${
              isEditing
                ? 'text-blue-600  cursor-pointer hover:underline'
                : 'text-[var(--db-text-muted,#6c757d)]'
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
              className="w-full db-font-xs p-2 border border-[var(--db-border,#dee2e6)] rounded bg-[var(--db-surface-alt,#fff)] text-[var(--db-text,#212529)] min-h-[80px] font-mono"
              placeholder={`Click "${key}" label above to add a timestamped entry`}
            />
          ) : (
            <div className="db-font-xs text-[var(--db-text,#212529)] p-2 bg-[var(--db-surface-alt,#f1f3f5)] rounded min-h-[30px] whitespace-pre-wrap font-mono">
              {notes[key] || '—'}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
