/* LastChecked: 2026-08-13 | WhereUsed: /gantt route | WhoCreated: Unknown */
/**
 * UnifiedGanttPage - Full page wrapper for UnifiedGantt
 *
 * Gantt has its own +/- zoom control (chartZoom), independent of the Font selector.
 * Zoom applies to the chart+list area only — toolbar stays at natural size.
 * Default scale is 0.5. Persisted in localStorage.
 */

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import { UnifiedGantt } from "./UnifiedGantt";
import { withDevIdentifier } from '@/components/common/DevIdentifier';
import { getUI } from '@/utils/contactUI';

const GANTT_SCALE_KEY = 'wc3_gantt_scale';
const DEFAULT_SCALE = 0.5;
const SCALE_STEP = 0.1;
const MIN_SCALE = 0.3;
const MAX_SCALE = 1.5;

function loadScale(): number {
  try {
    const v = localStorage.getItem(GANTT_SCALE_KEY);
    if (v) { const n = parseFloat(v); if (n >= MIN_SCALE && n <= MAX_SCALE) return n; }
  } catch {}
  return DEFAULT_SCALE;
}

const UnifiedGanttPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [theme, setTheme] = useState<string>(() => getUI('theme.active', 'dark'));

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (detail?.mode) setTheme(detail.mode);
    };
    window.addEventListener('wc3-zone-theme-changed', handler);
    return () => window.removeEventListener('wc3-zone-theme-changed', handler);
  }, []);

  const { projectId, initialProjectIds } = useMemo(() => {
    const singleProject = searchParams.get("project");
    if (singleProject) return { projectId: singleProject, initialProjectIds: [] };
    const multipleProjects = searchParams.get("projects");
    if (multipleProjects) {
      const ids = multipleProjects.split(",").map((id) => id.trim()).filter(Boolean);
      return { projectId: undefined, initialProjectIds: ids };
    }
    return { projectId: undefined, initialProjectIds: [] };
  }, [searchParams]);

  const [scale, setScale] = useState(loadScale);

  const adjustScale = (delta: number) => {
    setScale(prev => {
      const next = Math.round(Math.max(MIN_SCALE, Math.min(MAX_SCALE, prev + delta)) * 10) / 10;
      localStorage.setItem(GANTT_SCALE_KEY, String(next));
      return next;
    });
  };

  return (
    <div className="db-root flex flex-col h-[calc(100vh-2rem)]" data-theme={theme}>
      {/* Zoom control — not scaled */}
      <div className="flex items-center gap-1 px-2 py-0.5 flex-shrink-0" style={{ fontSize: 11 }}>
        <button
          onClick={() => adjustScale(-SCALE_STEP)}
          disabled={scale <= MIN_SCALE}
          className="px-1.5 py-0.5 rounded disabled:opacity-30"
          style={{ border: '1px solid var(--db-border)', background: 'var(--db-surface)', color: 'var(--db-text)' }}
          title="Zoom out"
        >−</button>
        <span className="min-w-[3em] text-center" style={{ color: 'var(--db-text-muted)' }} title="Gantt zoom level">
          {Math.round(scale * 100)}%
        </span>
        <button
          onClick={() => adjustScale(SCALE_STEP)}
          disabled={scale >= MAX_SCALE}
          className="px-1.5 py-0.5 rounded disabled:opacity-30"
          style={{ border: '1px solid var(--db-border)', background: 'var(--db-surface)', color: 'var(--db-text)' }}
          title="Zoom in"
        >+</button>
      </div>

      {/* Gantt — chartZoom scales chart+list only, toolbar stays natural */}
      <div className="flex-1 min-h-0">
        <UnifiedGantt
          projectId={projectId}
          initialProjectIds={initialProjectIds}
          showSelector={!projectId}
          autoRefresh={true}
          chartZoom={scale}
        />
      </div>
    </div>
  );
};

export default withDevIdentifier(UnifiedGanttPage, 'UnifiedGanttPage', 'rose', 'apps/utils/gantt/UnifiedGanttPage.tsx');
