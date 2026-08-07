/**
 * InvoicePrint — printable invoice document.
 * Matches vue2020 InvoicePrint.vue layout.
 * Route: /transactions/invoice/print/:id
 */
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getRecord } from '@/api/wcapi';
import { S, fmt, fmtDate, PRINT_CSS } from './printStyles';

export default function InvoicePrint() {
  const { id } = useParams<{ id: string }>();
  const [inv, setInv] = useState<any>(null);
  const [lines, setLines] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        const res = await getRecord('invoice', Number(id)) as any;
        const record = res?.record || res;
        setInv(record);
        setLines(record?.lines || []);
      } catch (e) { console.error('Failed to load invoice:', e); }
      finally { setLoading(false); }
    })();
  }, [id]);

  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = PRINT_CSS;
    document.head.appendChild(style);
    return () => { document.head.removeChild(style); };
  }, []);

  if (loading) return <div style={{ padding: 40, textAlign: 'center' }}>Loading invoice...</div>;
  if (!inv) return <div style={{ padding: 40, textAlign: 'center', color: '#c00' }}>Invoice not found.</div>;

  const totals = inv.totals || {};
  const cost = inv.cost || {};

  return (
    <div style={S.page}>
      <button className="no-print" style={S.printBtn} onClick={() => window.print()}>Print Invoice</button>

      {/* Header */}
      <div style={S.header}>
        <div style={S.headerLeft}>
          <div>{inv.phone || ''}</div>
          <div>{inv.email || ''}</div>
          <div>{inv.address_full || ''}</div>
        </div>
        <div style={S.headerCenter}>
          <img src="/img/logo.png" alt="Logo" style={S.logo} onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
        </div>
        <div style={S.headerRight}>
          <div style={S.companyName}>{inv.company || ''}</div>
          <div style={S.docTitle}>INVOICE: {inv.ida || inv.id}</div>
        </div>
      </div>

      {/* Bill To / Ship To */}
      <div style={S.sectionRow}>
        <div style={S.sectionBox}>
          <div style={S.sectionLabel}>Bill To</div>
          <div style={S.sectionValue}>
            <div>{inv.attention || ''}</div>
            <div>{inv.company || ''}</div>
            <div>{inv.address_full || ''}</div>
          </div>
        </div>
        <div style={S.sectionBox}>
          <div style={S.sectionLabel}>Ship To</div>
          <div style={S.sectionValue}>
            <div>{inv.attention || ''}</div>
            <div>{inv.address_full || ''}</div>
          </div>
        </div>
        <div style={S.sectionBox}>
          <div style={S.sectionLabel}>Contact</div>
          <div style={S.sectionValue}>
            <div>{inv.phone || ''}</div>
            <div>{inv.email || ''}</div>
          </div>
        </div>
      </div>

      {/* Metadata */}
      <div style={S.metaRow}>
        <div style={S.metaItem}><span style={S.metaLabel}>Cust PO#</span> <span style={S.metaValue}>{inv.source?.campaign_name || '--'}</span></div>
        <div style={S.metaItem}><span style={S.metaLabel}>Account</span> <span style={S.metaValue}>{inv.ida || '--'}</span></div>
        <div style={S.metaItem}><span style={S.metaLabel}>Status</span> <span style={S.metaValue}>{inv.status || '--'}</span></div>
        <div style={S.metaItem}><span style={S.metaLabel}>Priority</span> <span style={S.metaValue}>{inv.priority || '--'}</span></div>
      </div>
      <div style={S.metaRow}>
        <div style={S.metaItem}><span style={S.metaLabel}>Invoice Date</span> <span style={S.metaValue}>{fmtDate(inv.dt_created)}</span></div>
        <div style={S.metaItem}><span style={S.metaLabel}>Terms</span> <span style={S.metaValue}>{inv.terms || '--'}</span></div>
        <div style={S.metaItem}><span style={S.metaLabel}>Price Level</span> <span style={S.metaValue}>{inv.price_level || '--'}</span></div>
      </div>

      {/* Line Items */}
      <table style={S.table}>
        <thead>
          <tr>
            <th style={S.th}>Item #</th>
            <th style={{ ...S.th, width: '40%' }}>Description</th>
            <th style={S.thRight}>Qty</th>
            <th style={S.thRight}>Unit Price</th>
            <th style={S.thRight}>Extended</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line: any, i: number) => (
            <tr key={line.id || i}>
              <td style={S.td}>{line.item?.ida_item || line.ida || '--'}</td>
              <td style={S.td}>{line.item?.description || '--'}</td>
              <td style={S.tdRight}>{line.quantity?.active ?? '--'}</td>
              <td style={S.tdRight}>{fmt(line.price?.unit)}</td>
              <td style={S.tdRight}>{fmt(line.price?.extended)}</td>
            </tr>
          ))}
          {lines.length === 0 && (
            <tr><td colSpan={5} style={{ ...S.td, textAlign: 'center', color: '#999' }}>No line items</td></tr>
          )}
        </tbody>
      </table>

      {/* Totals */}
      <div style={S.totalsWrap}>
        <div style={S.totalsLeft}>
          <p>Thank you for your business.</p>
          {inv.comments?.public?.[0] && <p style={{ marginTop: 8 }}>{inv.comments.public[0]}</p>}
        </div>
        <div style={S.totalsRight}>
          <div style={S.totalRow}><span>Subtotal</span> <span>{fmt(totals.subtotal)}</span></div>
          <div style={S.totalRow}><span>Tax</span> <span>{fmt(totals.tax)}</span></div>
          <div style={S.totalRow}><span>Shipping</span> <span>{fmt(totals.shipping)}</span></div>
          <div style={S.totalRowFinal}><span>Invoice Total</span> <span>{fmt(totals.total || inv.total)}</span></div>
          <div style={S.totalRow}><span>Balance Due</span> <span style={{ fontWeight: 700 }}>{fmt(totals.balance || inv.balance)}</span></div>
        </div>
      </div>

      {/* Footer */}
      <div style={S.footer}>
        <div style={S.sigRow}>
          <div style={S.sigBox}>
            <div style={{ fontSize: 10, color: '#666' }}>By signing below, the customer accepts the terms and conditions of this invoice.</div>
            <div style={S.sigLine}>Signature</div>
            <div style={S.sigLine}>Date</div>
          </div>
          <div style={S.sigBox}>
            <div style={S.sigLine}>Accepted By</div>
            <div style={S.sigLine}>Date</div>
          </div>
        </div>
        <div style={S.refRow}>
          <div style={S.refBox}><div style={S.sectionLabel}>Invoice #</div><div>{inv.ida || inv.id}</div></div>
          <div style={S.refBox}><div style={S.sectionLabel}>Customer #</div><div>{inv.customer_id || '--'}</div></div>
          <div style={S.refBox}><div style={S.sectionLabel}>PO #</div><div>{inv.source?.campaign_name || '--'}</div></div>
        </div>
      </div>
    </div>
  );
}
