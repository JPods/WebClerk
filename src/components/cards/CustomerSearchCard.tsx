/**
 * CustomerSearchCard — card component with inline customer search.
 *
 * Wraps the default field rendering (passed as children) and adds
 * a search button in the title bar that opens a customer lookup.
 *
 * Registered in cardRegistry as 'customer_search'.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { getRecords } from '@/api/wcapi';
import { registerCardComponent } from './cardRegistry';
import type { CardComponentProps } from './cardRegistry';

const CustomerSearchCard: React.FC<CardComponentProps> = ({ spec, data, isEditing, onChange, children }) => {
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when search opens
  useEffect(() => {
    if (searchOpen) setTimeout(() => inputRef.current?.focus(), 50);
  }, [searchOpen]);

  // Debounced search
  useEffect(() => {
    if (query.length < 2) { setResults([]); return; }
    setSearching(true);
    const timer = setTimeout(async () => {
      try {
        const res = await getRecords('customer', { keyword: query, limit: 10 }) as any;
        setResults(res?.results || []);
      } catch { setResults([]); }
      setSearching(false);
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  const handleSelect = useCallback((cust: any) => {
    // Set the FK only — UiDetail.handleFieldChange detects
    // customer/customer_id changes and runs applyCustomerDefaults
    // which populates company, phone, attention, address, ship_to, etc.
    onChange('customer', cust.id);
    setSearchOpen(false);
    setQuery('');
    setResults([]);
  }, [onChange]);

  return (
    <>
      {/* Search button in card — only in edit mode */}
      {isEditing && !searchOpen && (
        <button
          type="button"
          className="float-right -mt-6 text-[10px] text-slate-400 hover:text-blue-600 px-1 py-0.5 rounded hover:bg-blue-50"
          title="Search customers"
          onClick={() => setSearchOpen(true)}
        >🔍</button>
      )}

      {/* Inline search input + results dropdown */}
      {isEditing && searchOpen && (
        <div className="mb-2 relative">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Escape') { setSearchOpen(false); setQuery(''); } }}
            placeholder="bil,jame or 612..."
            className="text-[11px] px-2 py-0.5 w-44 border border-blue-400 rounded bg-white dark:bg-slate-900 text-slate-900 dark:text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          {searching && <span className="absolute right-2 top-0.5 text-[10px] text-slate-400">...</span>}
          {results.length > 0 && (
            <div className="absolute top-6 left-0 w-96 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded shadow-lg z-50 max-h-60 overflow-y-auto">
              {results.map((c: any) => (
                <button
                  key={c.id}
                  type="button"
                  className="w-full text-left px-3 py-2 text-[11px] hover:bg-blue-50 dark:hover:bg-slate-700 border-b border-slate-100 dark:border-slate-700 last:border-0"
                  onClick={() => handleSelect(c)}
                >
                  <div className="flex items-baseline gap-2">
                    <span className="font-medium text-slate-900 dark:text-white">{c.company || c.display_name || `#${c.id}`}</span>
                    <span className="text-slate-400 font-mono text-[10px]">#{c.id}</span>
                  </div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">
                    {[c.attention, c.phone, c.address_full || c.email].filter(Boolean).join(' · ')}
                  </div>
                </button>
              ))}
            </div>
          )}
          {query.length >= 2 && !searching && results.length === 0 && (
            <div className="absolute top-6 left-0 w-52 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded shadow-lg z-50 px-3 py-2 text-[11px] text-slate-400">
              No customers found
            </div>
          )}
        </div>
      )}

      {/* Default field rendering */}
      {children}
    </>
  );
};

// Self-register
registerCardComponent('customer_search', CustomerSearchCard);

export default CustomerSearchCard;
