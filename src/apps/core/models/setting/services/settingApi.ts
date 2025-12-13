import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import type {
  CreateSettingRequest,
  SettingApiTask,
  UpdateSettingRequest,
} from "../types/settingType";

const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createSetting = async (
  payload: CreateSettingRequest
): Promise<SettingApiTask> => {
  const model_name: string = "setting";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<SettingApiTask>(res);
};

export const updateSetting = async (
  payload: UpdateSettingRequest
): Promise<SettingApiTask> => {
  const model_name: string = "setting";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<SettingApiTask>(res);
};

export const deleteSetting = async (id: any) => {
  try {
    const res = await apiClient.delete(PostLoginURL.allTypes + id + "/");
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchSettings = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=setting" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};

export const fetchSetting = async (): Promise<SettingApiTask[]> => {
  const res = await apiClient.get(PostLoginURL.allTypes + "model_name=setting");
  return unwrap<SettingApiTask[]>(res);
};