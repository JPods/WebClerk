/**
 * CardRenderer — renders a single card from its JSON spec.
 *
 * Pure JSON cards render as FieldRow grids. Cards with a registered
 * component delegate to that component, passing the default field
 * rendering as children. Footers render below the fields.
 *
 * Uses --db-* CSS variables so cards follow the DataBrowser theme
 * (light or dark) without Tailwind dark: prefix.
 */
import React from 'react';
import FieldRow from '@/apps/transactions/components/detail/FieldRow';
import { getCardComponent, getFooterComponent } from './cardRegistry';
import type { CardSpec, CardComponentProps } from './cardRegistry';

interface CardRendererProps {
  spec: CardSpec;
  data: any;
  isEditing: boolean;
  onChange: (field: string, value: unknown) => void;
}

const CardRenderer: React.FC<CardRendererProps> = ({ spec, data, isEditing, onChange }) => {
  const CardComponent = spec.component ? getCardComponent(spec.component) : undefined;
  const FooterComponent = spec.footer ? getFooterComponent(spec.footer) : undefined;

  // Title bar
  const titleIdaValue = spec.title_ida && data?.[spec.title_ida];
  const titleBar = (
    <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--db-text)', marginBottom: 8, borderBottom: '1px solid var(--db-border)', paddingBottom: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
      <span>{spec.title}</span>
      {titleIdaValue != null && (
        <span style={{ fontFamily: 'monospace', color: 'var(--db-text-muted)', fontWeight: 400, fontSize: '10px' }}>
          #{typeof titleIdaValue === 'object' ? titleIdaValue.id : titleIdaValue}
        </span>
      )}
    </div>
  );

  // Default field rendering
  const fieldRows = spec.fields.map((f) => (
    <FieldRow
      key={f.field}
      field={f.field}
      label={f.label || f.field.split('.').pop() || f.field}
      data={data}
      isEditing={isEditing}
      options={f.options}
      fieldType={f.type}
      help={f.help}
      onChange={onChange}
    />
  ));

  // Card shell — uses CSS variables for theme-aware styling
  return (
    <div style={{
      background: 'var(--db-surface)',
      borderRadius: 8,
      border: '1px solid var(--db-border)',
      padding: 12,
      color: 'var(--db-text)',
    }}>
      {titleBar}
      {CardComponent ? (
        <CardComponent spec={spec} data={data} isEditing={isEditing} onChange={onChange}>
          {fieldRows}
        </CardComponent>
      ) : (
        fieldRows
      )}
      {FooterComponent && (
        <FooterComponent spec={spec} data={data} isEditing={isEditing} onChange={onChange} />
      )}
    </div>
  );
};

export default CardRenderer;
