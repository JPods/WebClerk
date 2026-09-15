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

const variantStyles: Record<string, React.CSSProperties> = {
  primary: { background: 'var(--db-btn-primary)', color: '#fff', borderColor: 'var(--db-btn-primary)' },
  secondary: { background: 'var(--db-btn-bg)', color: 'var(--db-text)', borderColor: 'var(--db-border)' },
  danger: { background: 'var(--db-btn-bg)', color: 'var(--db-accent-red)', borderColor: 'var(--db-btn-danger-border)' },
  ghost: { background: 'transparent', color: 'var(--db-text-muted)', borderColor: 'transparent' },
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
      ${sizes[size]} ${className || ''}
    `.trim()}
    style={variantStyles[variant]}
  >
    {loading ? (
      <span className="animate-spin w-3 h-3 border-2 border-current border-t-transparent rounded-full" />
    ) : icon ? (
      <span className="shrink-0">{icon}</span>
    ) : null}
    {label && <span>{label}</span>}
  </button>
);
