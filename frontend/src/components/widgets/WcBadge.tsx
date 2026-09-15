/* LastChecked: 2026-08-02 | WhereUsed: All views | WhoCreated: Claude */
/**
 * WcBadge — status badge for records.
 * Colors based on status value. Used in headers, lists, tabs.
 */
import React from 'react';

export interface WcBadgeProps {
  value: string;
  size?: 'sm' | 'md';
  className?: string;
}

const statusStyles: Record<string, React.CSSProperties> = {
  open: { background: 'color-mix(in srgb, var(--db-accent) 15%, transparent)', color: 'var(--db-accent)' },
  active: { background: 'color-mix(in srgb, var(--db-accent-green) 15%, transparent)', color: 'var(--db-accent-green)' },
  completed: { background: 'color-mix(in srgb, var(--db-accent-green) 15%, transparent)', color: 'var(--db-accent-green)' },
  created: { background: 'var(--db-surface-alt)', color: 'var(--db-text-muted)' },
  planned: { background: 'var(--db-surface-alt)', color: 'var(--db-text-muted)' },
  draft: { background: 'var(--db-surface-alt)', color: 'var(--db-text-muted)' },
  'in progress': { background: 'color-mix(in srgb, var(--db-accent-gold) 15%, transparent)', color: 'var(--db-accent-gold)' },
  in_progress: { background: 'color-mix(in srgb, var(--db-accent-gold) 15%, transparent)', color: 'var(--db-accent-gold)' },
  journalized: { background: 'color-mix(in srgb, var(--db-accent-purple) 15%, transparent)', color: 'var(--db-accent-purple)' },
  released: { background: 'color-mix(in srgb, var(--db-accent-green) 15%, transparent)', color: 'var(--db-accent-green)' },
  shipped: { background: 'color-mix(in srgb, var(--db-accent-green) 15%, transparent)', color: 'var(--db-accent-green)' },
  received: { background: 'color-mix(in srgb, var(--db-accent-green) 15%, transparent)', color: 'var(--db-accent-green)' },
  applied: { background: 'color-mix(in srgb, var(--db-accent-green) 15%, transparent)', color: 'var(--db-accent-green)' },
  cancelled: { background: 'color-mix(in srgb, var(--db-accent-red) 15%, transparent)', color: 'var(--db-accent-red)' },
  void: { background: 'color-mix(in srgb, var(--db-accent-red) 15%, transparent)', color: 'var(--db-accent-red)' },
  closed: { background: 'var(--db-surface-alt)', color: 'var(--db-text-dim)' },
  expired: { background: 'color-mix(in srgb, var(--db-accent-red) 15%, transparent)', color: 'var(--db-accent-red)' },
};

const defaultStyle: React.CSSProperties = { background: 'var(--db-surface-alt)', color: 'var(--db-text-muted)' };

export const WcBadge: React.FC<WcBadgeProps> = ({ value, size = 'sm', className }) => {
  const style = statusStyles[value?.toLowerCase()] || defaultStyle;
  const sizeClass = size === 'sm' ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2 py-0.5';

  return (
    <span className={`inline-block rounded-full font-medium ${sizeClass} ${className || ''}`} style={style}>
      {value || '—'}
    </span>
  );
};
