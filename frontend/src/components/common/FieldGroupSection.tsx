/* FieldGroupSection — collapsible detail field group for DataBrowser.
   Matches JsonEnvelopePanel visual style: chevron + UPPERCASE label + count. */
import React, { useCallback } from 'react';

export type FieldGroup = {
  key: string;
  label: string;
  fields: string[];
};

type Theme = {
  text: string;
  textMuted: string;
  border: string;
  surfaceAlt: string;
  inputBg: string;
};

type Props = {
  group: FieldGroup;
  /** Fields from group.fields that actually exist on the record */
  presentFields: string[];
  collapsed: boolean;
  onToggle: (key: string) => void;
  fontSize: number;
  theme: Theme;
  children: React.ReactNode;
};

export default function FieldGroupSection({ group, presentFields, collapsed, onToggle, fontSize, theme: th, children }: Props) {
  const handleClick = useCallback(() => onToggle(group.key), [onToggle, group.key]);

  return (
    <div style={{ borderBottom: `1px solid ${th.border}` }}>
      <div
        style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '6px 12px',
          background: th.surfaceAlt, cursor: 'pointer', userSelect: 'none',
        }}
        onClick={handleClick}
        data-help={`${group.label} — ${presentFields.length} fields. Click to ${collapsed ? 'expand' : 'collapse'}.`}
      >
        <svg width="10" height="10" viewBox="0 0 10 10" fill="none" stroke={th.textMuted} strokeWidth="1.5">
          {collapsed ? <path d="M3 1 L7 5 L3 9" /> : <path d="M1 3 L5 7 L9 3" />}
        </svg>
        <span style={{ fontSize: fontSize - 1, fontWeight: 600, color: th.textMuted, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
          {group.label}
        </span>
        <span style={{ fontSize: fontSize - 2, color: th.textMuted, fontWeight: 400 }}>
          ({presentFields.length})
        </span>
      </div>
      {!collapsed && (
        <div className="db-detail-grid" style={{ padding: '4px 0' }}>
          {children}
        </div>
      )}
    </div>
  );
}
