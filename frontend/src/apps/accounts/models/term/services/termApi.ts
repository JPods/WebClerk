/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "@/api/wcapi";

export const createTerm = async (data: any) => {
  return saveRecord('term', data);
};

export const updateTerm = async (data: any) => {
  return saveRecord('term', data);
};

export const fetchTerms = async (params?: any) => {
  const res = await getRecords('term', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const deleteTerm = async (id: number) => {
  return deleteRecord('term', id);
};