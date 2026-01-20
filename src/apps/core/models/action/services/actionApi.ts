import { getRecords, saveRecord, deleteRecord, getRecord } from '../../../../../api/wcapi';

export const createAction = async (payload: Record<string, unknown>) => {
  return saveRecord('action', payload);
};

export const updateAction = async (id: string | number, payload: Record<string, unknown>) => {
  return saveRecord('action', { ...payload, id });
};

export const deleteAction = async (id: string | number) => {
  return deleteRecord('action', id);
};

export const fetchAction = async (id: string | number) => {
  return getRecord('action', id);
};

export const fetchActions = async () => {
  const res = await getRecords('action');
  return { status: 200, data: { items: res.results || [] } };
};
