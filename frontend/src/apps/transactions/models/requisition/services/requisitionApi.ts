/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";

export const fetchRequisitions = async (params?: any) => {
  const res = await getRecords('tx_requisitions', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createRequisition = async (data: any) => {
  return saveRecord('tx_requisitions', data);
};

export const updateRequisition = async (id: number, data: any) => {
  return saveRecord('tx_requisitions', { ...data, id });
};

export const deleteRequisition = async (id: number) => {
  return deleteRecord('tx_requisitions', id);
};