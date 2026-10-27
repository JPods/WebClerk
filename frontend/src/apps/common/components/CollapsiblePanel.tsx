/* LastChecked: 2026-10-27 | WhereUsed: PanelSectionRenderer, JsonSectionRenderer, DynamicDetail, DbColumns, RelatedTransactionsPanel | WhoCreated: Claude */
/**
 * CollapsiblePanel — the one panel frame (Bill, 2026-10-27: panels inherit their common
 * behavior and adjust only for special needs).
 *
 * What every panel gets, without writing it: the header (chevron, label, count badge,
 * header actions), collapse remembered per viewer (storageKey), Option+Cmd/Alt+Ctrl click to
 * remove (onRemove), and the status of its body — loading, error with retry, empty — worded
 * the same everywhere. A panel rendered inside the frame (a registry panel, whose frame is
 * PanelSectionRenderer's) declares its badge, actions and status with usePanelFrame();
 * props set by the caller take precedence. Before this, 20 panels drew a second header inside
 * the frame, 26 their own loading text and 19 their own empty text.
 *
 * Labels never scroll (TFTS 2026-10-27): the frame does not add a scroll container, so a
 * sticky label row inside the body (DbColumns' column headers) sticks to the page's one scroller.
 */
import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';

/** What a panel body is doing. Children render only when none of these applies. */
export interface PanelStatus {
  loading?: boolean;
  error?: string | null;
  /** True when there is nothing to show; emptyText says what is missing. */
  empty?: boolean;
  emptyText?: string;
  onRetry?: () => void;
}

interface PanelFrameDeclaration {
  badge?: string | number;
  headerActions?: React.ReactNode;
  status?: PanelStatus;
}

const PanelFrameContext = createContext<((d: PanelFrameDeclaration) => void) | null>(null);

/**
 * A panel inside the frame declares what the frame shows for it. Pass a stable or memoized
 * headerActions; the frame re-renders when any of these change. Outside a frame it does nothing.
 */
export function usePanelFrame(declaration: PanelFrameDeclaration): void {
  const declare = useContext(PanelFrameContext);
  const { badge, headerActions, status } = declaration;
  // No clearing on unmount: a collapsed panel's body unmounts, and its header keeps the
  // last count it declared.
  useEffect(() => {
    declare?.({ badge, headerActions, status });
  }, [declare, badge, headerActions, status?.loading, status?.error, status?.empty, status?.emptyText]); // eslint-disable-line react-hooks/exhaustive-deps
}

interface CollapsiblePanelProps {
  label: string;
  storageKey?: string;         // localStorage key for persistence; omit to skip persistence
  defaultCollapsed?: boolean;
  badge?: string | number;
  /** Always-visible content on the right side of the header (e.g. buttons, badges) */
  headerActions?: React.ReactNode;
  icon?: string;
  /** Option+Cmd (Mac) / Alt+Ctrl click on the header removes the panel from the layout. */
  onRemove?: () => void;
  status?: PanelStatus;
  /** Keep the body mounted (hidden) while collapsed, so its count stays current — a list that
   *  fetches. Default: the body unmounts when collapsed and fetches nothing. */
  keepMounted?: boolean;
  /** false: always open, no chevron (a panel that is the page's main list). */
  collapsible?: boolean;
  children: React.ReactNode;
}

function readCollapsed(storageKey: string | undefined, fallback: boolean): boolean {
  if (!storageKey) return fallback;
  try {
    const saved = localStorage.getItem(storageKey);
    return saved === null ? fallback : saved === '1';
  } catch { return fallback; }
}

const STATUS_TEXT = 'px-3 py-2 db-font-xs';

/** The panel's status above its body. The body always stays rendered — a panel that declared
 *  "loading" must stay mounted to declare that it finished — and is hidden while loading or
 *  in error. */
const PanelBodyStatus: React.FC<{ status?: PanelStatus; label: string; children: React.ReactNode }> = ({ status, label, children }) => {
  const blocked = !!(status?.error || status?.loading);
  return (
    <>
      {status?.error ? (
        <div className={STATUS_TEXT} style={{ color: 'var(--db-accent-red, #c92a2a)' }}>
          {status.error}
          {status.onRetry && (
            <button type="button" className="ml-2 underline" onClick={status.onRetry}>Try again</button>
          )}
        </div>
      ) : status?.loading ? (
        <div className={STATUS_TEXT} style={{ color: 'var(--db-text-dim)' }}>Loading…</div>
      ) : status?.empty ? (
        <div className={STATUS_TEXT} style={{ color: 'var(--db-text-dim)' }}>{status.emptyText ?? `No ${label.toLowerCase()}`}</div>
      ) : null}
      <div hidden={blocked}>{children}</div>
    </>
  );
};

const CollapsiblePanel: React.FC<CollapsiblePanelProps> = ({
  label, storageKey, defaultCollapsed = false, badge, headerActions, icon, onRemove, status,
  keepMounted = false, collapsible = true, children,
}) => {
  const [stored, setCollapsed] = useState(() => readCollapsed(storageKey, defaultCollapsed));
  const collapsed = collapsible && stored;
  const [declared, setDeclared] = useState<PanelFrameDeclaration>({});

  const toggle = useCallback(() => {
    setCollapsed(prev => {
      const next = !prev;
      try { if (storageKey) localStorage.setItem(storageKey, next ? '1' : '0'); } catch { /* per-viewer convenience only */ }
      return next;
    });
  }, [storageKey]);

  const shownBadge = badge ?? declared.badge;
  const shownActions = headerActions ?? declared.headerActions;
  const shownStatus = status ?? declared.status;

  return (
    <div className="bg-[var(--db-surface,#fff)] rounded-lg border border-[var(--db-border,#dee2e6)]">
      <div className="flex items-center px-3 py-2 hover:bg-[var(--db-surface-alt,#f8f9fa)] transition-colors rounded-t-lg">
        <button
          type="button"
          onClick={(e) => {
            if (onRemove && e.altKey && (e.metaKey || e.ctrlKey)) { onRemove(); return; }
            if (collapsible) toggle();
          }}
          className="flex items-center gap-2 text-left flex-1 min-w-0"
        >
          {collapsible && (
            <span className="db-font-xs text-[var(--db-text-muted,#6c757d)] transition-transform"
              style={{ transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)' }}>
              ▼
            </span>
          )}
          {icon && <span className="db-font-xs">{icon}</span>}
          <span className="db-font-sm uppercase tracking-wide text-[var(--db-text-muted,#6c757d)]">
            {label}
          </span>
          {shownBadge != null && (
            <span className="db-font-xs text-[var(--db-text-muted,#6c757d)]">({shownBadge})</span>
          )}
        </button>
        {shownActions && (
          <div className="flex items-center gap-2 ml-2 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
            {shownActions}
          </div>
        )}
      </div>
      {(!collapsed || keepMounted) && (
        <div className="px-3 pb-3" hidden={collapsed}>
          <PanelFrameContext.Provider value={setDeclared}>
            <PanelBodyStatus status={shownStatus} label={label}>{children}</PanelBodyStatus>
          </PanelFrameContext.Provider>
        </div>
      )}
    </div>
  );
};

export default CollapsiblePanel;
