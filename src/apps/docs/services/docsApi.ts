import axios from 'axios';
import type { DocsStats } from '../types/docsTypes';

export const docsApi = {
  getStats: async (): Promise<DocsStats> => {
    const response = await axios.get('/api/docs/stats/');
    return response.data;
  },
};