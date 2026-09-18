/**
 * LayoutPreviewRenderers — shared preview components for layout parade tools.
 *
 * Extracted from ComponentParade.tsx for reuse in LayoutWorkbench.
 *
 * LastChecked: 2026-09-14 | WhereUsed: ComponentParade, LayoutWorkbench | WhoCreated: Bill+Claude
 */

export interface LayoutItem {
  name: string;
  kind: string;
  columns?: number;
  fields?: number;
  tabs?: number;
  has_header?: boolean;
  has_lines?: boolean;
  spec: any;
}

export interface ModelGroup {
  model: string;
  singular: string;
  kind: string;
  items: LayoutItem[];
}

export interface ParadeData {
  type: string;
  total_models: number;
  total_items: number;
  models: ModelGroup[];
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Get a nested value from a record using dot notation */
export function getNestedValue(record: any, path: string): any {
  if (!record || !path) return undefined;
  const parts = path.split(".");
  let val = record;
  for (const p of parts) {
    if (val == null || typeof val !== "object") return undefined;
    val = val[p];
  }
  return val;
}

/** Format a value for display */
export function formatValue(val: any): string {
  if (val == null) return "";
  if (typeof val === "boolean") return val ? "Yes" : "No";
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
}

/** Count summary for an item */
export function itemSummary(item: LayoutItem): string {
  if (item.columns != null) return `${item.columns} col`;
  if (item.fields != null) return `${item.fields} fields`;
  if (item.tabs != null) return `${item.tabs} tabs`;
  return "";
}

/* ------------------------------------------------------------------ */
/*  Preview Renderers                                                  */
/* ------------------------------------------------------------------ */

/** Render a panel or list layout as a table with sample data */
export function PanelPreview({ item, records }: { item: LayoutItem; records: any[] }) {
  const columns: any[] =
    item.kind === "panel"
      ? (Array.isArray(item.spec) ? item.spec : [])
      : (item.spec?.columns || []);

  if (!columns.length) {
    return <div className="sp-empty"><p>No columns defined</p></div>;
  }

  return (
    <div className="sp-table-scroll">
      <table className="sp-table">
        <thead>
          <tr>
            {columns.map((col: any, i: number) => (
              <th key={i} className={col.width ? "sp-col-fixed" : undefined}
                  style={col.width ? { width: col.width } : undefined}>
                {col.label || col.field}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {records.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="sp-no-records">
                No records available for preview
              </td>
            </tr>
          ) : (
            records.map((rec, ri) => (
              <tr key={ri}>
                {columns.map((col: any, ci: number) => (
                  <td key={ci}>{formatValue(getNestedValue(rec, col.field))}</td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

/** Render a detail layout showing the field structure with one record */
export function DetailPreview({ item, records }: { item: LayoutItem; records: any[] }) {
  const spec = item.spec || {};
  const sections = spec.sections;
  const fields = spec.fields;
  const record = records[0] || {};

  // DynamicDetail sections format
  if (sections && typeof sections === "object" && !Array.isArray(sections)) {
    const cols = sections.columns || [];
    return (
      <div>
        {sections.layout && (
          <div className="sp-item-meta sp-section-meta">
            <span className="sp-purpose-tag">layout: {sections.layout}</span>
          </div>
        )}
        <div className="sp-detail-columns">
          {cols.map((col: any, ci: number) => (
            <div key={ci} className="sp-detail-column">
              {col.title && (
                <div className="sp-section-title">{col.title}</div>
              )}
              <table className="sp-table">
                <tbody>
                  {(col.fields || []).map((f: any, fi: number) => (
                    <tr key={fi}>
                      <td className="sp-field-name sp-field-label">
                        {f.label || f.field}
                      </td>
                      <td>{formatValue(getNestedValue(record, f.field))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Simple fields list
  if (Array.isArray(fields) && fields.length > 0) {
    return (
      <table className="sp-table">
        <thead>
          <tr>
            <th>field</th>
            <th>value</th>
          </tr>
        </thead>
        <tbody>
          {fields.map((f: any, i: number) => {
            const fieldName = typeof f === "string" ? f : f.field || f.name;
            const label = typeof f === "string" ? f : f.label || f.field;
            return (
              <tr key={i}>
                <td className="sp-field-name">{label}</td>
                <td>{formatValue(getNestedValue(record, fieldName))}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    );
  }

  // Fallback — show spec as JSON
  return (
    <pre className="sp-json-fallback">
      {JSON.stringify(spec, null, 2)}
    </pre>
  );
}

/** Render a card layout showing the card fields with one record */
export function CardPreview({ item, records }: { item: LayoutItem; records: any[] }) {
  const spec = item.spec || {};
  const fields = spec.fields || [];
  const record = records[0] || {};

  return (
    <div className="sp-card-preview">
      {spec.title && (
        <div className="sp-card-title">
          {spec.title}
        </div>
      )}
      {fields.length > 0 ? (
        <table className="sp-table sp-card-table">
          <tbody>
            {fields.map((f: any, i: number) => (
              <tr key={i}>
                <td className="sp-field-name sp-field-label">
                  {f.label || f.field}
                </td>
                <td>{formatValue(getNestedValue(record, f.field))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="sp-detail-text">No fields defined</div>
      )}
    </div>
  );
}

/** Render a single DynamicDetail-style section (header, panel, etc.) */
function FormSection({ sec, index, record }: { sec: any; index: number; record: any }) {
  const sectionType = sec.type || "unknown";
  const sectionTitle = sec.title || sec.content || sectionType;
  const cols = sec.columns || [];

  // Sections with columns and fields — render like detail view
  if (cols.length > 0) {
    return (
      <div className="sp-section">
        <div className="sp-section-title">
          {sectionTitle}
          {sec.layout && (
            <span className="sp-purpose-tag" style={{ marginLeft: 8 }}>
              {sec.layout}
            </span>
          )}
        </div>
        <div className="sp-detail-columns">
          {cols.map((col: any, ci: number) => (
            <div key={ci} className="sp-detail-column">
              {col.title && (
                <div className="sp-section-title">{col.title}</div>
              )}
              <table className="sp-table">
                <tbody>
                  {(col.fields || []).map((f: any, fi: number) => (
                    <tr key={fi}>
                      <td className="sp-field-name sp-field-label">
                        {f.label || f.field}
                      </td>
                      <td>
                        {f.type === "readonly" && (
                          <span className="sp-widget-badge readonly" style={{ marginRight: 4 }}>ro</span>
                        )}
                        {formatValue(getNestedValue(record, f.field))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Sections without columns — show type badge
  return (
    <div className="sp-form-section">
      <span className="sp-widget-badge default" style={{ marginRight: 6 }}>
        {sectionType}
      </span>
      <span className="sp-form-section-title">
        {sectionTitle !== sectionType ? sectionTitle : ""}
      </span>
    </div>
  );
}

/** Render a form layout showing structure with one record */
export function FormPreview({ item, records }: { item: LayoutItem; records: any[] }) {
  const spec = item.spec || {};
  const record = records[0] || {};

  // DynamicDetail sections array — the standard form structure
  if (spec.sections && Array.isArray(spec.sections) && spec.sections.length > 0) {
    return (
      <div>
        {spec.model && (
          <div className="sp-item-meta sp-section-meta">
            <span className="sp-purpose-tag">model: {spec.model}</span>
            {spec.family && (
              <span className="sp-purpose-tag">family: {spec.family}</span>
            )}
          </div>
        )}
        {spec.sections.map((sec: any, i: number) => (
          <FormSection key={i} sec={sec} index={i} record={record} />
        ))}
        {spec.edit_rules && (
          <div className="sp-section">
            <div className="sp-section-title">edit rules</div>
            <pre className="sp-json-fallback">
              {JSON.stringify(spec.edit_rules, null, 2)}
            </pre>
          </div>
        )}
      </div>
    );
  }

  // Legacy format: header.cards + tabs + lines
  return (
    <div>
      {spec.header && (
        <div className="sp-section">
          <div className="sp-section-title">header</div>
          <div className="sp-item-meta sp-section-meta">
            <span className="sp-purpose-tag">layout: {spec.header.layout || "default"}</span>
          </div>
          {spec.header.cards && (
            <div className="sp-header-cards">
              {spec.header.cards.map((cardName: string, i: number) => (
                <div key={i} className="sp-header-card-chip">
                  {cardName}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      {spec.lines && (
        <div className="sp-section">
          <div className="sp-section-title">lines</div>
          <div className="sp-item-meta">
            <span className="sp-purpose-tag">family: {spec.lines.family || "—"}</span>
            {spec.lines.toolbar && (
              <span className="sp-purpose-tag">
                toolbar: {spec.lines.toolbar.join(", ")}
              </span>
            )}
          </div>
        </div>
      )}
      {spec.tabs && Array.isArray(spec.tabs) && spec.tabs.length > 0 && (
        <div className="sp-section">
          <div className="sp-section-title">tabs ({spec.tabs.length})</div>
          <div className="sp-tabs-row">
            {spec.tabs.map((tab: any, i: number) => (
              <div
                key={i}
                className={`sp-tab-chip${i === 0 ? " sp-tab-active" : ""}`}
              >
                {tab.label || tab.content || `tab ${i}`}
              </div>
            ))}
          </div>
        </div>
      )}
      {spec.edit_rules && (
        <div className="sp-section">
          <div className="sp-section-title">edit rules</div>
          <pre className="sp-json-fallback">
            {JSON.stringify(spec.edit_rules, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

/** Build the Setting path for this layout item */
export function settingPath(model: string, item: LayoutItem): string {
  const kind = item.kind;
  const name = item.name;
  if (kind === "panel") return `setting.config.layout.panel`;
  if (kind === "column") return `setting.config.layout.column.${name}`;
  return `setting.config.layout.${kind}.${name}`;
}

/** Dispatch to the right preview renderer based on item.kind */
export function LayoutPreview({ item, records }: { item: LayoutItem; records: any[] }) {
  switch (item.kind) {
    case "panel":
    case "column":
    case "list":
      return <PanelPreview item={item} records={records} />;
    case "detail":
      return <DetailPreview item={item} records={records} />;
    case "card":
      return <CardPreview item={item} records={records} />;
    case "form":
      return <FormPreview item={item} records={records} />;
    default:
      return (
        <pre className="sp-json-fallback">
          {JSON.stringify(item.spec, null, 2)}
        </pre>
      );
  }
}
