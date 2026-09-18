/* LastChecked: 2026-08-02 | WhereUsed: App bootstrap, UiDetail, DataGrid | WhoCreated: Claude */
/**
 * companySlice — company-level configuration loaded once at startup.
 *
 * Fetched from /wcapi/_bootstrap/. Versioned — only re-downloads when
 * the company-profile Setting changes on the server.
 */
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { apiClient } from '@/api/axios';

export interface CompanyCurrency {
  symbol: string;
  code: string;
  locale: string;
  unit_price_precision: number;
  unit_cost_precision: number;
  total_precision: number;
  qty_precision: number;
}

export interface CompanyState {
  loaded: boolean;
  version: string;
  currency: CompanyCurrency;
  order_defaults: Record<string, any>;
  price_levels: Record<string, any>;
  inventory: Record<string, any>;
  /** config.inventory costing defaults: costing_method, unit_cost_default, unit_cost_precision */
  costing: Record<string, any>;
  commissions: Record<string, any>;
  collections: Record<string, any>;
  document_text: Record<string, any>;
  behavior: Record<string, any>;
  fiscal: Record<string, any>;
  company: Record<string, any>;
  logos: Record<string, any>;
  print_defaults: Record<string, any>;
}

const DEFAULT_CURRENCY: CompanyCurrency = {
  symbol: '$',
  code: 'USD',
  locale: 'en-US',
  unit_price_precision: 2,
  unit_cost_precision: 5,
  total_precision: 2,
  qty_precision: 0,
};

const initialState: CompanyState = {
  loaded: false,
  version: '',
  currency: DEFAULT_CURRENCY,
  order_defaults: {},
  price_levels: {},
  inventory: {},
  costing: {},
  commissions: {},
  collections: {},
  document_text: {},
  behavior: {},
  fiscal: {},
  company: {},
  logos: {},
  print_defaults: {},
};

export const fetchBootstrap = createAsyncThunk(
  'company/fetchBootstrap',
  async (_, { getState }) => {
    const state = getState() as any;
    // Ask "has it changed?" only when there is a copy to keep: the loaded state,
    // or a saved copy a 304 can restore on a fresh page load.
    const hasCopy = Boolean(state.company?.loaded || localStorage.getItem('wc_bootstrap_data'));
    const currentVersion = hasCopy
      ? (state.company?.version || localStorage.getItem('wc_bootstrap_version') || '')
      : '';

    // The view returns {status, data: payload} and the API renderer wraps that
    // again, so the payload is two levels down. Reading one level stored the
    // inner envelope as the payload: every company field loaded empty.
    const unwrap = (resData: any) => {
      const body = resData?.data;
      return body && typeof body === 'object' && '_version' in body ? body : body?.data ?? null;
    };

    try {
      // 304 is an answer, not an error: accept it here so no rejected promise escapes.
      const res = await apiClient.get('/wcapi/_bootstrap/', {
        params: currentVersion ? { v: currentVersion } : undefined,
        validateStatus: (s: number) => (s >= 200 && s < 300) || s === 304,
      });

      if (res.status === 304) {
        // No change. Already loaded: keep state. Fresh page load: the saved copy is current.
        if (state.company?.loaded) return null;
        const saved = localStorage.getItem('wc_bootstrap_data');
        if (saved) {
          try { return JSON.parse(saved); } catch { /* fall through to refetch */ }
        }
        return unwrap((await apiClient.get('/wcapi/_bootstrap/')).data);
      }

      const data = unwrap(res.data);
      if (data) {
        localStorage.setItem('wc_bootstrap_version', data._version || '');
        return data;
      }
    } catch (err: any) {
      // Try loading from localStorage cache
      const cached = localStorage.getItem('wc_bootstrap_data');
      if (cached) {
        try { return JSON.parse(cached); } catch { /* fall through */ }
      }
      throw err;
    }
    return null;
  }
);

const companySlice = createSlice({
  name: 'company',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder.addCase(fetchBootstrap.fulfilled, (state, action) => {
      if (action.payload) {
        const d = action.payload;
        state.currency = { ...DEFAULT_CURRENCY, ...d.currency };
        state.order_defaults = d.order_defaults || {};
        state.price_levels = d.price_levels || {};
        state.inventory = d.inventory || {};
        state.costing = d.costing || {};
        state.commissions = d.commissions || {};
        state.collections = d.collections || {};
        state.document_text = d.document_text || {};
        state.behavior = d.behavior || {};
        state.fiscal = d.fiscal || {};
        state.company = d.company || {};
        state.logos = d.logos || {};
        state.print_defaults = d.print_defaults || {};
        state.version = d._version || '';
        state.loaded = true;
        // Cache for offline/fast startup
        localStorage.setItem('wc_bootstrap_data', JSON.stringify(d));
      } else {
        state.loaded = true;
      }
    });
  },
});

export default companySlice.reducer;

// Selectors
export const selectCurrency = (state: any): CompanyCurrency => state.company?.currency || DEFAULT_CURRENCY;
export const selectOrderDefaults = (state: any) => state.company?.order_defaults || {};
export const selectPriceLevels = (state: any) => state.company?.price_levels || {};
export const selectCompanyInfo = (state: any) => state.company?.company || {};
export const selectLogos = (state: any) => state.company?.logos || {};
