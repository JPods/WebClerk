/**
 * Address API - Uses centralized wcapi endpoints
 */
import { getRecords, getRecord, saveRecord, deleteRecord } from "@/api/wcapi";
import type {
  CreateAddressRequest,
  UpdateAddressRequest,
  AddressApiTask,
} from "../types/addressType";

const MODEL_NAME = "address";

export const createAddress = async (
  payload: CreateAddressRequest
): Promise<AddressApiTask> => {
  return saveRecord(MODEL_NAME, payload);
};

export const updateAddress = async (
  payload: UpdateAddressRequest
): Promise<AddressApiTask> => {
  return saveRecord(MODEL_NAME, payload);
};

export const deleteAddress = async (id: number) => {
  return deleteRecord(MODEL_NAME, id);
};

export const fetchAddresses = async (id?: number | string) => {
  if (id) {
    return getRecord(MODEL_NAME, Number(id));
  }
  return getRecords(MODEL_NAME);
};
