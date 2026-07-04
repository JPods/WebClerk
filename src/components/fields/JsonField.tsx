import React, { useCallback, useState } from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';

export default function JsonField(props: FieldWidgetProps & { rows?: number; model?: string; recordId?: number }) {
  const { name, value, onChange, disabled, rows, model, recordId } = props;
  const js = JSON.stringify(value, null, 2);
  const rowCount = rows || (js.length > 200 ? 8 : 3);
  const [editing, setEditing] = useState(false);

  const openViewer = useCallback(() => {
    const params = new URLSearchParams();
    if (model) params.set('model', model);
    if (recordId) params.set('id', String(recordId));
    params.set('field', name);
    if (js.length < 2000) {
      params.set('json', js);
    }
    window.open(`/json-viewer?${params.toString()}`, '_blank',
      'width=700,height=600,menubar=no,toolbar=no');
  }, [name, js, model, recordId]);

  const keyCount = typeof value === 'object' && value !== null
    ? (Array.isArray(value) ? value.length : Object.keys(value).length)
    : 0;

  const labelSuffix = Array.isArray(value) ? `[${keyCount}]` : `{${keyCount}}`;

  if (!editing) {
    return (
      <BaseField props={{ ...props, span2: true }} labelColor="actionable"
        labelOnClick={openViewer} labelSuffix={<span className="db-json-count">{labelSuffix}</span>}>
        <div className="db-json-summary">
          <span className="db-json-preview" onClick={openViewer} title="Click to open JSON viewer">
            {Array.isArray(value) ? `[${keyCount} items]` : `{${keyCount} keys}`}
          </span>
          {!disabled && <button className="db-json-btn" onClick={() => setEditing(true)} title="Edit raw JSON">Edit</button>}
        </div>
      </BaseField>
    );
  }

  return (
    <BaseField props={{ ...props, span2: true }} labelColor="actionable"
      labelOnClick={openViewer} labelSuffix={<span className="db-json-count">{labelSuffix}</span>}>
      <textarea className="db-input db-input--mono db-input--textarea" rows={rowCount} value={js}
        onChange={(e) => { try { onChange(JSON.parse(e.target.value)); } catch { /* typing */ } }}
        disabled={disabled} />
      <div className="db-json-summary">
        <button className="db-json-btn" onClick={() => setEditing(false)}>Done</button>
      </div>
    </BaseField>
  );
}
