import { useState } from 'react';
import type { FieldWidgetProps } from './types';
import BaseField from './BaseField';

/** Money entered or applied shows .00 (Bill, 2026-11-03). The input shows the amount to the cent
 *  until it is focused; while typing it shows what was typed; on blur it is money again. */
export default function CurrencyField(props: FieldWidgetProps) {
  const { value, onChange, disabled } = props;
  const [draft, setDraft] = useState<string | null>(null);
  const shown = draft ?? (value != null && value !== '' && !isNaN(Number(value)) ? Number(value).toFixed(2) : '');
  return (
    <BaseField props={props}>
      <div className="db-currency-wrap">
        <span className="db-currency-symbol">$</span>
        <input className="db-input db-input--mono db-input--right" type="number" step="0.01"
          value={shown}
          onFocus={() => setDraft(value != null && value !== '' ? String(value) : '')}
          onChange={(e) => { setDraft(e.target.value); onChange(parseFloat(e.target.value) || 0); }}
          onBlur={() => setDraft(null)}
          disabled={disabled} />
      </div>
    </BaseField>
  );
}
