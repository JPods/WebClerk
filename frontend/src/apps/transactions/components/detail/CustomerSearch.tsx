/* LastChecked: 2026-08-02 | WhereUsed: UiDetail | WhoCreated: Claude */
import { useState, useCallback, useRef, useEffect } from 'react';
import { getRecords } from '@/api/wcapi';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Who a document is with: a sale's customer, a purchase's or receipt's vendor. */
export type Party = 'customer' | 'vendor';

export function partyOf(modelName: string): Party {
  return modelName === 'purchase' || modelName === 'receipt' ? 'vendor' : 'customer';
}

export interface CustomerSearchState {
  party: Party;
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
  party: Party = 'customer',
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
        const res = await getRecords(party, { keyword: q, limit: 10 });
        const records = res?.results || [];
        setResults(records);
      } catch { setResults([]); }
      setSearching(false);
    }, 300);
  }, [party]);

  const select = useCallback((cust: any) => {
    setOpen(false);
    setQuery('');
    setResults([]);
    // A purchase's party is its vendor: picking one sets vendor, which the receipt and its
    // payable inherit (To Receipt carried no vendor: the form could only pick a customer).
    setTimeout(() => onFieldChange(party, cust.id), 0);
  }, [onFieldChange, party]);

  useEffect(() => {
    if (open && inputRef.current) inputRef.current.focus();
  }, [open]);

  return { party, open, query, results, searching, inputRef, toggle, search, select };
}
