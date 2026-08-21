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
  children: React.ReactNode;
}

const CollapsiblePanel: React.FC<CollapsiblePanelProps> = ({
  label, storageKey, defaultCollapsed = false, badge, children,
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
      <button
        type="button"
        onClick={toggle}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-[var(--db-surface-alt,#f8f9fa)] transition-colors rounded-t-lg"
      >
        <span className="text-[10px] text-[var(--db-text-muted,#6c757d)] transition-transform"
          style={{ transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)' }}>
          ▼
        </span>
        <span className="text-xs font-bold uppercase tracking-wide text-[var(--db-text,#212529)]">
          {label}
        </span>
        {badge != null && (
          <span className="text-[10px] text-[var(--db-text-muted,#6c757d)]">({badge})</span>
        )}
      </button>
      {!collapsed && (
        <div className="px-3 pb-3">
          {children}
        </div>
      )}
    </div>
  );
};

export default CollapsiblePanel;
