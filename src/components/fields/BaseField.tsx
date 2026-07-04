/**
 * BaseField — shared wrapper for all field widgets.
 * Handles: label rendering, error display, span2 layout, disabled state.
 */
import React from 'react';
import type { FieldWidgetProps } from './types';

interface BaseFieldRenderProps {
  props: FieldWidgetProps;
  labelColor?: string;      // CSS class suffix: actionable, select, lookup, readonly, default
  labelSuffix?: React.ReactNode;
  labelHref?: string;
  children: React.ReactNode;
}

export default function BaseField({ props, labelColor = 'default', labelSuffix, labelHref, children }: BaseFieldRenderProps) {
  const { name, label, error, className, span2 } = props;
  const displayLabel = label || name;

  const labelEl = labelHref ? (
    <a href={labelHref} target={labelHref.startsWith('http') ? '_blank' : undefined} rel="noopener noreferrer"
      className={`db-label db-label--${labelColor}`}>
      {displayLabel}{labelSuffix && <> {labelSuffix}</>}
    </a>
  ) : (
    <span className={`db-label db-label--${labelColor}`}>
      {displayLabel}{labelSuffix && <> {labelSuffix}</>}
    </span>
  );

  return (
    <div className={`db-field ${span2 ? 'db-field--span2' : ''} ${className || ''}`} data-wc={`field-${name}`} data-wc-field={name}>
      {labelEl}
      {children}
      {error && <div className="db-field-error">{error}</div>}
    </div>
  );
}
