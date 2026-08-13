import React, { useState, useEffect, useRef, useCallback } from 'react';
import type { LookupFieldProps } from './types';
import BaseField from './BaseField';
import { getRecords } from '@/api/wcapi';

export default function LookupField(props: LookupFieldProps) {
  const { name, value: v, onChange, disabled, model } = props;
  const [query, setQuery] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();
  const wrapRef = useRef<HTMLDivElement>(null);

  // Resolve display name from ID on mount or value change
  useEffect(() => {
    if (!v) { setDisplayName(''); return; }
    getRecords(model, { id: v, limit: 1 }).then((res: any) => {
      const rec = (res?.results || [])[0];
      if (rec) {
        setDisplayName(rec.display_name || rec.name || rec.company || rec.ida || `#${rec.id}`);
      }
    }).catch(() => {});
  }, [v, model]);

  // Search on typing
  const doSearch = useCallback((q: string) => {
    if (q.length < 2) { setResults([]); return; }
    setLoading(true);
    getRecords(model, { keyword: q, limit: 10 }).then((res: any) => {
      setResults(res?.results || []);
      setOpen(true);
    }).catch(() => setResults([]))
      .finally(() => setLoading(false));
  }, [model]);

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const q = e.target.value;
    setQuery(q);
    setDisplayName('');
    onChange(null); // clear FK until they pick
    clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => doSearch(q), 250);
  };

  const handleSelect = (rec: any) => {
    onChange(rec.id);
    setDisplayName(rec.display_name || rec.name || rec.company || rec.ida || `#${rec.id}`);
    setQuery('');
    setOpen(false);
  };

  const handleAddNew = async () => {
    try {
      const { saveRecord } = await import('@/api/wcapi');
      const blank: any = { ida: query };
      if (model === 'contact') {
        const parts = query.trim().split(/\s+/);
        blank.name_first = parts[0] || query;
        blank.name_last = parts.slice(1).join(' ') || '';
      } else {
        blank.name = query;
      }
      const result = await saveRecord(model, blank) as any;
      if (result?.id) handleSelect(result);
    } catch (err) {
      console.error('[LookupField] add new failed:', err);
    }
  };

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div ref={wrapRef} style={{ position: 'relative' }}>
      <BaseField props={props} labelColor="lookup"
        labelSuffix={<span className="db-label-hint">{`→ ${model}`}</span>}>
        <input className="db-input" value={displayName || query}
          onChange={handleInput}
          onFocus={() => { if (displayName) { setQuery(displayName); setDisplayName(''); } }}
          placeholder={`search ${model}...`} disabled={disabled} />
      </BaseField>
      {open && results.length > 0 && (
        <div className="db-lookup-dropdown">
          {results.map((r) => (
            <div key={r.id} className="db-lookup-option" onClick={() => handleSelect(r)}>
              <span className="db-lookup-name">{r.display_name || r.name || r.company || r.ida}</span>
              {r.email && <span className="db-lookup-hint">{r.email}</span>}
            </div>
          ))}
          <div className="db-lookup-add" onClick={handleAddNew}>+ Add "{query}"</div>
        </div>
      )}
      {open && results.length === 0 && query.length >= 2 && !loading && (
        <div className="db-lookup-dropdown">
          <div className="db-lookup-empty">No matches</div>
          <div className="db-lookup-add" onClick={handleAddNew}>+ Add "{query}"</div>
        </div>
      )}
    </div>
  );
}
