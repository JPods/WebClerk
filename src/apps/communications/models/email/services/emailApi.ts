import { getRecords, saveRecord, deleteRecord } from "../../../../../api/wcapi";

export const createEmail = async (data: any) => {
  return saveRecord('email', data);
};

export const updateEmail = async (data: any) => {
  return saveRecord('email', data);
};

export const deleteEmail = async (id: number) => {
  return deleteRecord('email', id);
};

export const fetchEmails = async (params?: any) => {
  const res = await getRecords('email', params);
  return { status: 200, data: { items: res.results || [] } };
};