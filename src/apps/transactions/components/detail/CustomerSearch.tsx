/* LastChecked: 2026-08-02 | WhereUsed: UiDetail | WhoCreated: Claude */
import { useState, useCallback, useRef, useEffect } from 'react';
import { getRecords } from '@/api/wcapi';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CustomerSearchState {
  open: boolean;
  query: string;
  results: any[];
  searching: boolean;
  inputRef: React.RefObject<HTMLInputElement | null>;
  toggle: (open: boolean) => void;
  search: (query: string) => void;
  select: (cust: any) => void;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useCustomerSearch(
  onFieldChange: (field: string, value: unknown) => void,
): CustomerSearchState {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [searching, setSearching] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const toggle = useCallback((nextOpen: boolean) => {
    setOpen(nextOpen);
    if (!nextOpen) {
      setQuery('');
      setResults([]);
    }
  }, []);

  const search = useCallback((q: string) => {
    setQuery(q);
    if (timer.current) clearTimeout(timer.current);
    if (!q || q.length < 2) { setResults([]); return; }
    timer.current = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await getRecords('customer', { keyword: q, limit: 10 });
        const records = res?.results || res?.records || [];
        setResults(records);
      } catch { setResults([]); }
      setSearching(false);
    }, 300);
  }, []);

  const select = useCallback((cust: any) => {
    setOpen(false);
    setQuery('');
    setResults([]);
    setTimeout(() => onFieldChange('customer', cust.id), 0);
  }, [onFieldChange]);

  useEffect(() => {
    if (open && inputRef.current) inputRef.current.focus();
  }, [open]);

  return { open, query, results, searching, inputRef, toggle, search, select };
}
