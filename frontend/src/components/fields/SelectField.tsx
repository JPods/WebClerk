import React from 'react';
import type { SelectFieldProps } from './types';
import BaseField from './BaseField';

interface SelectFieldFullProps extends SelectFieldProps {
  allowCustom?: boolean;    // enable freehand text input alongside dropdown
}

export default function SelectField(props: SelectFieldFullProps) {
  const { value, onChange, disabled, options, allowCustom } = props;
  // Handle object values (e.g. assigned_to: {"en": "Bill"}) — serialize for comparison
  const isObjectValue = typeof value === 'object' && value !== null;
  const currentVal = isObjectValue ? JSON.stringify(value) : String(value ?? '');
  const inList = options.some((o) => o.value === currentVal);
  // When value is an object, parse the selected option back to an object
  const handleChange = isObjectValue
    ? (raw: string) => { try { onChange(JSON.parse(raw)); } catch { onChange(raw); } }
    : onChange;

  if (allowCustom) {
    return (
      <BaseField props={props} labelColor="select">
        <div className="db-select-custom-wrap">
          <select className="db-input db-input--select"
            value={inList ? currentVal : '__custom__'}
            onChange={(e) => { if (e.target.value !== '__custom__') handleChange(e.target.value); }}
            disabled={disabled}>
            <option value="">--</option>
            {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            {!inList && currentVal && <option value="__custom__">{currentVal}</option>}
            <option value="__custom__">other...</option>
          </select>
          {(!inList || currentVal === '') && (
            <input className="db-input" value={currentVal}
              onChange={(e) => handleChange(e.target.value)}
              placeholder="type here" disabled={disabled} />
          )}
        </div>
      </BaseField>
    );
  }

  // Parse comma-separated values for multi-select display
  const selectedValues = currentVal ? currentVal.split(',').map(s => s.trim()).filter(Boolean) : [];

  const handleSelect = (e: React.MouseEvent<HTMLSelectElement>) => {
    const select = e.currentTarget;
    const clickedValue = select.options[select.selectedIndex]?.value;
    if (!clickedValue) { handleChange(''); return; }

    if (e.metaKey || e.ctrlKey) {
      // Cmd/Ctrl+click: toggle the clicked value in/out of the list
      const idx = selectedValues.indexOf(clickedValue);
      const next = idx >= 0
        ? selectedValues.filter(v => v !== clickedValue)
        : [...selectedValues, clickedValue];
      handleChange(next.join(', '));
      e.preventDefault();
    } else {
      // Plain click: replace with single value
      handleChange(clickedValue);
    }
  };

  return (
    <BaseField props={props} labelColor="select">
      <select className="db-input db-input--select" value={currentVal}
        onClick={handleSelect}
        onChange={(e) => handleChange(e.target.value)} disabled={disabled}>
        <option value="">--</option>
        {options.map((o) => {
          const isSelected = selectedValues.includes(o.value);
          return <option key={o.value} value={o.value} style={isSelected && selectedValues.length > 1 ? { fontWeight: 'bold' } : undefined}>{isSelected && selectedValues.length > 1 ? '✓ ' : ''}{o.label}</option>;
        })}
      </select>
    </BaseField>
  );
}
