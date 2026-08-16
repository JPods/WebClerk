/* LastChecked: 2026-08-13 | WhereUsed: LineCardRenderer | WhoCreated: Claude */
// Commission detail panel — shows per-line commission breakdown by rep.
// Selection-aware totals matching MarginPanel pattern.
// Hidden unless C toggle is active in footer bar.
import React from 'react';

interface CommissionPanelProps {
  lines: any[];
  selectedIds: Set<number>;
  headerCommission?: any;
}

const formatCurrency = (v: number): string =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2 }).format(v);

const CommissionPanel: React.FC<CommissionPanelProps> = ({ lines, selectedIds, headerCommission }) => {
  // Build rows from lines — one row per line, showing primary rep info
  const rows = React.useMemo(() => {
    return lines.map((line, idx) => {
      const itemCode = line.item?.ida_item || line.ida_item || '—';
      const description = line.item?.description || line.description || '—';
      const extended = Number(line.price?.extended ?? 0);
      const comm = line.commission || {};
      const reps = comm.reps || [];
      const total = Number(comm.total ?? 0);
      const basis = comm.basis || '';
      const id = line.line_number ?? line.id ?? idx;

      return { id, itemCode, description, extended, reps, total, basis };
    });
  }, [lines]);

  // Selection-aware
  const activeRows = selectedIds.size > 0
    ? rows.filter(r => selectedIds.has(r.id))
    : rows;

  const totalExtended = activeRows.reduce((s, r) => s + r.extended, 0);
  const totalCommission = activeRows.reduce((s, r) => s + r.total, 0);
  const commPct = totalExtended > 0 ? (totalCommission / totalExtended) * 100 : 0;
  const selectionNote = selectedIds.size > 0
    ? `Totals for ${selectedIds.size} selected line${selectedIds.size > 1 ? 's' : ''}.`
    : 'Totals for all lines.';

  // Aggregate by rep across active lines
  const repSummary = React.useMemo(() => {
    const byRep: Record<number, { name: string; ida: string; rate: number; split: number; effRate: number; amount: number; basis: string; override: boolean }> = {};
    activeRows.forEach(row => {
      row.reps.forEach((rep: any) => {
        const rid = rep.rep_id || 0;
        if (!byRep[rid]) {
          byRep[rid] = {
            name: rep.name || rep.rep_ida || `Rep #${rid}`,
            ida: rep.rep_ida || '',
            rate: rep.rate_pct || 0,
            split: rep.split_pct || 100,
            effRate: rep.effective_rate || 0,
            amount: 0,
            basis: rep.basis || '',
            override: false,
          };
        }
        byRep[rid].amount += rep.amount || 0;
        if (rep.override) byRep[rid].override = true;
      });
    });
    return Object.values(byRep);
  }, [activeRows]);

  const hasData = rows.some(r => r.reps.length > 0);

  if (!hasData) {
    return (
      <div className="text-center py-6 text-sm db-text-dim">
        No commission data. Commission populates when customer has rep assignments.
      </div>
    );
  }

  return (
    <div>
      {/* Rep summary cards */}
      {repSummary.length > 0 && (
        <div className="px-3 py-2 db-border-bottom" style={{ background: 'color-mix(in srgb, var(--db-accent-purple) 10%, transparent)' }}>
          <div className="text-[10px] font-medium mb-1 db-text-purple">Representatives</div>
          <div className="flex flex-wrap gap-3">
            {repSummary.map((rep, i) => (
              <div key={i} className="rounded px-3 py-1.5 text-xs db-panel">
                <div className="font-medium db-text">
                  {rep.name}
                  {rep.override && <span className="ml-1 text-[9px] db-text-gold">(override)</span>}
                </div>
                <div className="flex gap-3 mt-0.5 db-text-muted">
                  <span>Rate: {rep.rate.toFixed(1)}%</span>
                  {rep.split < 100 && <span>Split: {rep.split.toFixed(0)}%</span>}
                  <span>Eff: {rep.effRate.toFixed(2)}%</span>
                  <span className="font-medium db-text-purple">{formatCurrency(rep.amount)}</span>
                  <span className="db-text-dim">{rep.basis}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Per-line table */}
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr className="db-surface-alt-muted">
            <th className="text-left px-2 py-1.5 font-medium">Item</th>
            <th className="text-left px-2 py-1.5 font-medium">Description</th>
            <th className="text-right px-2 py-1.5 font-medium">Extended</th>
            <th className="text-left px-2 py-1.5 font-medium">Rep(s)</th>
            <th className="text-right px-2 py-1.5 font-medium">Rate</th>
            <th className="text-right px-2 py-1.5 font-medium">Eff %</th>
            <th className="text-right px-2 py-1.5 font-medium">Commission</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const isSelected = selectedIds.size === 0 || selectedIds.has(r.id);
            const primaryRep = r.reps[0];
            const hasOverride = r.reps.some((rep: any) => rep.override);
            return (
              <tr
                key={r.id}
                className={`${isSelected ? '' : 'opacity-40'} db-border-bottom`}
              >
                <td className="px-2 py-1 font-mono">{r.itemCode}</td>
                <td className="px-2 py-1 max-w-[180px] truncate db-text-muted">{r.description}</td>
                <td className="px-2 py-1 text-right">{formatCurrency(r.extended)}</td>
                <td className="px-2 py-1 db-text-muted">
                  {r.reps.length === 0
                    ? '—'
                    : r.reps.map((rep: any) => rep.name || rep.rep_ida).join(', ')}
                </td>
                <td className="px-2 py-1 text-right">{primaryRep ? `${primaryRep.rate_pct}%` : '—'}</td>
                <td className="px-2 py-1 text-right">{primaryRep ? `${primaryRep.effective_rate?.toFixed(2)}%` : '—'}</td>
                <td className={`px-2 py-1 text-right font-medium db-text-purple ${hasOverride ? 'italic' : ''}`}>
                  {r.total > 0 ? formatCurrency(r.total) : '—'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Footer totals */}
      <div className="px-2 py-2 text-xs db-bg-surface-alt" style={{ borderTop: '2px solid var(--db-border)' }}>
        <div className="mb-1 db-text-dim">{selectionNote}</div>
        <div className="grid grid-cols-3 gap-4 text-right">
          <div>
            <div className="db-text-muted">Sales</div>
            <div className="font-bold db-text">{formatCurrency(totalExtended)}</div>
          </div>
          <div>
            <div className="db-text-muted">Commission</div>
            <div className="font-bold db-text-purple">{formatCurrency(totalCommission)}</div>
          </div>
          <div>
            <div className="db-text-muted">Effective %</div>
            <div className="font-bold db-text-purple">{commPct.toFixed(2)}%</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CommissionPanel;
