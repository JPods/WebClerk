import React from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';

export default function ReadonlyField(props: FieldWidgetProps) {
  const { name, value } = props;
  const display = (name.startsWith('dt_') && typeof value === 'number')
    ? new Date(value).toLocaleString()
    : String(value ?? '--');
  return (
    <BaseField props={props} labelColor="readonly">
      <div className="db-input db-input--readonly">{display}</div>
    </BaseField>
  );
}
