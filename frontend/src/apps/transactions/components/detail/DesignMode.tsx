/* LastChecked: 2026-11-14 | WhereUsed: DbForm | WhoCreated: Claude */
/**
 * DesignMode — arrange a form's header cards (Bill, 2026-11-14: "allow users to easily adjust
 * fields and leafs important to them").
 *
 * The form under this panel is the preview: every change here redraws it at once.
 * - Drag a field to move it, within a card or to another card.
 * - Drag the bar between two cards to make one wider and the other narrower.
 * - Click a card to list the model's leaves not yet placed (every leaf this viewer may see,
 *   from wcapi/<model>/fields/); click one to place it.
 * - Click a field's label to rename it; × removes the field.
 * - Save for me     → the person's own Contact (config.ui.form.<model>.columns); laid over the
 *                     company's form by useDetailLayout.
 * - Save for everyone (staff) → the model's definition (config.layout.form.default).
 * - Company form    → drop the person's own arrangement.
 * - Reset to default (staff) → the definition's form back to the code's; the old one is logged.
 */
import React, { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';
import { getViewLeaves, resetLayout, saveRecord } from '@/api/wcapi';
import { myFormColumns, saveMyFormColumns, type DetailLayout } from '@/hooks/useDetailLayout';

export interface DesignModeProps {
  layout: DetailLayout;
  modelName: string;
  /** Staff may change the form for everyone and reset it to the code's default. */
  isStaff?: boolean;
  onLayoutChange: (layout: DetailLayout) => void;
  /** The saved form changed (mine or everyone's): the form reads it again. */
  onSaved?: () => void;
}

type Spot = { col: number; idx: number };

const weightOf = (col: any): number => (Number(col?.weight) > 0 ? Number(col.weight) : 1);

/** Move one field to a spot; the spot is counted before the field is taken out. */
export function moveField(columns: any[], from: Spot, to: Spot): any[] {
  const next = JSON.parse(JSON.stringify(columns));
  const [moved] = (next[from.col]?.fields || []).splice(from.idx, 1);
  if (!moved || !next[to.col]) return columns;
  const at = from.col === to.col && from.idx < to.idx ? to.idx - 1 : to.idx;
  next[to.col].fields = next[to.col].fields || [];
  next[to.col].fields.splice(Math.max(0, Math.min(at, next[to.col].fields.length)), 0, moved);
  return next;
}

/** Shift width between card `left` and the card after it; `share` is the part of the row dragged. */
export function shiftWeight(columns: any[], left: number, share: number): any[] {
  const next = JSON.parse(JSON.stringify(columns));
  const a = next[left], b = next[left + 1];
  if (!a || !b) return columns;
  const total = next.reduce((n: number, c: any) => n + weightOf(c), 0);
  const pair = weightOf(a) + weightOf(b);
  const least = Math.min(0.25, pair / 4);
  const wa = Math.max(least, Math.min(pair - least, weightOf(a) + share * total));
  a.weight = Math.round(wa * 100) / 100;
  b.weight = Math.round((pair - wa) * 100) / 100;
  return next;
}

const DesignMode: React.FC<DesignModeProps> = ({ layout, modelName, isStaff, onLayoutChange, onSaved }) => {
  const dispatch = useDispatch();
  const [activeColumn, setActiveColumn] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [leaves, setLeaves] = useState<string[]>([]);
  const [find, setFind] = useState('');
  const [drag, setDrag] = useState<Spot | null>(null);
  const [over, setOver] = useState<Spot | null>(null);
  const [hasMine, setHasMine] = useState(() => !!myFormColumns(modelName));
  const rowRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let live = true;
    getViewLeaves(modelName).then((l) => { if (live) setLeaves(l); }).catch(() => { if (live) setLeaves([]); });
    return () => { live = false; };
  }, [modelName]);

  const headerSection = layout.sections?.find((s: any) => s.type === 'header') as any;
  const columns: any[] = headerSection?.columns || [];

  const setColumns = useCallback((next: any[]) => {
    const copy = JSON.parse(JSON.stringify(layout));
    const header = copy.sections.find((s: any) => s.type === 'header');
    if (!header) return;
    header.columns = next;
    onLayoutChange(copy);
  }, [layout, onLayoutChange]);

  const placed = useMemo(() => {
    const names = new Set<string>();
    columns.forEach((c) => (c.fields || []).forEach((f: any) => names.add(f.field)));
    return names;
  }, [columns]);

  // The leaves not placed: lines are the line card's, not the header's.
  const available = useMemo(() => {
    const q = find.trim().toLowerCase();
    return leaves.filter((l) => !placed.has(l) && !l.startsWith('lines.') && (!q || l.toLowerCase().includes(q)));
  }, [leaves, placed, find]);

  const addField = (colIdx: number, leaf: string) => {
    const next = JSON.parse(JSON.stringify(columns));
    next[colIdx].fields = [...(next[colIdx].fields || []), { field: leaf, label: leaf.split('.').pop() || leaf }];
    setColumns(next);
  };
  const removeField = (colIdx: number, idx: number) => {
    const next = JSON.parse(JSON.stringify(columns));
    next[colIdx].fields.splice(idx, 1);
    setColumns(next);
  };
  const renameField = (colIdx: number, idx: number) => {
    const f = columns[colIdx]?.fields?.[idx];
    const label = window.prompt(`Label for ${f?.field}`, f?.label || '');
    if (label == null || !label.trim()) return;
    const next = JSON.parse(JSON.stringify(columns));
    next[colIdx].fields[idx].label = label.trim();
    setColumns(next);
  };
  const drop = (to: Spot) => {
    if (drag) setColumns(moveField(columns, drag, to));
    setDrag(null); setOver(null);
  };

  // Drag the bar between two cards: width moves from one to the other.
  const startResize = (left: number, e: React.MouseEvent) => {
    e.preventDefault(); e.stopPropagation();
    const width = rowRef.current?.getBoundingClientRect().width || 1;
    const startX = e.clientX;
    const start = columns;
    const move = (ev: MouseEvent) => setColumns(shiftWeight(start, left, (ev.clientX - startX) / width));
    const up = () => { window.removeEventListener('mousemove', move); window.removeEventListener('mouseup', up); };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
  };

  const saveMine = () => {
    saveMyFormColumns(modelName, columns);
    setHasMine(true);
    dispatch(showToast({ message: `Your ${modelName} form is saved. Others still see the company's.`, type: 'success' }));
    onSaved?.();
  };
  const dropMine = () => {
    saveMyFormColumns(modelName, null);
    setHasMine(false);
    dispatch(showToast({ message: `You now see the company's ${modelName} form.`, type: 'info' }));
    onSaved?.();
  };
  // Where useDetailLayout reads the company's form: the model's definition. A posted config
  // merges into the stored one. The person's own arrangement is dropped so they see what they saved.
  const saveForEveryone = async () => {
    setSaving(true);
    try {
      const { getRecords } = await import('@/api/wcapi');
      const res = await getRecords('setting', { parent_model: modelName, purpose: 'wc:model', limit: 1 });
      const setting = res?.results?.[0];
      if (!setting) {
        dispatch(showToast({ message: `No model definition for ${modelName}`, type: 'error' }));
      } else {
        await saveRecord('setting', { id: setting.id, config: { layout: { form: { default: layout } } } });
        saveMyFormColumns(modelName, null);
        setHasMine(false);
        dispatch(showToast({ message: `The ${modelName} form is saved for everyone`, type: 'success' }));
        onSaved?.();
      }
    } catch (err: any) {
      dispatch(showToast({ message: err?.response?.data?.message || 'Failed to save the form', type: 'error' }));
    }
    setSaving(false);
  };
  const resetForm = async () => {
    if (!window.confirm(`Reset the ${modelName} form to the default? The current form is kept in the Log.`)) return;
    try {
      await resetLayout(modelName, 'form');
      window.location.reload();
    } catch (err: any) {
      dispatch(showToast({ message: err?.response?.data?.message || 'Failed to reset the form', type: 'error' }));
    }
  };

  const button = 'px-3 py-1 text-xs font-medium rounded disabled:opacity-50';
  const outline = `${button} border border-amber-600 text-amber-700 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-900/40`;

  if (!columns.length) {
    return (
      <div className="bg-amber-50 dark:bg-amber-900/20 border-2 border-dashed border-amber-400 rounded-lg p-3 mb-3 text-xs text-amber-700">
        This form's header is made of named cards, not columns; it cannot be arranged here yet.
      </div>
    );
  }

  return (
    <div data-wc="design-mode" className="bg-amber-50 dark:bg-amber-900/20 border-2 border-dashed border-amber-400 rounded-lg p-3 mb-3">
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <span className="text-xs font-bold text-amber-700 dark:text-amber-300">LAYOUT</span>
        <span className="text-[11px] text-amber-700">
          Drag a field to move it. Drag the bar between cards to resize. Click a card to add a field.
        </span>
        <span className="flex-1" />
        {hasMine && <button data-wc="design-company" onClick={dropMine} disabled={saving} className={outline}>Company form</button>}
        {isStaff && <button data-wc="design-reset" onClick={resetForm} disabled={saving} className={outline}>Reset to default</button>}
        {isStaff && (
          <button data-wc="design-save-all" onClick={saveForEveryone} disabled={saving} className={outline}>
            {saving ? 'Saving...' : 'Save for everyone'}
          </button>
        )}
        <button data-wc="design-save-mine" onClick={saveMine} disabled={saving}
          className={`${button} bg-amber-600 text-white hover:bg-amber-700`}>Save for me</button>
      </div>

      <div ref={rowRef} className="flex items-stretch">
        {columns.map((col: any, colIdx: number) => (
          <React.Fragment key={colIdx}>
            <div data-wc="design-card"
              className={`border rounded-lg p-2 cursor-pointer transition-colors min-w-0 ${activeColumn === colIdx ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' : 'border-amber-300 hover:border-blue-400'}`}
              style={{ flex: `${weightOf(col)} 1 0` }}
              onClick={() => { setActiveColumn(activeColumn === colIdx ? null : colIdx); setFind(''); }}
              onDragOver={(e) => { e.preventDefault(); setOver({ col: colIdx, idx: (col.fields || []).length }); }}
              onDrop={(e) => { e.preventDefault(); drop(over && over.col === colIdx ? over : { col: colIdx, idx: (col.fields || []).length }); }}
            >
              <div className="text-[11px] font-bold text-slate-600 mb-1">{col.title}</div>
              {(col.fields || []).map((f: any, fIdx: number) => (
                <div key={f.field} data-wc="design-field" data-field={f.field} draggable
                  onDragStart={(e) => { e.stopPropagation(); e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', f.field); setDrag({ col: colIdx, idx: fIdx }); }}
                  onDragEnd={() => { setDrag(null); setOver(null); }}
                  onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); setOver({ col: colIdx, idx: fIdx }); }}
                  onClick={(e) => e.stopPropagation()}
                  className="text-[11px] px-1.5 py-0.5 bg-white dark:bg-slate-800 rounded border border-slate-200 dark:border-slate-600 mb-0.5 flex items-center gap-1 cursor-grab"
                  style={over && drag && over.col === colIdx && over.idx === fIdx ? { borderTop: '2px solid #2563eb' } : undefined}
                >
                  <span className="shrink-0 hover:underline cursor-text" title="Click to rename"
                    onClick={() => renameField(colIdx, fIdx)}>{f.label || f.field}</span>
                  <span className="text-[10px] text-slate-400 font-mono truncate min-w-0">{f.field}</span>
                  <button className="ml-auto text-red-400 hover:text-red-600 px-1" title="Remove from the form"
                    onClick={() => removeField(colIdx, fIdx)}>×</button>
                </div>
              ))}
              {activeColumn === colIdx && (
                <div className="mt-2 pt-2 border-t border-blue-200" onClick={(e) => e.stopPropagation()}>
                  <input data-wc="design-find" autoFocus value={find} onChange={(e) => setFind(e.target.value)}
                    placeholder={`Find a field (${available.length} not placed)`}
                    className="w-full text-[11px] px-1.5 py-0.5 mb-1 rounded border border-blue-200 bg-white dark:bg-slate-800" />
                  <div className="max-h-40 overflow-y-auto space-y-0.5">
                    {available.slice(0, 200).map((leaf) => (
                      <button key={leaf} data-wc="design-leaf" onClick={() => addField(colIdx, leaf)}
                        className="w-full text-left text-[11px] px-1.5 py-0.5 rounded hover:bg-blue-100 dark:hover:bg-blue-800 font-mono truncate">
                        {leaf}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
            {colIdx < columns.length - 1 && (
              <div data-wc="design-resize" title="Drag to resize the cards beside this bar"
                onMouseDown={(e) => startResize(colIdx, e)}
                className="w-3 mx-0.5 shrink-0 cursor-col-resize flex items-center justify-center">
                <div className="w-1 h-10 rounded bg-amber-400" />
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};

export default DesignMode;
