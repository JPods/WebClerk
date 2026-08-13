import React from 'react';
import type { SelectFieldProps } from './types';
import BaseField from './BaseField';

interface SelectFieldFullProps extends SelectFieldProps {
  allowCustom?: boolean;    // enable freehand text input alongside dropdown
}

export default function SelectField(props: SelectFieldFullProps) {
  const { value, onChange, disabled, options, allowCustom } = props;
  const currentVal = String(value ?? '');
  const inList = options.some((o) => o.value === currentVal);

  if (allowCustom) {
    return (
      <BaseField props={props} labelColor="select">
        <div className="db-select-custom-wrap">
          <select className="db-input db-input--select"
            value={inList ? currentVal : '__custom__'}
            onChange={(e) => { if (e.target.value !== '__custom__') onChange(e.target.value); }}
            disabled={disabled}>
            <option value="">--</option>
            {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            {!inList && currentVal && <option value="__custom__">{currentVal}</option>}
            <option value="__custom__">other...</option>
          </select>
          {(!inList || currentVal === '') && (
            <input className="db-input" value={currentVal}
              onChange={(e) => onChange(e.target.value)}
              placeholder="type here" disabled={disabled} />
          )}
        </div>
      </BaseField>
    );
  }

  return (
    <BaseField props={props} labelColor="select">
      <select className="db-input db-input--select" value={currentVal}
        onChange={(e) => onChange(e.target.value)} disabled={disabled}>
        <option value="">--</option>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </BaseField>
  );
}
