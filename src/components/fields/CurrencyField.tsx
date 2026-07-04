import React from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';

export default function CurrencyField(props: FieldWidgetProps) {
  const { value, onChange, disabled } = props;
  return (
    <BaseField props={props}>
      <div className="db-currency-wrap">
        <span className="db-currency-symbol">$</span>
        <input className="db-input db-input--mono db-input--right" type="number" step="0.01"
          value={value != null ? value : ''} onChange={(e) => onChange(parseFloat(e.target.value) || 0)} disabled={disabled} />
      </div>
    </BaseField>
  );
}
