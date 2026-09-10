/* LastChecked: 2026-08-18 | WhereUsed: PanelSectionRenderer, JsonSectionRenderer, OrgDetail | WhoCreated: Claude */
/**
 * CollapsiblePanel — shared collapsible card wrapper for form sections.
 *
 * Chevron toggle, label, optional badge. Persists open/closed state
 * in localStorage keyed by storageKey prop.
 */
import React, { useState, useCallback } from 'react';

interface CollapsiblePanelProps {
  label: string;
  storageKey?: string;         // localStorage key for persistence; omit to skip persistence
  defaultCollapsed?: boolean;
  badge?: string | number;
  /** Always-visible content on the right side of the header (e.g. buttons, badges) */
  headerActions?: React.ReactNode;
  children: React.ReactNode;
}

const CollapsiblePanel: React.FC<CollapsiblePanelProps> = ({
  label, storageKey, defaultCollapsed = false, badge, headerActions, children,
}) => {
  const [collapsed, setCollapsed] = useState(() => {
    if (storageKey) {
      const saved = localStorage.getItem(storageKey);
      if (saved !== null) return saved === '1';
    }
    return defaultCollapsed;
  });

  const toggle = useCallback(() => {
    setCollapsed(prev => {
      const next = !prev;
      if (storageKey) localStorage.setItem(storageKey, next ? '1' : '0');
      return next;
    });
  }, [storageKey]);

  return (
    <div className="bg-[var(--db-surface,#fff)] rounded-lg border border-[var(--db-border,#dee2e6)]">
      <div className="flex items-center px-3 py-2 hover:bg-[var(--db-surface-alt,#f8f9fa)] transition-colors rounded-t-lg">
        <button
          type="button"
          onClick={toggle}
          className="flex items-center gap-2 text-left flex-1 min-w-0"
        >
          <span className="db-font-xs text-[var(--db-text-muted,#6c757d)] transition-transform"
            style={{ transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)' }}>
            ▼
          </span>
          <span className="db-font-sm uppercase tracking-wide text-[var(--db-text-muted,#6c757d)]">
            {label}
          </span>
          {badge != null && (
            <span className="db-font-xs text-[var(--db-text-muted,#6c757d)]">({badge})</span>
          )}
        </button>
        {headerActions && (
          <div className="flex items-center gap-2 ml-2 flex-shrink-0" onClick={(e) => e.stopPropagation()}>
            {headerActions}
          </div>
        )}
      </div>
      {!collapsed && (
        <div className="px-3 pb-3">
          {children}
        </div>
      )}
    </div>
  );
};

export default CollapsiblePanel;
