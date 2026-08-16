/* LastChecked: 2026-08-01 | WhereUsed: UiDetail | WhoCreated: Claude */
/**
 * useDetailLayout — fetch and cache the detail_layout Setting for a model.
 * Returns the layout JSON that drives UiDetail rendering.
 */
import { useState, useEffect, useCallback } from 'react';
import { getRecords } from '@/api/wcapi';

export interface HeaderRow {
  fields: string[];
  cols: number;
}

export interface HeaderSection {
  type: 'header';
  rows: HeaderRow[];
}

export interface LineCardSection {
  type: 'line_card';
  family: 'sell' | 'exec';
  toolbar?: string[];
  actions?: string[];
}

export interface TabDef {
  label: string;
  content: string;
}

export interface TabsSection {
  type: 'tabs';
  tabs: TabDef[];
}

export type LayoutSection = HeaderSection | LineCardSection | TabsSection;

export interface EditRules {
  locked_statuses: string[];
  status_field: string;
  require_unlock_for?: string[];
}

export interface DetailLayout {
  model: string;
  family: 'sell' | 'exec';
  sections: LayoutSection[];
  edit_rules: EditRules;
  card?: Record<string, any>;  // named card specs for db.display
}

// Default layout for models without a Setting — shows basic fields + lines
function defaultLayout(modelName: string): DetailLayout {
  const isSell = ['order', 'invoice', 'proposal'].includes(modelName);
  return {
    model: modelName,
    family: isSell ? 'sell' : 'exec',
    sections: [
      {
        type: 'header',
        rows: [
          { fields: ['ida', 'status'], cols: 2 },
          { fields: ['dt_created', 'dt_modified'], cols: 2 },
        ],
      },
      {
        type: 'line_card',
        family: isSell ? 'sell' : 'exec',
        toolbar: ['L', 'S', 'XR', 'M'],
        actions: [],
      },
      {
        type: 'tabs',
        tabs: [
          { label: 'Summary', content: 'summary' },
          { label: 'Actions', content: 'actions' },
          { label: 'Documents', content: 'documents' },
        ],
      },
    ],
    edit_rules: {
      locked_statuses: ['completed', 'cancelled', 'void'],
      status_field: 'status',
    },
  };
}

// Cache layouts by model name to avoid re-fetching
const layoutCache = new Map<string, DetailLayout>();

export function useDetailLayout(modelName: string) {
  const [layout, setLayout] = useState<DetailLayout | null>(
    layoutCache.get(modelName) ?? null
  );
  const [loading, setLoading] = useState(!layoutCache.has(modelName));

  useEffect(() => {
    if (layoutCache.has(modelName)) {
      setLayout(layoutCache.get(modelName)!);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);

    (async () => {
      try {
        const res = await getRecords('setting', {
          parent_model: modelName,
          purpose: 'wc:detail_layout',
          limit: 1,
        });
        console.log('[useDetailLayout]', modelName, 'response:', res);
        const setting = res?.results?.[0] ?? res?.records?.[0];
        console.log('[useDetailLayout]', modelName, 'setting:', setting?.config ? 'FOUND' : 'NOT FOUND');
        if (cancelled) return;

        if (setting?.config && typeof setting.config === 'object') {
          const parsed = setting.config as DetailLayout;
          layoutCache.set(modelName, parsed);
          setLayout(parsed);
        } else {
          // No Setting found — use default layout
          const fallback = defaultLayout(modelName);
          layoutCache.set(modelName, fallback);
          setLayout(fallback);
        }
      } catch {
        if (!cancelled) {
          const fallback = defaultLayout(modelName);
          setLayout(fallback);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [modelName]);

  const invalidate = useCallback(() => {
    layoutCache.delete(modelName);
    setLayout(null);
    setLoading(true);
  }, [modelName]);

  return { layout, loading, invalidate };
}
