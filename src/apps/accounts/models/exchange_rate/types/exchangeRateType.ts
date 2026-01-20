export interface ExchangeRateAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateExchangeRateRequest {
  from_currency: string;
  to_currency: string;
  rate: number;
  date: string;
}

export interface ExchangeRateApiTask {
  from_currency: string;
  to_currency: string;
  rate: number;
  date: string;
}

export interface UpdateExchangeRateRequest {
  id: string;
  from_currency: string;
  to_currency: string;
  rate: number;
  date: string;
}