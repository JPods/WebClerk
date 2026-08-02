/* LastChecked: 2026-08-02 | WhereUsed: All views | WhoCreated: Claude */
/**
 * WcIconButton — icon-only button with tooltip.
 * Used in toolbars, line card footer, panel headers.
 */
import React from 'react';

export interface WcIconButtonProps {
  icon: React.ReactNode;
  label: string;  // used as tooltip
  active?: boolean;
  variant?: 'default' | 'primary' | 'danger' | 'success';
  size?: 'sm' | 'md';
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
}

const variantStyles = {
  default: {
    base: 'text-slate-500 hover:text-slate-700 hover:bg-slate-100 dark:text-slate-400 dark:hover:text-slate-200 dark:hover:bg-slate-700',
    active: 'bg-blue-600 text-white',
  },
  primary: {
    base: 'text-slate-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20',
    active: 'bg-blue-600 text-white',
  },
  danger: {
    base: 'text-slate-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20',
    active: 'bg-red-600 text-white',
  },
  success: {
    base: 'text-slate-500 hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20',
    active: 'bg-green-600 text-white',
  },
};

export const WcIconButton: React.FC<WcIconButtonProps> = ({
  icon, label, active, variant = 'default', size = 'md',
  onClick, disabled, className,
}) => {
  const styles = variantStyles[variant];
  const sizeClass = size === 'sm' ? 'w-6 h-6 text-xs' : 'w-8 h-8 text-sm';

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={label}
      className={`
        inline-flex items-center justify-center rounded transition-colors
        disabled:opacity-50 disabled:cursor-not-allowed
        ${active ? styles.active : styles.base}
        ${sizeClass} ${className || ''}
      `.trim()}
    >
      {icon}
    </button>
  );
};
