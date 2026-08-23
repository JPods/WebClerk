/* LastChecked: 2026-08-18 | WhereUsed: TransactionDetail, OrgDetail | WhoCreated: Claude */
/**
 * JsonSectionRenderer — renders JSON envelope fields in a collapsible panel.
 *
 * Uses JsonTree from JsonTreeWidget for each JSON field on the record.
 * Collapsed by default — users expand to inspect raw data.
 */
import React from 'react';
import type { JsonTreeSection } from '@/hooks/useDetailLayout';
import { JsonTree } from '@/components/widgets/JsonTreeWidget';
import CollapsiblePanel from '@/apps/common/components/CollapsiblePanel';

// Default JSON envelope fields to show when section.fields is not specified
const DEFAULT_JSON_FIELDS = [
  'config', 'metadata', 'prefs', 'refs', 'comments', 'actions',
  'totals', 'sell', 'cost', 'tax', 'financial', 'metrics',
  'connections', 'relations', 'quantity', 'physical',
];

interface JsonSectionRendererProps {
  section: JsonTreeSection;
  data: any;
  isEditing: boolean;
  modelName: string;
  onChange?: (field: string, value: unknown) => void;
}

const JsonSectionRenderer: React.FC<JsonSectionRendererProps> = ({
  section, data, isEditing, modelName, onChange,
}) => {
  const fieldList = section.fields || DEFAULT_JSON_FIELDS;

  // Only show fields that exist on the record and have content
  const activeFields = fieldList.filter(f => {
    const val = data?.[f];
    return val != null && (typeof val === 'object' ? Object.keys(val).length > 0 : true);
  });

  if (activeFields.length === 0) return null;

  return (
    <CollapsiblePanel
      label={section.label || 'Data'}
      storageKey={`panel_${modelName}_json_tree`}
      defaultCollapsed={section.collapsed ?? true}
      badge={activeFields.length}
    >
      <div className="space-y-2">
        {activeFields.map(field => (
          <JsonTree
            key={field}
            label={field}
            data={data[field]}
            readOnly={!isEditing}
            defaultExpanded={false}
            maxHeight="none"
            onChange={isEditing && onChange ? (val) => onChange(field, val) : undefined}
          />
        ))}
      </div>
    </CollapsiblePanel>
  );
};

export default JsonSectionRenderer;
