/* LastChecked: 2026-08-02 | WhereUsed: All views | WhoCreated: Claude */
/**
 * WcButton — standard button for all WC3 views.
 * Supports variants: primary, secondary, danger, ghost.
 * Can show icon + label or icon only.
 */
import React from 'react';

export interface WcButtonProps {
  label?: string;
  icon?: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  loading?: boolean;
  onClick?: () => void;
  title?: string;
  className?: string;
}

const variants = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700 border-blue-600',
  secondary: 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 border-slate-300 dark:border-slate-600',
  danger: 'bg-white dark:bg-slate-800 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 border-red-300 dark:border-red-700',
  ghost: 'bg-transparent text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 border-transparent',
};

const sizes = {
  sm: 'px-2 py-1 text-xs gap-1',
  md: 'px-3 py-1.5 text-sm gap-1.5',
  lg: 'px-4 py-2 text-sm gap-2',
};

export const WcButton: React.FC<WcButtonProps> = ({
  label, icon, variant = 'secondary', size = 'md',
  disabled, loading, onClick, title, className,
}) => (
  <button
    type="button"
    onClick={onClick}
    disabled={disabled || loading}
    title={title || label}
    className={`
      inline-flex items-center justify-center font-medium rounded border
      transition-colors duration-150
      disabled:opacity-50 disabled:cursor-not-allowed
      ${variants[variant]} ${sizes[size]} ${className || ''}
    `.trim()}
  >
    {loading ? (
      <span className="animate-spin w-3 h-3 border-2 border-current border-t-transparent rounded-full" />
    ) : icon ? (
      <span className="shrink-0">{icon}</span>
    ) : null}
    {label && <span>{label}</span>}
  </button>
);
