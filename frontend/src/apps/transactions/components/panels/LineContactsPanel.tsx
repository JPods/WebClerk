/* LastChecked: 2026-11-12 | WhereUsed: LineCardRenderer | WhoCreated: Claude */
/**
 * Line contacts (readme 110; Bill, 2026-11-12): the people a quote, order or invoice line
 * names by role — a furniture store's customer who holds the warranty. The panel edits the
 * selected line's refs.contacts; the form saves it with the document. Server is truth: a
 * person picked here shows as "saves with the document" until the server has copied their
 * name, company, email and phone into the entry (transactions/services/line_contacts.py).
 * The roles are the contact definition's selectlists.transaction_role.
 */
import React, { useEffect, useRef, useState } from 'react';
import { getRecords } from '@/api/wcapi';

export interface LineContact {
  role: string;
  contact_id: number;
  display_name?: string;
  company?: string;
  email?: string;
  phone?: string;
  /** Picked in this edit, not yet saved: the name shown is the browser's, marked as such. */
  _unsaved?: boolean;
}

export interface LineContactsPanelProps {
  /** The selected line, or null when none is selected. */
  line: any | null;
  canEdit: boolean;
  onChange: (contacts: LineContact[]) => void;
}

interface RoleOption { value: string; label?: string }

const nameOf = (r: any): string =>
  r.display_name || [r.name_first, r.name_last].filter(Boolean).join(' ') || r.company || r.email || `#${r.id}`;

/** What the save sends for a line's contacts: the entry without the browser's own mark. */
export function contactsToSend(contacts: LineContact[] | undefined): Omit<LineContact, '_unsaved'>[] {
  return (contacts || []).map(({ _unsaved, ...entry }) => (_unsaved ? { role: entry.role, contact_id: entry.contact_id } : entry));
}

const LineContactsPanel: React.FC<LineContactsPanelProps> = ({ line, canEdit, onChange }) => {
  const [roles, setRoles] = useState<RoleOption[]>([]);
  const [role, setRole] = useState('');
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let stale = false;
    (async () => {
      try {
        const res: any = await getRecords('setting', { parent_model: 'contact', purpose: 'wc:model', limit: 1 });
        const list: RoleOption[] = res?.results?.[0]?.config?.selectlists?.transaction_role || [];
        if (stale) return;
        setRoles(list);
        setRole((r) => r || String(list[0]?.value ?? ''));
      } catch { if (!stale) setRoles([]); }
    })();
    return () => { stale = true; };
  }, []);

  useEffect(() => {
    if (query.length < 2) { setResults([]); return; }
    let stale = false;
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const res: any = await getRecords('contact', { keyword: query, limit: 10 });
        if (!stale) setResults(res?.results || []);
      } catch { if (!stale) setResults([]); }
      if (!stale) setSearching(false);
    }, 300);
    return () => { stale = true; clearTimeout(timer); };
  }, [query]);

  if (!line) {
    return <div className="px-3 py-2 db-font-sm" style={{ color: 'var(--db-text-muted)' }}>Select a line to see its contacts</div>;
  }
  const contacts: LineContact[] = Array.isArray(line.refs?.contacts) ? line.refs.contacts : [];
  const labelOf = (value: string) => roles.find((r) => String(r.value) === value)?.label || value;
  const add = (picked: any) => {
    if (!role) return;
    if (contacts.some((c) => c.role === role && Number(c.contact_id) === Number(picked.id))) { setQuery(''); return; }
    onChange([...contacts, { role, contact_id: Number(picked.id), display_name: nameOf(picked), company: picked.company || '',
                             email: picked.email || '', phone: picked.phone || '', _unsaved: true }]);
    setQuery(''); setResults([]);
  };

  return (
    <div className="px-3 py-2" data-wc="line-contacts">
      {contacts.length === 0 && (
        <div className="db-font-sm mb-2" style={{ color: 'var(--db-text-muted)' }}>Nobody is named on this line.</div>
      )}
      {contacts.length > 0 && (
        <table className="db-font-sm mb-2" style={{ borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ color: 'var(--db-text-muted)', textAlign: 'left' }}>
              <th className="pr-4 font-normal">role</th><th className="pr-4 font-normal">name</th>
              <th className="pr-4 font-normal">company</th><th className="pr-4 font-normal">email</th>
              <th className="pr-4 font-normal">phone</th><th />
            </tr>
          </thead>
          <tbody>
            {contacts.map((c, i) => (
              <tr key={`${c.role}-${c.contact_id}`} data-wc="line-contact-row">
                <td className="pr-4">{labelOf(c.role)}</td>
                <td className="pr-4 font-medium" style={c._unsaved ? { fontStyle: 'italic' } : undefined}
                  title={c._unsaved ? 'Saves with the document; the server then copies the contact\'s details' : `contact #${c.contact_id}`}>
                  {c.display_name || `contact #${c.contact_id}`}
                </td>
                <td className="pr-4">{c.company}</td>
                <td className="pr-4">{c.email}</td>
                <td className="pr-4">{c.phone}</td>
                <td>
                  {canEdit && (
                    <button type="button" data-wc="line-contact-remove" title="Take this person off the line"
                      className="db-font-xs text-slate-400 hover:text-red-600 px-1"
                      onClick={() => onChange(contacts.filter((_, j) => j !== i))}>✕</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {canEdit && (
        <div className="relative flex items-center gap-2">
          <select data-wc="line-contact-role" value={role} onChange={(e) => setRole(e.target.value)}
            className="db-font-sm px-1 py-0.5 rounded" aria-label="Role"
            style={{ border: '1px solid var(--db-border, #dee2e6)', background: 'var(--db-input-bg, #fff)', color: 'var(--db-text, #212529)' }}>
            {roles.length === 0 && <option value="">no roles listed</option>}
            {roles.map((r) => <option key={String(r.value)} value={String(r.value)}>{r.label || String(r.value)}</option>)}
          </select>
          <input ref={inputRef} type="text" data-wc="line-contact-search" value={query} placeholder="search contacts…"
            onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === 'Escape') setQuery(''); }}
            className="db-font-sm px-2 py-0.5 w-56 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
            style={{ border: '1px solid var(--db-accent)', background: 'var(--db-input-bg, #fff)', color: 'var(--db-text, #212529)' }} />
          {(results.length > 0 || (query.length >= 2 && !searching)) && (
            <div className="absolute bottom-7 left-0 w-96 rounded shadow-lg z-50 max-h-60 overflow-y-auto"
              style={{ background: 'var(--db-surface, #fff)', border: '1px solid var(--db-border, #dee2e6)' }}>
              {results.map((r: any) => (
                <button key={r.id} type="button" data-wc="line-contact-result"
                  className="w-full text-left px-3 py-2 db-font-sm font-normal"
                  style={{ borderBottom: '1px solid var(--db-border-light, #e9ecef)' }}
                  onClick={() => add(r)}>
                  <span className="font-medium" style={{ color: 'var(--db-text)' }}>{nameOf(r)}</span>
                  <span className="db-font-xs ml-2" style={{ color: 'var(--db-text-muted)' }}>
                    {[r.company, r.email, r.phone].filter(Boolean).join(' · ')}
                  </span>
                </button>
              ))}
              {results.length === 0 && (
                <div className="px-3 py-2 db-font-sm" style={{ color: 'var(--db-text-muted)' }}>No contacts found</div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default LineContactsPanel;
