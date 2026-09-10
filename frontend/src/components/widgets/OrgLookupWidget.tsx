/**
 * OrgLookupWidget — standard reusable customer/vendor/contact search widget.
 *
 * One widget for all org lookups: customer search on orders/proposals/actions,
 * vendor search on purchases. Driven by parameters:
 *   searchModel:  'customer' | 'vendor' | 'contact'
 *   onSelect:     (record) => void — caller maps fields
 *
 * UI pattern matches the assign button (db-section-header__action):
 *   🔍 button → inline input → dropdown → select → callback
 *
 * Usage:
 *   <OrgLookup searchModel="customer" current={data.company} currentId={data.customer}
 *     onSelect={(c) => { onChange('customer', c.id); }} />
 */
import React, { useState, useCallback, useRef, useEffect } from 'react';
import { getRecords } from '@/api/wcapi';

export interface OrgLookupProps {
  /** Model to search: customer, vendor, contact */
  searchModel: string;
  /** Display name of the currently assigned org */
  current?: string;
  /** ID of the currently assigned org */
  currentId?: number | null;
  /** Called when user selects a record from search results */
  onSelect: (record: any) => void;
  /** Disabled state */
  disabled?: boolean;
  /** Placeholder for the search input */
  placeholder?: string;
}

export const OrgLookup: React.FC<OrgLookupProps> = ({
  searchModel, current, currentId, onSelect, disabled,
  placeholder = 'bil,jame or 612...',
}) => {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const toggle = useCallback((nextOpen: boolean) => {
    setOpen(nextOpen);
    if (!nextOpen) { setQuery(''); setResults([]); }
  }, []);

  const search = useCallback((q: string) => {
    setQuery(q);
    if (timerRef.current) clearTimeout(timerRef.current);
    if (!q || q.length < 2) { setResults([]); return; }
    timerRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await getRecords(searchModel, { keyword: q, limit: 10 });
        setResults(res?.results || res?.records || []);
      } catch { setResults([]); }
      setSearching(false);
    }, 300);
  }, [searchModel]);

  const handleSelect = useCallback((record: any) => {
    onSelect(record);
    toggle(false);
  }, [onSelect, toggle]);

  useEffect(() => {
    if (open && inputRef.current) inputRef.current.focus();
  }, [open]);

  return (
    <div className="flex items-center gap-2 ml-auto" onClick={(e) => e.stopPropagation()} onMouseDown={(e) => e.stopPropagation()}>
      {currentId && (
        <span className="font-mono font-normal db-font-xs" style={{ color: 'var(--db-text-dim)' }}>
          #{currentId}
        </span>
      )}
      {!disabled && !open && (
        <button
          type="button"
          className="db-font-xs text-slate-400 hover:text-blue-600 px-1 py-0.5 rounded hover:bg-blue-50"
          title={`Search ${searchModel}s`}
          onClick={() => toggle(true)}
        >🔍</button>
      )}
      {!disabled && open && (
        <div className="relative">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => search(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Escape') toggle(false); }}
            placeholder={placeholder}
            className="db-font-sm px-2 py-0.5 w-44 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
            style={{ border: '1px solid var(--db-accent)', background: 'var(--db-input-bg, #fff)', color: 'var(--db-text)' }}
          />
          {searching && <span className="absolute right-2 top-0.5 db-font-xs text-slate-400">...</span>}
          {results.length > 0 && (
            <div className="absolute top-6 left-0 w-96 rounded shadow-lg z-50 max-h-60 overflow-y-auto"
              style={{ background: 'var(--db-surface)', border: '1px solid var(--db-border)' }}>
              {results.map((c: any) => (
                <button
                  key={c.id}
                  type="button"
                  className="w-full text-left px-3 py-2 db-font-sm last:border-0"
                  style={{ borderBottom: '1px solid var(--db-border-light)' }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--db-row-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  onClick={() => handleSelect(c)}
                >
                  <div className="flex items-baseline gap-2">
                    <span className="font-medium" style={{ color: 'var(--db-text)' }}>
                      {c.company || c.display_name || `#${c.id}`}
                    </span>
                    <span className="font-mono db-font-xs" style={{ color: 'var(--db-text-dim)' }}>#{c.id}</span>
                  </div>
                  <div className="db-font-xs mt-0.5" style={{ color: 'var(--db-text-muted)' }}>
                    {[c.attention, c.phone, c.address_full || c.email].filter(Boolean).join(' · ')}
                  </div>
                </button>
              ))}
            </div>
          )}
          {query.length >= 2 && !searching && results.length === 0 && (
            <div className="absolute top-6 left-0 w-52 rounded shadow-lg z-50 px-3 py-2 db-font-sm"
              style={{ background: 'var(--db-surface)', border: '1px solid var(--db-border)', color: 'var(--db-text-muted)' }}>
              No {searchModel}s found
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default OrgLookup;
