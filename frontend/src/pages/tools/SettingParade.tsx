/**
 * SettingParade — reference tool for browsing Setting records.
 *
 * Research tool, not operational. Users come here to understand what
 * Settings exist, what they control, and whether they understand them.
 * Same parade pattern as FormParade: left list grouped by purpose,
 * right panel shows what each Setting controls.
 *
 * LastChecked: 2026-08-25 | WhereUsed: /setting-parade | WhoCreated: Bill+Claude
 */
import { useEffect, useState } from "react";
import PageMeta from "@/components/common/PageMeta";
import apiClient from "../../api/axios";
import { getPjpvFieldsCatalog, type PjpvFieldMeta } from "@/api/wcapi";
import "./SettingParade.css";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface SettingFeedback {
  choice: "understood" | "needs_work" | "dont_understand";
  notes: string;
}

interface SettingSummary {
  behavior_count?: number;
  select_fields?: string[];
  selectlist_count?: number;
  selectlist_fields?: string[];
  field_group_count?: number;
  default_count?: number;
  list_field_count?: number;
  detail_field_count?: number;
}

interface ParadeSetting {
  id: number;
  ida: string;
  name: string;
  parent_model: string;
  purpose: string;
  explanation: string;
  summary: SettingSummary;
  feedback: SettingFeedback | null;
}

interface ParadeGroup {
  name: string;
  description: string;
  settings: ParadeSetting[];
  count: number;
}

interface ParadeManifest {
  groups: ParadeGroup[];
  total_settings: number;
  reviewed_count: number;
}

interface SettingPreview {
  id: number;
  ida: string;
  name: string;
  parent_model: string;
  purpose: string;
  explanation: string;
  scope: string;
  behaviors?: Record<string, any>;
  selectlists?: Record<string, any[]>;
  field_groups?: any[];
  list_layout?: string[];
  detail_layout?: string[];
  defaults?: Record<string, any>;
  profile_ref_count?: number;
  feedback: SettingFeedback | null;
}

/* ------------------------------------------------------------------ */
/*  Purpose → explanation of use                                       */
/* ------------------------------------------------------------------ */

const PURPOSE_EXPLANATIONS: Record<string, string> = {
  'wc:model':
    'Controls how fields render for this model — widget types (select, currency, text), ' +
    'labels, precision, readonly flags, and select list options. ' +
    'When you open a record of this model, these behaviors determine what the form looks like.',
  'wc:list_column_config':
    'Defines which columns appear in the list view for this model, their order, and widths. ' +
    'Users see this layout when browsing records in the DataBrowser.',
  'wc:workbench_fields':
    'Controls which fields appear in the list and detail views of the DataBrowser workbench. ' +
    'Separate from column config — this determines field visibility, not just column order.',
  'wc:field_access':
    'Role-based field visibility and edit rules. Determines which fields each role can see ' +
    'and edit. A field hidden here will not appear in the form regardless of other settings.',
};

function getUseExplanation(purpose: string, hasSelectlists: boolean): string {
  const base = PURPOSE_EXPLANATIONS[purpose];
  if (base) return base;
  if (purpose && purpose.includes('defaults'))
    return 'Default values for new records of this model. When a user creates a new record, these values pre-fill the form.';
  if (hasSelectlists)
    return 'Contains select list options. These populate dropdown fields. ' +
      'Records can point to this Setting via config.selectlist_profile for category-specific options.';
  return 'Configuration record. Check the explanation field and JSON contents for details on what this Setting controls.';
}

/* ------------------------------------------------------------------ */
/*  Label helper — show full path for reference clarity                */
/* ------------------------------------------------------------------ */

function fieldLabel(field: string): string {
  // Reference tool — always show the full path so users know
  // whether a field is a scalar (name) or envelope leaf (price.unit)
  return field;
}

function isEnvelopeLeaf(field: string): boolean {
  return field.includes('.');
}

/* ------------------------------------------------------------------ */
/*  Sort helper                                                        */
/* ------------------------------------------------------------------ */

function sortedEntries(obj: Record<string, any>): [string, any][] {
  return Object.entries(obj).sort(([a], [b]) => a.localeCompare(b));
}

/* ------------------------------------------------------------------ */
/*  Preview sub-components                                             */
/* ------------------------------------------------------------------ */

const FieldGroupsSection: React.FC<{ groups: any[] }> = ({ groups }) => (
  <div className="sp-section">
    <h3 className="sp-section-title">field groups ({groups.length})</h3>
    {groups.map((g: any, i: number) => (
      <div key={i} className="sp-fg-item">
        <span className="sp-fg-label">{g.label || g.name || `group ${i + 1}`}</span>
        {g.fields && (
          <span className="sp-fg-fields">
            {Array.isArray(g.fields) ? g.fields.join(', ') : ''}
          </span>
        )}
      </div>
    ))}
  </div>
);

const BehaviorsTable: React.FC<{ behaviors: Record<string, any> }> = ({ behaviors }) => {
  // Separate scalar fields from envelope leaves, group leaves by envelope
  const scalars: [string, any][] = [];
  const envelopes: Record<string, [string, any][]> = {};

  for (const [field, beh] of sortedEntries(behaviors)) {
    if (isEnvelopeLeaf(field)) {
      const envelope = field.split('.')[0];
      if (!envelopes[envelope]) envelopes[envelope] = [];
      envelopes[envelope].push([field, beh]);
    } else {
      scalars.push([field, beh]);
    }
  }

  const scalarCount = scalars.length;
  const leafCount = Object.values(envelopes).reduce((n, a) => n + a.length, 0);

  // Build unified list: scalars and envelope groups interleaved alphabetically
  type Row = { kind: 'scalar'; field: string; beh: any } | { kind: 'envelope'; name: string; leaves: [string, any][] };
  const rows: Row[] = [];
  for (const [field, beh] of scalars) rows.push({ kind: 'scalar', field, beh });
  for (const [name, leaves] of Object.entries(envelopes)) rows.push({ kind: 'envelope', name, leaves });
  rows.sort((a, b) => {
    const aKey = a.kind === 'scalar' ? a.field : a.name;
    const bKey = b.kind === 'scalar' ? b.field : b.name;
    return aKey.localeCompare(bKey);
  });

  return (
    <div className="sp-section">
      <h3 className="sp-section-title">
        field behaviors ({scalarCount} fields · {leafCount} JSON leaves)
      </h3>
      <table className="sp-table">
        <thead>
          <tr>
            <th>field</th>
            <th>widget</th>
            <th>details</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) =>
            row.kind === 'scalar'
              ? <BehaviorRow key={row.field} field={row.field} beh={row.beh} />
              : <EnvelopeGroup key={row.name} envelope={row.name} leaves={row.leaves} />
          )}
        </tbody>
      </table>
    </div>
  );
};

const BehaviorRow: React.FC<{ field: string; beh: any; leaf?: boolean }> = ({ field, beh, leaf }) => {
  const widgetClass = ['select', 'currency', 'readonly'].includes(beh.type)
    ? beh.type : 'default';
  const details: string[] = [];
  if (beh.precision != null) details.push(`precision: ${beh.precision}`);
  if (beh.readonly) details.push('readonly');
  if (beh.selectlist_key) details.push(`key: ${beh.selectlist_key}`);
  if (beh.options?.length) details.push(`${beh.options.length} options`);
  return (
    <tr className={leaf ? 'sp-envelope-leaf' : ''}>
      <td className="sp-field-name">{field}</td>
      <td><span className={`sp-widget-badge ${widgetClass}`}>{beh.type || 'text'}</span></td>
      <td className="sp-detail-text">{details.join(' · ')}</td>
    </tr>
  );
};

const EnvelopeGroup: React.FC<{ envelope: string; leaves: [string, any][] }> = ({ envelope, leaves }) => (
  <>
    <tr className="sp-envelope-header">
      <td className="sp-field-name sp-envelope-name">
        {envelope}.*
      </td>
      <td><span className="sp-widget-badge default">json</span></td>
      <td className="sp-detail-text">{leaves.length} leaves</td>
    </tr>
    {leaves.map(([field, beh]) => (
      <BehaviorRow key={field} field={field} beh={beh} leaf />
    ))}
  </>
);

const SelectlistsSection: React.FC<{ selectlists: Record<string, any[]> }> = ({ selectlists }) => {
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <div className="sp-section">
      <h3 className="sp-section-title">select lists ({Object.keys(selectlists).length})</h3>
      {sortedEntries(selectlists).map(([field, opts]) => (
        <div key={field} className="sp-sl-item">
          <button
            className="sp-sl-header"
            onClick={() => setExpanded(expanded === field ? null : field)}
          >
            <span className="sp-sl-field">{fieldLabel(field)}</span>
            <span className="sp-sl-count">
              {Array.isArray(opts) ? opts.length : 0} options {expanded === field ? '▾' : '▸'}
            </span>
          </button>
          {expanded === field && Array.isArray(opts) && (
            <div className="sp-sl-body">
              <table className="sp-sl-table">
                <thead>
                  <tr><th>value</th><th>label</th></tr>
                </thead>
                <tbody>
                  {opts.map((opt: any, i: number) => (
                    <tr key={i}>
                      <td>{opt.value}</td>
                      <td>{opt.label}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="sp-tryit">
                <span className="sp-tryit-label">try it:</span>
                <select className="sp-tryit-select" defaultValue="">
                  <option value="">-- select --</option>
                  {opts.map((opt: any, i: number) => (
                    <option key={i} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};

const LayoutPreview: React.FC<{ fields: string[]; label: string }> = ({ fields, label }) => (
  <div className="sp-section">
    <h3 className="sp-section-title">{label} ({fields.length} fields)</h3>
    <div className="sp-layout-chips">
      {fields.map((f, i) => (
        <span key={i} className="sp-layout-chip">{f}</span>
      ))}
    </div>
  </div>
);

const DefaultsTable: React.FC<{ defaults: Record<string, any> }> = ({ defaults }) => (
  <div className="sp-section">
    <h3 className="sp-section-title">defaults ({Object.keys(defaults).length})</h3>
    <table className="sp-table">
      <thead>
        <tr><th>field</th><th>default value</th></tr>
      </thead>
      <tbody>
        {sortedEntries(defaults).map(([field, val]) => (
          <tr key={field}>
            <td className="sp-field-name">{fieldLabel(field)}</td>
            <td>{typeof val === 'object' ? JSON.stringify(val) : String(val)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

const PjpvEnvelopesSection: React.FC<{ catalog: Record<string, Record<string, PjpvFieldMeta>> }> = ({ catalog }) => {
  const [expanded, setExpanded] = useState<string | null>(null);

  const envelopes = sortedEntries(catalog);
  if (!envelopes.length) return null;

  return (
    <div className="sp-section">
      <h3 className="sp-section-title">JSON envelope schemas ({envelopes.length})</h3>
      {envelopes.map(([envName, fields]) => {
        const fieldEntries = sortedEntries(fields);
        return (
          <div key={envName} className="sp-sl-item">
            <button
              className="sp-sl-header"
              onClick={() => setExpanded(expanded === envName ? null : envName)}
            >
              <span className="sp-sl-field">{envName}</span>
              <span className="sp-sl-count">
                {fieldEntries.length} fields {expanded === envName ? '▾' : '▸'}
              </span>
            </button>
            {expanded === envName && (
              <div className="sp-sl-body">
                <table className="sp-table">
                  <thead>
                    <tr>
                      <th>field</th>
                      <th>type</th>
                      <th>widget</th>
                      <th>details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fieldEntries.map(([fieldName, meta]) => {
                      const m = meta as PjpvFieldMeta;
                      const widgetClass = ['select', 'currency', 'readonly'].includes(m.widget)
                        ? m.widget : 'default';
                      const details: string[] = [];
                      if (m.precision != null) details.push(`precision: ${m.precision}`);
                      if (m.readonly) details.push('readonly');
                      if (m.selectlist_key) details.push(`key: ${m.selectlist_key}`);
                      if (m.min != null) details.push(`min: ${m.min}`);
                      if (m.max != null) details.push(`max: ${m.max}`);
                      if (m.description) details.push(m.description);
                      return (
                        <tr key={fieldName}>
                          <td className="sp-field-name">{envName}.{fieldName}</td>
                          <td className="sp-detail-text">{m.type}</td>
                          <td><span className={`sp-widget-badge ${widgetClass}`}>{m.widget}</span></td>
                          <td className="sp-detail-text">{details.join(' · ')}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

const SettingParade: React.FC = () => {
  const [manifest, setManifest] = useState<ParadeManifest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSetting, setSelectedSetting] = useState<ParadeSetting | null>(null);
  const [preview, setPreview] = useState<SettingPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [pjpvCatalog, setPjpvCatalog] = useState<Record<string, Record<string, PjpvFieldMeta>>>({});
  const [feedbackMap, setFeedbackMap] = useState<Record<number, SettingFeedback>>({});
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    apiClient
      .get("/wcapi/_setting_parade_manifest/")
      .then((res) => {
        const data: ParadeManifest = res.data?.data ?? res.data;
        setManifest(data);
        const initial: Record<number, SettingFeedback> = {};
        for (const g of data.groups) {
          for (const s of g.settings) {
            if (s.feedback) initial[s.id] = s.feedback;
          }
        }
        setFeedbackMap(initial);
      })
      .catch((err) => {
        setError(err?.response?.data?.detail ?? "Failed to load manifest");
      })
      .finally(() => setLoading(false));

    // Load PJPV catalog (cached per session)
    getPjpvFieldsCatalog().then(setPjpvCatalog).catch(() => {});
  }, []);

  const handleSelect = (s: ParadeSetting) => {
    setSelectedSetting(s);
    setNotes(feedbackMap[s.id]?.notes ?? "");
    setPreviewLoading(true);
    apiClient
      .get(`/wcapi/_setting_parade_preview/?setting_id=${s.id}`)
      .then((res) => setPreview(res.data?.data ?? res.data))
      .catch(() => setPreview(null))
      .finally(() => setPreviewLoading(false));
  };

  const handleFeedback = async (choice: SettingFeedback["choice"]) => {
    if (!selectedSetting) return;
    setSaving(true);
    try {
      await apiClient.post("/wcapi/_setting_parade_feedback/", {
        setting_id: selectedSetting.id,
        feedback: choice,
        notes,
      });
      setFeedbackMap((prev) => ({
        ...prev,
        [selectedSetting.id]: { choice, notes },
      }));
    } catch (err: any) {
      console.error("Feedback save failed:", err);
    } finally {
      setSaving(false);
    }
  };

  const feedbackLabel = (choice: string) => {
    switch (choice) {
      case "understood": return "understood";
      case "needs_work": return "needs work";
      case "dont_understand": return "don't understand";
      default: return choice;
    }
  };

  const summaryText = (s: SettingSummary) => {
    const parts: string[] = [];
    if (s.field_group_count) parts.push(`${s.field_group_count} groups`);
    if (s.behavior_count) parts.push(`${s.behavior_count} behaviors`);
    if (s.selectlist_count) parts.push(`${s.selectlist_count} lists`);
    if (s.list_field_count) parts.push(`${s.list_field_count} list cols`);
    if (s.detail_field_count) parts.push(`${s.detail_field_count} detail fields`);
    if (s.default_count) parts.push(`${s.default_count} defaults`);
    return parts.join(' · ') || 'empty';
  };

  const currentFeedback = selectedSetting ? feedbackMap[selectedSetting.id] : null;

  if (loading) {
    return (
      <div className="sp-empty" style={{ height: '100vh' }}>
        <p className="big">loading settings...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="sp-empty" style={{ height: '100vh' }}>
        <p className="big">{error}</p>
      </div>
    );
  }

  const hasSelectlists = preview?.selectlists && Object.keys(preview.selectlists).length > 0;

  return (
    <>
      <PageMeta title="Setting Parade" description="PJPV configuration reference" />

      <div className="sp-container">
        {/* Header */}
        <div className="sp-header">
          <h1>setting parade</h1>
          {manifest && (
            <span className="sp-header-stats">
              {manifest.total_settings} settings | {Object.keys(feedbackMap).length} reviewed
            </span>
          )}
        </div>

        <div className="sp-main">
          {/* Left panel */}
          <div className="sp-left">
            {manifest?.groups.map((group) => (
              <div key={group.name}>
                <div className="sp-group-header">
                  <h2 className="sp-group-title">{group.name}</h2>
                  <p className="sp-group-desc">{group.description}</p>
                </div>
                {group.settings.map((s) => {
                  const fb = feedbackMap[s.id];
                  const isSelected = selectedSetting?.id === s.id;
                  return (
                    <button
                      key={s.id}
                      onClick={() => handleSelect(s)}
                      className={`sp-item${isSelected ? ' selected' : ''}`}
                    >
                      <div className="sp-item-row">
                        <span className="sp-item-name">{s.name || s.ida}</span>
                        {fb && (
                          <span className={`sp-item-badge ${fb.choice}`} title={feedbackLabel(fb.choice)}>
                            {fb.choice === 'understood' ? '✓' : fb.choice === 'needs_work' ? '✎' : '?'}
                          </span>
                        )}
                      </div>
                      <div className="sp-item-meta">
                        {s.parent_model && <span className="sp-item-model">{s.parent_model}</span>}
                        <span className="sp-item-purpose">{s.purpose}</span>
                      </div>
                      <div className="sp-item-summary">{summaryText(s.summary)}</div>
                    </button>
                  );
                })}
              </div>
            ))}
          </div>

          {/* Right panel */}
          <div className="sp-right">
            {/* Toolbar */}
            {selectedSetting && (
              <div className="sp-toolbar">
                <span className="sp-toolbar-name">{selectedSetting.name || selectedSetting.ida}</span>
                <div className="sp-toolbar-divider" />
                <button
                  onClick={() => handleFeedback("understood")}
                  disabled={saving}
                  className={`sp-fb-btn understood${currentFeedback?.choice === 'understood' ? ' active' : ''}`}
                >understood</button>
                <button
                  onClick={() => handleFeedback("needs_work")}
                  disabled={saving}
                  className={`sp-fb-btn needs_work${currentFeedback?.choice === 'needs_work' ? ' active' : ''}`}
                >needs work</button>
                <button
                  onClick={() => handleFeedback("dont_understand")}
                  disabled={saving}
                  className={`sp-fb-btn dont_understand${currentFeedback?.choice === 'dont_understand' ? ' active' : ''}`}
                >don't understand</button>
                <div className="sp-toolbar-divider" />
                <input
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="notes..."
                  className="sp-notes-input"
                />
                {currentFeedback && (
                  <span className="sp-toolbar-status">{feedbackLabel(currentFeedback.choice)}</span>
                )}
                {saving && <span className="sp-toolbar-status">saving...</span>}
              </div>
            )}

            {/* Preview */}
            <div className="sp-preview">
              {previewLoading ? (
                <div className="sp-empty"><p className="big">loading...</p></div>
              ) : preview ? (
                <div className="sp-preview-content">
                  {/* Identity */}
                  <div className="sp-identity">
                    <div className="sp-identity-row">
                      <span className="sp-ida">{preview.ida}</span>
                      {preview.parent_model && <span className="sp-model-tag">{preview.parent_model}</span>}
                      <span className="sp-purpose-tag">{preview.purpose}</span>
                      <span className="sp-scope-tag">scope: {preview.scope}</span>
                    </div>
                    {preview.explanation && (
                      <p className="sp-explanation">{preview.explanation}</p>
                    )}
                    {preview.profile_ref_count != null && preview.profile_ref_count > 0 && (
                      <p className="sp-profile-refs">
                        {preview.profile_ref_count} record{preview.profile_ref_count !== 1 ? 's' : ''} use this as their selectlist_profile
                      </p>
                    )}
                    {/* Explanation of use */}
                    <div className="sp-use-explanation">
                      {getUseExplanation(preview.purpose, !!hasSelectlists)}
                    </div>
                  </div>

                  {/* Field groups — at the top */}
                  {preview.field_groups && preview.field_groups.length > 0 && (
                    <FieldGroupsSection groups={preview.field_groups} />
                  )}

                  {/* Behaviors */}
                  {preview.behaviors && Object.keys(preview.behaviors).length > 0 && (
                    <BehaviorsTable behaviors={preview.behaviors} />
                  )}

                  {/* Select lists */}
                  {hasSelectlists && (
                    <SelectlistsSection selectlists={preview.selectlists!} />
                  )}

                  {/* Layouts */}
                  {preview.list_layout && preview.list_layout.length > 0 && (
                    <LayoutPreview fields={preview.list_layout} label="list layout" />
                  )}
                  {preview.detail_layout && preview.detail_layout.length > 0 && (
                    <LayoutPreview fields={preview.detail_layout} label="detail layout" />
                  )}

                  {/* Defaults */}
                  {preview.defaults && Object.keys(preview.defaults).length > 0 && (
                    <DefaultsTable defaults={preview.defaults} />
                  )}

                  {/* PJPV JSON envelope schemas — show all envelopes from the catalog */}
                  {Object.keys(pjpvCatalog).length > 0 && (
                    <PjpvEnvelopesSection catalog={pjpvCatalog} />
                  )}

                  {/* Empty */}
                  {!preview.behaviors && !hasSelectlists && !preview.list_layout &&
                   !preview.detail_layout && !preview.defaults && !preview.field_groups && (
                    <div className="sp-empty">
                      <div>
                        <p className="big">empty setting</p>
                        <p className="small">no behaviors, select lists, layouts, or defaults in this record's JSON</p>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="sp-empty">
                  <div>
                    <p className="big">select a setting to preview</p>
                    <p className="small">click any setting in the left panel to see what it controls</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default SettingParade;
