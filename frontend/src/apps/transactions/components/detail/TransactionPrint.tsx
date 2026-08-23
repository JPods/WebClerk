/* LastChecked: 2026-08-03 | WhereUsed: TransactionToolbar | WhoCreated: Claude */
import { getRecord } from '@/api/wcapi';
import type { DetailLayout } from '@/hooks/useDetailLayout';
import { formatDt } from '@/utils/fieldFormatters';

/**
 * Open a print-ready window rendering any transaction as clean HTML.
 * Reads column titles, field labels, and sell/exec family from the layout JSON.
 * Same data, same layout, purpose-built for output.
 */
export async function openPrintWindow(
  data: any,
  companyInfo: any,
  _logos: any,
  documentText: any,
  modelName: string,
  layout?: DetailLayout | null,
): Promise<void> {
  const w = window.open('', '_blank', 'width=800,height=1000');
  if (!w) return;
  w.document.write('<html><body><p>Loading...</p></body></html>');

  const d = data;
  const co = companyInfo;
  const lines = d?.lines || [];
  const totals = d?.totals || {};

  // Determine sell vs exec from layout
  const lineCardSection = layout?.sections?.find((s: any) => s.type === 'line_card') as any;
  const isSellSide = (lineCardSection?.family || 'sell') === 'sell';

  // Read column definitions from layout
  const headerSection = layout?.sections?.find((s: any) => s.type === 'header') as any;
  const columns = headerSection?.columns || [
    { title: 'Customer', fields: [] },
    { title: 'Ship To', fields: [] },
    { title: modelName.charAt(0).toUpperCase() + modelName.slice(1), fields: [] },
  ];

  // Resolve conditions text from Setting by id
  let conditionsText = '';
  if (d.conditions_description) {
    const parts = d.conditions_description.split('|');
    if (parts.length >= 2) {
      try {
        const res = await getRecord('setting', Number(parts[1]));
        const setting = res?.record || res;
        conditionsText = setting?.config?.current?.text || parts[0];
      } catch { conditionsText = parts[0]; }
    } else {
      conditionsText = parts[0];
    }
  }

  // Build header columns from layout
  const getFieldValue = (field: string): string => {
    if (field.includes('.')) {
      const val = field.split('.').reduce((obj: any, key: string) => obj?.[key], d);
      return val != null ? String(val) : '';
    }
    const val = d?.[field];
    if (val == null) return '';
    if (typeof val === 'number' && (field.startsWith('dt_') || field.includes('date'))) {
      return formatDt(val, 'date', field);
    }
    // Strip pipe-delimited pointers (conditions)
    const s = String(val);
    return s.includes('|') ? s.split('|')[0] : s;
  };

  const renderColumn = (col: any): string => {
    const fields = (col.fields || []).map((f: any) => {
      const val = getFieldValue(f.field);
      if (!val && !f.label) return '';
      return `<div class="row"><span class="lbl">${f.label || f.field}</span><span>${val || ''}</span></div>`;
    }).join('');
    return `<div><h3>${col.title}</h3>${fields}</div>`;
  };

  const headerHtml = columns.map(renderColumn).join('');

  // Build line rows — sell side shows price, exec side shows cost
  const priceLabel = isSellSide ? 'Unit Price' : 'Unit Cost';
  const lineRows = lines.map((l: any) => {
    const item = l.item || {};
    const price = l.price || {};
    const cost = l.cost || {};
    const qty = l.quantity || {};
    const unitVal = isSellSide ? (price.unit ?? 0) : (cost.unit ?? 0);
    const extVal = isSellSide ? (price.extended ?? 0) : (cost.extended ?? 0);
    return `<tr>
      <td>${item.ida_item || ''}</td>
      <td style="text-align:right">${qty.active ?? ''}</td>
      <td style="text-align:right;font-style:italic">${qty.remaining ?? ''}</td>
      <td>${item.description || ''}</td>
      <td style="text-align:right">${unitVal ? unitVal.toFixed(2) : ''}</td>
      <td style="text-align:right;font-style:italic">${extVal ? extVal.toLocaleString('en-US', {minimumFractionDigits:2}) : ''}</td>
    </tr>`;
  }).join('');

  const totalQty = lines.reduce((s: number, l: any) => s + (l.quantity?.active ?? 0), 0);
  const totalExt = lines.reduce((s: number, l: any) => {
    return s + (isSellSide ? (l.price?.extended ?? 0) : (l.cost?.extended ?? 0));
  }, 0);

  const printName = `${modelName.toUpperCase()}_${d.ida}_${(d.company || '').replace(/\s+/g, '_')}`;

  w.document.open();
  w.document.write(`<!DOCTYPE html><html><head><title>${printName}</title>
    <style>body{font-family:-apple-system,system-ui,sans-serif;font-size:12px;color:#1a1a1a;margin:0.5in;line-height:1.4}
    table{width:100%;border-collapse:collapse}th,td{padding:4px 8px;border-bottom:1px solid #e2e8f0}
    th{text-align:left;font-size:11px;color:#64748b;border-bottom:2px solid #cbd5e1}
    .hdr{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-bottom:16px}
    .hdr>div{border:1px solid #e2e8f0;border-radius:6px;padding:10px}
    .hdr h3{font-size:11px;font-weight:700;margin:0 0 6px;border-bottom:1px solid #f1f5f9;padding-bottom:4px}
    .row{display:flex;gap:8px;font-size:11px;padding:2px 0}.row .lbl{color:#94a3b8;width:60px;text-align:right;flex-shrink:0}
    .top{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:2px solid #1e293b;padding-bottom:8px;margin-bottom:16px}
    .co{font-size:16px;font-weight:700}.co-addr{font-size:10px;color:#64748b}
    .doc-type{font-size:20px;font-weight:700;text-align:right}.doc-id{font-size:13px;font-family:monospace;color:#475569}
    .footer{margin-top:12px;padding-top:8px;border-top:2px solid #cbd5e1;display:flex;justify-content:flex-end;gap:16px;font-size:11px}
    .footer span{font-style:italic}.footer .total{font-weight:700;font-size:12px}
    .terms{margin-top:16px;padding-top:8px;border-top:1px solid #e2e8f0;font-size:10px;color:#64748b}
    @media print{@page{margin:0.5in;size:letter}}</style></head><body>
    <div class="top"><div><img src="/images/logo/webclerk.png" alt="" style="height:36px;margin-bottom:4px">
    <div class="co">${co?.name || co?.legal_name || 'Company'}</div>
    <div class="co-addr">${co?.address?.street1 || ''}${co?.address?.street2 ? ', ' + co.address.street2 : ''}</div>
    <div class="co-addr">${[co?.address?.city, co?.address?.state, co?.address?.zip].filter(Boolean).join(', ')}</div>
    <div class="co-addr">${[co?.phone, co?.email, co?.website].filter(Boolean).join(' · ')}</div></div>
    <div><div class="doc-type">${modelName.toUpperCase()}</div><div class="doc-id">${d.ida}</div><div style="font-size:11px;color:#64748b">${d.status}</div></div></div>
    <div class="hdr">${headerHtml}</div>
    <table><thead><tr><th>Item</th><th style="text-align:right">Qty</th><th style="text-align:right;font-style:italic">Remain</th><th>Description</th><th style="text-align:right">${priceLabel}</th><th style="text-align:right;font-style:italic">Extended</th></tr></thead>
    <tbody>${lineRows}</tbody>
    <tfoot><tr style="border-top:2px solid #cbd5e1;font-weight:700"><td></td><td style="text-align:right">${totalQty}</td><td></td><td></td><td></td><td style="text-align:right">${totalExt.toLocaleString('en-US', {minimumFractionDigits:2})}</td></tr></tfoot></table>
    <div class="footer"><span>Tax: $${(totals.tax ?? 0).toFixed(2)}</span><span>Ship: $${(totals.shipping ?? 0).toFixed(2)}</span><span>|</span><span class="total">Total: $${totalExt.toLocaleString('en-US', {minimumFractionDigits:2})}</span></div>
    ${d.comments?.public ? `<div class="terms"><strong>Notes:</strong> ${d.comments.public}</div>` : ''}
    ${d.conditions_description ? `<div class="terms"><strong>Conditions:</strong> <em>${d.conditions_description}</em><br>${conditionsText}</div>` : ''}
    ${d.terms || documentText?.invoice_comment ? `<div class="terms">${d.terms ? '<strong>Terms:</strong> ' + d.terms : ''}${documentText?.invoice_comment ? '<br>' + documentText.invoice_comment : ''}</div>` : ''}
    </body></html>`);
  w.document.close();
  setTimeout(() => w.print(), 300);
}
