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

const cssVarStyles: Record<string, { base: React.CSSProperties; active: React.CSSProperties }> = {
  default: {
    base: { color: 'var(--db-text-muted)' },
    active: { background: 'var(--db-btn-primary)', color: '#fff' },
  },
  primary: {
    base: { color: 'var(--db-text-muted)' },
    active: { background: 'var(--db-btn-primary)', color: '#fff' },
  },
  danger: {
    base: { color: 'var(--db-text-muted)' },
    active: { background: 'var(--db-btn-danger)', color: '#fff' },
  },
  success: {
    base: { color: 'var(--db-text-muted)' },
    active: { background: 'var(--db-btn-save)', color: '#fff' },
  },
};

export const WcIconButton: React.FC<WcIconButtonProps> = ({
  icon, label, active, variant = 'default', size = 'md',
  onClick, disabled, className,
}) => {
  const styles = cssVarStyles[variant];
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
        ${sizeClass} ${className || ''}
      `.trim()}
      style={active ? styles.active : styles.base}
    >
      {icon}
    </button>
  );
};
