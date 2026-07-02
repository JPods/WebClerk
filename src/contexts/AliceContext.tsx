/**
 * AliceContext — React context for Alice coaching, WCHQ guidance, and power user sharing.
 *
 * Three sources of intelligence:
 *   1. Alice — local agent observations, pattern detection, coaching hints
 *   2. WCHQ — best practices, default layouts, training docs (via sync)
 *   3. Power users — shared layouts, searches, workflows
 *
 * Any component can consume:
 *   const { hints, observations, presets, dismissHint } = useAlice();
 *
 * Loads on mount, refreshes every 5 minutes.
 */
import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { useAppSelector } from '@/store/hooks';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AliceHint {
  id: string;
  source: 'alice' | 'wchq' | 'power_user';
  category: 'coaching' | 'layout' | 'search' | 'workflow' | 'training' | 'alert';
  message: string;
  action?: string;           // manage action to execute if user accepts
  actionParams?: Record<string, unknown>;
  model?: string;            // relevant model (shows hint only on that model)
  field?: string;            // relevant field (shows hint next to that field)
  priority: number;          // 0=normal, 1=important, 2=urgent
  dt: number;
  dismissed: boolean;
}

export interface SearchPreset {
  model: string;
  term: string;
  label: string;
  source: 'alice' | 'wchq' | 'power_user';
  dt_promoted: number;
}

export interface AliceContextValue {
  // Hints and observations for the current user
  hints: AliceHint[];
  observations: AliceHint[];
  searchPresets: SearchPreset[];

  // Hints filtered for a specific context
  hintsForModel: (model: string) => AliceHint[];
  hintsForField: (model: string, field: string) => AliceHint[];

  // Actions
  dismissHint: (id: string) => void;
  acknowledgeObservation: (id: string) => void;
  refreshHints: () => Promise<void>;

  // State
  loading: boolean;
  lastRefresh: number;
}

const AliceContext = createContext<AliceContextValue>({
  hints: [],
  observations: [],
  searchPresets: [],
  hintsForModel: () => [],
  hintsForField: () => [],
  dismissHint: () => {},
  acknowledgeObservation: () => {},
  refreshHints: async () => {},
  loading: false,
  lastRefresh: 0,
});

export const useAlice = () => useContext(AliceContext);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export const AliceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isAuthenticated } = useAppSelector((s) => s.auth);
  const [hints, setHints] = useState<AliceHint[]>([]);
  const [observations, setObservations] = useState<AliceHint[]>([]);
  const [searchPresets, setSearchPresets] = useState<SearchPreset[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(0);
  const refreshTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const dismissedIds = useRef<Set<string>>(new Set());

  const loadHints = useCallback(async () => {
    if (!isAuthenticated || !user?.id) return;
    setLoading(true);
    try {
      const { getRecord, getRecords } = await import('@/api/wcapi');

      // 1. Load user's Alice observations from contact.metadata
      const contact = await getRecord('contact', Number(user.id)) as any;
      const metadata = contact?.metadata || {};
      const aliceObs = metadata.alice_observations || [];
      const navHints: AliceHint[] = [];

      // Convert observations to hints
      aliceObs.forEach((obs: any, i: number) => {
        if (obs.acknowledged) return;
        navHints.push({
          id: `obs-${i}-${obs.dt}`,
          source: 'alice',
          category: obs.category || 'coaching',
          message: obs.observation,
          priority: 0,
          dt: obs.dt || 0,
          dismissed: dismissedIds.current.has(`obs-${i}-${obs.dt}`),
        });
      });
      setObservations(navHints);

      // 2. Load search presets from Setting
      try {
        const presetRes = await getRecords('setting', { name: 'search_presets', limit: 1 }) as any;
        const presetRec = (presetRes?.results || [])[0];
        const presets = presetRec?.data?.presets || [];
        setSearchPresets(presets.map((p: any) => ({
          model: p.model,
          term: p.term,
          label: p.label || `${p.model}: ${p.term}`,
          source: p.source || 'alice',
          dt_promoted: p.dt_promoted || 0,
        })));
      } catch { setSearchPresets([]); }

      // 3. Load WCHQ hints from training documents (coaching tips)
      // These are lightweight — just check if there are unread training docs
      try {
        const trainingRes = await getRecords('document', { name__startswith: 'WC Training', limit: 50 }) as any;
        const trainingDocs = trainingRes?.results || [];
        // Only show hint if there are training docs the user hasn't accessed
        if (trainingDocs.length > 0) {
          const unaccessed = trainingDocs.filter((d: any) => (d.count_accessed || 0) === 0);
          if (unaccessed.length > 0) {
            navHints.push({
              id: 'wchq-training',
              source: 'wchq',
              category: 'training',
              message: `${unaccessed.length} training document${unaccessed.length > 1 ? 's' : ''} available — check Help for details.`,
              priority: 0,
              dt: Date.now(),
              dismissed: dismissedIds.current.has('wchq-training'),
            });
          }
        }
      } catch { /* silent */ }

      // 4. Check agent messages for Alice coaching messages
      try {
        const { manageAction } = await import('@/api/wcapi');
        const inbox = await manageAction('check_agent_inbox', { agent: 'alice', unread_only: true });
        if (Array.isArray(inbox)) {
          inbox.forEach((msg: any) => {
            if (msg.category === 'coaching' || msg.category === 'observation') {
              navHints.push({
                id: `msg-${msg.id}`,
                source: 'alice',
                category: msg.category,
                message: `${msg.subject}: ${msg.body || ''}`.trim(),
                priority: msg.priority || 0,
                dt: msg.dt_created || 0,
                dismissed: dismissedIds.current.has(`msg-${msg.id}`),
              });
            }
          });
        }
      } catch { /* silent */ }

      setHints(navHints.filter((h) => !h.dismissed));
      setLastRefresh(Date.now());
    } catch {
      /* silent — don't break the app if Alice is unavailable */
    }
    setLoading(false);
  }, [isAuthenticated, user?.id]);

  // Load on mount and refresh every 5 minutes
  useEffect(() => {
    loadHints();
    refreshTimer.current = setInterval(loadHints, 5 * 60 * 1000);
    return () => { if (refreshTimer.current) clearInterval(refreshTimer.current); };
  }, [loadHints]);

  const hintsForModel = useCallback((model: string) => {
    return hints.filter((h) => !h.model || h.model === model);
  }, [hints]);

  const hintsForField = useCallback((model: string, field: string) => {
    return hints.filter((h) => h.field === field && (!h.model || h.model === model));
  }, [hints]);

  const dismissHint = useCallback((id: string) => {
    dismissedIds.current.add(id);
    setHints((prev) => prev.filter((h) => h.id !== id));
  }, []);

  const acknowledgeObservation = useCallback(async (id: string) => {
    dismissHint(id);
    // Also mark as acknowledged in the contact record
    if (!user?.id) return;
    try {
      const { getRecord, saveRecord } = await import('@/api/wcapi');
      const contact = await getRecord('contact', Number(user.id)) as any;
      const metadata = contact?.metadata || {};
      const obs = metadata.alice_observations || [];
      // Find and mark acknowledged
      const idx = obs.findIndex((_: any, i: number) => id === `obs-${i}-${_.dt}`);
      if (idx >= 0) {
        obs[idx].acknowledged = true;
        metadata.alice_observations = obs;
        await saveRecord('contact', { id: Number(user.id), metadata });
      }
    } catch { /* silent */ }
  }, [user?.id, dismissHint]);

  const value: AliceContextValue = {
    hints,
    observations,
    searchPresets,
    hintsForModel,
    hintsForField,
    dismissHint,
    acknowledgeObservation,
    refreshHints: loadHints,
    loading,
    lastRefresh,
  };

  return <AliceContext.Provider value={value}>{children}</AliceContext.Provider>;
};

export default AliceContext;
