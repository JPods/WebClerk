/**
 * Phone API - Uses centralized wcapi endpoints
 */
import { getRecords, getRecord, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreatePhoneRequest,
  UpdatePhoneRequest,
  PhoneApiTask,
} from "../types/phoneType";

const MODEL_NAME = "phone";

export const createPhone = async (
  payload: CreatePhoneRequest,
): Promise<PhoneApiTask> => {
  return saveRecord(MODEL_NAME, payload);
};

export const updatePhone = async (
  payload: UpdatePhoneRequest,
): Promise<PhoneApiTask> => {
  return saveRecord(MODEL_NAME, payload);
};

export const deletePhone = async (id: number) => {
  return deleteRecord(MODEL_NAME, id);
};

export const fetchPhones = async (params?: any) => {
  const res = await getRecords("phone", params);
  return { status: 200, data: { items: res.results || [] } };
};
