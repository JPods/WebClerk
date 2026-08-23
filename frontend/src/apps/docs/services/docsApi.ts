/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import apiClient from '@/api/axios';
import type { DocsStats } from '../types/docsTypes';

export const docsApi = {
  getStats: async (): Promise<DocsStats> => {
    const response = await apiClient.get('/wcapi/docs/stats/');
    return response.data;
  },
};