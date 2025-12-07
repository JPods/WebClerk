import { getRecords, saveRecord, deleteRecord } from "../../../../../api/wcapi";
import type {
  CreatePhoneRequest,
  UpdatePhoneRequest,
} from "../types/phoneType";

export const createPhone = async (data: CreatePhoneRequest) => {
  return saveRecord('phone', data);
};

export const updatePhone = async (data: UpdatePhoneRequest) => {
  return saveRecord('phone', data);
};

export const deletePhone = async (id: number) => {
  return deleteRecord('phone', id);
};

export const fetchPhones = async (params?: any) => {
  const res = await getRecords('phone', params);
  return { status: 200, data: { items: res.results || [] } };
};