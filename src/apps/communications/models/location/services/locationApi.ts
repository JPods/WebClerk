import apiClient from "../../../../../api/axios";
import { PostLoginURL } from "../../../../../routes/network";
import type {
  CreateLocationRequest,
  UpdateLocationRequest,
  LocationApiTask,
} from "../types/locationType";
import { getRecords, saveRecord, deleteRecord } from "../../../../../api/wcapi";
const unwrap = <T>(response: any): T => {
  if (!response) return [] as unknown as T;
  if (response.data?.data) return response.data.data as T;
  if (response.data) return response.data as T;
  return response as T;
};

export const createLocation = async (
  payload: CreateLocationRequest
): Promise<LocationApiTask> => {
  const model_name: string = "location";
  const res = await apiClient.post(PostLoginURL.allSave, {
    ...payload,
    model_name,
  });
  return unwrap<LocationApiTask>(res);
};

export const updateLocation = async (
  payload: UpdateLocationRequest
): Promise<LocationApiTask> => {
  const model_name: string = "location";
  const res = await apiClient.post(`${PostLoginURL.allSave}`, {
    ...payload,
    model_name,
  });
  return unwrap<LocationApiTask>(res);
};

export const deleteLocation = async (id: number) => {
  return deleteRecord("location", id);
};

export const fetchLocations = async (id: any = "") => {
  try {
    const res = await apiClient.get(
      PostLoginURL.allTypes + "model_name=location" + (id ? `&id=${id}` : "")
    );
    return res;
  } catch (error: any) {
    return error.response?.data || error.message;
  }
};
