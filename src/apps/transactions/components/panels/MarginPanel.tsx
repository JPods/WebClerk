/* LastChecked: 2026-08-13 | WhereUsed: LinesCard | WhoCreated: Claude */
// Margin view panel — replaces main grid when active.
// Shows Item, Description, Qty, Price, Cost, Margin per line.
// Selection-aware totals: "Totals are for all lines if no lines are selected
// or only the lines selected." — WC2 behavior.
import React from 'react';

interface MarginPanelProps {
  lines: any[];
  selectedIds: Set<number>;
  isSellSide: boolean;
}

const formatCurrency = (v: number): string =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(v);

const marginStyle = (margin: number): React.CSSProperties =>
  margin > 0
    ? { color: 'var(--db-accent-green)' }
    : margin < 0
      ? { color: 'var(--db-accent-red)' }
      : { color: 'var(--db-text-muted)' };

const MarginPanel: React.FC<MarginPanelProps> = ({ lines, selectedIds, isSellSide }) => {
  // Build margin rows from lines
  const rows = React.useMemo(() => {
    return lines.map((line, idx) => {
      const itemCode = line.item?.ida_item || line.ida_item || '—';
      const description = line.item?.description || line.description || '—';
      const qty = Number(line.quantity?.active ?? 0);

      let price = 0;
      let cost = 0;
      if (isSellSide) {
        price = Number(line.price?.extended ?? 0);
        cost = Number(line.cost?.extended ?? qty * (line.cost?.unit ?? 0));
      } else {
        price = Number(line.cost?.extended ?? 0);
        cost = price; // exec-side: cost is the primary value
      }

      const margin = price - cost;
      const id = line.line_number ?? line.id ?? idx;

      return { id, itemCode, description, qty, price, cost, margin };
    });
  }, [lines, isSellSide]);

  // Selection-aware totals
  const activeRows = selectedIds.size > 0
    ? rows.filter(r => selectedIds.has(r.id))
    : rows;

  const totalPrice = activeRows.reduce((s, r) => s + r.price, 0);
  const totalCost = activeRows.reduce((s, r) => s + r.cost, 0);
  const totalMargin = totalPrice - totalCost;
  const marginPct = totalPrice > 0 ? (totalMargin / totalPrice) * 100 : 0;
  const selectionNote = selectedIds.size > 0
    ? `Totals for ${selectedIds.size} selected line${selectedIds.size > 1 ? 's' : ''}.`
    : 'Totals for all lines.';

  return (
    <div>
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr style={{ background: 'var(--db-surface-alt)', color: 'var(--db-text-muted)' }}>
            <th className="text-left px-2 py-1.5 font-medium">Item</th>
            <th className="text-left px-2 py-1.5 font-medium">Description</th>
            <th className="text-right px-2 py-1.5 font-medium">Qty</th>
            <th className="text-right px-2 py-1.5 font-medium">Price</th>
            <th className="text-right px-2 py-1.5 font-medium">Cost</th>
            <th className="text-right px-2 py-1.5 font-medium">Margin</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const isSelected = selectedIds.size === 0 || selectedIds.has(r.id);
            return (
              <tr
                key={r.id}
                className={isSelected ? '' : 'opacity-40'}
                style={{ borderBottom: '1px solid var(--db-border)' }}
              >
                <td className="px-2 py-1 font-mono">{r.itemCode}</td>
                <td className="px-2 py-1 max-w-[200px] truncate" style={{ color: 'var(--db-text-muted)' }}>{r.description}</td>
                <td className="px-2 py-1 text-right">{r.qty}</td>
                <td className="px-2 py-1 text-right">{formatCurrency(r.price)}</td>
                <td className="px-2 py-1 text-right">{formatCurrency(r.cost)}</td>
                <td className="px-2 py-1 text-right font-medium" style={marginStyle(r.margin)}>
                  {r.margin !== 0 ? formatCurrency(r.margin) : '—'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Footer totals */}
      <div className="px-2 py-2 text-xs" style={{ background: 'var(--db-surface-alt)', borderTop: '2px solid var(--db-border)' }}>
        <div className="mb-1" style={{ color: 'var(--db-text-dim)' }}>{selectionNote}</div>
        <div className="grid grid-cols-4 gap-4 text-right">
          <div>
            <div style={{ color: 'var(--db-text-muted)' }}>Amount</div>
            <div className="font-bold" style={{ color: 'var(--db-text)' }}>{formatCurrency(totalPrice)}</div>
          </div>
          <div>
            <div style={{ color: 'var(--db-text-muted)' }}>Cost</div>
            <div className="font-bold" style={{ color: 'var(--db-text)' }}>{formatCurrency(totalCost)}</div>
          </div>
          <div>
            <div style={{ color: 'var(--db-text-muted)' }}>Margin</div>
            <div className="font-bold" style={{ color: 'var(--db-accent-green)' }}>{formatCurrency(totalMargin)}</div>
          </div>
          <div>
            <div style={{ color: 'var(--db-text-muted)' }}>Margin %</div>
            <div className="font-bold" style={{ color: 'var(--db-accent-green)' }}>{marginPct.toFixed(2)}%</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MarginPanel;
