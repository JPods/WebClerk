import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import { deleteRecord } from "@/api/wcapi";
import type {
  CreateExchangeTransactionRequest,
  ExchangeTransactionApiTask,
  UpdateExchangeTransactionRequest,
} from "../types/exchangeTransactionType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createExchangeTransaction = async (
  payload: CreateExchangeTransactionRequest
): Promise<ExchangeTransactionApiTask> => {
  const model_name: string = "exchange_transaction";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<ExchangeTransactionApiTask>(res);
};

export const updateExchangeTransaction = async (
  payload: UpdateExchangeTransactionRequest
): Promise<ExchangeTransactionApiTask> => {
  const model_name: string = "exchange_transaction";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<ExchangeTransactionApiTask>(res);
};

export const deleteExchangeTransaction = async (id: number) => {
  return deleteRecord("exchange_transaction", id);
};

export const fetchExchangeTransactions = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=exchange_transaction" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchExchangeTransaction = async (): Promise<ExchangeTransactionApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=exchange_transaction");
  return unwrap<ExchangeTransactionApiTask[]>(res);
};