/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateExchangeTransactionRequest,
  ExchangeTransactionApiTask,
  UpdateExchangeTransactionRequest,
} from "../types/exchangeTransactionType";

export const createExchangeTransaction = async (
  payload: CreateExchangeTransactionRequest
): Promise<ExchangeTransactionApiTask> => {
  return saveRecord("exchange_transaction", payload);
};

export const updateExchangeTransaction = async (
  payload: UpdateExchangeTransactionRequest
): Promise<ExchangeTransactionApiTask> => {
  return saveRecord("exchange_transaction", payload);
};

export const deleteExchangeTransaction = async (id: number) => {
  return deleteRecord("exchange_transaction", id);
};

export const fetchExchangeTransactions = async (params?: any) => {
  const res = await getRecords("exchange_transaction", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchExchangeTransaction = async (): Promise<ExchangeTransactionApiTask[]> => {
  const res = await getRecords("exchange_transaction");
  return res.results || [];
};