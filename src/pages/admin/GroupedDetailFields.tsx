/* LastChecked: 2026-08-14 | WhereUsed: DataBrowser detail pane (admin mode) | WhoCreated: Bill+Claude */
import React from 'react';
import BehaviorField from '../../components/common/BehaviorField';
import FieldGroupSection from '../../components/common/FieldGroupSection';
import type { FieldSpec } from '../../hooks/useDataBrowser';

// ---------------------------------------------------------------------------
// GroupedDetailFields — renders BehaviorFields in collapsible groups
// ---------------------------------------------------------------------------

export type GroupedDetailFieldsProps = {
  fields: string[];
  record: Record<string, unknown>;
  fieldGroups: { key: string; label: string; fields: string[] }[];
  collapsedKeys: string[];
  onToggleGroup: (key: string) => void;
  fieldBehaviors: Record<string, any>;
  detailFieldSpecs: FieldSpec[];
  detailRowSizes: Record<string, number>;
  validationErrors: Record<string, string>;
  updateField: (field: string, value: unknown) => void;
  fontSize: number;
  theme: any;
};

/** Resolve a dot-path (e.g. "comments.process") to a value in a record. */
function resolveDotPath(record: Record<string, unknown>, path: string): unknown {
  if (!path.includes('.')) return record[path];
  return path.split('.').reduce((o: any, k: string) => o?.[k], record);
}

/** Check if a dot-path field is present in a record (top-level key or nested path). */
function fieldPresent(record: Record<string, unknown>, field: string): boolean {
  if (Object.prototype.hasOwnProperty.call(record, field)) return true;
  if (!field.includes('.')) return false;
  const root = field.split('.')[0];
  return Object.prototype.hasOwnProperty.call(record, root) && resolveDotPath(record, field) !== undefined;
}

export function GroupedDetailFields({ fields, record, fieldGroups, collapsedKeys, onToggleGroup, fieldBehaviors, detailFieldSpecs, detailRowSizes, validationErrors, updateField, fontSize, theme }: GroupedDetailFieldsProps) {
  const presentFields = fields.filter((f) => fieldPresent(record, f));
  const groupTheme = { text: theme.text, textMuted: theme.textMuted, border: theme.border, surfaceAlt: theme.surfaceAlt, inputBg: theme.inputBg };

  const renderField = (f: string) => (
    <BehaviorField key={f} name={f} value={resolveDotPath(record, f)} behavior={fieldBehaviors[f] || {}}
      onChange={(v: unknown) => updateField(f, v)} record={record}
      fontSize={fontSize} theme={theme} rowSize={detailRowSizes[f]}
      typeHint={detailFieldSpecs.find(s => s.field === f)?.typeHint}
      error={validationErrors[f]} />
  );

  // No groups defined — flat layout (backward compatible)
  if (!fieldGroups.length) {
    return <div className="db-detail-grid">{presentFields.map(renderField)}</div>;
  }

  // Partition fields into groups — preserve user's detail order within each group
  const fieldOrder = new Map(presentFields.map((f, i) => [f, i]));
  const assigned = new Set<string>();
  const groups = fieldGroups.map(g => {
    const gFields = g.fields
      .filter(f => presentFields.includes(f))
      .sort((a, b) => (fieldOrder.get(a) ?? 999) - (fieldOrder.get(b) ?? 999));
    gFields.forEach(f => assigned.add(f));
    return { ...g, presentFields: gFields };
  }).filter(g => g.presentFields.length > 0);

  const ungrouped = presentFields.filter(f => !assigned.has(f));

  return (
    <div>
      {groups.map(g => (
        <FieldGroupSection
          key={g.key}
          group={g}
          presentFields={g.presentFields}
          collapsed={collapsedKeys.includes(g.key)}
          onToggle={onToggleGroup}
          fontSize={fontSize}
          theme={groupTheme}
        >
          {g.presentFields.map(renderField)}
        </FieldGroupSection>
      ))}
      {ungrouped.length > 0 && (
        <FieldGroupSection
          group={{ key: '_other', label: 'Other', fields: ungrouped }}
          presentFields={ungrouped}
          collapsed={collapsedKeys.includes('_other')}
          onToggle={onToggleGroup}
          fontSize={fontSize}
          theme={groupTheme}
        >
          {ungrouped.map(renderField)}
        </FieldGroupSection>
      )}
    </div>
  );
}

export default GroupedDetailFields;
