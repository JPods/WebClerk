/**
 * PortalDashboard — role-aware landing page for portal users (customer/vendor/rep).
 *
 * The backend's inject_role_filters ensures each role only receives their own data.
 * This component renders a dashboard tailored to the user's portal role.
 */
import React, { useEffect, useState } from 'react';
import { useAppSelector } from '../../store/hooks';
import { getRecords } from '../../api/wcapi';
import { formatCurrency } from '@/utils/stringUtils';

interface PortalCard {
  title: string;
  value: string | number;
  subtitle?: string;
  link?: string;
}

interface PortalRecord {
  id: number;
  ida?: string;
  status?: string;
  totals?: { total?: number; balance?: number };
  dt_created?: string;
  company?: string;
  display_name?: string;
  name?: string;
  quantity?: {
    on_hand?: number;
    available?: number;
    vendor_min?: number;
    vendor_max?: number;
    inventory_min?: number;
    inventory_max?: number;
    on_po?: number;
  };
  [key: string]: any;
}

/* ── helpers ── */
const fmt = (n?: number) => formatCurrency(n) || '$0.00';

const statusColor = (s?: string) => {
  if (!s) return 'var(--color-gray-400)';
  const lc = s.toLowerCase();
  if (lc === 'open' || lc === 'active') return 'var(--color-brand-500)';
  if (lc === 'shipped' || lc === 'complete' || lc === 'paid') return 'var(--color-success-500)';
  if (lc === 'overdue' || lc === 'past_due') return 'var(--color-error-500)';
  return 'var(--color-gray-500)';
};

/* ── kanban indicator ── */
const KanbanBar: React.FC<{ qty: number; min: number; max: number }> = ({ qty, min, max }) => {
  const range = max - min || 1;
  const pct = Math.max(0, Math.min(100, ((qty - min) / range) * 100));
  let color = 'var(--color-success-500)';
  if (qty <= min) color = 'var(--color-error-500)';
  else if (pct < 30) color = 'var(--color-warning-500)';
  return (
    <div className="wc-kanban-bar">
      <div className="wc-kanban-fill" style={{ width: `${pct}%`, backgroundColor: color }} />
      <span className="wc-kanban-label">{qty} (min {min} / max {max})</span>
    </div>
  );
};

/* ── record list ── */
const RecordList: React.FC<{
  title: string;
  records: PortalRecord[];
  columns: { key: string; label: string; render?: (r: PortalRecord) => React.ReactNode }[];
  onRowClick?: (r: PortalRecord) => void;
}> = ({ title, records, columns, onRowClick }) => (
  <div className="wc-portal-section">
    <h3 className="wc-portal-section-title">{title}</h3>
    {records.length === 0 ? (
      <p className="wc-portal-empty">No records</p>
    ) : (
      <table className="wc-portal-table" data-wc="portal-table">
        <thead>
          <tr>{columns.map(c => <th key={c.key}>{c.label}</th>)}</tr>
        </thead>
        <tbody>
          {records.map(r => (
            <tr key={r.id} onClick={() => onRowClick?.(r)} className={onRowClick ? 'wc-clickable' : ''}>
              {columns.map(c => (
                <td key={c.key}>{c.render ? c.render(r) : String(r[c.key] ?? '')}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    )}
  </div>
);

/* ── summary cards ── */
const SummaryCards: React.FC<{ cards: PortalCard[] }> = ({ cards }) => (
  <div className="wc-portal-cards">
    {cards.map((c, i) => (
      <div key={i} className="wc-portal-card">
        <div className="wc-portal-card-title">{c.title}</div>
        <div className="wc-portal-card-value">{c.value}</div>
        {c.subtitle && <div className="wc-portal-card-subtitle">{c.subtitle}</div>}
      </div>
    ))}
  </div>
);

/* ── customer dashboard ── */
const CustomerDashboard: React.FC = () => {
  const [orders, setOrders] = useState<PortalRecord[]>([]);
  const [invoices, setInvoices] = useState<PortalRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getRecords('order', { limit: 20, sort: '-dt_created' }),
      getRecords('invoice', { limit: 20, sort: '-dt_created' }),
    ]).then(([o, i]) => {
      setOrders(o?.results || []);
      setInvoices(i?.results || []);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="wc-portal-loading">Loading...</div>;

  const openInvoices = invoices.filter(i => i.status !== 'paid' && i.status !== 'void');
  // Aggregate of server-provided envelope values — no server-side aggregate available
  const totalBalance = openInvoices.reduce((s, i) => s + (i.totals?.balance ?? 0), 0);
  const recentOrders = orders.slice(0, 5);

  return (
    <>
      <SummaryCards cards={[
        { title: 'Open Orders', value: orders.filter(o => o.status === 'open').length },
        { title: 'Open Invoices', value: openInvoices.length },
        { title: 'Balance Due', value: fmt(totalBalance) },
        { title: 'Total Orders', value: orders.length },
      ]} />
      <RecordList
        title="Recent Orders"
        records={recentOrders}
        columns={[
          { key: 'ida', label: 'Order #' },
          { key: 'status', label: 'status', render: r => <span style={{ color: statusColor(r.status) }}>{r.status}</span> },
          { key: 'total', label: 'total', render: r => fmt(r.totals?.total) },
          { key: 'dt_created', label: 'date', render: r => r.dt_created ? new Date(r.dt_created).toLocaleDateString() : '' },
        ]}
      />
      <RecordList
        title="Open Invoices"
        records={openInvoices}
        columns={[
          { key: 'ida', label: 'Invoice #' },
          { key: 'status', label: 'status', render: r => <span style={{ color: statusColor(r.status) }}>{r.status}</span> },
          { key: 'balance', label: 'balance', render: r => fmt(r.totals?.balance) },
          { key: 'dt_created', label: 'date', render: r => r.dt_created ? new Date(r.dt_created).toLocaleDateString() : '' },
        ]}
      />
    </>
  );
};

/* ── vendor dashboard ── */
const VendorDashboard: React.FC = () => {
  const [items, setItems] = useState<PortalRecord[]>([]);
  const [purchases, setPurchases] = useState<PortalRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getRecords('item', { limit: 50, sort: 'ida' }),
      getRecords('purchase', { limit: 20, sort: '-dt_created' }),
    ]).then(([i, p]) => {
      setItems(i?.results || []);
      setPurchases(p?.results || []);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="wc-portal-loading">Loading...</div>;

  const belowMin = items.filter(i => {
    const qty = i.quantity?.on_hand ?? 0;
    const min = i.quantity?.vendor_min ?? i.quantity?.inventory_min ?? 0;
    return min > 0 && qty <= min;
  });

  return (
    <>
      <SummaryCards cards={[
        { title: 'Items Supplied', value: items.length },
        { title: 'Below Min', value: belowMin.length, subtitle: belowMin.length > 0 ? 'Needs replenishment' : 'All stocked' },
        { title: 'Open POs', value: purchases.filter(p => p.status === 'open').length },
        { title: 'Total POs', value: purchases.length },
      ]} />
      {belowMin.length > 0 && (
        <RecordList
          title="Items Below Minimum — Needs Replenishment"
          records={belowMin}
          columns={[
            { key: 'ida', label: 'sku' },
            { key: 'name', label: 'item' },
            { key: 'kanban', label: 'inventory level', render: r => (
              <KanbanBar
                qty={r.quantity?.on_hand ?? 0}
                min={r.quantity?.vendor_min ?? r.quantity?.inventory_min ?? 0}
                max={r.quantity?.vendor_max ?? r.quantity?.inventory_max ?? 100}
              />
            )},
            { key: 'on_po', label: 'on po', render: r => r.quantity?.on_po ?? 0 },
          ]}
        />
      )}
      <RecordList
        title="All Supplied Items"
        records={items}
        columns={[
          { key: 'ida', label: 'sku' },
          { key: 'name', label: 'item' },
          { key: 'kanban', label: 'inventory level', render: r => {
            const min = r.quantity?.vendor_min ?? r.quantity?.inventory_min ?? 0;
            const max = r.quantity?.vendor_max ?? r.quantity?.inventory_max ?? 100;
            return min > 0
              ? <KanbanBar qty={r.quantity?.on_hand ?? 0} min={min} max={max} />
              : String(r.quantity?.on_hand ?? 0);
          }},
        ]}
      />
      <RecordList
        title="Recent Purchase Orders"
        records={purchases.slice(0, 10)}
        columns={[
          { key: 'ida', label: 'PO #' },
          { key: 'status', label: 'status', render: r => <span style={{ color: statusColor(r.status) }}>{r.status}</span> },
          { key: 'total', label: 'total', render: r => fmt(r.totals?.total) },
          { key: 'dt_created', label: 'date', render: r => r.dt_created ? new Date(r.dt_created).toLocaleDateString() : '' },
        ]}
      />
    </>
  );
};

/* ── rep dashboard ── */
const RepDashboard: React.FC = () => {
  const [orders, setOrders] = useState<PortalRecord[]>([]);
  const [customers, setCustomers] = useState<PortalRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getRecords('order', { limit: 20, sort: '-dt_created' }),
      getRecords('customer', { limit: 50, sort: 'company' }),
    ]).then(([o, c]) => {
      setOrders(o?.results || []);
      setCustomers(c?.results || []);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="wc-portal-loading">Loading...</div>;

  const openOrders = orders.filter(o => o.status === 'open');
  // Aggregate of server-provided envelope values — no server-side aggregate available
  const totalSales = orders.reduce((s, o) => s + (o.totals?.total ?? 0), 0);

  return (
    <>
      <SummaryCards cards={[
        { title: 'My Customers', value: customers.length },
        { title: 'Open Orders', value: openOrders.length },
        { title: 'Total Sales', value: fmt(totalSales) },
        { title: 'Total Orders', value: orders.length },
      ]} />
      <RecordList
        title="My Customers"
        records={customers}
        columns={[
          { key: 'company', label: 'company' },
          { key: 'ida', label: 'Account #' },
        ]}
      />
      <RecordList
        title="Recent Orders"
        records={orders.slice(0, 10)}
        columns={[
          { key: 'ida', label: 'Order #' },
          { key: 'status', label: 'status', render: r => <span style={{ color: statusColor(r.status) }}>{r.status}</span> },
          { key: 'total', label: 'total', render: r => fmt(r.totals?.total) },
          { key: 'dt_created', label: 'date', render: r => r.dt_created ? new Date(r.dt_created).toLocaleDateString() : '' },
        ]}
      />
    </>
  );
};

/* ── main portal dashboard ── */
const PortalDashboard: React.FC = () => {
  const user = useAppSelector(s => s.auth.user);
  const roles = user?.roles || [];

  const portalRole = roles.find(r =>
    ['user_customer', 'user_vendor', 'user_manufacturer', 'user_rep'].includes(r)
  );

  return (
    <div className="wc-portal-dashboard">
      <div className="wc-portal-header">
        <h2>Welcome, {user?.name_first || 'User'}</h2>
        {user?.company && <span className="wc-portal-company">{user.company}</span>}
      </div>
      {portalRole === 'user_customer' && <CustomerDashboard />}
      {portalRole === 'user_vendor' || portalRole === 'user_manufacturer' ? <VendorDashboard /> : null}
      {portalRole === 'user_rep' && <RepDashboard />}
      {!portalRole && (
        <p className="wc-portal-empty">No portal role assigned. Contact your administrator.</p>
      )}
    </div>
  );
};

export default PortalDashboard;
