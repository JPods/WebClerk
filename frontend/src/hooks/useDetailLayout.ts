/* LastChecked: 2026-08-20 | WhereUsed: TransactionDetail, OrgDetail | WhoCreated: Claude */
/**
 * useDetailLayout — fetch form layout from the wc:model Setting.
 *
 * Single source of truth: config.layout.form.default on the wc:model Setting.
 * No separate wc:detail_layout records.
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

export interface PanelSection {
  type: 'panel';
  content: string;
  label: string;
  collapsed?: boolean;
  collapse_when_empty?: boolean;
  /** Arbitrary config passed through to the panel renderer (e.g., channels for comments) */
  config?: Record<string, unknown>;
}

export interface JsonTreeSection {
  type: 'json_tree';
  label?: string;
  collapsed?: boolean;
  fields?: string[];
}

export type LayoutSection = HeaderSection | LineCardSection | TabsSection | PanelSection | JsonTreeSection;

export interface EditRules {
  locked_statuses: string[];
  status_field: string;
  require_unlock_for?: string[];
}

export interface DetailLayout {
  model: string;
  family: 'sell' | 'exec' | 'org' | 'core' | 'product' | 'docs' | 'sync' | 'transaction';
  sections: LayoutSection[];
  edit_rules: EditRules;
  card?: Record<string, any>;
  behaviors?: Record<string, any>;
}

// Cache layouts by model name
const layoutCache = new Map<string, DetailLayout>();
// Expose cache for debugging — window.__wc_layout_cache.clear() to force re-fetch
if (typeof window !== 'undefined') (window as any).__wc_layout_cache = layoutCache;

export function useDetailLayout(modelName: string) {
  const [layout, setLayout] = useState<DetailLayout | null>(
    layoutCache.get(modelName) ?? null
  );
  const [loading, setLoading] = useState(!layoutCache.has(modelName));
  // Every model's form is in its definition (backend apps/core/layouts); one missing is said, not guessed.
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (layoutCache.has(modelName)) {
      const cached = layoutCache.get(modelName)!;
      setLayout(cached);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);

    (async () => {
      try {
        // Read from wc:model — single source of truth
        const res = await getRecords('setting', {
          parent_model: modelName,
          purpose: 'wc:model',
          limit: 1,
        });
        const setting = res?.results?.[0];
        if (cancelled) return;

        // Form layout lives at config.layout.form.default
        const formLayout = setting?.config?.layout?.form?.default;
        if (formLayout && typeof formLayout === 'object' && formLayout.sections) {
          const parsed = formLayout as DetailLayout;
          // Attach behaviors from Setting — drives label styles and select options
          parsed.behaviors = setting?.config?.behaviors || {};
          layoutCache.set(modelName, parsed);
          setLayout(parsed);
        } else {
          console.warn('[useDetailLayout] no form for', modelName, setting?.id ?? 'no wc:model setting');
          setError(`${modelName} has no form in its definition. A staff member can run seed_layouts or reset the form.`);
        }
      } catch (err) {
        console.error('[useDetailLayout] fetch error', modelName, err);
        if (!cancelled) setError(`Could not read the ${modelName} form.`);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [modelName]);

  const invalidate = useCallback(() => {
    layoutCache.delete(modelName);
    setLayout(null);
    setError(null);
    setLoading(true);
  }, [modelName]);

  return { layout, loading, error, invalidate };
}
