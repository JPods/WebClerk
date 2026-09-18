import React from 'react';
import type { GeoFieldProps } from './types';
import BaseField from './BaseField';

export default function GeoField(props: GeoFieldProps) {
  const { name, value, onChange, disabled, pair, record } = props;
  const lat = name === 'latitude' ? value : record?.[pair || ''];
  const lng = name === 'longitude' ? value : record?.[pair || ''];
  const mapUrl = lat && lng ? `https://maps.google.com/?q=${lat},${lng}` : undefined;
  return (
    <BaseField props={props} labelColor="actionable" labelHref={mapUrl}>
      <input className="db-input db-input--mono" type="number" step="any"
        value={value != null ? value : ''} onChange={(e) => onChange(parseFloat(e.target.value) || 0)} disabled={disabled} />
    </BaseField>
  );
}
