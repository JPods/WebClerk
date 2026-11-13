/* LastChecked: 2026-08-18 | WhereUsed: TransactionDetail, OrgDetail | WhoCreated: Claude */
/**
 * JsonSectionRenderer — the form's json panel: every JSON object the record's model has that
 * the viewer may see (Bill, 2026-11-12: list all objects in the panel rather than fold them
 * into metadata, prefs or refs).
 *
 * The list is the server's: GET /wcapi/<model>/fields/ → json_objects, the model's JSON columns
 * with at least one leaf this role may view. The layout's json_tree section only orders them
 * (`fields`: those first, in that order) and hides them (`hide`). A form whose layout has no
 * json_tree section gets the panel at its end (DbForm). Only objects with content are drawn.
 */
import React, { useEffect, useState } from 'react';
import type { JsonTreeSection } from '@/hooks/useDetailLayout';
import { JsonTree } from '@/components/widgets/JsonTreeWidget';
import CollapsiblePanel from '@/apps/common/components/CollapsiblePanel';
import { getJsonObjects } from '@/api/wcapi';

const cache = new Map<string, Promise<string[]>>();

/** The model's JSON objects this viewer may see, once per model per page load. */
export function loadJsonObjects(modelName: string): Promise<string[]> {
  if (!cache.has(modelName)) {
    cache.set(modelName, getJsonObjects(modelName).catch((err) => { cache.delete(modelName); throw err; }));
  }
  return cache.get(modelName)!;
}

/** The panel's list: the layout's order first, then the rest as the model has them; hidden ones out.
 *  A name the layout lists that the server does not give (not the model's, or not this role's) is dropped. */
export function orderedObjects(available: string[], order: string[] = [], hide: string[] = []): string[] {
  const first = order.filter((f) => available.includes(f));
  return [...first, ...available.filter((f) => !first.includes(f))].filter((f) => !hide.includes(f));
}

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
  const [available, setAvailable] = useState<string[] | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  useEffect(() => {
    let stale = false;
    setAvailable(null); setFailed(null);
    loadJsonObjects(modelName)
      .then((names) => { if (!stale) setAvailable(names); })
      .catch((err) => { if (!stale) setFailed(err?.message || 'request failed'); });
    return () => { stale = true; };
  }, [modelName]);

  if (failed) {
    return <div className="px-2 py-1 db-font-sm" style={{ color: 'var(--db-accent-red, #dc3545)' }}
      data-wc="json-panel-error">The json panel could not read this model's objects: {failed}</div>;
  }
  if (available === null) return null;
  const fieldList = orderedObjects(available, section.fields, section.hide);

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
