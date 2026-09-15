import React from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';
import { formatDt } from '@/utils/fieldFormatters';

export default function ReadonlyField(props: FieldWidgetProps) {
  const { name, value } = props;
  const display = (name.startsWith('dt_') && typeof value === 'number')
    ? formatDt(value, 'datetime', name)
    : String(value ?? '--');
  return (
    <BaseField props={props} labelColor="readonly">
      <div className="db-input db-input--readonly">{display}</div>
    </BaseField>
  );
}
