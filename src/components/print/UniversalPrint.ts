/**
 * UniversalPrint — JSON-driven print renderer.
 *
 * Reads a PrintLayout (from print_layout Setting) and record data,
 * renders HTML in a popup window, calls window.print().
 *
 * Alice drafts the PrintLayout JSON from user-uploaded PDF/image examples.
 * Users tweak field mappings in the DataBrowser Setting editor.
 */
import type {
  PrintLayout, PrintLayoutSection, PrintField,
  CompanyHeaderSection, AddressBlocksSection, MetaRowSection,
  DetailFieldsSection,
  CommentsSection, LineItemsSection, TotalsSection,
  ConditionsSection, SignatureSection, FooterSection,
  DataTableSection, ConditionalTextSection, ConditionalTextRule,
} from './printLayoutTypes';

// ---------------------------------------------------------------------------
// Formatters
// ---------------------------------------------------------------------------

function fmtCurrency(v: unknown): string {
  if (v == null || v === '') return '';
  const n = typeof v === 'number' ? v : Number(v);
  if (isNaN(n)) return String(v);
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 });
}

function fmtDate(v: unknown): string {
  if (!v) return '';
  if (typeof v === 'number') {
    const ms = v > 1e12 ? v : v * 1000;
    return new Date(ms).toLocaleDateString();
  }
  if (typeof v === 'string') {
    const d = new Date(v);
    return isNaN(d.getTime()) ? v : d.toLocaleDateString();
  }
  return String(v);
}

function fmtNumber(v: unknown): string {
  if (v == null || v === '') return '';
  const n = typeof v === 'number' ? v : Number(v);
  if (isNaN(n)) return String(v);
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtPercent(v: unknown): string {
  if (v == null || v === '') return '';
  const n = typeof v === 'number' ? v : Number(v);
  if (isNaN(n)) return String(v);
  return (n * 100).toFixed(1) + '%';
}

function formatValue(v: unknown, format?: string): string {
  if (format === 'currency') return fmtCurrency(v);
  if (format === 'date') return fmtDate(v);
  if (format === 'number') return fmtNumber(v);
  if (format === 'percent') return fmtPercent(v);
  if (v == null || v === '') return '';
  const s = String(v);
  // Strip pipe-delimited pointers (conditions_description: "Standard|505|1")
  return s.includes('|') ? s.split('|')[0] : s;
}

// ---------------------------------------------------------------------------
// Dot-notation field resolver
// ---------------------------------------------------------------------------

function resolve(data: any, path: string): unknown {
  if (!data || !path) return undefined;
  return path.split('.').reduce((obj: any, key: string) => obj?.[key], data);
}

function resolveField(data: any, field: PrintField): string {
  const raw = resolve(data, field.field);
  return formatValue(raw, field.format);
}

// ---------------------------------------------------------------------------
// HTML helpers
// ---------------------------------------------------------------------------

function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function styleAttr(field: PrintField): string {
  const parts: string[] = [];
  if (field.align === 'right') parts.push('text-align:right');
  if (field.align === 'center') parts.push('text-align:center');
  if (field.width) parts.push(`width:${field.width}`);
  if (field.style?.includes('bold')) parts.push('font-weight:700');
  if (field.style?.includes('italic')) parts.push('font-style:italic');
  return parts.length ? ` style="${parts.join(';')}"` : '';
}

// ---------------------------------------------------------------------------
// Section renderers
// ---------------------------------------------------------------------------

function renderCompanyHeader(section: CompanyHeaderSection, _data: any, company: any): string {
  const name = company?.name || company?.legal_name || 'Company';
  const addr = company?.address || {};
  const street = [addr.street1, addr.street2].filter(Boolean).join(', ');
  const cityLine = [addr.city, addr.state, addr.zip].filter(Boolean).join(', ');
  const contact = [company?.phone, company?.email, company?.website].filter(Boolean).join(' · ');

  return `<div class="up-company-header">
    ${section.logo !== false ? '<img src="/images/logo/webclerk.png" alt="" class="up-logo" onerror="this.style.display=\'none\'">' : ''}
    <div>
      <div class="up-company-name">${esc(name)}</div>
      ${section.show_address !== false ? `<div class="up-company-sub">${esc(street)}</div><div class="up-company-sub">${esc(cityLine)}</div>` : ''}
      ${section.show_contact !== false && contact ? `<div class="up-company-sub">${esc(contact)}</div>` : ''}
    </div>
  </div>`;
}

function renderAddressBlocks(section: AddressBlocksSection, data: any): string {
  const cols = section.columns.map(col => {
    const rows = col.fields.map(f => {
      const val = resolveField(data, f);
      if (!val && !f.label) return '';
      return `<div class="up-addr-row"><span class="up-addr-label">${esc(f.label || f.field)}</span><span>${esc(val)}</span></div>`;
    }).filter(Boolean).join('');
    return `<div class="up-addr-col"><div class="up-addr-title">${esc(col.title)}</div>${rows}</div>`;
  }).join('');
  return `<div class="up-addr-blocks">${cols}</div>`;
}

function renderMetaRow(section: MetaRowSection, data: any): string {
  const items = section.fields.map(f => {
    const val = resolveField(data, f);
    return `<div class="up-meta-item"><span class="up-meta-label">${esc(f.label || f.field)}</span><span>${esc(val || '--')}</span></div>`;
  }).join('');
  return `<div class="up-meta-row">${items}</div>`;
}

function renderDetailFields(section: DetailFieldsSection, data: any): string {
  const items = section.fields.map(f => {
    const val = resolveField(data, f);
    return `<div class="up-detail-field"><span class="up-detail-label">${esc(f.label || f.field)}:</span> <span>${esc(val || '--')}</span></div>`;
  }).join('');
  return `<div class="up-detail-fields">${items}</div>`;
}

function renderComments(section: CommentsSection, data: any): string {
  const val = resolve(data, section.source);
  if (!val) return '';
  const text = Array.isArray(val) ? val[0] : String(val);
  if (!text) return '';
  return `<div class="up-comments"><strong>${esc(section.label || 'Comments')}:</strong> ${esc(text)}</div>`;
}

function renderLineItems(section: LineItemsSection, data: any): string {
  const lines: any[] = data?.lines || [];
  const cols = section.columns;

  const thead = cols.map(c =>
    `<th${styleAttr(c)}>${esc(c.label || c.field)}</th>`
  ).join('');

  const tbody = lines.map((line: any) => {
    const cells = cols.map(c => {
      const val = resolveField(line, c);
      return `<td${styleAttr(c)}>${esc(val)}</td>`;
    }).join('');
    return `<tr>${cells}</tr>`;
  }).join('');

  let tfoot = '';
  if (section.show_footer_totals && lines.length > 0) {
    const footCells = cols.map((c, i) => {
      if (c.format === 'currency') {
        const total = lines.reduce((s: number, l: any) => {
          const v = resolve(l, c.field);
          return s + (typeof v === 'number' ? v : Number(v) || 0);
        }, 0);
        return `<td${styleAttr(c)} style="font-weight:700;border-top:2px solid #333;${c.align === 'right' ? 'text-align:right' : ''}">${fmtCurrency(total)}</td>`;
      }
      if (c.field.includes('quantity') || c.field.includes('qty')) {
        const total = lines.reduce((s: number, l: any) => {
          const v = resolve(l, c.field);
          return s + (typeof v === 'number' ? v : Number(v) || 0);
        }, 0);
        return `<td${styleAttr(c)} style="font-weight:700;border-top:2px solid #333;${c.align === 'right' ? 'text-align:right' : ''}">${total}</td>`;
      }
      return `<td style="border-top:2px solid #333"></td>`;
    }).join('');
    tfoot = `<tfoot><tr>${footCells}</tr></tfoot>`;
  }

  return `<table class="up-table"><thead><tr>${thead}</tr></thead><tbody>${tbody}</tbody>${tfoot}</table>`;
}

function renderTotals(section: TotalsSection, data: any): string {
  const rows = section.rows.map(r => {
    const val = resolveField(data, r);
    const cls = r.bold || r.style?.includes('bold') ? ' class="up-total-final"' : '';
    return `<div${cls} class="up-total-row"><span>${esc(r.label || '')}</span><span>${esc(val)}</span></div>`;
  }).join('');

  return `<div class="up-totals-wrap">
    <div class="up-totals-left">${section.left_text ? `<p>${esc(section.left_text)}</p>` : ''}</div>
    <div class="up-totals-right">${rows}</div>
  </div>`;
}

function renderConditions(section: ConditionsSection, data: any): string {
  const raw = resolve(data, section.source);
  if (!raw) return '';
  const text = String(raw);
  const display = text.includes('|') ? text.split('|')[0] : text;
  return `<div class="up-conditions"><strong>Conditions:</strong> <em>${esc(display)}</em></div>`;
}

function renderSignature(section: SignatureSection): string {
  const preamble = section.preamble
    ? `<div class="up-sig-preamble">${esc(section.preamble)}</div>` : '';
  const blocks = section.blocks.map(b => {
    const lines = b.lines.map(l => `<div class="up-sig-line">${esc(l)}</div>`).join('');
    return `<div class="up-sig-block">${lines}</div>`;
  }).join('');
  return `<div class="up-signature">${preamble}<div class="up-sig-row">${blocks}</div></div>`;
}

function renderFooter(section: FooterSection, data: any): string {
  const items = section.fields.map(f => {
    const val = resolveField(data, f);
    return `<div class="up-footer-box"><div class="up-footer-label">${esc(f.label || f.field)}</div><div>${esc(val || '--')}</div></div>`;
  }).join('');
  return `<div class="up-footer">${items}</div>`;
}

function renderDataTable(section: DataTableSection, data: any): string {
  const rows: any[] = data?.rows || [];
  if (!rows.length) return '<div class="up-comments">No records.</div>';

  const cols = section.columns;
  const groupBy = section.group_by;

  // Build grouped structure
  const groups: Map<string, any[]> = new Map();
  for (const row of rows) {
    const key = groupBy ? String(resolve(row, groupBy) ?? '(none)') : '__all__';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(row);
  }

  const thead = cols.map(c =>
    `<th${styleAttr(c)}>${esc(c.label || c.field)}</th>`
  ).join('');

  // Render a totals row for currency/number columns
  function totalsRow(subset: any[], label: string, cls: string): string {
    const cells = cols.map((c, i) => {
      if (c.format === 'currency' || c.format === 'number') {
        const total = subset.reduce((s: number, r: any) => {
          const v = resolve(r, c.field);
          return s + (typeof v === 'number' ? v : Number(v) || 0);
        }, 0);
        const formatted = c.format === 'currency' ? fmtCurrency(total) : fmtNumber(total);
        return `<td${styleAttr(c)} style="font-weight:700;${c.align === 'right' ? 'text-align:right;' : ''}">${formatted}</td>`;
      }
      if (i === 0) return `<td style="font-weight:700">${esc(label)}</td>`;
      return '<td></td>';
    }).join('');
    return `<tr class="${cls}">${cells}</tr>`;
  }

  const pageBreak = data?._layout?.page_break_between_groups;
  let tbody = '';
  let groupIndex = 0;
  for (const [groupKey, groupRows] of groups) {
    // Group header
    if (groupBy && groupKey !== '__all__') {
      const breakCls = pageBreak && groupIndex > 0 ? ' up-group-break' : '';
      tbody += `<tr class="up-group-header${breakCls}"><td colspan="${cols.length}" style="font-weight:700;background:#f0f0f0;padding:6px 8px;border-bottom:2px solid #333">${esc(section.group_label || groupBy)}: ${esc(groupKey)} (${groupRows.length})</td></tr>`;
      groupIndex++;
    }
    // Data rows
    for (const row of groupRows) {
      const cells = cols.map(c => {
        const val = resolveField(row, c);
        return `<td${styleAttr(c)}>${esc(val)}</td>`;
      }).join('');
      tbody += `<tr>${cells}</tr>`;
    }
    // Group subtotals
    if (section.group_subtotals && groupBy && groupKey !== '__all__') {
      tbody += totalsRow(groupRows, `Subtotal: ${groupKey}`, 'up-subtotal-row');
    }
  }

  // Grand totals
  let tfoot = '';
  if (section.grand_totals) {
    tfoot = `<tfoot>${totalsRow(rows, `Total (${rows.length} records)`, 'up-grand-total')}</tfoot>`;
  }

  return `<table class="up-table"><thead><tr>${thead}</tr></thead><tbody>${tbody}</tbody>${tfoot}</table>`;
}

// Conditional text — evaluate rules against record data, first match wins
function evaluateCondition(expr: string, data: any): boolean {
  // Simple expression parser: "field.path > 0", "field.path == value"
  const match = expr.match(/^([a-zA-Z0-9_.]+)\s*(>|>=|<|<=|==|!=)\s*(.+)$/);
  if (!match) return false;
  const [, path, op, rawVal] = match;
  const left = Number(resolve(data, path) ?? 0);
  const right = Number(rawVal.trim());
  if (isNaN(left) || isNaN(right)) return false;
  switch (op) {
    case '>':  return left > right;
    case '>=': return left >= right;
    case '<':  return left < right;
    case '<=': return left <= right;
    case '==': return left === right;
    case '!=': return left !== right;
    default:   return false;
  }
}

function renderConditionalText(section: ConditionalTextSection, data: any): string {
  // Rules live in the report config at the source path (e.g. config.statement.comments)
  // The layout's _layout ref carries the full report config
  const reportConfig = (data as any)?._reportConfig || {};
  const rules: ConditionalTextRule[] = resolve(reportConfig, section.source) as any || [];
  if (!Array.isArray(rules) || rules.length === 0) return '';

  for (const rule of rules) {
    if (rule.default) {
      const s = rule.style === 'bold' ? 'font-weight:700;' : '';
      return `<div class="up-conditional-text" style="padding:8px 0;${s}">${esc(rule.text)}</div>`;
    }
    if (rule.when && evaluateCondition(rule.when, data)) {
      const s = rule.style === 'bold' ? 'font-weight:700;' : '';
      return `<div class="up-conditional-text" style="padding:8px 0;${s}">${esc(rule.text)}</div>`;
    }
  }
  return '';
}

// Renderer map
const RENDERERS: Record<string, (s: any, data: any, company: any) => string> = {
  company_header: renderCompanyHeader,
  address_blocks: renderAddressBlocks,
  meta_row: renderMetaRow,
  detail_fields: renderDetailFields,
  comments: renderComments,
  line_items: renderLineItems,
  totals: renderTotals,
  conditions: renderConditions,
  signature: renderSignature,
  footer: renderFooter,
  data_table: renderDataTable,
  conditional_text: renderConditionalText,
};

// ---------------------------------------------------------------------------
// CSS
// ---------------------------------------------------------------------------

const PRINT_CSS = `
body { font-family: -apple-system, system-ui, 'Segoe UI', sans-serif; font-size: 12px; color: #1a1a1a; margin: 0.5in; line-height: 1.4; }
.up-print-btn { padding: 8px 20px; font-size: 13px; font-weight: 600; background: #0d6efd; color: #fff; border: none; border-radius: 4px; cursor: pointer; margin-bottom: 16px; }
.up-company-header { display: flex; align-items: flex-start; gap: 12px; border-bottom: 2px solid #1e293b; padding-bottom: 8px; margin-bottom: 16px; }
.up-logo { height: 36px; }
.up-company-name { font-size: 16px; font-weight: 700; }
.up-company-sub { font-size: 10px; color: #64748b; }
.up-doc-info { margin-left: auto; text-align: right; }
.up-doc-title { font-size: 20px; font-weight: 700; }
.up-doc-id { font-size: 13px; font-family: monospace; color: #475569; }
.up-addr-blocks { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 12px; }
.up-addr-col { border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px; }
.up-addr-title { font-size: 11px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; border-bottom: 1px solid #f1f5f9; padding-bottom: 4px; }
.up-addr-row { display: flex; gap: 8px; font-size: 11px; padding: 2px 0; }
.up-addr-label { color: #94a3b8; width: 70px; text-align: right; flex-shrink: 0; }
.up-meta-row { display: flex; gap: 8px; margin-bottom: 4px; flex-wrap: wrap; }
.up-meta-item { flex: 1; min-width: 120px; display: flex; gap: 4px; }
.up-meta-label { font-size: 10px; font-weight: 700; color: #94a3b8; white-space: nowrap; }
.up-detail-fields { margin: 8px 0; }
.up-detail-field { display: flex; gap: 6px; padding: 2px 0; font-size: 12px; }
.up-detail-label { font-weight: 700; color: #555; min-width: 100px; }
.up-comments { margin: 8px 0; padding: 8px 12px; background: #f8f9fa; border-radius: 4px; font-size: 11px; }
.up-table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 11px; }
.up-table th { border-bottom: 2px solid #333; padding: 6px 8px; font-size: 10px; font-weight: 700; color: #666; text-transform: uppercase; text-align: left; }
.up-table td { border-bottom: 1px solid #eee; padding: 5px 8px; vertical-align: top; }
.up-totals-wrap { display: flex; justify-content: space-between; margin-top: 16px; gap: 24px; }
.up-totals-left { flex: 1; font-size: 12px; color: #666; line-height: 1.6; }
.up-totals-right { width: 280px; border-left: 2px solid #bbb; padding-left: 16px; }
.up-total-row { display: flex; justify-content: space-between; padding: 3px 0; font-size: 12px; }
.up-total-final { display: flex; justify-content: space-between; padding: 6px 0 3px; font-size: 14px; font-weight: 700; border-top: 2px solid #333; margin-top: 4px; }
.up-conditions { margin-top: 16px; padding-top: 8px; border-top: 1px solid #e2e8f0; font-size: 10px; color: #64748b; }
.up-signature { margin-top: 24px; }
.up-sig-preamble { font-size: 10px; color: #666; margin-bottom: 8px; }
.up-sig-row { display: flex; gap: 24px; }
.up-sig-block { flex: 1; border: 1px solid #ccc; border-radius: 4px; padding: 12px 16px; }
.up-sig-line { border-bottom: 1px solid #333; margin-top: 28px; margin-bottom: 4px; font-size: 10px; color: #999; }
.up-footer { display: flex; gap: 16px; margin-top: 16px; border-top: 1px solid #ddd; padding-top: 12px; }
.up-footer-box { flex: 1; border: 1px solid #ddd; border-radius: 4px; padding: 8px 12px; text-align: center; }
.up-footer-label { font-size: 10px; font-weight: 700; color: #999; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
.up-group-header td { font-size: 11px; }
.up-subtotal-row td { border-top: 1px solid #999; font-size: 11px; }
.up-grand-total td { border-top: 2px solid #333; font-size: 12px; padding-top: 6px; }
.up-page-header { display: none; }
.up-page-footer { display: none; }
.up-group-break { page-break-before: auto; }
@media print {
  body { margin: 0; }
  .up-print-btn { display: none !important; }
  @page { margin: 10mm 8mm 20mm 8mm; size: letter; }
  table { page-break-inside: auto; }
  tr { page-break-inside: avoid; }
  thead { display: table-header-group; }
  tfoot { display: table-footer-group; }
  .up-page-header { display: block; position: running(pageHeader); }
  .up-page-footer { display: block; position: fixed; bottom: 0; left: 0; right: 0; font-size: 9px; color: #999; text-align: center; padding: 4px 0; border-top: 1px solid #ddd; }
  .up-group-break { page-break-before: always; }
}
`;

// ---------------------------------------------------------------------------
// HTML generation (pure function — used by both print popup and designer preview)
// ---------------------------------------------------------------------------

export { PRINT_CSS };

export function generatePrintHtml(
  data: any,
  companyInfo: any,
  layout: PrintLayout,
  reportConfig?: Record<string, unknown>,
): string {
  const title = layout.title || layout.model || 'Document';
  const isList = layout.sections.some(s => s.type === 'data_table');
  const ida = isList ? '' : (data?.ida || data?.id || '');
  const recordCount = isList ? (data?.rows?.length || 0) : 0;
  const printName = isList
    ? `${title.toUpperCase()}_${recordCount}_records`
    : `${title.toUpperCase()}_${ida}_${(data?.company || '').replace(/\s+/g, '_')}`;

  const idLine = isList ? `${recordCount} records` : String(ida);
  const docInfo = `<div class="up-doc-info"><div class="up-doc-title">${esc(title.toUpperCase())}</div><div class="up-doc-id">${esc(idLine)}</div><div style="font-size:11px;color:#64748b">${esc(data?.status || '')}</div></div>`;

  const renderData = { ...data, _layout: layout, _reportConfig: reportConfig || {} };

  const sectionsHtml = layout.sections.map(section => {
    const renderer = RENDERERS[section.type];
    if (!renderer) return `<!-- unknown section type: ${section.type} -->`;
    return renderer(section, renderData, companyInfo);
  }).join('\n');

  const bodyHtml = sectionsHtml.replace(
    '</div>\n  </div>',
    `</div>${docInfo}</div>`
  );

  const co = companyInfo || {};
  const footerParts = [co.name, co.domain, co.phone, co.email].filter(Boolean).join(' · ');
  const pageFooter = `<div class="up-page-footer">${esc(footerParts)}</div>`;

  return `<!DOCTYPE html><html><head><title>${esc(printName)}</title><style>${PRINT_CSS}</style></head><body>
    <button class="up-print-btn" onclick="window.print()">Print ${esc(title)}</button>
    ${bodyHtml}
    ${pageFooter}
  </body></html>`;
}

// ---------------------------------------------------------------------------
// Main export — opens print popup
// ---------------------------------------------------------------------------

export async function openUniversalPrint(
  data: any,
  companyInfo: any,
  layout: PrintLayout,
  options?: { autoprint?: boolean; reportConfig?: Record<string, unknown> },
): Promise<void> {
  const w = window.open('', '_blank', 'width=850,height=1000');
  if (!w) return;

  const html = generatePrintHtml(data, companyInfo, layout, options?.reportConfig);

  w.document.open();
  w.document.write(html);
  w.document.close();

  if (options?.autoprint !== false) {
    setTimeout(() => w.print(), 300);
  }
}
