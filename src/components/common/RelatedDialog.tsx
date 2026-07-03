/**
 * RelatedDialog — shows models related to the current DataBrowser model.
 *
 * Data source: Settings with purpose='model_related' and parent_model={currentModel}.
 * Each Setting has data.related[] with entries like:
 *   { model, label, fk, fk_field, type, filter }
 *
 * Clicking a related model opens a new DataBrowser window filtered to show
 * related records.
 *
 * LastChecked: 2026-06-30 | WhereUsed: AdminWorkbench | WhoCreated: Bill+Claude
 */
import React, { useEffect, useState } from 'react';
import { fetchLatestSettingRecord } from '@/api/settingsBridge';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface RelatedEntry {
  model: string;
  label: string;
  fk?: string;
  fk_field?: string;
  type: 'children' | 'parent' | 'refs';
  filter?: Record<string, string>;
}

interface RelatedSettingData {
  related: RelatedEntry[];
}

interface Props {
  open: boolean;
  model: string;
  /** Currently selected record (detail context) or null (list context) */
  selectedRecord: Record<string, unknown> | null;
  /** Set of selected row IDs (list context) */
  selectedRowIds: Set<number>;
  theme: {
    bg: string; surface: string; surfaceAlt: string;
    border: string; borderLight: string;
    text: string; textMuted: string; textDim: string;
    accent: string; accentGreen: string; accentRed: string; accentPurple: string;
    [k: string]: string;
  };
  fontSize: number;
  onClose: () => void;
}

// ---------------------------------------------------------------------------
// Type badge colors
// ---------------------------------------------------------------------------

const TYPE_BADGES: Record<string, { label: string; bg: string; color: string }> = {
  children: { label: 'Children', bg: '#1a6b2e', color: '#fff' },
  parent:   { label: 'Parent',   bg: '#0e639c', color: '#fff' },
  refs:     { label: 'Refs',     bg: '#555',    color: '#ccc' },
};

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const RelatedDialog: React.FC<Props> = ({ open, model, selectedRecord, selectedRowIds, theme: t, fontSize, onClose }) => {
  const [entries, setEntries] = useState<RelatedEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState('');

  // Fetch related config when model changes
  useEffect(() => {
    if (!open || !model || loaded === model) return;
    setLoading(true);
    fetchLatestSettingRecord<RelatedSettingData>({
      purpose: 'model_related',
      parent_model: model,
    }).then((rec) => {
      setEntries(rec?.data?.related || []);
      setLoaded(model);
    }).catch(() => {
      setEntries([]);
      setLoaded(model);
    }).finally(() => setLoading(false));
  }, [open, model, loaded]);

  // Reset when model changes
  useEffect(() => { setLoaded(''); }, [model]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;

  const handleClick = (entry: RelatedEntry) => {
    // Build the URL for the related model
    let url = `/admin-wb?model=${encodeURIComponent(entry.model)}`;

    // For now, open the related model — filtering can be enhanced later
    // Parent type: navigate to the parent record
    if (entry.type === 'parent' && selectedRecord && entry.fk_field) {
      const parentId = selectedRecord[entry.fk_field];
      if (parentId) {
        url += `&id=${parentId}`;
      }
    }

    window.open(url, '_blank');
    onClose();
  };

  return (
    // Backdrop
    <div data-wc="related-dialog-backdrop"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      style={{
        position: 'fixed', inset: 0, zIndex: 9000,
        background: 'rgba(0,0,0,0.5)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
      {/* Dialog */}
      <div data-wc="related-dialog"
        style={{
          background: t.surface, border: `1px solid ${t.border}`,
          borderRadius: 8, width: 420, maxHeight: '70vh',
          display: 'flex', flexDirection: 'column',
          boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
        }}>
        {/* Header */}
        <div style={{
          padding: '12px 16px', borderBottom: `1px solid ${t.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <span style={{ fontWeight: 700, fontSize: fontSize + 1, color: t.accent }}>
            Related to {model}
          </span>
          <button onClick={onClose} style={{
            background: 'none', border: 'none', color: t.textMuted,
            fontSize: 18, cursor: 'pointer', padding: '0 4px',
          }}>&times;</button>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
          {loading && (
            <div style={{ padding: '16px', color: t.textMuted, textAlign: 'center' }}>
              Loading...
            </div>
          )}
          {!loading && entries.length === 0 && (
            <div style={{ padding: '24px 16px', color: t.textDim, textAlign: 'center' }}>
              No relationships configured
            </div>
          )}
          {!loading && entries.map((entry, i) => {
            const badge = TYPE_BADGES[entry.type] || TYPE_BADGES.refs;
            return (
              <div key={`${entry.model}-${i}`}
                data-wc="related-dialog-row"
                onClick={() => handleClick(entry)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '10px 16px', cursor: 'pointer',
                  borderBottom: i < entries.length - 1 ? `1px solid ${t.borderLight}` : 'none',
                  transition: 'background 0.1s',
                }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = t.surfaceAlt; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
              >
                {/* Type badge */}
                <span style={{
                  padding: '2px 8px', borderRadius: 3, fontSize: fontSize - 2,
                  fontWeight: 700, background: badge.bg, color: badge.color,
                  flexShrink: 0, minWidth: 60, textAlign: 'center',
                }}>{badge.label}</span>

                {/* Label and model name */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, color: t.text, fontSize }}>{entry.label}</div>
                  <div style={{ fontSize: fontSize - 2, color: t.textMuted }}>{entry.model}{entry.fk ? ` (${entry.fk})` : entry.fk_field ? ` (${entry.fk_field})` : ''}</div>
                </div>

                {/* Arrow */}
                <span style={{ color: t.textDim, fontSize: fontSize + 2 }}>&rarr;</span>
              </div>
            );
          })}
        </div>

        {/* Footer context */}
        <div style={{
          padding: '8px 16px', borderTop: `1px solid ${t.border}`,
          fontSize: fontSize - 2, color: t.textMuted,
        }}>
          {selectedRecord ? `Record #${(selectedRecord as any).id || '?'}` : `${selectedRowIds.size} selected`}
          {' '}&middot; Opens in new window
        </div>
      </div>
    </div>
  );
};

export default RelatedDialog;
