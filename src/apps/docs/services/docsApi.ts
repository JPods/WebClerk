/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
import axios from 'axios';
import type { DocsStats } from '../types/docsTypes';

export const docsApi = {
  getStats: async (): Promise<DocsStats> => {
    const response = await axios.get('/api/docs/stats/');
    return response.data;
  },
};