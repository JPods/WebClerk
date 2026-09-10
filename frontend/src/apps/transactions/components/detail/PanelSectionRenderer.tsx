/* LastChecked: 2026-09-09 | WhereUsed: TransactionDetail, OrgDetail | WhoCreated: Claude */
/**
 * PanelSectionRenderer — renders a single collapsible panel section.
 *
 * Link-type panels (contacts, documents, touches, actions) use LinkedRecordsPanel
 * for the standard db.columns header with hamburger (≡), count, and assign button.
 * Comments stays as CommentsPanel. Other types fall back to CollapsiblePanel + panelRegistry.
 *
 * Times and billing panels show summary + controls in the header (always visible when collapsed).
 */
import React, { useCallback } from 'react';
import type { PanelSection } from '@/hooks/useDetailLayout';
import CollapsiblePanel from '@/apps/common/components/CollapsiblePanel';
import { LinkedRecordsPanel } from '@/apps/common/components/panels/LinkedRecordsPanel';
import { renderPanel } from '@/components/common/panelRegistry';
import { useWindowManager } from '@/context/WindowManagerContext';
import { saveRecord } from '@/api/wcapi';

/** Panels that should render as LinkedRecordsPanel with db.columns header */
const LINKED_PANEL_MODELS = new Set([
  'contacts', 'documents', 'touches', 'actions',
  'phone', 'email', 'domain', 'address',  // contact comms
]);

/** Map panel content name to the linked model name */
const PANEL_TO_MODEL: Record<string, string> = {
  contacts: 'contact',
  documents: 'document',
  touches: 'touch',
  actions: 'action',
};

interface PanelSectionRendererProps {
  section: PanelSection;
  data: any;
  isEditing: boolean;
  modelName: string;
  onChange: (field: string, value: unknown) => void;
  onRefresh: () => void;
  loggedInUserName?: string;
}

const PanelSectionRenderer: React.FC<PanelSectionRendererProps> = ({
  section, data, isEditing, modelName, onChange, onRefresh, loggedInUserName,
}) => {
  const windowManager = useWindowManager();

  // Link-type panels → LinkedRecordsPanel (db.columns header with hamburger + assign)
  if (LINKED_PANEL_MODELS.has(section.content) && data?.id) {
    const linkedModel = PANEL_TO_MODEL[section.content] || section.content;
    return (
      <LinkedRecordsPanel
        linkedModel={linkedModel}
        parentModel={modelName}
        parentId={data.id}
        defaultCollapsed={section.collapsed ?? true}
        collapseWhenEmpty={section.collapse_when_empty ?? false}
      />
    );
  }

  // ── Times: clock in/out with auto-persist ──
  const clockToggle = useCallback(() => {
    const times = data?.config?.times ?? { entries: [] };
    const entries = Array.isArray(times.entries) ? [...times.entries] : [];
    const now = Date.now();
    const openIdx = entries.findIndex((e: any) => e.dt_in && !e.dt_out);

    if (openIdx >= 0) {
      // Clock out
      const e = { ...entries[openIdx] };
      e.dt_out = now;
      e.elapsed_ms = now - (e.dt_in ?? now);
      entries[openIdx] = e;
    } else {
      // Clock in
      entries.push({
        id: crypto.randomUUID?.() ?? `${now}-${Math.random().toString(36).slice(2, 9)}`,
        dt_in: now, dt_out: null, elapsed_ms: null,
        percent_active: 100, reason: '', notes: '', tags: [], issue: null,
      });
    }
    // Rollup totals
    let totalElapsed = 0, totalActive = 0;
    for (const e of entries) {
      const el = e.elapsed_ms ?? 0;
      totalElapsed += el;
      totalActive += Math.round(el * ((e.percent_active ?? 100) / 100));
    }
    const updated = { entries, total_elapsed_ms: totalElapsed, total_active_ms: totalActive };
    onChange('config.times', updated);
    // Auto-persist
    if (data?.id) {
      const config = { ...(data.config || {}), times: updated };
      saveRecord('action', { id: data.id, config: { mode: 'update', value: config } }).catch(() => {});
    }
  }, [data, onChange]);

  // ── Extract badge + headerActions per panel type ──
  let badge: string | number | undefined;
  let headerActions: React.ReactNode = undefined;

  // ── Combined billing panel: times header + billable header + both bodies ──
  if (section.content === 'billing') {
    const times = data?.config?.times;
    const entries = times?.entries;
    const count = Array.isArray(entries) ? entries.length : 0;
    const totalMs = times?.total_elapsed_ms ?? 0;
    const isOpen = Array.isArray(entries) && entries.some((e: any) => e.dt_in && !e.dt_out);
    const b = data?.config?.billable;
    const isBillable = b?.is_billable !== false;

    const fmtMs = (ms: number) => {
      if (ms <= 0) return '';
      const h = Math.floor(ms / 3600000);
      const m = Math.floor((ms % 3600000) / 60000);
      if (h > 0) return `${h}h ${String(m).padStart(2, '0')}m`;
      return `${m}m`;
    };

    badge = count > 0 ? count : undefined;

    headerActions = (
      <>
        {totalMs > 0 && (
          <span className="db-font-xs" style={{ color: 'var(--db-text-muted)' }}>{fmtMs(totalMs)}</span>
        )}
        <button
          type="button"
          onClick={clockToggle}
          className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold transition-colors"
          style={isOpen
            ? { background: 'color-mix(in srgb, var(--db-accent-red) 15%, transparent)', color: 'var(--db-accent-red)' }
            : { background: 'color-mix(in srgb, var(--db-accent-green) 15%, transparent)', color: 'var(--db-accent-green)' }
          }
        >
          {isOpen ? 'Stop' : (
            <>
              <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
              Clock In
            </>
          )}
        </button>
        <span
          className="rounded-full px-1.5 py-0.5 text-[10px] font-semibold"
          style={isBillable
            ? { background: 'color-mix(in srgb, var(--db-accent-green) 15%, transparent)', color: 'var(--db-accent-green)' }
            : { background: 'var(--db-surface-alt)', color: 'var(--db-text-dim)' }
          }
        >
          {isBillable ? 'billable' : 'non-billable'}
        </span>
        <label className="inline-flex items-center gap-1.5 cursor-pointer">
          <input
            type="checkbox"
            checked={isBillable}
            onChange={(e) => {
              const updated = { ...(b || { rate_unit: 'hour', currency: 'USD' }), is_billable: e.target.checked };
              onChange('config.billable', updated);
            }}
            className="rounded"
          />
          <span className="text-[11px]" style={{ color: 'var(--db-text-muted)' }}>billable</span>
        </label>
      </>
    );
  }

  // Build panel context for panelRegistry
  const panelCtx = {
    modelName,
    recordId: data?.id ?? 0,
    data,
    isEditing,
    onFieldChange: onChange,
    onRefresh,
    ensureWindow: (path: string, title: string) => windowManager.ensureWindow(path, title),
  };

  // Everything else (comments, times, billable, financials, etc.) → CollapsiblePanel + panelRegistry
  return (
    <CollapsiblePanel
      label={section.label}
      storageKey={`panel_${modelName}_${section.content}`}
      defaultCollapsed={section.collapse_when_empty ? true : (section.collapsed ?? false)}
      badge={badge}
      headerActions={headerActions}
    >
      {renderPanel(section.content, panelCtx)}
    </CollapsiblePanel>
  );
};

export default PanelSectionRenderer;
