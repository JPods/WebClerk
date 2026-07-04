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
 *   - Company profile (Setting purpose='company_profile')
 *   - Select lists (Setting purpose='admin_selectlist' per model)
 *   - Payment terms (Term model — for dropdowns)
 *   - Tax jurisdictions (TaxJurisdiction — for dropdowns)
 *   - Default values (Setting purpose='db_defaults')
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
      const resp = await apiClient.post('/wcapi/manage/', {
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

      cachedData = bootstrap;
      cacheTimestamp = Date.now();
      setData(bootstrap);

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

  // Lightweight poll: check if admin changed defaults (dt_changed flag)
  useEffect(() => {
    if (!isAuthenticated) return;
    const interval = setInterval(async () => {
      try {
        const { default: apiClient } = await import('@/api/axios');
        const resp = await apiClient.post('/wcapi/manage/', {
          action: 'get_bootstrap_dt', params: {},
        });
        const serverDt = resp.data?.data?.dt_changed || 0;
        if (serverDt > 0 && cachedData && serverDt > cachedData.dt_changed) {
          refresh(true); // admin changed something — refresh
        }
      } catch { /* silent — don't break the app for a poll failure */ }
    }, 60000); // check every 60 seconds
    return () => clearInterval(interval);
  }, [isAuthenticated, refresh]);

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
