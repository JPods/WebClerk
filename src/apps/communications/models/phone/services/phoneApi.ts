import { getRecords, saveRecord, deleteRecord } from "../../../../../api/wcapi";
import type {
  CreatePhoneRequest,
  PhoneApiTask,
  UpdatePhoneRequest,
} from "../types/phoneType";

export const createPhone = async (data: any) => {
  return saveRecord('phone', data);
};

export const updatePhone = async (data: any) => {
  return saveRecord('phone', data);
};

export const deletePhone = async (id: number) => {
  return deleteRecord('phone', id);
};

export const fetchPhones = async (params?: any) => {
  const res = await getRecords('phone', params);
  return { status: 200, data: { items: res.results || [] } };
};