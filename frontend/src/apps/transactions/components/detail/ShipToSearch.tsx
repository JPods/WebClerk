/* LastChecked: 2026-11-11 | WhereUsed: HeaderRenderer | WhoCreated: Claude */
/**
 * Ship-to search (Bill, 2026-11-11): ship a document to any contact or customer — a drop
 * shipment. The tick box picks which is searched. The pick is not copied here: the form saves
 * the signal `_ship_to_from: {model, id}` and reloads; the server fills the block
 * (transactions/services/party_fill.py take_ship_to). Server is truth.
 */
import React, { useEffect, useRef, useState } from 'react';
import { getRecords } from '@/api/wcapi';

export type ShipToSource = 'contact' | 'customer';

export interface ShipToSearchProps {
  onPick: (model: ShipToSource, id: number) => void;
}

const nameOf = (r: any): string =>
  r.company || r.display_name || r.attention || [r.name_first, r.name_last].filter(Boolean).join(' ') || `#${r.id}`;

const ShipToSearch: React.FC<ShipToSearchProps> = ({ onPick }) => {
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState<ShipToSource>('customer');
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { if (open) inputRef.current?.focus(); }, [open, source]);
  useEffect(() => {
    if (!open || query.length < 2) { setResults([]); return; }
    let stale = false;
    const timer = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await getRecords(source, { keyword: query, limit: 10 });
        if (!stale) setResults(res?.results || []);
      } catch { if (!stale) setResults([]); }
      if (!stale) setSearching(false);
    }, 300);
    return () => { stale = true; clearTimeout(timer); };
  }, [open, query, source]);

  const close = () => { setOpen(false); setQuery(''); setResults([]); };

  if (!open) {
    return (
      <button type="button" data-wc="ship-to-search-open"
        className="ml-auto db-font-xs text-slate-400 hover:text-blue-600 px-1 py-0.5 rounded hover:bg-blue-50"
        title="Ship to a contact or a customer" onClick={() => setOpen(true)}>🔍</button>
    );
  }
  return (
    <div className="ml-auto relative flex items-center gap-2" data-wc="ship-to-search">
      <label className="flex items-center gap-1 db-font-xs font-normal" style={{ color: 'var(--db-text-muted)' }}
        title="Ticked: search contacts. Unticked: search customers.">
        <input type="checkbox" data-wc="ship-to-search-contact" checked={source === 'contact'}
          onChange={(e) => setSource(e.target.checked ? 'contact' : 'customer')} />
        <span>contact</span>
      </label>
      <input ref={inputRef} type="text" value={query} onChange={(e) => setQuery(e.target.value)}
        onKeyDown={(e) => { if (e.key === 'Escape') close(); }}
        placeholder={source === 'contact' ? 'search contacts…' : 'search customers…'}
        className="db-font-sm px-2 py-0.5 w-40 rounded font-normal focus:outline-none focus:ring-1 focus:ring-blue-500"
        style={{ border: '1px solid var(--db-accent)', background: 'var(--db-input-bg, #fff)', color: 'var(--db-text, #212529)' }} />
      <button type="button" className="db-font-xs text-slate-400 hover:text-slate-700" title="Close" onClick={close}>✕</button>
      {(results.length > 0 || (query.length >= 2 && !searching)) && (
        <div className="absolute top-6 right-0 w-96 rounded shadow-lg z-50 max-h-60 overflow-y-auto"
          style={{ background: 'var(--db-surface, #fff)', border: '1px solid var(--db-border, #dee2e6)' }}>
          {results.map((r: any) => (
            <button key={r.id} type="button" data-wc="ship-to-search-result"
              className="w-full text-left px-3 py-2 db-font-sm font-normal last:border-0"
              style={{ borderBottom: '1px solid var(--db-border-light, #e9ecef)' }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--db-row-hover)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              onClick={() => { onPick(source, r.id); close(); }}>
              <div className="flex items-baseline gap-2">
                <span className="font-medium" style={{ color: 'var(--db-text)' }}>{nameOf(r)}</span>
                <span className="font-mono db-font-xs" style={{ color: 'var(--db-text-dim)' }}>{source} #{r.id}</span>
              </div>
              <div className="db-font-xs mt-0.5" style={{ color: 'var(--db-text-muted)' }}>
                {[r.company && r.attention, r.phone, r.address_full || r.email].filter(Boolean).join(' · ')}
              </div>
            </button>
          ))}
          {results.length === 0 && (
            <div className="px-3 py-2 db-font-sm font-normal" style={{ color: 'var(--db-text-muted)' }}>
              No {source}s found
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ShipToSearch;
