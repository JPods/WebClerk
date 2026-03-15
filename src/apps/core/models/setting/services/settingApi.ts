/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateSettingRequest,
  SettingApiTask,
  UpdateSettingRequest,
} from "../types/settingType";

export const createSetting = async (
  payload: CreateSettingRequest
): Promise<SettingApiTask> => {
  const res = await saveRecord("setting", payload);
  return res;
};

export const updateSetting = async (
  payload: UpdateSettingRequest
): Promise<SettingApiTask> => {
  const res = await saveRecord("setting", payload);
  return res;
};

export const deleteSetting = async (id: number) => {
  return deleteRecord("setting", id);
};

export const fetchSettings = async (params?: any) => {
  const res = await getRecords("setting", params);
  return { status: 200, data: { items: res.results || [] } };
};

export const fetchSetting = async (): Promise<SettingApiTask[]> => {
  const res = await getRecords("setting");
  return res.results || [];
};