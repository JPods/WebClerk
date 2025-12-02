export interface CurrencyAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateCurrencyRequest {
  code: string;
  name: string;
  symbol: string;
  rate: number;
}

export interface CurrencyApiTask {
  code: string;
  name: string;
  symbol: string;
  rate: number;
}

export interface UpdateCurrencyRequest {
  id: string;
  code: string;
  name: string;
  symbol: string;
  rate: number;
}