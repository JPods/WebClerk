import apiClient from "../../../../../axios";
import { PostLoginURL } from "../../../../../../routes/network";
import type {
  CreateExchangeRateRequest,
  ExchangeRateApiTask,
  UpdateExchangeRateRequest,
} from "../types/exchangeRateType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createExchangeRate = async (
  payload: CreateExchangeRateRequest
): Promise<ExchangeRateApiTask> => {
  const model_name: string = "exchange_rate";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<ExchangeRateApiTask>(res);
};

export const updateExchangeRate = async (
  payload: UpdateExchangeRateRequest
): Promise<ExchangeRateApiTask> => {
  const model_name: string = "exchange_rate";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<ExchangeRateApiTask>(res);
};

export const deleteExchangeRate = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchExchangeRates = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=exchange_rate" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchExchangeRate = async (): Promise<ExchangeRateApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=exchange_rate");
  return unwrap<ExchangeRateApiTask[]>(res);
};