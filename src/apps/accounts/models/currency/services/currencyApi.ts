import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import type {
  CreateCurrencyRequest,
  CurrencyApiTask,
  UpdateCurrencyRequest,
} from "../types/currencyType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createCurrency = async (
  payload: CreateCurrencyRequest
): Promise<CurrencyApiTask> => {
  const model_name: string = "currency";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<CurrencyApiTask>(res);
};

export const updateCurrency = async (
  payload: UpdateCurrencyRequest
): Promise<CurrencyApiTask> => {
  const model_name: string = "currency";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<CurrencyApiTask>(res);
};

export const deleteCurrency = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchCurrencies = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=currency" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchCurrency = async (): Promise<CurrencyApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=currency");
  return unwrap<CurrencyApiTask[]>(res);
};