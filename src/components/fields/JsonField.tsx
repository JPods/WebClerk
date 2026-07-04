import React from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';

export default function JsonField(props: FieldWidgetProps & { rows?: number }) {
  const { value, onChange, disabled, rows } = props;
  const js = JSON.stringify(value, null, 2);
  const rowCount = rows || (js.length > 200 ? 8 : 3);
  return (
    <BaseField props={{ ...props, span2: true }}>
      <textarea className="db-input db-input--mono db-input--textarea" rows={rowCount} value={js}
        onChange={(e) => { try { onChange(JSON.parse(e.target.value)); } catch { /* typing in progress */ } }}
        disabled={disabled} />
    </BaseField>
  );
}
