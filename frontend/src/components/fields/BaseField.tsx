/**
 * BaseField — shared wrapper for all field widgets.
 * Handles: label rendering, error display, span2 layout, disabled state,
 * Shift-for-Help on all labels, Cmd+Shift+click for behavior override (admin).
 */
import React, { useState } from 'react';
import type { FieldWidgetProps } from './types';
import { openFieldHelp } from '../common/HelpMenu';
import BehaviorOverrideDialog from './BehaviorOverrideDialog';

interface BaseFieldRenderProps {
  props: FieldWidgetProps;
  labelColor?: string;      // CSS class suffix: actionable, select, lookup, readonly, default
  labelSuffix?: React.ReactNode;
  labelHref?: string;
  labelOnClick?: () => void; // for behaviors like JSON → open viewer
  model?: string;           // model name for Shift-for-Help + data-wc-model
  children: React.ReactNode;
}

export default function BaseField({ props, labelColor = 'default', labelSuffix, labelHref, labelOnClick, model: modelOverride, children }: BaseFieldRenderProps) {
  const { name, label, error, className, span2, model: propsModel } = props;
  const displayLabel = label || name;
  const model = modelOverride || propsModel;
  const [behaviorOpen, setBehaviorOpen] = useState(false);

  const [behaviorPreset, setBehaviorPreset] = useState<string | undefined>(undefined);

  const handleLabelClick = (e: React.MouseEvent) => {
    // Cmd+Shift+click → full behavior override dialog (admin)
    if ((e.metaKey || e.ctrlKey) && e.shiftKey) {
      e.preventDefault();
      e.stopPropagation();
      setBehaviorPreset(undefined);
      setBehaviorOpen(true);
      return;
    }
    // Cmd/Ctrl+click → launch action (dial/email/map) or select list editor
    if (e.metaKey || e.ctrlKey) {
      e.preventDefault();
      e.stopPropagation();
      if (labelHref) {
        window.open(labelHref, '_blank', 'noopener,noreferrer');
      } else {
        setBehaviorPreset('select');
        setBehaviorOpen(true);
      }
      return;
    }
    // Shift+click → field help
    if (e.shiftKey) {
      e.preventDefault();
      e.stopPropagation();
      openFieldHelp(model || 'system', name);
      return;
    }
    if (labelOnClick) labelOnClick();
  };

  const handleLabelMouseDown = (e: React.MouseEvent) => {
    if (e.shiftKey) e.preventDefault();
  };

  const linkColor = labelHref ? 'actionable' : labelColor;
  const labelEl = (
    <span className={`db-label db-label--${linkColor}`}
      onMouseDown={handleLabelMouseDown} onClick={handleLabelClick}
      title={labelHref ? `Cmd+click: ${labelHref.startsWith('tel:') ? 'dial' : labelHref.startsWith('mailto:') ? 'email' : 'open'}` : undefined}
      style={labelOnClick || labelHref ? { cursor: 'pointer' } : undefined}>
      {displayLabel}{labelSuffix && <> {labelSuffix}</>}
    </span>
  );

  const wcAttrs: Record<string, string> = { 'data-wc': `field-${name}`, 'data-wc-field': name };
  if (model) wcAttrs['data-wc-model'] = model;

  return (
    <div className={`db-field ${span2 ? 'db-field--span2' : ''} ${className || ''}`} {...wcAttrs}>
      {labelEl}
      {children}
      {error && <div className="db-field-error">{error}</div>}
      {behaviorOpen && model && (
        <BehaviorOverrideDialog
          open={behaviorOpen}
          onClose={() => { setBehaviorOpen(false); setBehaviorPreset(undefined); }}
          onReload={() => window.dispatchEvent(new CustomEvent('wc:reload-behaviors'))}
          model={model}
          fieldName={name}
          presetType={behaviorPreset}
        />
      )}
    </div>
  );
}
