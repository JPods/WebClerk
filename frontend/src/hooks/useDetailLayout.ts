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
}

// Default layout for models without form sections
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
          { label: 'summary', content: 'summary' },
          { label: 'actions', content: 'actions' },
          { label: 'documents', content: 'documents' },
        ],
      },
    ],
    edit_rules: {
      locked_statuses: ['completed', 'cancelled', 'void'],
      status_field: 'status',
    },
  };
}

// Cache layouts by model name
const layoutCache = new Map<string, DetailLayout>();

export function useDetailLayout(modelName: string) {
  const [layout, setLayout] = useState<DetailLayout | null>(
    layoutCache.get(modelName) ?? null
  );
  const [loading, setLoading] = useState(!layoutCache.has(modelName));

  useEffect(() => {
    if (layoutCache.has(modelName)) {
      const cached = layoutCache.get(modelName)!;
      console.log('[useDetailLayout] CACHE HIT for', modelName, 'sections:', cached.sections?.length, 'first:', cached.sections?.[0]?.type, cached.sections?.[0]?.layout);
      setLayout(cached);
      setLoading(false);
      return;
    }
    console.log('%c[useDetailLayout] CACHE MISS for ' + modelName + ' — fetching from API', 'color: yellow; font-weight: bold; font-size: 14px');

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
        const setting = res?.results?.[0] ?? res?.records?.[0];
        if (cancelled) return;

        // Form layout lives at config.layout.form.default
        const formLayout = setting?.config?.layout?.form?.default;
        const debugInfo = {
          model: modelName,
          hasSetting: !!setting,
          settingId: setting?.id,
          settingIda: setting?.ida,
          configKeys: setting?.config ? Object.keys(setting.config) : 'NO CONFIG',
          layoutKeys: setting?.config?.layout ? Object.keys(setting.config.layout) : 'NO LAYOUT',
          formKeys: setting?.config?.layout?.form ? Object.keys(setting.config.layout.form) : 'NO FORM',
          sectionCount: formLayout?.sections?.length ?? 0,
          firstSectionType: formLayout?.sections?.[0]?.type,
          firstSectionLayout: formLayout?.sections?.[0]?.layout,
          resultCount: res?.results?.length ?? res?.records?.length ?? 0,
        };
        console.log('%c[useDetailLayout] FETCH RESULT', 'color: lime; font-size: 16px; font-weight: bold', debugInfo);
        (window as any).__layoutDebug = { res, setting, formLayout, debugInfo };
        if (formLayout && typeof formLayout === 'object' && formLayout.sections) {
          const parsed = formLayout as DetailLayout;
          layoutCache.set(modelName, parsed);
          setLayout(parsed);
        } else {
          console.warn('%c[useDetailLayout] FALLBACK — using defaultLayout!', 'color: red; font-size: 16px; font-weight: bold', debugInfo);
          const fallback = defaultLayout(modelName);
          layoutCache.set(modelName, fallback);
          setLayout(fallback);
        }
      } catch (err) {
        console.error('%c[useDetailLayout] FETCH ERROR', 'color: red; font-size: 16px; font-weight: bold', modelName, err);
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
