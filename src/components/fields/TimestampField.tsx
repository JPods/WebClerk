import React from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';
import { formatDt } from '@/utils/fieldFormatters';

export default function TimestampField(props: FieldWidgetProps) {
  const { value, field } = props;
  const display = formatDt(value, 'datetime', field);
  return (
    <BaseField props={props} labelColor="readonly">
      <div className="db-input db-input--readonly">{display}</div>
    </BaseField>
  );
}
