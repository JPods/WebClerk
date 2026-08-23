/**
 * useDashboardCounts — single API call for all dashboard period comparisons.
 *
 * Replaces N×M individual /wcapi/get/ calls with one POST to /wcapi/_manage/.
 * Falls back to staggered individual fetches if the batch endpoint fails.
 */
import { useEffect, useState } from 'react';
import apiClient from '@/api/axios';

type PeriodDef = { key: string; from: number; to: number };

export function buildPeriods(): PeriodDef[] {
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth();
  const d = now.getDate();
  const qStart = m - (m % 3);
  return [
    { key: 'this_mo', from: new Date(y, m, 1).getTime(), to: now.getTime() },
    { key: 'last_mo', from: new Date(y, m - 1, 1).getTime(), to: new Date(y, m, 1).getTime() },
    { key: 'this_mo_ly', from: new Date(y - 1, m, 1).getTime(), to: new Date(y - 1, m, d).getTime() },
    { key: 'this_qtr', from: new Date(y, qStart, 1).getTime(), to: now.getTime() },
    { key: 'last_qtr', from: new Date(y, qStart - 3, 1).getTime(), to: new Date(y, qStart, 1).getTime() },
    { key: 'ytd', from: new Date(y, 0, 1).getTime(), to: now.getTime() },
    { key: 'last_ytd', from: new Date(y - 1, 0, 1).getTime(), to: new Date(y - 1, m, d).getTime() },
  ];
}

type CountsResult = Record<string, Record<string, number>>;

export function useDashboardCounts(modelNames: string[]): {
  counts: CountsResult;
  loading: boolean;
  periods: PeriodDef[];
} {
  const [counts, setCounts] = useState<CountsResult>({});
  const [loading, setLoading] = useState(true);
  const periods = buildPeriods();

  useEffect(() => {
    if (!modelNames.length) return;

    const fetchBatch = async () => {
      try {
        const res = await apiClient.post('/wcapi/_manage/', {
          action: 'get_dashboard_counts',
          params: {
            models: modelNames,
            periods: periods.map(p => ({ key: p.key, from: p.from, to: p.to })),
          },
        });
        const data = res.data?.data ?? res.data;
        if (data && typeof data === 'object') {
          setCounts(data);
          setLoading(false);
          return;
        }
      } catch {
        // Batch endpoint failed — fall back to staggered individual fetches
      }

      // Fallback: staggered individual fetches
      const result: CountsResult = {};
      for (const model of modelNames) {
        result[model] = {};
        const pairs = await Promise.all(
          periods.map(p =>
            apiClient.get(`/wcapi/get/?model_name=${model}&limit=1&dt_created__gte=${p.from}&dt_created__lte=${p.to}`)
              .then(r => [p.key, r.data?.data?.total ?? r.data?.data?.count ?? 0] as [string, number])
              .catch(() => [p.key, 0] as [string, number])
          )
        );
        for (const [k, v] of pairs) {
          result[model][k] = v;
        }
      }
      setCounts(result);
      setLoading(false);
    };

    fetchBatch();
  }, [modelNames.join(',')]); // stable dependency

  return { counts, loading, periods };
}
