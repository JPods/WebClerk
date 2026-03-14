/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateExchangeRateRequest,
  ExchangeRateApiTask,
  UpdateExchangeRateRequest,
} from "../types/exchangeRateType";

export const createExchangeRate = async (
  payload: CreateExchangeRateRequest
): Promise<ExchangeRateApiTask> => {
  return saveRecord("exchange_rate", payload);
};

export const updateExchangeRate = async (
  payload: UpdateExchangeRateRequest
): Promise<ExchangeRateApiTask> => {
  return saveRecord("exchange_rate", payload);
};

export const deleteExchangeRate = async (id: number) => {
  return deleteRecord("exchange_rate", id);
};

export const fetchExchangeRates = async (params?: any) => {
  const res = await getRecords("exchange_rate", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchExchangeRate = async (): Promise<ExchangeRateApiTask[]> => {
  const res = await getRecords("exchange_rate");
  return res.results || [];
};