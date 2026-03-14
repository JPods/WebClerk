/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import { getRecords, saveRecord, deleteRecord } from '../../../../../api/wcapi';

export const fetchProjects = async (params?: any) => {
  const res = await getRecords('tx_projects', params);
  return { status: 200, data: { items: res.results || [] } };
};

export const createProject = async (data: any) => {
  return saveRecord('tx_projects', data);
};

export const updateProject = async (id: number, data: any) => {
  return saveRecord('tx_projects', { ...data, id });
};

export const deleteProject = async (id: number) => {
  return deleteRecord('tx_projects', id);
};