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

const statusColors: Record<string, string> = {
  open: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  active: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  created: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
  planned: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
  draft: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
  'in progress': 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  in_progress: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  journalized: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  released: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
  shipped: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
  received: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
  applied: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  cancelled: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  void: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  closed: 'bg-slate-200 text-slate-500 dark:bg-slate-600 dark:text-slate-300',
  expired: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400',
};

const defaultColor = 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300';

export const WcBadge: React.FC<WcBadgeProps> = ({ value, size = 'sm', className }) => {
  const color = statusColors[value?.toLowerCase()] || defaultColor;
  const sizeClass = size === 'sm' ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2 py-0.5';

  return (
    <span className={`inline-block rounded-full font-medium ${sizeClass} ${color} ${className || ''}`}>
      {value || '—'}
    </span>
  );
};
