/**
 * Shared print styles — matches vue2020 InvoicePrint/OrderPrint/ProposalPrint layout.
 * Uses inline styles for print reliability (no Tailwind in print media).
 */

export const fmt = (v: unknown): string => {
  if (v == null || v === '') return '--';
  if (typeof v === 'number') return v.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 });
  if (typeof v === 'string' && !isNaN(Number(v))) return Number(v).toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 });
  return String(v);
};

export const fmtDate = (v: unknown): string => {
  if (!v) return '--';
  if (typeof v === 'number') return new Date(v).toLocaleDateString();
  return String(v);
};

export const S = {
  page: {
    fontFamily: "'Segoe UI', Arial, sans-serif",
    fontSize: 12,
    color: '#333',
    maxWidth: 900,
    margin: '0 auto',
    padding: '20px 24px',
  } as React.CSSProperties,

  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    borderBottom: '2px solid #333',
    paddingBottom: 12,
    marginBottom: 16,
  } as React.CSSProperties,

  headerLeft: {
    fontSize: 11,
    color: '#666',
    lineHeight: 1.6,
  } as React.CSSProperties,

  headerCenter: {
    textAlign: 'center' as const,
    flex: 1,
  } as React.CSSProperties,

  headerRight: {
    textAlign: 'right' as const,
  } as React.CSSProperties,

  logo: {
    maxWidth: 180,
    maxHeight: 80,
  } as React.CSSProperties,

  docTitle: {
    fontSize: 18,
    fontWeight: 700,
    color: '#000',
    marginTop: 4,
  } as React.CSSProperties,

  companyName: {
    fontSize: 14,
    fontWeight: 700,
    color: '#000',
  } as React.CSSProperties,

  sectionRow: {
    display: 'flex',
    gap: 16,
    marginBottom: 12,
  } as React.CSSProperties,

  sectionBox: {
    flex: 1,
    border: '1px solid #ddd',
    borderRadius: 4,
    padding: '8px 12px',
  } as React.CSSProperties,

  sectionLabel: {
    fontSize: 10,
    fontWeight: 700,
    color: '#999',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.06em',
    marginBottom: 4,
  } as React.CSSProperties,

  sectionValue: {
    fontSize: 12,
    color: '#333',
    lineHeight: 1.5,
  } as React.CSSProperties,

  metaRow: {
    display: 'flex',
    gap: 8,
    marginBottom: 4,
  } as React.CSSProperties,

  metaItem: {
    flex: 1,
    display: 'flex',
    gap: 4,
  } as React.CSSProperties,

  metaLabel: {
    fontSize: 10,
    fontWeight: 700,
    color: '#999',
    whiteSpace: 'nowrap' as const,
  } as React.CSSProperties,

  metaValue: {
    fontSize: 12,
    color: '#333',
  } as React.CSSProperties,

  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    marginTop: 12,
    marginBottom: 12,
    fontSize: 11,
  } as React.CSSProperties,

  th: {
    borderBottom: '2px solid #333',
    padding: '6px 8px',
    textAlign: 'left' as const,
    fontSize: 10,
    fontWeight: 700,
    color: '#666',
    textTransform: 'uppercase' as const,
  } as React.CSSProperties,

  thRight: {
    borderBottom: '2px solid #333',
    padding: '6px 8px',
    textAlign: 'right' as const,
    fontSize: 10,
    fontWeight: 700,
    color: '#666',
    textTransform: 'uppercase' as const,
  } as React.CSSProperties,

  td: {
    borderBottom: '1px solid #eee',
    padding: '5px 8px',
    verticalAlign: 'top' as const,
  } as React.CSSProperties,

  tdRight: {
    borderBottom: '1px solid #eee',
    padding: '5px 8px',
    textAlign: 'right' as const,
    verticalAlign: 'top' as const,
  } as React.CSSProperties,

  totalsWrap: {
    display: 'flex',
    justifyContent: 'space-between',
    marginTop: 16,
    gap: 24,
  } as React.CSSProperties,

  totalsLeft: {
    flex: 1,
    fontSize: 12,
    color: '#666',
    lineHeight: 1.6,
  } as React.CSSProperties,

  totalsRight: {
    width: 280,
    borderLeft: '2px solid #bbb',
    paddingLeft: 16,
  } as React.CSSProperties,

  totalRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '3px 0',
    fontSize: 12,
  } as React.CSSProperties,

  totalRowFinal: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '6px 0 3px',
    fontSize: 14,
    fontWeight: 700,
    borderTop: '2px solid #333',
    marginTop: 4,
  } as React.CSSProperties,

  footer: {
    marginTop: 24,
    borderTop: '1px solid #ddd',
    paddingTop: 12,
  } as React.CSSProperties,

  contractTitle: {
    fontSize: 11,
    fontWeight: 700,
    color: '#666',
    marginBottom: 4,
  } as React.CSSProperties,

  contractText: {
    fontSize: 10,
    color: '#666',
    lineHeight: 1.5,
    marginBottom: 12,
  } as React.CSSProperties,

  sigRow: {
    display: 'flex',
    gap: 24,
    marginTop: 16,
  } as React.CSSProperties,

  sigBox: {
    flex: 1,
    border: '1px solid #ccc',
    borderRadius: 4,
    padding: '12px 16px',
  } as React.CSSProperties,

  sigLine: {
    borderBottom: '1px solid #333',
    marginTop: 28,
    marginBottom: 4,
    fontSize: 10,
    color: '#999',
  } as React.CSSProperties,

  refRow: {
    display: 'flex',
    gap: 16,
    marginTop: 16,
  } as React.CSSProperties,

  refBox: {
    flex: 1,
    border: '1px solid #ddd',
    borderRadius: 4,
    padding: '8px 12px',
    textAlign: 'center' as const,
  } as React.CSSProperties,

  printBtn: {
    padding: '8px 20px',
    fontSize: 13,
    fontWeight: 600,
    background: '#0d6efd',
    color: '#fff',
    border: 'none',
    borderRadius: 4,
    cursor: 'pointer',
    marginBottom: 16,
  } as React.CSSProperties,

  noPrint: {
    '@media print': { display: 'none' },
  } as React.CSSProperties,
};

// Global print CSS — inject once
export const PRINT_CSS = `
@media print {
  body { margin: 0; padding: 0; }
  .no-print { display: none !important; }
  @page { margin: 10mm 8mm 20mm 8mm; }
  table { page-break-inside: auto; }
  tr { page-break-inside: avoid; }
  thead { display: table-header-group; }
}
`;
