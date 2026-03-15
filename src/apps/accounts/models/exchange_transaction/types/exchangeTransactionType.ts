/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
export interface ExchangeTransactionAddProps {
  modeProp?: "add" | "edit" | "view";
  dataProp?: any; // TODO: Type this properly
  hideBreadcrumb?: boolean;
  onSaved?: () => void;
  inline?: boolean;
  onCancelInline?: () => void;
}

export interface CreateExchangeTransactionRequest {
  from_currency: string;
  to_currency: string;
  amount: number;
  rate: number;
  date: string;
  status: string;
}

export interface ExchangeTransactionApiTask {
  from_currency: string;
  to_currency: string;
  amount: number;
  rate: number;
  date: string;
  status: string;
}

export interface UpdateExchangeTransactionRequest {
  id: string;
  from_currency: string;
  to_currency: string;
  amount: number;
  rate: number;
  date: string;
  status: string;
}