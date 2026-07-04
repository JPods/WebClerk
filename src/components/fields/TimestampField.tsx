import React from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';

export default function TimestampField(props: FieldWidgetProps) {
  const { value } = props;
  const display = value ? new Date(value as number).toLocaleString() : '--';
  return (
    <BaseField props={props} labelColor="readonly">
      <div className="db-input db-input--readonly">{display}</div>
    </BaseField>
  );
}
