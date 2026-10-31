import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';
import { formatDt } from '@/utils/fieldFormatters';

export default function TimestampField(props: FieldWidgetProps) {
  const { value, name } = props;
  const dateOnly = formatDt(value, 'date', name);
  const fullDatetime = formatDt(value, 'datetime', name);
  return (
    <BaseField props={props} labelColor="readonly">
      <div className="db-input db-input--readonly" title={fullDatetime}>{dateOnly}</div>
    </BaseField>
  );
}
