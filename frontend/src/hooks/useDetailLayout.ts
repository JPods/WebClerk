/* LastChecked: 2026-08-20 | WhereUsed: TransactionDetail, OrgDetail | WhoCreated: Claude */
/**
 * useDetailLayout — fetch form layout from the wc:model Setting.
 *
 * Single source of truth: config.layout.form.default on the wc:model Setting.
 * No separate wc:detail_layout records.
 */
import { companyFormatting, formattingOf, type Formatting } from '@/utils/formatting';
import { fieldBehaviorsOf } from '@/utils/fieldBehaviorsOf';
import { useState, useEffect, useCallback } from 'react';
import { getRecords } from '@/api/wcapi';
import { getUI, setUI } from '@/utils/contactUI';

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
  /** The order: these objects first. The panel lists every JSON object the viewer may see. */
  fields?: string[];
  /** Objects this form's panel does not show. */
  hide?: string[];
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
  /** config.defaults.formatting of the definition (utils/formatting). */
  formatting?: Formatting;
  /** config.defaults.features of the definition: the model's switches (line_contacts). */
  features?: Record<string, boolean>;
}

// ── A person's own form (Bill, 2026-11-14: "fields and leafs important to them") ──
// The company's form is the model's definition. A person may arrange the header's cards for
// themselves; that arrangement is kept on their own Contact (config.ui.form.<model>.columns)
// and laid over the company's form when it is read. Nothing else of the form is theirs:
// lines, tabs, panels and edit rules stay the company's.

/** The header columns this person saved for a model, or null. */
export function myFormColumns(modelName: string): any[] | null {
  const mine = getUI<any>(`form.${modelName}`, null);
  return Array.isArray(mine?.columns) && mine.columns.length ? mine.columns : null;
}

/** Keep (or with null, drop) this person's header columns for a model. */
export function saveMyFormColumns(modelName: string, columns: any[] | null): void {
  setUI(`form.${modelName}`, columns ? { columns } : null);
}

/** `layout` with this person's header columns in place of the company's, when they have any. */
export function withMyForm(layout: DetailLayout, modelName: string): DetailLayout {
  const columns = myFormColumns(modelName);
  if (!columns) return layout;
  return {
    ...layout,
    sections: (layout.sections || []).map((s: any) =>
      s?.type === 'header' && Array.isArray(s.columns)
        ? { ...s, columns: JSON.parse(JSON.stringify(columns)) } : s),
  };
}

// Cache layouts by model name
const layoutCache = new Map<string, DetailLayout>();
// Expose cache for debugging — window.__wc_layout_cache.clear() to force re-fetch
if (typeof window !== 'undefined') (window as any).__wc_layout_cache = layoutCache;

export function useDetailLayout(modelName: string) {
  const [layout, setLayout] = useState<DetailLayout | null>(
    layoutCache.has(modelName) ? withMyForm(layoutCache.get(modelName)!, modelName) : null
  );
  const [loading, setLoading] = useState(!layoutCache.has(modelName));
  // Every model's form is in its definition (backend apps/core/layouts); one missing is said, not guessed.
  const [error, setError] = useState<string | null>(null);
  // invalidate() bumps this so the form is read again (the effect ran once per model before).
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (layoutCache.has(modelName)) {
      const cached = layoutCache.get(modelName)!;
      setLayout(withMyForm(cached, modelName));
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
        const company = await companyFormatting();
        if (cancelled) return;

        // Form layout lives at config.layout.form.default
        const formLayout = setting?.config?.layout?.form?.default;
        if (formLayout && typeof formLayout === 'object' && formLayout.sections) {
          const parsed = formLayout as DetailLayout;
          // Attach behaviors from Setting — drives label styles and select options
          parsed.behaviors = fieldBehaviorsOf(setting?.config);
          parsed.formatting = formattingOf(setting?.config, company);
          parsed.features = setting?.config?.defaults?.features || {};
          layoutCache.set(modelName, parsed);
          setLayout(withMyForm(parsed, modelName));
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
  }, [modelName, version]);

  const invalidate = useCallback(() => {
    layoutCache.delete(modelName);
    setLayout(null);
    setError(null);
    setLoading(true);
    setVersion((v) => v + 1);
  }, [modelName]);

  return { layout, loading, error, invalidate };
}
