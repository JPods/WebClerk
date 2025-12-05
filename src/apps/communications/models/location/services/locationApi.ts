import { getRecords, saveRecord, deleteRecord } from "../../../../../api/wcapi";
import type {
  CreateLocationRequest,
  LocationApiTask,
  UpdateLocationRequest,
} from "../types/locationType";

export const createLocation = async (data: any) => {
  return saveRecord('location', data);
};

export const updateLocation = async (data: any) => {
  return saveRecord('location', data);
};

export const deleteLocation = async (id: number) => {
  return deleteRecord('location', id);
};

export const fetchLocations = async (params?: any) => {
  const res = await getRecords('location', params);
  return { status: 200, data: { items: res.results || [] } };
};