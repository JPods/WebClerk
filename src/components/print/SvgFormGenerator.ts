/**
 * SvgFormGenerator — generates a clean SVG from a PrintLayout.
 *
 * The user selects fields inside WebClerk. This module produces an SVG
 * with every element carrying an ID that maps to a field path.
 * The user exports the SVG, designs it in their tool (Affinity, Figma,
 * Illustrator), hands it back. We populate it with data.
 *
 * Architecture:
 *   SVG  = the template (fonts, positions, styling — designer owns this)
 *   CSS  = our standard print plumbing (page breaks, color-adjust)
 *   JSON = runtime config (line counts, page numbers, text_format)
 *
 * Same card patterns as form layouts (DynamicDetail) — address blocks,
 * info rows, line items, totals, footer. Consistent building blocks
 * across screen and print.
 */
import type {
  PrintLayout, PrintLayoutSection, PrintField,
  AddressBlocksSection, LineItemsSection,
} from './printLayoutTypes';

// ---------------------------------------------------------------------------
// Page dimensions in SVG points (1pt = 1/72 inch)
// ---------------------------------------------------------------------------

const PAGE_DIMS: Record<string, { w: number; h: number }> = {
  letter: { w: 612, h: 792 },
  legal:  { w: 612, h: 1008 },
  a4:     { w: 595, h: 842 },
};

const MARGIN = 36; // 0.5 inch

// ---------------------------------------------------------------------------
// SVG element helpers
// ---------------------------------------------------------------------------

function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/** Generate a sanitized SVG ID from a field path */
function fieldId(field: string, prefix?: string): string {
  const clean = field.replace(/[^a-zA-Z0-9_]/g, '_');
  return prefix ? `${prefix}__${clean}` : `field__${clean}`;
}

function svgText(
  x: number, y: number, text: string,
  opts: { id?: string; fontSize?: number; fill?: string; fontWeight?: string; anchor?: string } = {},
): string {
  const fs = opts.fontSize || 10;
  const fill = opts.fill || '#222';
  const fw = opts.fontWeight || 'normal';
  const anchor = opts.anchor || 'start';
  const idAttr = opts.id ? ` id="${esc(opts.id)}"` : '';
  return `<text${idAttr} x="${x}" y="${y}" font-size="${fs}" fill="${fill}" font-weight="${fw}" text-anchor="${anchor}" font-family="sans-serif">${esc(text)}</text>`;
}

function svgRect(
  x: number, y: number, w: number, h: number,
  opts: { fill?: string; stroke?: string; rx?: number; id?: string } = {},
): string {
  const fill = opts.fill || 'none';
  const stroke = opts.stroke || '#ccc';
  const rx = opts.rx || 2;
  const idAttr = opts.id ? ` id="${esc(opts.id)}"` : '';
  return `<rect${idAttr} x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}" stroke="${stroke}" rx="${rx}" />`;
}

function svgLine(x1: number, y1: number, x2: number, y2: number, stroke = '#ccc'): string {
  return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${stroke}" stroke-width="0.5" />`;
}

// ---------------------------------------------------------------------------
// Section renderers — each returns SVG elements + height consumed
// ---------------------------------------------------------------------------

interface RenderResult {
  svg: string;
  height: number;
}

function renderCompanyHeader(x: number, y: number, contentW: number): RenderResult {
  const lines: string[] = [];
  // Logo placeholder
  lines.push(svgRect(x, y, 120, 40, { fill: '#f5f5f5', stroke: '#ddd', id: 'company__logo' }));
  lines.push(svgText(x + 60, y + 24, '[Logo]', { fontSize: 9, fill: '#999', anchor: 'middle', id: 'company__logo_label' }));
  // Company name
  lines.push(svgText(x + 130, y + 16, '{{company.name}}', { id: 'company__name', fontSize: 14, fontWeight: 'bold' }));
  // Address, phone, email, website
  lines.push(svgText(x + 130, y + 28, '{{company.address}}', { id: 'company__address', fontSize: 9, fill: '#666' }));
  lines.push(svgText(x + 130, y + 38, '{{company.phone}} · {{company.email}}', { id: 'company__contact', fontSize: 9, fill: '#666' }));
  // Document type — right side
  lines.push(svgText(x + contentW, y + 20, '{{document_type}}', { id: 'doc__type', fontSize: 18, fontWeight: 'bold', anchor: 'end' }));
  lines.push(svgText(x + contentW, y + 34, '{{document_number}}', { id: 'doc__number', fontSize: 11, anchor: 'end' }));
  // Divider
  lines.push(svgLine(x, y + 46, x + contentW, y + 46, '#333'));

  return { svg: lines.join('\n'), height: 52 };
}

function renderAddressBlocks(section: AddressBlocksSection, x: number, y: number, contentW: number): RenderResult {
  const cols = section.columns || [];
  const colCount = cols.length || 3;
  const colW = (contentW - (colCount - 1) * 8) / colCount;
  const lines: string[] = [];
  let maxH = 0;

  cols.forEach((col, ci) => {
    const cx = x + ci * (colW + 8);
    const cardId = `addr_${ci}`;
    // Card border
    lines.push(svgRect(cx, y, colW, 80, { stroke: '#ddd', rx: 3, id: `${cardId}__card` }));
    // Card title bar
    lines.push(svgRect(cx, y, colW, 16, { fill: '#f5f5f5', stroke: '#ddd', rx: 3, id: `${cardId}__header` }));
    lines.push(svgText(cx + 6, y + 12, col.title, { fontSize: 8, fill: '#666', fontWeight: 'bold', id: `${cardId}__title` }));

    // Fields — label above value, two columns within card
    const fields = col.fields || [];
    fields.forEach((f, fi) => {
      const row = Math.floor(fi / 2);
      const col2 = fi % 2;
      const fx = cx + 6 + col2 * (colW / 2 - 4);
      const fy = y + 22 + row * 22;
      const fid = fieldId(f.field, cardId);
      lines.push(svgText(fx, fy, f.label || f.field, { fontSize: 7, fill: '#999', id: `${fid}__label` }));
      lines.push(svgText(fx, fy + 10, `{{${f.field}}}`, { fontSize: 9, fill: '#222', id: fid }));
    });

    const cardH = 22 + Math.ceil(fields.length / 2) * 22 + 4;
    maxH = Math.max(maxH, cardH);
  });

  return { svg: lines.join('\n'), height: Math.max(maxH, 80) + 6 };
}

function renderMetaRow(fields: PrintField[], x: number, y: number, contentW: number, sectionId: string): RenderResult {
  const lines: string[] = [];
  const colCount = fields.length || 4;
  const colW = contentW / colCount;

  // Card border
  lines.push(svgRect(x, y, contentW, 28, { stroke: '#ddd', rx: 2, id: `${sectionId}__card` }));

  fields.forEach((f, fi) => {
    const fx = x + fi * colW + 6;
    const fid = fieldId(f.field, sectionId);
    lines.push(svgText(fx, y + 10, f.label || f.field, { fontSize: 7, fill: '#999', id: `${fid}__label` }));
    lines.push(svgText(fx, y + 22, `{{${f.field}}}`, { fontSize: 9, fill: '#222', id: fid }));
    // Divider between columns
    if (fi > 0) {
      lines.push(svgLine(x + fi * colW, y + 2, x + fi * colW, y + 26, '#eee'));
    }
  });

  return { svg: lines.join('\n'), height: 34 };
}

function renderDetailFields(fields: PrintField[], x: number, y: number, contentW: number): RenderResult {
  const lines: string[] = [];
  const rowH = 22;
  const cols = 2;
  const colW = contentW / cols;

  fields.forEach((f, fi) => {
    const row = Math.floor(fi / cols);
    const col = fi % cols;
    const fx = x + col * colW;
    const fy = y + row * rowH;
    const fid = fieldId(f.field, 'detail');
    lines.push(svgText(fx, fy + 8, f.label || f.field, { fontSize: 7, fill: '#999', id: `${fid}__label` }));
    lines.push(svgText(fx, fy + 18, `{{${f.field}}}`, { fontSize: 9, fill: '#222', id: fid }));
  });

  const totalRows = Math.ceil(fields.length / cols);
  return { svg: lines.join('\n'), height: totalRows * rowH + 4 };
}

function renderComments(source: string, label: string, x: number, y: number, contentW: number): RenderResult {
  const lines: string[] = [];
  const fid = fieldId(source, 'comments');
  lines.push(svgText(x, y + 10, label || 'Comments', { fontSize: 8, fill: '#666', fontWeight: 'bold', id: `${fid}__label` }));
  // foreignObject placeholder for markdown-rendered text
  lines.push(`<foreignObject id="${esc(fid)}" x="${x}" y="${y + 14}" width="${contentW}" height="40">`);
  lines.push(`  <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:9px;color:#333">{{${source}}}</div>`);
  lines.push(`</foreignObject>`);
  return { svg: lines.join('\n'), height: 58 };
}

function renderLineItems(section: LineItemsSection, x: number, y: number, contentW: number, linesPerPage: number): RenderResult {
  const columns = section.columns || [];
  const lines: string[] = [];
  const headerH = 16;
  const rowH = section.row_height || 16;
  const panelId = section.svg_panel_id || 'line_panel';

  // Table header
  lines.push(svgRect(x, y, contentW, headerH, { fill: '#f5f5f5', stroke: '#ddd', id: 'lines__header_bg' }));
  let cx = x;
  columns.forEach((col) => {
    const w = col.width ? parseFloat(col.width) / 100 * contentW : contentW / columns.length;
    const align = col.align === 'right' ? 'end' : 'start';
    const tx = col.align === 'right' ? cx + w - 4 : cx + 4;
    lines.push(svgText(tx, y + 11, col.label || col.field, {
      fontSize: 8, fill: '#666', fontWeight: 'bold', anchor: align,
      id: fieldId(col.field, 'lines__header'),
    }));
    cx += w;
  });

  // Divider under header
  lines.push(svgLine(x, y + headerH, x + contentW, y + headerH, '#ccc'));

  // Line panel template — a <g> group that gets cloned per line item
  // This is the reusable building block. Row 0 is the template.
  const templateY = y + headerH + 2;
  lines.push(`<g id="${esc(panelId)}" data-role="line-panel-template" data-row-height="${rowH}">`);
  cx = x;
  columns.forEach((col) => {
    const w = col.width ? parseFloat(col.width) / 100 * contentW : contentW / columns.length;
    const align = col.align === 'right' ? 'end' : 'start';
    const tx = col.align === 'right' ? cx + w - 4 : cx + 4;
    lines.push(svgText(tx, templateY + 11, `{{${col.field}}}`, {
      fontSize: 9, anchor: align,
      id: fieldId(col.field, panelId),
    }));
    cx += w;
  });
  // Row divider
  lines.push(svgLine(x, templateY + rowH, x + contentW, templateY + rowH, '#eee'));
  lines.push('</g>');

  // Show line count slots (empty rows for visual reference in design tool)
  const displayLines = linesPerPage || 10;
  for (let i = 1; i < displayLines; i++) {
    const ry = templateY + i * rowH;
    lines.push(svgLine(x, ry + rowH, x + contentW, ry + rowH, '#f0f0f0'));
    lines.push(svgText(x + 2, ry + 11, `[line ${i + 1}]`, { fontSize: 7, fill: '#ddd' }));
  }

  return { svg: lines.join('\n'), height: headerH + displayLines * rowH + 4 };
}

function renderTotals(fields: PrintField[], leftText: string | undefined, x: number, y: number, contentW: number): RenderResult {
  const lines: string[] = [];
  const totalsW = 200;
  const totalsX = x + contentW - totalsW;
  const rowH = 16;

  // Left text (Thank you message)
  if (leftText) {
    lines.push(svgText(x, y + 12, leftText, { fontSize: 9, fill: '#666', fontWeight: 'bold', id: 'totals__left_text' }));
  }

  // Divider
  lines.push(svgLine(totalsX - 8, y, totalsX - 8, y + fields.length * rowH + 4, '#ddd'));

  // Total rows
  fields.forEach((f, fi) => {
    const fy = y + fi * rowH;
    const fid = fieldId(f.field, 'totals');
    const isBold = (f as any).bold || f.style === 'bold';
    if (isBold && fi > 0) {
      lines.push(svgLine(totalsX, fy, totalsX + totalsW, fy, '#999'));
    }
    lines.push(svgText(totalsX, fy + 12, f.label || f.field, {
      fontSize: 9, fill: '#666', fontWeight: isBold ? 'bold' : 'normal', id: `${fid}__label`,
    }));
    lines.push(svgText(totalsX + totalsW, fy + 12, `{{${f.field}}}`, {
      fontSize: 9, anchor: 'end', fontWeight: isBold ? 'bold' : 'normal', id: fid,
    }));
  });

  return { svg: lines.join('\n'), height: fields.length * rowH + 8 };
}

function renderSignature(x: number, y: number, contentW: number): RenderResult {
  const lines: string[] = [];
  lines.push(svgLine(x, y, x + contentW, y, '#ccc'));
  lines.push(svgText(x, y + 14, 'Authorized by:', { fontSize: 9, fill: '#666', id: 'signature__preamble' }));
  // Signature line
  lines.push(svgLine(x + 100, y + 30, x + 320, y + 30, '#333'));
  lines.push(svgText(x + 100, y + 40, 'Signature', { fontSize: 7, fill: '#999', id: 'signature__sig_label' }));
  // Date line
  lines.push(svgLine(x + 340, y + 30, x + 460, y + 30, '#333'));
  lines.push(svgText(x + 340, y + 40, 'Date', { fontSize: 7, fill: '#999', id: 'signature__date_label' }));

  return { svg: lines.join('\n'), height: 48 };
}

function renderFooter(fields: PrintField[], x: number, y: number, contentW: number, layout: PrintLayout): RenderResult {
  const lines: string[] = [];
  lines.push(svgLine(x, y, x + contentW, y, '#ddd'));

  // Fields spread across footer
  const spacing = contentW / (fields.length + 2); // +2 for optional page#/domain
  fields.forEach((f, fi) => {
    const fx = x + fi * spacing;
    const fid = fieldId(f.field, 'footer');
    lines.push(svgText(fx, y + 12, `${f.label || f.field}: {{${f.field}}}`, { fontSize: 8, fill: '#999', id: fid }));
  });

  // Standard offerings — user toggles these in JSON
  if (layout.show_domain) {
    lines.push(svgText(x + contentW / 2, y + 12, '{{domain}}', { fontSize: 8, fill: '#999', anchor: 'middle', id: 'footer__domain' }));
  }
  if (layout.show_page_numbers) {
    lines.push(svgText(x + contentW, y + 12, 'Page {{page}} of {{pages}}', { fontSize: 8, fill: '#999', anchor: 'end', id: 'footer__page_numbers' }));
  }

  return { svg: lines.join('\n'), height: 18 };
}

function renderConditions(source: string, x: number, y: number, contentW: number): RenderResult {
  const lines: string[] = [];
  const fid = fieldId(source, 'conditions');
  lines.push(svgLine(x, y, x + contentW, y, '#eee'));
  lines.push(`<foreignObject id="${esc(fid)}" x="${x}" y="${y + 4}" width="${contentW}" height="30">`);
  lines.push(`  <div xmlns="http://www.w3.org/1999/xhtml" style="font-size:8px;color:#999">{{${source}}}</div>`);
  lines.push(`</foreignObject>`);
  return { svg: lines.join('\n'), height: 38 };
}

// ---------------------------------------------------------------------------
// Section dispatcher
// ---------------------------------------------------------------------------

function renderSection(
  section: PrintLayoutSection, x: number, y: number, contentW: number, layout: PrintLayout,
): RenderResult {
  switch (section.type) {
    case 'company_header':
      return renderCompanyHeader(x, y, contentW);
    case 'address_blocks':
      return renderAddressBlocks(section, x, y, contentW);
    case 'meta_row':
      return renderMetaRow((section as any).fields || [], x, y, contentW, 'meta');
    case 'detail_fields':
      return renderDetailFields((section as any).fields || [], x, y, contentW);
    case 'comments':
      return renderComments((section as any).source || 'comments.public', (section as any).label || 'Comments', x, y, contentW);
    case 'line_items':
      return renderLineItems(section, x, y, contentW, layout.lines_page_1 || 10);
    case 'totals':
      return renderTotals((section as any).rows || [], (section as any).left_text, x, y, contentW);
    case 'conditions':
      return renderConditions((section as any).source || 'conditions_description', x, y, contentW);
    case 'signature':
      return renderSignature(x, y, contentW);
    case 'footer':
      return renderFooter((section as any).fields || [], x, y, contentW, layout);
    default:
      return { svg: '', height: 0 };
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Generate a clean SVG string from a PrintLayout.
 * Every data element has an ID mapping to a field path.
 * Designed for export → external design tool → import back → populate with data.
 */
export function generateFormSvg(layout: PrintLayout): string {
  const paper = layout.paper || 'letter';
  const dim = PAGE_DIMS[paper] || PAGE_DIMS.letter;
  const contentW = dim.w - MARGIN * 2;
  const x = MARGIN;
  let y = MARGIN;

  const sectionSvgs: string[] = [];

  for (const section of layout.sections) {
    const result = renderSection(section, x, y, contentW, layout);
    if (result.svg) {
      sectionSvgs.push(`<!-- ${section.type} -->`);
      sectionSvgs.push(result.svg);
    }
    y += result.height;
  }

  // Build complete SVG document
  return [
    `<?xml version="1.0" encoding="UTF-8"?>`,
    `<svg xmlns="http://www.w3.org/2000/svg" width="${dim.w}" height="${dim.h}" viewBox="0 0 ${dim.w} ${dim.h}">`,
    `  <!-- Generated by WebClerk Form Designer -->`,
    `  <!-- Every element with an id maps to a data field path -->`,
    `  <!-- Edit in your design tool, hand back to WebClerk, we populate with data -->`,
    `  `,
    `  <!-- Page background -->`,
    `  <rect width="${dim.w}" height="${dim.h}" fill="white" />`,
    `  `,
    `  <!-- Form content -->`,
    ...sectionSvgs.map(s => '  ' + s.split('\n').join('\n  ')),
    `</svg>`,
  ].join('\n');
}

/**
 * Populate an SVG template with record data.
 * Walks all elements with IDs matching field__* patterns,
 * resolves the field path against the record, sets textContent.
 *
 * For line items: clones the line panel <g> group per line,
 * offsets by row_height, fills field values.
 */
export function populateFormSvg(
  svgString: string, data: any, companyInfo?: any, lineItems?: any[],
  config?: { max_description_lines?: number; text_format?: string },
): string {
  const parser = new DOMParser();
  const doc = parser.parseFromString(svgString, 'image/svg+xml');
  const svg = doc.documentElement;

  // Resolve a dot-path against data
  const resolve = (path: string, context?: any): string => {
    const obj = context || data;
    if (!obj || !path) return '';
    const val = path.split('.').reduce((o: any, k: string) => o?.[k], obj);
    return val != null ? String(val) : '';
  };

  // Populate company fields
  if (companyInfo) {
    const companyFields: Record<string, string> = {
      'company__name': companyInfo.name || companyInfo.legal_name || '',
      'company__address': companyInfo.address?.street1 || '',
      'company__contact': [companyInfo.phone, companyInfo.email].filter(Boolean).join(' · '),
    };
    for (const [id, val] of Object.entries(companyFields)) {
      const el = svg.querySelector(`#${id}`);
      if (el) el.textContent = val;
    }
  }

  // Populate all field__* elements from data
  const allElements = svg.querySelectorAll('[id]');
  allElements.forEach(el => {
    const id = el.getAttribute('id') || '';
    // Skip labels, headers, and structural elements
    if (id.endsWith('__label') || id.endsWith('__card') || id.endsWith('__header') || id.endsWith('__header_bg')) return;
    if (id.startsWith('company__') || id.startsWith('signature__')) return;

    // Extract field path from ID
    // Pattern: prefix__field_path (e.g., "meta__ida", "detail__config_ship_to_company")
    // Or: "field__ida"
    const match = id.match(/^(?:field|meta|detail|footer|totals|addr_\d+|lines__header)__(.+)$/);
    if (!match) return;

    const fieldPath = match[1].replace(/__/g, '.').replace(/_/g, '.');
    // Try direct lookup first, then converted path
    const textContent = el.textContent || '';
    const templateMatch = textContent.match(/^\{\{(.+)\}\}$/);
    if (templateMatch) {
      const path = templateMatch[1];
      el.textContent = resolve(path);
    }
  });

  // Populate line items — clone the line panel template
  const panelTemplate = svg.querySelector('[data-role="line-panel-template"]');
  if (panelTemplate && lineItems && lineItems.length > 0) {
    const rowHeight = parseFloat(panelTemplate.getAttribute('data-row-height') || '16');
    const parent = panelTemplate.parentNode;
    const maxDescLines = config?.max_description_lines || 2;

    let slotOffset = 0;
    lineItems.forEach((line, li) => {
      const clone = panelTemplate.cloneNode(true) as Element;
      clone.setAttribute('id', `line_row_${li}`);
      clone.removeAttribute('data-role');
      clone.setAttribute('transform', `translate(0, ${slotOffset * rowHeight})`);

      // Populate fields in the clone
      clone.querySelectorAll('[id]').forEach(el => {
        const text = el.textContent || '';
        const m = text.match(/^\{\{(.+)\}\}$/);
        if (m) {
          const val = resolve(m[1], line);
          el.textContent = val;
          el.setAttribute('id', `${el.getAttribute('id')}_${li}`);
        }
      });

      parent?.insertBefore(clone, panelTemplate.nextSibling);

      // Description wrapping: count how many slots this line consumes
      // For now, each line = 1 slot. max_description_lines is the cap.
      slotOffset += 1; // TODO: calculate wrapped lines based on text length and field width
    });

    // Hide the template row
    panelTemplate.setAttribute('display', 'none');
  }

  // Populate page numbers
  const pageNumEl = svg.querySelector('#footer__page_numbers');
  if (pageNumEl) {
    pageNumEl.textContent = 'Page 1 of 1'; // Multi-page handled by caller
  }

  // Populate domain
  const domainEl = svg.querySelector('#footer__domain');
  if (domainEl && companyInfo?.domain) {
    domainEl.textContent = companyInfo.domain;
  }

  // Serialize back
  const serializer = new XMLSerializer();
  return serializer.serializeToString(svg);
}

/**
 * Trigger SVG download in the browser.
 */
export function downloadSvg(svgString: string, filename: string): void {
  const blob = new Blob([svgString], { type: 'image/svg+xml' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename.endsWith('.svg') ? filename : `${filename}.svg`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
