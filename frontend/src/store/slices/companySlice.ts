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
    const currentVersion = state.company?.version || localStorage.getItem('wc_bootstrap_version') || '';

    try {
      const res = await apiClient.get('/wcapi/_bootstrap/', {
        params: currentVersion ? { v: currentVersion } : undefined,
      });

      // 304 handled by axios — won't reach here
      const data = res.data?.data;
      if (data) {
        localStorage.setItem('wc_bootstrap_version', data._version || '');
        return data;
      }
    } catch (err: any) {
      if (err?.response?.status === 304) {
        // No change — keep current state
        return null;
      }
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
