/**
 * SelectListBrowser — browse and edit all select lists across Settings.
 *
 * Left: flat index of every options array, sorted by field name.
 * Right: selected row's options editable at top, sibling select lists
 * (same field name, different settings) listed below, expandable to edit.
 *
 * LastChecked: 2026-08-18 | WhereUsed: /selectlists | WhoCreated: Bill+Claude
 */
import { useEffect, useState, useCallback } from "react";
import PageMeta from "@/components/common/PageMeta";
import apiClient from "@/api/axios";
import { saveRecord } from "@/api/wcapi";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface SelectListRow {
  field: string;
  path: string;
  count: number;
  options: { value: string; label: string; sequence?: number; alternate?: string }[];
  setting_id: number;
  setting_ida: string;
  setting_name: string;
  setting_parent_model: string;
  setting_purpose: string;
  shared_count: number;
}

/* ------------------------------------------------------------------ */
/*  OptionsEditor — inline add/edit/remove for an options array        */
/* ------------------------------------------------------------------ */

const OptionsEditor: React.FC<{
  options: any[];
  onChange: (opts: any[]) => void;
  saving?: boolean;
  onSave?: () => void;
  compact?: boolean;
}> = ({ options, onChange, saving, onSave, compact }) => {
  const [adding, setAdding] = useState(false);
  const [newValue, setNewValue] = useState('');
  const [newLabel, setNewLabel] = useState('');

  const handleAdd = () => {
    if (!newValue.trim()) return;
    onChange([...options, { value: newValue.trim(), label: newLabel.trim() || newValue.trim() }]);
    setNewValue('');
    setNewLabel('');
    setAdding(false);
  };

  const handleRemove = (idx: number) => {
    onChange(options.filter((_, i) => i !== idx));
  };

  const handleEdit = (idx: number, field: 'value' | 'label', val: string) => {
    const updated = [...options];
    updated[idx] = { ...updated[idx], [field]: val };
    onChange(updated);
  };

  const fs = compact ? '11px' : '12px';

  return (
    <div style={{ fontSize: fs }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--db-border)' }}>
            <th style={{ textAlign: 'left', padding: '4px 8px', color: 'var(--db-text-muted)', fontWeight: 600 }}>Value</th>
            <th style={{ textAlign: 'left', padding: '4px 8px', color: 'var(--db-text-muted)', fontWeight: 600 }}>Label</th>
            <th style={{ width: 30 }}></th>
          </tr>
        </thead>
        <tbody>
          {options.map((opt, idx) => (
            <tr key={idx} style={{ borderBottom: '1px solid color-mix(in srgb, var(--db-border) 50%, transparent)' }}>
              <td style={{ padding: '3px 8px' }}>
                <input type="text" value={opt.value || ''} onChange={(e) => handleEdit(idx, 'value', e.target.value)}
                  style={{ background: 'transparent', border: 'none', color: 'var(--db-text)', width: '100%', fontSize: fs }} />
              </td>
              <td style={{ padding: '3px 8px' }}>
                <input type="text" value={opt.label || ''} onChange={(e) => handleEdit(idx, 'label', e.target.value)}
                  style={{ background: 'transparent', border: 'none', color: 'var(--db-text)', width: '100%', fontSize: fs }} />
              </td>
              <td>
                <button onClick={() => handleRemove(idx)} title="Remove"
                  style={{ background: 'none', border: 'none', color: '#e53e3e', cursor: 'pointer', fontSize: '14px', fontWeight: 700 }}>×</button>
              </td>
            </tr>
          ))}
          {adding && (
            <tr>
              <td style={{ padding: '3px 8px' }}>
                <input type="text" value={newValue} onChange={(e) => setNewValue(e.target.value)}
                  placeholder="value" autoFocus
                  style={{ background: 'var(--db-input-bg, var(--db-surface))', border: '1px solid var(--db-border)', borderRadius: 3, color: 'var(--db-text)', width: '100%', padding: '2px 6px', fontSize: fs }} />
              </td>
              <td style={{ padding: '3px 8px' }}>
                <input type="text" value={newLabel} onChange={(e) => setNewLabel(e.target.value)}
                  placeholder="label" onKeyDown={(e) => { if (e.key === 'Enter') handleAdd(); }}
                  style={{ background: 'var(--db-input-bg, var(--db-surface))', border: '1px solid var(--db-border)', borderRadius: 3, color: 'var(--db-text)', width: '100%', padding: '2px 6px', fontSize: fs }} />
              </td>
              <td>
                <button onClick={handleAdd} style={{ background: 'none', border: 'none', color: 'var(--db-accent)', cursor: 'pointer', fontSize: '14px' }}>✓</button>
              </td>
            </tr>
          )}
        </tbody>
      </table>
      <div style={{ display: 'flex', gap: 8, marginTop: 6, alignItems: 'center' }}>
        {!adding && (
          <button onClick={() => setAdding(true)}
            style={{ background: 'color-mix(in srgb, #22c55e 12%, transparent)', border: '1px solid #22c55e', borderRadius: 3, padding: '2px 8px', color: '#22c55e', cursor: 'pointer', fontSize: fs, fontWeight: 600 }}>
            + Add
          </button>
        )}
        {onSave && (
          <button onClick={onSave} disabled={saving}
            style={{ background: '#3355FF', border: 'none', borderRadius: 3, padding: '3px 12px', color: '#fff', cursor: 'pointer', fontWeight: 600, fontSize: fs }}>
            {saving ? 'Saving...' : '💾 Save'}
          </button>
        )}
      </div>
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  SiblingPanel — collapsed panel for a related select list           */
/* ------------------------------------------------------------------ */

const SiblingPanel: React.FC<{
  row: SelectListRow;
  onSaved: () => void;
}> = ({ row, onSaved }) => {
  const [expanded, setExpanded] = useState(false);
  const [options, setOptions] = useState(row.options);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  const handleChange = (opts: any[]) => {
    setOptions(opts);
    setDirty(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // Build the nested update — only send the specific path
      const parts = row.path.split('.');
      let update: any = options;
      for (let i = parts.length - 1; i >= 0; i--) {
        update = { [parts[i]]: update };
      }
      await saveRecord('setting', { id: row.setting_id, config: update });
      setDirty(false);
      onSaved();
    } catch (err) {
      console.error('Save failed:', err);
    }
    setSaving(false);
  };

  return (
    <div style={{ border: '1px solid var(--db-border)', borderRadius: 4, marginBottom: 8 }}>
      <button onClick={() => setExpanded(!expanded)}
        style={{
          width: '100%', textAlign: 'left', padding: '8px 12px',
          background: expanded ? 'color-mix(in srgb, var(--db-accent) 8%, transparent)' : 'var(--db-surface-alt)',
          border: 'none', cursor: 'pointer', color: 'var(--db-text)',
          display: 'flex', alignItems: 'center', gap: 8, fontSize: 12,
        }}>
        <span style={{ color: 'var(--db-text-muted)' }}>{expanded ? '▾' : '▸'}</span>
        <span style={{ fontWeight: 600 }}>{row.setting_ida}</span>
        <span style={{ color: 'var(--db-text-muted)' }}>{row.setting_purpose}</span>
        <span style={{ marginLeft: 'auto', color: 'var(--db-text-muted)' }}>{row.count} options</span>
        {dirty && <span style={{ color: 'var(--db-accent)', fontWeight: 600 }}>●</span>}
      </button>
      {expanded && (
        <div style={{ padding: '8px 12px' }}>
          <OptionsEditor options={options} onChange={handleChange} saving={saving} onSave={handleSave} compact />
        </div>
      )}
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  Main Page                                                          */
/* ------------------------------------------------------------------ */

type SortKey = 'field' | 'setting_ida' | 'setting_name' | 'setting_parent_model' | 'setting_purpose' | 'count' | 'shared_count';

const SelectListBrowser: React.FC = () => {
  const [rows, setRows] = useState<SelectListRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [editOptions, setEditOptions] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [sortKey, setSortKey] = useState<SortKey>('field');
  const [sortAsc, setSortAsc] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/wcapi/selectlists/', { credentials: 'include' });
      const json = await res.json();
      console.log('[SelectListBrowser] raw keys:', Object.keys(json), 'data keys:', json.data ? Object.keys(json.data) : 'no data');
      const r = json?.data?.rows || json?.rows || [];
      console.log('[SelectListBrowser] fetched', r.length, 'rows');
      setRows(r);
    } catch (err) {
      console.error('Failed to load select lists:', err);
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(true); }
  };

  const sortedRows = [...rows].sort((a, b) => {
    const av = a[sortKey];
    const bv = b[sortKey];
    const cmp = typeof av === 'string' ? av.localeCompare(bv as string) : (av as number) - (bv as number);
    return sortAsc ? cmp : -cmp;
  });

  const selected = selectedIdx !== null ? sortedRows[selectedIdx] : null;

  // Find siblings — same field name, different settings
  const siblings = selected
    ? sortedRows.filter(r => r.field === selected.field && (r.setting_id !== selected.setting_id || r.path !== selected.path))
    : [];

  const handleSelect = (idx: number) => {
    setSelectedIdx(idx);
    setEditOptions([...rows[idx].options]);
    setDirty(false);
  };

  const handleSave = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      const parts = selected.path.split('.');
      let update: any = editOptions;
      for (let i = parts.length - 1; i >= 0; i--) {
        update = { [parts[i]]: update };
      }
      await saveRecord('setting', { id: selected.setting_id, config: update });
      setDirty(false);
      fetchData();
    } catch (err) {
      console.error('Save failed:', err);
    }
    setSaving(false);
  };

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--db-surface)' }}>
      <PageMeta title="Select Lists" />

      {/* Left — list with sortable header */}
      <div style={{ width: 620, borderRight: '1px solid var(--db-border)', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--db-border)', fontWeight: 700, fontSize: 13, color: 'var(--db-text)' }}>
          Select Lists ({rows.length})
        </div>
        {/* Column header — clickable to sort */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '4px 12px',
          borderBottom: '2px solid var(--db-border)', background: 'var(--db-surface-alt)',
          fontSize: 10, fontWeight: 700, color: 'var(--db-text-muted)', textTransform: 'uppercase',
        }}>
          {([['field', 'Field', 100], ['setting_ida', 'IDA', 90], ['setting_name', 'Name', 0], ['setting_parent_model', 'Model', 65], ['setting_purpose', 'Purpose', 70], ['count', '#', 22], ['shared_count', '×', 22]] as const).map(([key, label, minW]) => (
            <button key={key} onClick={() => handleSort(key as SortKey)}
              style={{
                background: 'none', border: 'none', cursor: 'pointer', padding: '2px 0',
                color: sortKey === key ? 'var(--db-accent)' : 'var(--db-text-muted)',
                fontWeight: 700, fontSize: 10, textTransform: 'uppercase', textAlign: 'left',
                minWidth: minW || undefined, flex: minW === 0 ? 1 : undefined,
              }}>
              {label} {sortKey === key ? (sortAsc ? '▲' : '▼') : ''}
            </button>
          ))}
        </div>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {loading ? (
            <div style={{ padding: 16, color: 'var(--db-text-muted)' }}>Loading...</div>
          ) : sortedRows.map((row, idx) => (
            <button key={`${row.setting_id}-${row.path}`}
              onClick={() => handleSelect(idx)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8, width: '100%',
                padding: '5px 12px', border: 'none', borderBottom: '1px solid color-mix(in srgb, var(--db-border) 50%, transparent)',
                background: selectedIdx === idx ? 'color-mix(in srgb, var(--db-accent) 12%, transparent)' : 'transparent',
                cursor: 'pointer', textAlign: 'left', fontSize: 11, color: 'var(--db-text)',
              }}>
              <span style={{ fontWeight: 600, minWidth: 100 }}>{row.field}</span>
              <span style={{ color: 'var(--db-text-muted)', minWidth: 90, fontFamily: 'monospace', fontSize: 10 }}>{row.setting_ida}</span>
              <span style={{ color: 'var(--db-text)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{row.setting_name}</span>
              <span style={{ color: 'var(--db-text-muted)', minWidth: 65 }}>{row.setting_parent_model}</span>
              <span style={{ color: 'var(--db-text-muted)', minWidth: 70, fontSize: 10 }}>{row.setting_purpose}</span>
              <span style={{ color: 'var(--db-text-muted)', minWidth: 22, textAlign: 'right' }}>{row.count}</span>
              <span style={{ color: row.shared_count > 1 ? 'var(--db-accent)' : 'var(--db-text-muted)', minWidth: 22, textAlign: 'right', fontSize: 10, fontWeight: row.shared_count > 1 ? 600 : 400 }}>
                {row.shared_count > 1 ? `×${row.shared_count}` : ''}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Right — detail */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {selected ? (
          <>
            {/* Header — actions at top */}
            <div style={{
              padding: '10px 16px', borderBottom: '1px solid var(--db-border)',
              display: 'flex', alignItems: 'center', gap: 12,
              background: 'var(--db-surface-alt)',
            }}>
              <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--db-text)' }}>{selected.field}</span>
              <span style={{ color: 'var(--db-text-muted)', fontSize: 12 }}>{selected.setting_ida}</span>
              <span style={{ color: 'var(--db-text-muted)', fontSize: 11 }}>{selected.setting_purpose}</span>
              <span style={{ flex: 1 }} />
              {dirty && <span style={{ color: 'var(--db-accent)', fontWeight: 600, fontSize: 11 }}>unsaved</span>}
              <button onClick={handleSave} disabled={saving || !dirty}
                style={{
                  background: dirty ? 'var(--db-accent)' : 'var(--db-surface-alt)',
                  border: '1px solid var(--db-border)', borderRadius: 4,
                  padding: '4px 14px', color: dirty ? '#fff' : 'var(--db-text-muted)',
                  cursor: dirty ? 'pointer' : 'default', fontWeight: 600, fontSize: 12,
                }}>
                {saving ? 'Saving...' : '💾 Save'}
              </button>
            </div>

            {/* Selected row's options — editable */}
            <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
              <OptionsEditor
                options={editOptions}
                onChange={(opts) => { setEditOptions(opts); setDirty(true); }}
              />

              {/* Siblings — same field, other settings */}
              {siblings.length > 0 && (
                <div style={{ marginTop: 24 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--db-text-muted)', marginBottom: 8 }}>
                    Same field in other settings ({siblings.length})
                  </div>
                  {siblings.map((sib) => (
                    <SiblingPanel key={`${sib.setting_id}-${sib.path}`} row={sib} onSaved={fetchData} />
                  ))}
                </div>
              )}
            </div>
          </>
        ) : (
          <div style={{ padding: 40, color: 'var(--db-text-muted)', textAlign: 'center', fontSize: 13 }}>
            Select a field from the list to view and edit its options.
          </div>
        )}
      </div>
    </div>
  );
};

export default SelectListBrowser;
