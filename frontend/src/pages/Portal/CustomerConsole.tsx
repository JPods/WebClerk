/**
 * CustomerConsole — the customer's (and buyer's) landing page (Bill, 2026-09-28).
 *
 * "Customers should only be able to place new orders, pay for them, and add a limited number
 * of action records to request support" — plus their own contact, their customer record,
 * their quotes and invoices, and the published catalog with images. The server enforces all
 * of it (access.PORTAL_CUSTOMER_ACCESS): it stamps their customer on what they create, prices
 * every line, caps open requests, and refuses the rest. This page only shows what it answers
 * and passes its refusals through as they are worded.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { getRecord, getRecords, newRecord, refusedFrom, saveRecord } from '../../api/wcapi';
import { useAppSelector } from '../../store/hooks';
import { formatCurrency, formatDate } from '@/utils/stringUtils';
import SpreedlyCardForm from '../../apps/transactions/components/SpreedlyCardForm';
import { fetchGatewayConfig } from '../../apps/transactions/models/cash/services/cashApi';
import { Modal } from '@/components/ui/modal';

type Rec = Record<string, any>;
type Tab = 'home' | 'order' | 'invoices' | 'support' | 'account';

/** Mirrors access.PORTAL_OPEN_ACTIONS; the server's 409 is the authority. */
const OPEN_REQUEST_LIMIT = 3;
const CLOSED = ['complete', 'completed', 'closed', 'canceled', 'cancelled', 'done'];
const CONTACT_FIELDS: Array<[string, string]> = [
  ['name_first', 'First name'], ['name_last', 'Last name'], ['title', 'Title'],
  ['company', 'Company'], ['department', 'Department'],
];

const money = (n?: number | string) => formatCurrency(n ?? 0) || '$0.00';
const when = (r: Rec) => formatDate(typeof r.dt_created === 'number' ? r.dt_created : Date.parse(r.dt_created));
const imageUrl = (ida: string, size: 'tn' | 'md') => `/wcapi/_image/Item/${encodeURIComponent(ida)}/${size}.jpg`;
/** The one price a customer is shown: their level's (the server sends only that one). */
const unitPrice = (item: Rec): number | undefined => {
  const price = item.price || {};
  const n = Object.values(price).find((v) => typeof v === 'number');
  return typeof n === 'number' ? n : undefined;
};

const Notice: React.FC<{ text: string | null; kind?: 'error' | 'ok' }> = ({ text, kind = 'error' }) =>
  text ? <div className={`wc-console-notice wc-console-notice-${kind}`} role="status">{text}</div> : null;

const Table: React.FC<{ head: string[]; rows: React.ReactNode[][]; empty: string }> = ({ head, rows, empty }) =>
  rows.length === 0 ? <p className="wc-portal-empty">{empty}</p> : (
    <table className="wc-portal-table">
      <thead><tr>{head.map((h) => <th key={h}>{h}</th>)}</tr></thead>
      <tbody>{rows.map((cells, i) => <tr key={i}>{cells.map((c, j) => <td key={j}>{c}</td>)}</tr>)}</tbody>
    </table>
  );

/* ── Order: the catalog, a cart, place the order ─────────────────────────── */
const OrderPanel: React.FC<{ onPlaced: () => void }> = ({ onPlaced }) => {
  const [keyword, setKeyword] = useState('');
  const [items, setItems] = useState<Rec[]>([]);
  const [cart, setCart] = useState<Record<number, { item: Rec; qty: number }>>({});
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ text: string; kind: 'error' | 'ok' } | null>(null);

  const search = useCallback((kw: string) => {
    getRecords('item', { keyword: kw || undefined, limit: 48, sort: 'name' })
      .then((r) => setItems(r?.results || []))
      .catch((e) => setMessage({ text: refusedFrom(e, 'Could not load the catalog').message, kind: 'error' }));
  }, []);
  useEffect(() => { search(''); }, [search]);

  const add = (item: Rec) => setCart((c) => ({ ...c, [item.id]: { item, qty: (c[item.id]?.qty || 0) + 1 } }));
  const setQty = (id: number, qty: number) =>
    setCart((c) => { const n = { ...c }; if (qty <= 0) delete n[id]; else n[id] = { ...n[id], qty }; return n; });
  const lines = Object.values(cart);
  const estimate = lines.reduce((s, l) => s + (unitPrice(l.item) || 0) * l.qty, 0);

  const place = async () => {
    setBusy(true); setMessage(null);
    try {
      // `new` makes the order for their customer; the lines are its next save, priced by the server.
      const made = await newRecord('order');
      await saveRecord('order', {
        id: made.id, version: made.record?.version,
        ...(note.trim() ? { attention: note.trim() } : {}),
        lines: lines.map((l) => ({ item: { item_id: l.item.id }, quantity: { active: l.qty } })),
      });
      setCart({}); setNote('');
      setMessage({ text: `Order ${made.record?.ida || made.id} placed. We will confirm it shortly.`, kind: 'ok' });
      onPlaced();
    } catch (e) {
      setMessage({ text: refusedFrom(e, 'The order was not placed').message, kind: 'error' });
    } finally { setBusy(false); }
  };

  return (
    <div className="wc-console-order">
      <div className="wc-console-catalog">
        <form className="wc-console-search" onSubmit={(e) => { e.preventDefault(); search(keyword); }}>
          <input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="Search the catalog" />
          <button type="submit">Search</button>
        </form>
        <div className="wc-console-grid">
          {items.map((item) => (
            <div key={item.id} className="wc-console-item">
              <img src={imageUrl(item.ida, 'md')} alt={item.name || item.ida}
                   onError={(e) => { (e.target as HTMLImageElement).style.visibility = 'hidden'; }} />
              <div className="wc-console-item-name">{item.name || item.ida}</div>
              <div className="wc-console-item-sku">{item.sku || item.ida}</div>
              <div className="wc-console-item-price">{unitPrice(item) !== undefined ? money(unitPrice(item)) : 'Price on request'}</div>
              <button type="button" onClick={() => add(item)}>Add</button>
            </div>
          ))}
          {items.length === 0 && <p className="wc-portal-empty">Nothing in the catalog matches.</p>}
        </div>
      </div>
      <aside className="wc-console-cart">
        <h3 className="wc-portal-section-title">Your order</h3>
        {lines.length === 0 ? <p className="wc-portal-empty">Add items from the catalog.</p> : (
          <>
            {lines.map(({ item, qty }) => (
              <div key={item.id} className="wc-console-cart-line">
                <img src={imageUrl(item.ida, 'tn')} alt="" onError={(e) => { (e.target as HTMLImageElement).style.visibility = 'hidden'; }} />
                <span>{item.name || item.ida}</span>
                <input type="number" min={0} value={qty} aria-label={`Quantity of ${item.name || item.ida}`}
                       onChange={(e) => setQty(item.id, parseInt(e.target.value, 10) || 0)} />
              </div>
            ))}
            <div className="wc-console-cart-total">Estimate {money(estimate)}</div>
            <p className="wc-console-hint">Prices are set when the order is saved, at your account's level.</p>
            <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Attention / note (optional)" />
            <button type="button" disabled={busy} onClick={place}>{busy ? 'Placing…' : 'Place order'}</button>
          </>
        )}
        <Notice text={message?.text ?? null} kind={message?.kind} />
      </aside>
    </div>
  );
};

/* ── Invoices: what is owed, and a Pay dialog (check, or card once a gateway is set up) ── */
type PayBy = 'check' | 'card';

const PayDialog: React.FC<{ invoice: Rec; cardReady: boolean; onClose: () => void; onPaid: () => void }> =
  ({ invoice, cardReady, onClose, onPaid }) => {
  const [payBy, setPayBy] = useState<PayBy>(cardReady ? 'card' : 'check');
  const owed = Number(invoice.totals?.balance || 0);
  // The company's published pay_to (company profile config.company.pay_to, Bill 2026-09-29).
  const company = useAppSelector((s) => s.company?.company) || {};
  const payTo = company.pay_to || {};
  return (
    <Modal isOpen onClose={onClose} className="wc-console-dialog">
      <h3 className="wc-portal-section-title">Pay invoice {invoice.ida}</h3>
      <p>Amount due: <strong>{money(owed)}</strong></p>
      <label className="wc-console-field">
        <span>Pay by</span>
        <select value={payBy} onChange={(e) => setPayBy(e.target.value as PayBy)} aria-label="Pay by">
          <option value="check">Check</option>
          {/* Card is offered once a card gateway is set up (Bill, 2026-09-29). */}
          <option value="card" disabled={!cardReady}>Card{cardReady ? '' : ' (not set up yet)'}</option>
        </select>
      </label>
      {payBy === 'check' && (
        <div className="wc-console-check">
          <p>Make the check payable to <strong>{payTo.name || company.name || 'the company named on your invoice'}</strong>
            {' '}for <strong>{money(owed)}</strong>, and write invoice <strong>{invoice.ida}</strong> on it.</p>
          {payTo.address_full ? (
            <address className="wc-console-payto">
              Mail it to:<br />{payTo.name || company.name}<br />
              {(payTo.address?.street1 ? [payTo.address.street1, payTo.address.street2,
                `${payTo.address.city || ''}${payTo.address.state ? ', ' + payTo.address.state : ''} ${payTo.address.zip || ''}`.trim()]
                : [payTo.address_full]).filter(Boolean).map((line: string) => <React.Fragment key={line}>{line}<br /></React.Fragment>)}
            </address>
          ) : <p>Mail it to the remit-to address on your invoice.</p>}
          {(company.phone || company.email) && (
            <p className="wc-console-hint">Questions: {[company.phone, company.email].filter(Boolean).join(' · ')}</p>
          )}
          <p className="wc-console-hint">Your balance changes when we receive the check.</p>
          <button type="button" onClick={onClose}>Done</button>
        </div>
      )}
      {payBy === 'card' && cardReady && (
        <SpreedlyCardForm invoiceId={invoice.id} amount={owed} onSuccess={() => { onClose(); onPaid(); }} />
      )}
    </Modal>
  );
};

const InvoicesPanel: React.FC<{ invoices: Rec[]; onPaid: () => void }> = ({ invoices, onPaid }) => {
  const [paying, setPaying] = useState<Rec | null>(null);
  const [cardReady, setCardReady] = useState(false);
  useEffect(() => {
    fetchGatewayConfig().then((c) => setCardReady(Boolean(c?.environment_key))).catch(() => setCardReady(false));
  }, []);
  const owed = (i: Rec) => Number(i.totals?.balance || 0);
  return (
    <>
      {paying && <PayDialog invoice={paying} cardReady={cardReady} onClose={() => setPaying(null)} onPaid={onPaid} />}
      <Table head={['Invoice', 'Date', 'Total', 'Balance', '']} empty="No invoices yet."
             rows={invoices.map((i) => [i.ida, when(i), money(i.totals?.total), money(owed(i)),
               owed(i) > 0 ? <button type="button" onClick={() => setPaying(i)}>Pay</button> : 'Paid'])} />
    </>
  );
};

/* ── Support: their requests, and a new one (at most OPEN_REQUEST_LIMIT open) ── */
const SupportPanel: React.FC<{ requests: Rec[]; onAdded: () => void }> = ({ requests, onAdded }) => {
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ text: string; kind: 'error' | 'ok' } | null>(null);
  const open = requests.filter((r) => !CLOSED.includes(String(r.status || '').toLowerCase()));
  const full = open.length >= OPEN_REQUEST_LIMIT;

  const send = async () => {
    setBusy(true); setMessage(null);
    try {
      const made = await newRecord('action');
      await saveRecord('action', { id: made.id, version: made.record?.version, description: { en: text.trim() } });
      setText('');
      setMessage({ text: 'Request sent. We will answer here.', kind: 'ok' });
      onAdded();
    } catch (e) {
      setMessage({ text: refusedFrom(e, 'The request was not sent').message, kind: 'error' });
    } finally { setBusy(false); }
  };
  const lastReply = (r: Rec) => {
    const thread = r.comments?.partner;
    return Array.isArray(thread) && thread.length ? thread[thread.length - 1]?.mgs : '';
  };

  return (
    <>
      <div className="wc-console-request">
        <h3 className="wc-portal-section-title">New request</h3>
        {full ? (
          <p className="wc-console-hint">You have {open.length} open requests, the most at one time. Add to one of them
            by replying, or wait until one is closed.</p>
        ) : (
          <>
            <textarea value={text} onChange={(e) => setText(e.target.value)} rows={4}
                      placeholder="What do you need? Include an order or invoice number if it helps." />
            <button type="button" disabled={busy || !text.trim()} onClick={send}>{busy ? 'Sending…' : 'Send request'}</button>
            <span className="wc-console-hint">{open.length} of {OPEN_REQUEST_LIMIT} open</span>
          </>
        )}
        <Notice text={message?.text ?? null} kind={message?.kind} />
      </div>
      <Table head={['Request', 'Date', 'Status', 'Latest reply']} empty="No requests yet."
             rows={requests.map((r) => [r.description?.en || r.ida, when(r), r.status || 'open', lastReply(r)])} />
    </>
  );
};

/* ── Account: their contact (editable) and their customer record (read) ──── */
const AccountPanel: React.FC<{ contactId: number | string | undefined }> = ({ contactId }) => {
  const [contact, setContact] = useState<Rec | null>(null);
  const [customer, setCustomer] = useState<Rec | null>(null);
  const [draft, setDraft] = useState<Rec>({});
  const [message, setMessage] = useState<{ text: string; kind: 'error' | 'ok' } | null>(null);

  const load = useCallback(() => {
    if (contactId) getRecord('contact', Number(contactId)).then((r) => { setContact(r?.record || null); setDraft({}); });
    getRecords('customer', { limit: 1 }).then((r) => setCustomer(r?.results?.[0] || null));
  }, [contactId]);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    if (!contact) return;
    setMessage(null);
    try {
      await saveRecord('contact', { id: contact.id, version: contact.version, ...draft });
      setMessage({ text: 'Saved.', kind: 'ok' });
      load();
    } catch (e) {
      setMessage({ text: refusedFrom(e, 'Not saved').message, kind: 'error' });
    }
  };

  return (
    <div className="wc-console-account">
      <section className="wc-portal-section">
        <h3 className="wc-portal-section-title">You</h3>
        {contact && CONTACT_FIELDS.map(([key, label]) => (
          <label key={key} className="wc-console-field">
            <span>{label}</span>
            <input value={draft[key] ?? contact[key] ?? ''} onChange={(e) => setDraft((d) => ({ ...d, [key]: e.target.value }))} />
          </label>
        ))}
        {contact?.email && <p className="wc-console-hint">Sign-in email: {contact.email}</p>}
        <button type="button" disabled={Object.keys(draft).length === 0} onClick={save}>Save</button>
        <Notice text={message?.text ?? null} kind={message?.kind} />
      </section>
      <section className="wc-portal-section">
        <h3 className="wc-portal-section-title">Your account</h3>
        {customer ? (
          <dl className="wc-console-dl">
            <dt>Company</dt><dd>{customer.company}</dd>
            {customer.terms && <><dt>Terms</dt><dd>{customer.terms}</dd></>}
            {customer.email && <><dt>Email</dt><dd>{customer.email}</dd></>}
            {customer.status && <><dt>Status</dt><dd>{customer.status}</dd></>}
          </dl>
        ) : <p className="wc-portal-empty">No customer account is linked to this login. Send a request and we will link it.</p>}
      </section>
    </div>
  );
};

/* ── The console ─────────────────────────────────────────────────────────── */
const CustomerConsole: React.FC = () => {
  const user = useAppSelector((s) => s.auth.user);
  const [tab, setTab] = useState<Tab>('home');
  const [orders, setOrders] = useState<Rec[]>([]);
  const [quotes, setQuotes] = useState<Rec[]>([]);
  const [invoices, setInvoices] = useState<Rec[]>([]);
  const [requests, setRequests] = useState<Rec[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    const list = (model: string) => getRecords(model, { limit: 50, sort: '-dt_created' }).then((r) => r?.results || []);
    Promise.all([list('order'), list('quote'), list('invoice'), list('action')])
      .then(([o, q, i, a]) => { setOrders(o); setQuotes(q); setInvoices(i); setRequests(a); setError(null); })
      .catch((e) => setError(refusedFrom(e, 'Could not load your account').message));
  }, []);
  useEffect(() => { load(); }, [load]);

  const balanceDue = useMemo(() => invoices.reduce((s, i) => s + Number(i.totals?.balance || 0), 0), [invoices]);
  const openRequests = requests.filter((r) => !CLOSED.includes(String(r.status || '').toLowerCase())).length;

  const tabs: Array<[Tab, string]> = [
    ['home', 'Home'], ['order', 'Place an order'], ['invoices', 'Invoices'], ['support', 'Support'], ['account', 'Account'],
  ];

  return (
    <>
      <nav className="wc-console-tabs" aria-label="Customer console">
        {tabs.map(([key, label]) => (
          <button key={key} type="button" className={tab === key ? 'is-active' : ''} onClick={() => setTab(key)}>{label}</button>
        ))}
      </nav>
      <Notice text={error} />

      {tab === 'home' && (
        <>
          <div className="wc-portal-cards">
            <button type="button" className="wc-portal-card" onClick={() => setTab('invoices')}>
              <div className="wc-portal-card-title">Balance due</div>
              <div className="wc-portal-card-value">{money(balanceDue)}</div>
            </button>
            <button type="button" className="wc-portal-card" onClick={() => setTab('order')}>
              <div className="wc-portal-card-title">Orders</div>
              <div className="wc-portal-card-value">{orders.length}</div>
              <div className="wc-portal-card-subtitle">Place an order</div>
            </button>
            <button type="button" className="wc-portal-card" onClick={() => setTab('support')}>
              <div className="wc-portal-card-title">Open requests</div>
              <div className="wc-portal-card-value">{openRequests}</div>
              <div className="wc-portal-card-subtitle">of {OPEN_REQUEST_LIMIT}</div>
            </button>
          </div>
          <section className="wc-portal-section">
            <h3 className="wc-portal-section-title">Recent orders</h3>
            <Table head={['Order', 'Date', 'Status', 'Total']} empty="No orders yet."
                   rows={orders.slice(0, 10).map((o) => [o.ida, when(o), o.status || '', money(o.totals?.total)])} />
          </section>
          {quotes.length > 0 && (
            <section className="wc-portal-section">
              <h3 className="wc-portal-section-title">Quotes</h3>
              <Table head={['Quote', 'Date', 'Status', 'Total']} empty=""
                     rows={quotes.slice(0, 10).map((q) => [q.ida, when(q), q.status || '', money(q.totals?.total)])} />
            </section>
          )}
        </>
      )}
      {tab === 'order' && <OrderPanel onPlaced={load} />}
      {tab === 'invoices' && <InvoicesPanel invoices={invoices} onPaid={load} />}
      {tab === 'support' && <SupportPanel requests={requests} onAdded={load} />}
      {tab === 'account' && <AccountPanel contactId={user?.id} />}
    </>
  );
};

export default CustomerConsole;
