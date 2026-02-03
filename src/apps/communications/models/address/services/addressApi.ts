import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import type {
  CreateAddressRequest,
  UpdateAddressRequest,
  AddressApiTask,
} from "../types/addressType";
import { deleteRecord } from "../../../../../api/wcapi";
const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createAddress = async (
  payload: CreateAddressRequest
): Promise<AddressApiTask> => {
  const model_name: string = "address";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<AddressApiTask>(res);
};

export const updateAddress = async (
  payload: UpdateAddressRequest
): Promise<AddressApiTask> => {
  const model_name: string = "address";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<AddressApiTask>(res);
};

export const deleteAddress = async (id: number) => {
  return deleteRecord("address", id);
};

export const fetchAddresses = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=address" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};
