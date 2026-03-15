/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from "../../../../../api/wcapi";

export const createAudit = async (data: any) => {
  return saveRecord('audit', data);
};

export const updateAudit = async (data: any) => {
  return saveRecord('audit', data);
};

export const fetchAudits = async (params?: any) => {
  const res = await getRecords('audit', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const deleteAudit = async (id: number) => {
  return deleteRecord('audit', id);
};