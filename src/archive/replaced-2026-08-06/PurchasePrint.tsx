/**
 * PurchasePrint — printable purchase order document.
 * Route: /transactions/purchase/print/:id
 */
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { getRecord } from '@/api/wcapi';
import { S, fmt, fmtDate, PRINT_CSS } from './printStyles';

export default function PurchasePrint() {
  const { id } = useParams<{ id: string }>();
  const [po, setPo] = useState<any>(null);
  const [lines, setLines] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    (async () => {
      try {
        const res = await getRecord('purchase', Number(id)) as any;
        const record = res?.record || res;
        setPo(record);
        setLines(record?.lines || []);
      } catch (e) { console.error('Failed to load purchase order:', e); }
      finally { setLoading(false); }
    })();
  }, [id]);

  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = PRINT_CSS;
    document.head.appendChild(style);
    return () => { document.head.removeChild(style); };
  }, []);

  if (loading) return <div style={{ padding: 40, textAlign: 'center' }}>Loading purchase order...</div>;
  if (!po) return <div style={{ padding: 40, textAlign: 'center', color: '#c00' }}>Purchase order not found.</div>;

  const totals = po.totals || {};

  return (
    <div style={S.page}>
      <button className="no-print" style={S.printBtn} onClick={() => window.print()}>Print Purchase Order</button>

      {/* Header */}
      <div style={S.header}>
        <div style={S.headerLeft}>
          <div>{po.phone || ''}</div>
          <div>{po.email || ''}</div>
          <div>{po.address_full || ''}</div>
        </div>
        <div style={S.headerCenter}>
          <img src="/img/logo.png" alt="Logo" style={S.logo} onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
        </div>
        <div style={S.headerRight}>
          <div style={S.companyName}>{po.company || ''}</div>
          <div style={S.docTitle}>PURCHASE ORDER: {po.ida || po.id}</div>
        </div>
      </div>

      {/* Vendor / Ship To */}
      <div style={S.sectionRow}>
        <div style={S.sectionBox}>
          <div style={S.sectionLabel}>Vendor</div>
          <div style={S.sectionValue}>
            <div>{po.vendor_name || po.attention || ''}</div>
            <div>{po.vendor_address || po.address_full || ''}</div>
            <div>{po.vendor_phone || ''}</div>
            <div>{po.vendor_email || ''}</div>
          </div>
        </div>
        <div style={S.sectionBox}>
          <div style={S.sectionLabel}>Ship To</div>
          <div style={S.sectionValue}>
            <div>{po.ship_to_name || po.company || ''}</div>
            <div>{po.ship_to_address || ''}</div>
          </div>
        </div>
        <div style={S.sectionBox}>
          <div style={S.sectionLabel}>PO Details</div>
          <div style={S.sectionValue}>
            <div>PO#: {po.ida || po.id}</div>
            <div>Requisitioner: {po.requisitioner || '--'}</div>
          </div>
        </div>
      </div>

      {/* Metadata */}
      <div style={S.metaRow}>
        <div style={S.metaItem}><span style={S.metaLabel}>PO Date</span> <span style={S.metaValue}>{fmtDate(po.dt_created)}</span></div>
        <div style={S.metaItem}><span style={S.metaLabel}>Terms</span> <span style={S.metaValue}>{po.terms || '--'}</span></div>
        <div style={S.metaItem}><span style={S.metaLabel}>Ship Via</span> <span style={S.metaValue}>{po.ship_via || '--'}</span></div>
        <div style={S.metaItem}><span style={S.metaLabel}>F.O.B.</span> <span style={S.metaValue}>{po.fob || '--'}</span></div>
      </div>
      <div style={S.metaRow}>
        <div style={S.metaItem}><span style={S.metaLabel}>Status</span> <span style={S.metaValue}>{po.status || '--'}</span></div>
        <div style={S.metaItem}><span style={S.metaLabel}>Vendor Pack List</span> <span style={S.metaValue}>{po.vendor_pack_list || '--'}</span></div>
        <div style={S.metaItem}><span style={S.metaLabel}>Receipt</span> <span style={S.metaValue}>{po.receipt_id || '--'}</span></div>
      </div>

      {/* Comments */}
      {po.comments?.public?.[0] && (
        <div style={{ margin: '8px 0', padding: '8px 12px', background: '#f8f9fa', borderRadius: 4, fontSize: 12 }}>
          <strong>Comments:</strong> {po.comments.public[0]}
        </div>
      )}

      {/* Line Items */}
      <table style={S.table}>
        <thead>
          <tr>
            <th style={S.thRight}>Qty</th>
            <th style={S.th}>Unit</th>
            <th style={S.th}>Item #</th>
            <th style={{ ...S.th, width: '40%' }}>Description</th>
            <th style={S.thRight}>Unit Cost</th>
            <th style={S.thRight}>Extended</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line: any, i: number) => (
            <tr key={line.id || i}>
              <td style={S.tdRight}>{line.quantity?.active ?? line.qty ?? '--'}</td>
              <td style={S.td}>{line.unit || 'EA'}</td>
              <td style={S.td}>{line.item?.ida_item || line.ida || '--'}</td>
              <td style={S.td}>{line.item?.description || line.description || '--'}</td>
              <td style={S.tdRight}>{fmt(line.cost?.unit || line.price?.unit)}</td>
              <td style={S.tdRight}>{fmt(line.cost?.extended || line.price?.extended)}</td>
            </tr>
          ))}
          {lines.length === 0 && (
            <tr><td colSpan={6} style={{ ...S.td, textAlign: 'center', color: '#999' }}>No line items</td></tr>
          )}
        </tbody>
      </table>

      {/* Totals */}
      <div style={S.totalsWrap}>
        <div style={S.totalsLeft}>
          <p style={{ fontSize: 11 }}>
            The P.O. number must appear on all related correspondence, shipping papers, and invoices.
          </p>
          <p style={{ fontSize: 11, marginTop: 4 }}>
            Please notify us immediately if you are unable to ship as specified.
          </p>
        </div>
        <div style={S.totalsRight}>
          <div style={S.totalRow}><span>Subtotal</span> <span>{fmt(totals.subtotal)}</span></div>
          <div style={S.totalRow}><span>Sales Tax</span> <span>{fmt(totals.tax)}</span></div>
          <div style={S.totalRow}><span>Shipping &amp; Handling</span> <span>{fmt(totals.shipping)}</span></div>
          <div style={S.totalRowFinal}><span>Total</span> <span>{fmt(totals.total || po.total)}</span></div>
        </div>
      </div>

      {/* Footer */}
      <div style={S.footer}>
        <div style={S.sigRow}>
          <div style={S.sigBox}>
            <div style={{ fontSize: 10, color: '#666' }}>Authorized by:</div>
            <div style={S.sigLine}>Signature</div>
            <div style={S.sigLine}>Date</div>
          </div>
          <div style={S.sigBox}>
            <div style={{ fontSize: 10, color: '#666' }}>Vendor acknowledgment:</div>
            <div style={S.sigLine}>Signature</div>
            <div style={S.sigLine}>Date</div>
          </div>
        </div>
        <div style={S.refRow}>
          <div style={S.refBox}><div style={S.sectionLabel}>PO #</div><div>{po.ida || po.id}</div></div>
          <div style={S.refBox}><div style={S.sectionLabel}>Vendor</div><div>{po.vendor_name || '--'}</div></div>
          <div style={S.refBox}><div style={S.sectionLabel}>Date</div><div>{fmtDate(po.dt_created)}</div></div>
        </div>
      </div>
    </div>
  );
}
