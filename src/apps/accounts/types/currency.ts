// TypeScript interface for Currency model based on webclerk3 Django model

export interface Currency {
  id?: number;
  created_at?: string;
  updated_at?: string;
  code?: string; // e.g., USD, EUR
  name?: string;
  symbol?: string;
  precision?: number;
  is_active?: boolean;
}

// Field labels - using exact field names as requested
export const CURRENCY_FIELD_LABELS: Record<keyof Currency, string> = {
  id: 'id',
  created_at: 'created_at',
  updated_at: 'updated_at',
  code: 'code',
  name: 'name',
  symbol: 'symbol',
  precision: 'precision',
  is_active: 'is_active',
};