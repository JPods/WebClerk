/**
 * CommPanel — consolidated communications table.
 *
 * One DbColumns list showing all communication records (email, phone,
 * address, domain) for a contact. Grouped by type with section headers.
 * Replaces the old four-section CommList/CommCard approach.
 *
 * Address rows are taller to show the full address. Users can paste a
 * full_address and the backend parses it into components.
 *
 * Usage:
 *   <CommPanel
 *     contactId={8}
 *     emails={refs.links.email}
 *     phones={refs.links.phone}
 *     addresses={refs.links.address}
 *     domains={refs.links.domain}
 *     onRefresh={reloadRecord}
 *   />
 */
import React, { useMemo, useState, useCallback } from 'react';
import { useDispatch } from 'react-redux';
import { showToast } from '@/store/slices/toastSlice';
import { saveRecord, deleteRecord } from '@/api/wcapi';
import { DbColumns, type DbColumnDef } from '@/apps/common/components/panels/DbColumns';

export interface CommPanelProps {
  contactId: number;
  emails?: any[];
  phones?: any[];
  addresses?: any[];
  domains?: any[];
  onRefresh?: () => void;
}

// ── Normalize all comm records into a flat array ─────────────────────────────

interface CommRow {
  _type: 'email' | 'phone' | 'address' | 'domain';
  _sortKey: string;
  id?: number;
  value: string;
  name: string;
  raw: any;
}

function buildRows(
  emails: any[],
  phones: any[],
  addresses: any[],
  domains: any[],
): CommRow[] {
  const rows: CommRow[] = [];

  for (const e of emails) {
    rows.push({
      _type: 'email',
      _sortKey: `1-email-${e.id}`,
      id: e.id,
      value: e.email || '',
      name: e.name || e.type || '',
      raw: e,
    });
  }
  for (const p of phones) {
    rows.push({
      _type: 'phone',
      _sortKey: `2-phone-${p.id}`,
      id: p.id,
      value: p.number || p.format || '',
      name: p.name || '',
      raw: p,
    });
  }
  for (const a of addresses) {
    rows.push({
      _type: 'address',
      _sortKey: `3-address-${a.id}`,
      id: a.id,
      value: a.full || [a.address1, a.city, a.state, a.zip].filter(Boolean).join(', '),
      name: a.address_type || '',
      raw: a,
    });
  }
  for (const d of domains) {
    rows.push({
      _type: 'domain',
      _sortKey: `4-domain-${d.id}`,
      id: d.id,
      value: d.path || '',
      name: d.type || '',
      raw: d,
    });
  }

  return rows.sort((a, b) => a._sortKey.localeCompare(b._sortKey));
}

// ── Inline edit row ──────────────────────────────────────────────────────────

const AddRow: React.FC<{
  contactId: number;
  onSaved: () => void;
  onCancel: () => void;
}> = ({ contactId, onSaved, onCancel }) => {
  const dispatch = useDispatch();
  const [type, setType] = useState<'email' | 'phone' | 'address' | 'domain'>('email');
  const [value, setValue] = useState('');
  const [name, setName] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!value.trim()) return;
    setSaving(true);
    try {
      const payload: any = { contact: contactId };
      if (type === 'email') payload.email = value;
      else if (type === 'phone') payload.number = value;
      else if (type === 'address') payload.full = value;
      else if (type === 'domain') payload.path = value;
      if (name) payload.name = name;

      await saveRecord(type, payload);
      dispatch(showToast({ message: `${type} added`, type: 'success' }));
      onSaved();
    } catch {
      dispatch(showToast({ message: `Failed to add ${type}`, type: 'error' }));
    }
    setSaving(false);
  };

  return (
    <div
      className="db-list-row"
      style={{ padding: '6px 12px', background: 'var(--db-row-active)' }}
    >
      <div className="db-list-row__indicator" style={{ background: 'var(--db-accent)' }} />
      <select
        value={type}
        onChange={(e) => setType(e.target.value as any)}
        style={{
          width: 80, flexShrink: 0, fontSize: 11,
          background: 'var(--db-input-bg)', color: 'var(--db-text)',
          border: '1px solid var(--db-input-border)', borderRadius: 3, padding: '2px 4px',
        }}
      >
        <option value="email">email</option>
        <option value="phone">phone</option>
        <option value="address">address</option>
        <option value="domain">domain</option>
      </select>
      <input
        autoFocus
        placeholder={type === 'address' ? 'Paste full address...' : `Enter ${type}...`}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        style={{
          flex: 1, fontSize: 12,
          background: 'var(--db-input-bg)', color: 'var(--db-text)',
          border: '1px solid var(--db-input-border)', borderRadius: 3, padding: '3px 6px',
        }}
      />
      <input
        placeholder="Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        style={{
          width: 100, fontSize: 12,
          background: 'var(--db-input-bg)', color: 'var(--db-text)',
          border: '1px solid var(--db-input-border)', borderRadius: 3, padding: '3px 6px',
        }}
      />
      <button
        onClick={handleSave}
        disabled={saving}
        style={{ fontSize: 10, fontWeight: 600, color: 'var(--db-accent-green)', padding: '0 6px' }}
      >
        {saving ? '...' : 'save'}
      </button>
      <button
        onClick={onCancel}
        style={{ fontSize: 10, color: 'var(--db-text-muted)', padding: '0 6px' }}
      >
        cancel
      </button>
    </div>
  );
};

// ── Column definitions ───────────────────────────────────────────────────────

const COMM_COLUMNS: DbColumnDef<CommRow>[] = [
  {
    key: 'type',
    label: 'Type',
    width: '80px',
    render: (r) => (
      <span style={{ color: 'var(--db-text-muted)', textTransform: 'uppercase', fontSize: 10, fontWeight: 600 }}>
        {r._type}
      </span>
    ),
  },
  {
    key: 'value',
    label: 'Value',
    render: (r) => (
      <span style={{
        whiteSpace: r._type === 'address' ? 'normal' : 'nowrap',
        lineHeight: r._type === 'address' ? '1.4' : undefined,
      }}>
        {r.value}
      </span>
    ),
  },
  {
    key: 'name',
    label: 'Name',
    width: '100px',
    render: (r) => (
      <span style={{ color: 'var(--db-text-muted)' }}>{r.name || '—'}</span>
    ),
  },
];

// ── Main component ───────────────────────────────────────────────────────────

const CommPanel: React.FC<CommPanelProps> = ({
  contactId,
  emails = [],
  phones = [],
  addresses = [],
  domains = [],
  onRefresh,
}) => {
  const dispatch = useDispatch();
  const [adding, setAdding] = useState(false);

  const rows = useMemo(
    () => buildRows(emails, phones, addresses, domains),
    [emails, phones, addresses, domains],
  );

  const handleDelete = useCallback(async (row: CommRow) => {
    if (!row.id) return;
    if (!confirm(`Delete this ${row._type} record?`)) return;
    if (!confirm('CONFIRM: Permanently delete. This cannot be undone.')) return;
    try {
      await deleteRecord(row._type, row.id);
      dispatch(showToast({ message: `${row._type} deleted`, type: 'success' }));
      onRefresh?.();
    } catch {
      dispatch(showToast({ message: `Failed to delete ${row._type}`, type: 'error' }));
    }
  }, [dispatch, onRefresh]);

  return (
    <DbColumns<CommRow>
      storageKey="panel:contact:communications"
      columns={COMM_COLUMNS}
      data={rows}
      rowKey={(r) => `${r._type}-${r.id ?? 'new'}`}
      sectionLabel="Communications"
      sectionIcon="📇"
      onAdd={() => setAdding(true)}
      collapsible={false}
      onRowAction={(r) => handleDelete(r)}
      emptyMessage="No communications"
    >
      {adding && (
        <AddRow
          contactId={contactId}
          onSaved={() => { setAdding(false); onRefresh?.(); }}
          onCancel={() => setAdding(false)}
        />
      )}
    </DbColumns>
  );
};

export default CommPanel;
