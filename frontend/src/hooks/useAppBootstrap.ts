/**
 * useAppBootstrap — loads server-driven defaults and select lists at startup.
 *
 * Nothing hardcoded in React. All defaults, select lists, company info,
 * and field behaviors come from the server via one bootstrap call.
 *
 * Called once at app startup and on manual refresh.
 * Results cached in module state + localStorage fallback.
 *
 * Data loaded:
 *   - Company profile (Setting purpose='wc:company_profile')
 *   - Select lists (Setting purpose='wc:selectlist' per model)
 *   - Payment terms (Term model — for dropdowns)
 *   - Tax jurisdictions (TaxJurisdiction — for dropdowns)
 *   - Default values (Setting purpose='wc:db_defaults')
 *   - Active campaigns (for source attribution dropdown)
 *   - Warehouses (for location dropdowns)
 */
import { useCallback, useEffect, useRef, useState } from 'react';

export interface BootstrapData {
  dt_changed: number;              // server timestamp — React refreshes when this changes
  company: {
    name: string;
    legal_name: string;
    address: { street1: string; street2: string; city: string; state: string; zip: string; country: string };
    phone: string;
    email: string;
    website: string;
    tax_id: string;
    logos: { primary: string; icon: string; watermark: string };
  };
  selectLists: Record<string, Array<{ value: string; label: string }>>;
  paymentTerms: Array<{ id: number; description: string; days_due: number }>;
  taxJurisdictions: Array<{ id: number; jurisdiction: string; rate: number }>;
  warehouses: Array<{ id: number; code: string; name: string }>;
  campaigns: Array<{ id: number; name: string }>;
  defaults: Record<string, any>;
  loaded: boolean;
  loading: boolean;
  error: string | null;
}

const CACHE_KEY = 'wc3-bootstrap';
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes
const POLL_MIN = 15_000;          // 15s — fast during setup / after flush
const POLL_MAX = 300_000;         // 5min — idle ceiling

// Module-level cache — survives re-renders, cleared on refresh
let cachedData: BootstrapData | null = null;
let cacheTimestamp = 0;

function emptyBootstrap(): BootstrapData {
  return {
    dt_changed: 0,
    company: {
      name: '', legal_name: '', address: { street1: '', street2: '', city: '', state: '', zip: '', country: 'US' },
      phone: '', email: '', website: '', tax_id: '',
      logos: { primary: '', icon: '', watermark: '' },
    },
    selectLists: {},
    paymentTerms: [],
    taxJurisdictions: [],
    warehouses: [],
    campaigns: [],
    defaults: {},
    loaded: false,
    loading: false,
    error: null,
  };
}

export function useAppBootstrap(isAuthenticated: boolean) {
  const [data, setData] = useState<BootstrapData>(() => cachedData || emptyBootstrap());
  const fetchingRef = useRef(false);

  const refresh = useCallback(async (force = false) => {
    if (fetchingRef.current) return;
    if (!force && cachedData && Date.now() - cacheTimestamp < CACHE_TTL) {
      setData(cachedData);
      return;
    }

    fetchingRef.current = true;
    setData(prev => ({ ...prev, loading: true, error: null }));

    try {
      const { default: apiClient } = await import('@/api/axios');
      const resp = await apiClient.post('/wcapi/_manage/', {
        action: 'get_app_bootstrap',
        params: {},
      });

      const result = resp.data?.data || resp.data || {};
      const bootstrap: BootstrapData = {
        dt_changed: result.dt_changed || 0,
        company: result.company || emptyBootstrap().company,
        selectLists: result.select_lists || {},
        paymentTerms: result.payment_terms || [],
        taxJurisdictions: result.tax_jurisdictions || [],
        warehouses: result.warehouses || [],
        campaigns: result.campaigns || [],
        defaults: result.defaults || {},
        loaded: true,
        loading: false,
        error: null,
      };

      const wasFlush = cachedData && bootstrap.dt_changed > cachedData.dt_changed;
      cachedData = bootstrap;
      cacheTimestamp = Date.now();
      setData(bootstrap);

      // Notify panels and other components that Settings changed
      if (wasFlush) {
        window.dispatchEvent(new Event('wc3-settings-changed'));
      }

      // localStorage fallback for offline/fast reload
      try {
        localStorage.setItem(CACHE_KEY, JSON.stringify({
          ...bootstrap, loaded: true, loading: false, error: null,
        }));
      } catch { /* localStorage full — ignore */ }

    } catch (e) {
      // Try localStorage fallback
      try {
        const cached = localStorage.getItem(CACHE_KEY);
        if (cached) {
          const parsed = JSON.parse(cached);
          setData({ ...parsed, loading: false, error: 'Using cached data (server unreachable)' });
          return;
        }
      } catch { /* no fallback */ }

      setData(prev => ({ ...prev, loading: false, error: 'Failed to load app configuration' }));
    } finally {
      fetchingRef.current = false;
    }
  }, []);

  // Load on auth
  useEffect(() => {
    if (isAuthenticated) refresh();
  }, [isAuthenticated, refresh]);

  // Adaptive poll: check if admin/Alice changed Settings (dt_changed flag)
  // Starts at 15s, backs off to 5min when idle. Resets to 15s on flush
  // detection or when Alice sends 'wake' via BroadcastChannel.
  const pollIntervalRef = useRef(POLL_MIN);
  const consecutiveIdleRef = useRef(0);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const schedulePoll = useCallback(() => {
    if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    pollTimerRef.current = setTimeout(async () => {
      try {
        const { default: apiClient } = await import('@/api/axios');
        const resp = await apiClient.post('/wcapi/_manage/', {
          action: 'get_bootstrap_dt', params: {},
        });
        const serverDt = resp.data?.data?.dt_changed || 0;
        if (serverDt > 0 && cachedData && serverDt > cachedData.dt_changed) {
          // Flush detected — reload and reset to fast polling
          consecutiveIdleRef.current = 0;
          pollIntervalRef.current = POLL_MIN;
          refresh(true);
          try { flushChannel?.postMessage('flush'); } catch { /* ignore */ }
        } else {
          // No change — back off: 15s → 30s → 60s → 120s → 300s
          consecutiveIdleRef.current++;
          if (consecutiveIdleRef.current > 4) {
            pollIntervalRef.current = Math.min(pollIntervalRef.current * 2, POLL_MAX);
          }
        }
      } catch { /* silent */ }
      schedulePoll(); // schedule next poll at current interval
    }, pollIntervalRef.current);
  }, [refresh]);

  useEffect(() => {
    if (!isAuthenticated) return;
    schedulePoll();
    return () => { if (pollTimerRef.current) clearTimeout(pollTimerRef.current); };
  }, [isAuthenticated, schedulePoll]);

  // BroadcastChannel — flush from another tab, or Alice sends 'wake'
  const [flushChannel] = useState(() => {
    try { return new BroadcastChannel('wc3-flush'); } catch { return null; }
  });
  useEffect(() => {
    if (!flushChannel || !isAuthenticated) return;
    const handler = (ev: MessageEvent) => {
      // 'flush' = another tab detected a change; 'wake' = Alice says check now
      consecutiveIdleRef.current = 0;
      pollIntervalRef.current = POLL_MIN;
      if (ev.data === 'flush') {
        refresh(true);
      } else if (ev.data === 'wake') {
        // Just reset the poll interval — next tick will check
        if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
        schedulePoll();
      }
    };
    flushChannel.addEventListener('message', handler);
    return () => flushChannel.removeEventListener('message', handler);
  }, [flushChannel, isAuthenticated, refresh, schedulePoll]);

  return { ...data, refresh };
}

// ---------------------------------------------------------------------------
// Utility: get a select list by key
// ---------------------------------------------------------------------------

export function getSelectList(data: BootstrapData, key: string): Array<{ value: string; label: string }> {
  return data.selectLists[key] || [];
}

export function getPaymentTermOptions(data: BootstrapData): Array<{ value: string; label: string }> {
  return data.paymentTerms.map(t => ({ value: String(t.id), label: `${t.description} (${t.days_due} days)` }));
}

export function getTaxJurisdictionOptions(data: BootstrapData): Array<{ value: string; label: string }> {
  return data.taxJurisdictions.map(j => ({ value: String(j.id), label: `${j.jurisdiction} (${j.rate}%)` }));
}

export function getWarehouseOptions(data: BootstrapData): Array<{ value: string; label: string }> {
  return data.warehouses.map(w => ({ value: String(w.id), label: `${w.code} — ${w.name}` }));
}

export function getCampaignOptions(data: BootstrapData): Array<{ value: string; label: string }> {
  return data.campaigns.map(c => ({ value: String(c.id), label: c.name }));
}
