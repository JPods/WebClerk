/**
 * Commerce Dashboard — unified 5-tab view for small businesses.
 *
 * Tabs: Sales | Purchasing | Inventory | Velocity | Accounting
 * Shared filter bar: date range, salesperson, rep, customer/vendor, warehouse
 * Desktop: any tab can pop into separate window via spawn pattern
 * Mobile: tabs within one view
 *
 * Data sources:
 *   POST /wcapi/manage/ { action: "get_sales_dashboard", params: {...} }
 *   POST /wcapi/manage/ { action: "get_purchasing_dashboard", params: {...} }
 *   POST /wcapi/manage/ { action: "get_inventory_summary", params: {...} }
 *   POST /wcapi/manage/ { action: "get_velocity_report", params: {...} }
 *   POST /wcapi/manage/ { action: "get_accounting_dashboard", params: {...} }
 */
import React, { useCallback, useEffect, useState } from 'react';
import apiClient from '../../api/axios';
import './CommerceDashboard.css';

type TabKey = 'sales' | 'purchasing' | 'inventory' | 'velocity' | 'accounting';

const TABS: { key: TabKey; label: string }[] = [
  { key: 'sales', label: 'Sales' },
  { key: 'purchasing', label: 'Purchasing' },
  { key: 'inventory', label: 'Inventory' },
  { key: 'velocity', label: 'Velocity' },
  { key: 'accounting', label: 'Accounting' },
];

// ---------------------------------------------------------------------------
// Filters
// ---------------------------------------------------------------------------

type Filters = {
  period_days: number;
  salesperson_id: string;
  rep_id: string;
  customer_id: string;
  vendor_id: string;
  warehouse_id: string;
};

const DEFAULT_FILTERS: Filters = {
  period_days: 30,
  salesperson_id: '',
  rep_id: '',
  customer_id: '',
  vendor_id: '',
  warehouse_id: '',
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function CommerceDashboard() {
  const [activeTab, setActiveTab] = useState<TabKey>('sales');
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [data, setData] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  const [theme, setTheme] = useState<'dark' | 'light'>(() =>
    (localStorage.getItem('db-theme') as 'dark' | 'light') || 'dark'
  );

  const updateFilter = (key: keyof Filters, value: string | number) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  // Fetch data for active tab when filters change
  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const actionMap: Record<TabKey, string> = {
        sales: 'get_sales_dashboard',
        purchasing: 'get_purchasing_dashboard',
        inventory: 'get_inventory_summary',
        velocity: 'get_velocity_report',
        accounting: 'get_accounting_dashboard',
      };
      const resp = await apiClient.post('/wcapi/manage/', {
        action: actionMap[activeTab],
        params: {
          period_days: filters.period_days,
          ...(filters.salesperson_id && { salesperson_id: Number(filters.salesperson_id) }),
          ...(filters.rep_id && { rep_id: Number(filters.rep_id) }),
          ...(filters.customer_id && { customer_id: Number(filters.customer_id) }),
          ...(filters.vendor_id && { vendor_id: Number(filters.vendor_id) }),
          ...(filters.warehouse_id && { warehouse_id: Number(filters.warehouse_id) }),
        },
      });
      setData(prev => ({ ...prev, [activeTab]: resp.data?.data || resp.data }));
    } catch (e) {
      console.error(`Commerce dashboard fetch failed for ${activeTab}:`, e);
    }
    setLoading(false);
  }, [activeTab, filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Spawn tab as separate window (desktop pattern)
  const spawnTab = (tab: TabKey) => {
    const params = new URLSearchParams({ tab, ...Object.fromEntries(
      Object.entries(filters).filter(([_, v]) => v !== '' && v !== 0)
    ) });
    window.open(`/commerce?${params.toString()}`, '_blank', 'width=900,height=700');
  };

  const tabData = data[activeTab] || {};

  return (
    <div className="cd-root" data-theme={theme}>

      {/* Header */}
      <header className="cd-header">
        <h1 className="cd-title">Commerce Dashboard</h1>
        <div className="cd-header-right">
          <button className="cd-btn cd-btn--ghost" onClick={fetchData}>Refresh</button>
          <button className="cd-btn cd-btn--ghost" onClick={() => {
            const n = theme === 'dark' ? 'light' : 'dark';
            setTheme(n); localStorage.setItem('db-theme', n);
          }}>{theme === 'dark' ? 'Light' : 'Dark'}</button>
        </div>
      </header>

      {/* Shared filter bar */}
      <div className="cd-filter-bar">
        <label className="cd-filter">
          Period
          <select value={filters.period_days} onChange={e => updateFilter('period_days', Number(e.target.value))}>
            <option value={7}>7 days</option>
            <option value={30}>30 days</option>
            <option value={90}>90 days</option>
            <option value={180}>6 months</option>
            <option value={365}>1 year</option>
          </select>
        </label>
        <label className="cd-filter">
          Salesperson
          <input type="text" placeholder="ID" value={filters.salesperson_id}
            onChange={e => updateFilter('salesperson_id', e.target.value)} />
        </label>
        <label className="cd-filter">
          Rep
          <input type="text" placeholder="ID" value={filters.rep_id}
            onChange={e => updateFilter('rep_id', e.target.value)} />
        </label>
        <label className="cd-filter">
          Customer
          <input type="text" placeholder="ID" value={filters.customer_id}
            onChange={e => updateFilter('customer_id', e.target.value)} />
        </label>
        <label className="cd-filter">
          Vendor
          <input type="text" placeholder="ID" value={filters.vendor_id}
            onChange={e => updateFilter('vendor_id', e.target.value)} />
        </label>
        <label className="cd-filter">
          Warehouse
          <input type="text" placeholder="ID" value={filters.warehouse_id}
            onChange={e => updateFilter('warehouse_id', e.target.value)} />
        </label>
      </div>

      {/* Tab bar */}
      <div className="cd-tab-bar">
        {TABS.map(t => (
          <button key={t.key}
            className={`cd-tab ${activeTab === t.key ? 'cd-tab--active' : ''}`}
            onClick={() => setActiveTab(t.key)}
            onDoubleClick={() => spawnTab(t.key)}
            title="Click to switch. Double-click to open in new window.">
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="cd-content">
        {loading && <div className="cd-loading">Loading...</div>}

        {activeTab === 'sales' && <SalesTab data={tabData} />}
        {activeTab === 'purchasing' && <PurchasingTab data={tabData} />}
        {activeTab === 'inventory' && <InventoryTab data={tabData} />}
        {activeTab === 'velocity' && <VelocityTab data={tabData} />}
        {activeTab === 'accounting' && <AccountingTab data={tabData} />}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab components
// ---------------------------------------------------------------------------

function MetricCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="cd-metric">
      <div className="cd-metric-value">{value}</div>
      <div className="cd-metric-label">{label}</div>
      {sub && <div className="cd-metric-sub">{sub}</div>}
    </div>
  );
}

function SalesTab({ data }: { data: any }) {
  const tx = data?.transactions || {};
  const margin = data?.margin || {};
  return (
    <div className="cd-tab-content">
      <div className="cd-metrics-row">
        <MetricCard label="Orders" value={tx.orders?.count || 0} sub={`$${(tx.orders?.total || 0).toLocaleString()}`} />
        <MetricCard label="Invoices" value={tx.invoices?.count || 0} sub={`$${(tx.invoices?.total || 0).toLocaleString()}`} />
        <MetricCard label="Proposals" value={tx.proposals?.count || 0} sub={`$${(tx.proposals?.total || 0).toLocaleString()}`} />
      </div>
      <div className="cd-metrics-row">
        <MetricCard label="Avg Margin" value={`${(margin.avg_pct || 0).toFixed(1)}%`} />
        <MetricCard label="Above Margin" value={margin.above_count || 0} />
        <MetricCard label="Below Margin" value={margin.below_count || 0} sub={`Floor: ${margin.floor || 20}%`} />
      </div>
    </div>
  );
}

function PurchasingTab({ data }: { data: any }) {
  const po = data?.purchase_orders || {};
  const wo = data?.work_orders || {};
  const receipts = data?.receipts || {};
  const layers = data?.layers || {};
  return (
    <div className="cd-tab-content">
      <div className="cd-metrics-row">
        <MetricCard label="POs Open" value={po.open || 0} />
        <MetricCard label="POs Partial" value={po.partial || 0} />
        <MetricCard label="POs Received" value={po.received || 0} />
        <MetricCard label="POs Total" value={po.total || 0} />
      </div>
      <div className="cd-metrics-row">
        <MetricCard label="WOs Open" value={wo.open || 0} />
        <MetricCard label="WOs In Progress" value={wo.in_progress || 0} />
        <MetricCard label="WOs Completed" value={wo.completed || 0} />
      </div>
      <div className="cd-metrics-row">
        <MetricCard label="Receipts" value={receipts.count || 0} sub={`Qty: ${receipts.qty || 0}`} />
        <MetricCard label="Layers Created" value={layers.created || 0} />
        <MetricCard label="Unreconciled" value={layers.unreconciled || 0} sub="Layers >30 days" />
      </div>
      {(data?.stale_pos || []).length > 0 && (
        <div className="cd-section">
          <h3 className="cd-section-title">Stale POs ({data.stale_pos.length})</h3>
          <table className="cd-table">
            <thead><tr><th>IDA</th><th>Days Open</th><th>Status</th></tr></thead>
            <tbody>
              {data.stale_pos.map((po: any) => (
                <tr key={po.po_id}><td>{po.ida}</td><td>{po.days_open}</td><td>{po.status}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function InventoryTab({ data }: { data: any }) {
  return (
    <div className="cd-tab-content">
      <div className="cd-metrics-row">
        <MetricCard label="Total Items" value={data?.total_items || 0} />
        <MetricCard label="Active Layers" value={data?.active_layers || 0} />
        <MetricCard label="Reservations" value={data?.active_reservations || 0} />
        <MetricCard label="Low Stock" value={data?.low_stock_count || 0} />
      </div>
      <div className="cd-metrics-row">
        <MetricCard label="Inventory Value" value={`$${(data?.total_value || 0).toLocaleString()}`} />
        <MetricCard label="Avg Turns" value={(data?.avg_turns || 0).toFixed(1)} />
      </div>
    </div>
  );
}

function VelocityTab({ data }: { data: any }) {
  const v = data?.velocity || data || {};
  const renderItems = (items: any[], title: string) => {
    if (!items?.length) return null;
    return (
      <div className="cd-section">
        <h3 className="cd-section-title">{title}</h3>
        <table className="cd-table">
          <thead><tr><th>IDA</th><th>Name</th><th>Velocity</th><th>Margin %</th><th>Turns/yr</th></tr></thead>
          <tbody>
            {items.map((item: any) => (
              <tr key={item.id}>
                <td>{item.ida}</td>
                <td>{(item.name || '').slice(0, 30)}</td>
                <td>{(item.margin_velocity || 0).toFixed(2)}</td>
                <td>{(item.margin_pct || 0).toFixed(1)}%</td>
                <td>{(item.annual_turns || 0).toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="cd-tab-content">
      <div className="cd-metrics-row">
        <MetricCard label="Avg Velocity" value={(v.avg || 0).toFixed(2)} />
        <MetricCard label="Stars" value={v.stars?.length || 0} sub=">20% margin, >20 turns" />
        <MetricCard label="Dead Capital" value={v.dead_capital?.length || 0} sub=">50% margin, <2 turns" />
        <MetricCard label="Volume Drivers" value={v.volume_drivers?.length || 0} sub="<10% margin, >50 turns" />
      </div>
      {renderItems(v.stars, 'Stars — High Margin, High Turns')}
      {renderItems(v.dead_capital, 'Dead Capital — High Margin, Low Turns')}
      {renderItems(v.volume_drivers, 'Volume Drivers — Low Margin, High Turns')}
      {renderItems(v.top_items, 'Top Velocity Items')}
    </div>
  );
}

function AccountingTab({ data }: { data: any }) {
  const summary = data?.account_summary || [];
  const docs = data?.document_counts || {};
  const stale = data?.unaccounted_prior || {};
  const totalDebit = summary.reduce((s: number, r: any) => s + (r.debit || 0), 0);
  const totalCredit = summary.reduce((s: number, r: any) => s + (r.credit || 0), 0);
  const balanced = Math.abs(totalDebit - totalCredit) < 0.01;

  const openStaleInDbr = (model: string) => {
    window.open(`/admin-wb?model=${model}&status=planned&ordering=dt_created`, '_blank');
  };

  const handleExport = async (format: string) => {
    try {
      const resp = await apiClient.post('/wcapi/manage/', {
        action: 'export_gl_journals',
        params: { format },
      });
      const content = resp.data?.data?.content || resp.data?.content || '';
      const blob = new Blob([content], { type: 'text/plain' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `gl_export.${format === 'quickbooks_iif' ? 'iif' : format}`;
      a.click();
    } catch (e) {
      console.error('Export failed:', e);
    }
  };

  return (
    <div className="cd-tab-content">
      {/* AR Aging summary */}
      {(data?.aging) && (
        <div className="cd-metrics-row">
          <MetricCard label="Future" value={`$${(data.aging.future || 0).toLocaleString()}`} sub="Not yet due" />
          <MetricCard label="Current" value={`$${(data.aging.current || 0).toLocaleString()}`} sub="Due ≤ 30 days" />
          <MetricCard label="1-30 Past Due" value={`$${(data.aging.period_1 || 0).toLocaleString()}`} />
          <MetricCard label="31-60 Past Due" value={`$${(data.aging.period_2 || 0).toLocaleString()}`} />
          <MetricCard label="60+ Past Due" value={`$${(data.aging.period_3 || 0).toLocaleString()}`} />
          <MetricCard label="Total AR" value={`$${(data.aging.total || 0).toLocaleString()}`} />
        </div>
      )}

      {/* Credit metrics */}
      {(data?.credit_metrics) && (
        <div className="cd-metrics-row">
          <MetricCard label="Avg Days to Pay" value={data.credit_metrics.days_avg_paid || '—'} />
          <MetricCard label="High Credit" value={`$${(data.credit_metrics.high_credit || 0).toLocaleString()}`} sub="Peak balance ever" />
          <MetricCard label="Total Exposure" value={`$${(data.credit_metrics.total_exposure || 0).toLocaleString()}`} sub="AR + open orders" />
        </div>
      )}

      {/* Document counts for period + unaccounted older documents */}
      <div className="cd-metrics-row">
        <MetricCard label="Invoices (period)" value={docs.invoices || 0} />
        <MetricCard label="Payments (period)" value={docs.payments || 0} />
        <MetricCard label="Purchases (period)" value={docs.purchases || 0} />
        <MetricCard label="Credit Notes (period)" value={docs.credit_notes || 0} />
      </div>
      {(stale.invoices > 0 || stale.payments > 0 || stale.purchases > 0) && (
        <div className="cd-section">
          <h3 className="cd-section-title">Unaccounted Prior Period</h3>
          <div className="cd-metrics-row">
            {stale.invoices > 0 && (
              <div className="cd-metric cd-metric--clickable" onClick={() => openStaleInDbr('invoice')}>
                <div className="cd-metric-value cd-metric-value--warn">{stale.invoices}</div>
                <div className="cd-metric-label">Invoices</div>
                <div className="cd-metric-sub">Click to open in DataBrowser</div>
              </div>
            )}
            {stale.payments > 0 && (
              <div className="cd-metric cd-metric--clickable" onClick={() => openStaleInDbr('payment')}>
                <div className="cd-metric-value cd-metric-value--warn">{stale.payments}</div>
                <div className="cd-metric-label">Payments</div>
                <div className="cd-metric-sub">Click to open in DataBrowser</div>
              </div>
            )}
            {stale.purchases > 0 && (
              <div className="cd-metric cd-metric--clickable" onClick={() => openStaleInDbr('purchase')}>
                <div className="cd-metric-value cd-metric-value--warn">{stale.purchases}</div>
                <div className="cd-metric-label">Purchases</div>
                <div className="cd-metric-sub">Click to open in DataBrowser</div>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="cd-section">
        <div className="cd-section-header">
          <h3 className="cd-section-title">$ by Account Code</h3>
          <div className="cd-export-btns">
            <button className="cd-btn cd-btn--small" onClick={() => handleExport('csv')}>CSV</button>
            <button className="cd-btn cd-btn--small" onClick={() => handleExport('json')}>JSON</button>
            <button className="cd-btn cd-btn--small" onClick={() => handleExport('tab')}>Tab</button>
            <button className="cd-btn cd-btn--small" onClick={() => handleExport('quickbooks_iif')}>IIF</button>
          </div>
        </div>
        <table className="cd-table cd-table--accounting">
          <thead>
            <tr>
              <th>Account Code</th>
              <th>Account Name</th>
              <th className="cd-align-right">Debit</th>
              <th className="cd-align-right">Credit</th>
            </tr>
          </thead>
          <tbody>
            {summary.map((row: any, i: number) => (
              <tr key={i}>
                <td className="cd-mono">{row.account}</td>
                <td>{row.account_name}</td>
                <td className="cd-align-right cd-mono">{row.debit ? `$${row.debit.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : ''}</td>
                <td className="cd-align-right cd-mono">{row.credit ? `$${row.credit.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : ''}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="cd-table-footer">
              <td colSpan={2}></td>
              <td className="cd-align-right cd-mono">${totalDebit.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
              <td className="cd-align-right cd-mono">${totalCredit.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
            </tr>
            <tr>
              <td colSpan={4} className="cd-balance-status">
                {balanced ? '✓ Balanced' : `⚠ Out of balance: $${(totalDebit - totalCredit).toFixed(2)}`}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
