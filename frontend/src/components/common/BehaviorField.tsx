/**
 * BehaviorField — dispatches to the field widget registry.
 *
 * Thin wrapper: maps behavior config to renderField() from components/fields/.
 * All rendering is done by individual widget components.
 */
import React from 'react';
import { renderField } from '@/components/fields';

interface BehaviorFieldProps {
  name: string;
  value: unknown;
  behavior: Record<string, any>;
  onChange: (value: unknown) => void;
  record?: Record<string, unknown>;
  fontSize?: number;
  theme?: Record<string, string>;  // kept for API compat; CSS vars drive styling
  rowSize?: number;
  error?: string;
  leaf?: { type: string; extract?: string };
}

export default function BehaviorField({
  name, value, behavior, onChange, record, rowSize, error, leaf,
}: BehaviorFieldProps) {
  const wcModel = (record as any)?._model || '';

  return renderField(name, value, behavior, onChange, {
    error,
    record,
    model: wcModel,
    rowSize,
    leaf,
    span2: undefined, // let renderField auto-detect from type
  });
}
