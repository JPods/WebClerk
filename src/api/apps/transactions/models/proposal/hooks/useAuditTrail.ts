import { useState, useEffect, useCallback } from 'react';
import { useWCAPI } from './useWCAPI';

export interface AuditEntry {
  id: number;
  transaction_id: number;
  model: string;
  action: string;
  details: Record<string, any>;
  user_id: number;
  user_name?: string;
  timestamp: string;
  ip_address?: string;
}

export const useAuditTrail = (transactionId: number, model: string) => {
  const [trail, setTrail] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const { get, create } = useWCAPI();

  // Fetch audit trail
  const fetchTrail = useCallback(async () => {
    if (!transactionId) return;

    setLoading(true);
    try {
      const response = await get<AuditEntry>('audit', {
        transaction_id: transactionId,
        model_name: model,
        order_by: '-timestamp',
        limit: 100,
      });

      if (response?.results) {
        setTrail(response.results);
      }
    } catch (error) {
      console.error('Failed to fetch audit trail:', error);
    } finally {
      setLoading(false);
    }
  }, [transactionId, model, get]);

  // Add audit entry
  const addEntry = useCallback(async (
    action: string,
    details: Record<string, any> = {}
  ) => {
    try {
      const entryData = {
        transaction_id: transactionId,
        model,
        action,
        details: JSON.stringify(details),
        user_id: 1, // TODO: Get from auth context
        timestamp: new Date().toISOString(),
      };

      const response = await create<AuditEntry>('audit', entryData);

      if (response?.record) {
        setTrail(prev => [response.record!, ...prev]);
        return response.record;
      }
    } catch (error) {
      console.error('Failed to add audit entry:', error);
    }
  }, [transactionId, model, create]);

  // Auto-fetch on mount/change
  useEffect(() => {
    fetchTrail();
  }, [fetchTrail]);

  return {
    trail,
    loading,
    addEntry,
    refresh: fetchTrail,
  };
};