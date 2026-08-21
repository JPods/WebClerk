/**
 * BehaviorOverrideDialog — admin tool for reviewing and overriding field behaviors.
 *
 * Opened via Cmd+Shift+click on any field label in the DataBrowser.
 * Shows the computed behavior (from Django model metadata) alongside any
 * stored override (from the wc:model Setting). Admin can change the type,
 * add select options, or set a custom label. Changes save to
 * Setting.config.behaviors as overrides — the service function stays
 * authoritative for everything not overridden.
 *
 * Admin-only. Non-admin users never see this dialog.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { getRecords, saveRecord } from '@/api/wcapi';

const WIDGET_TYPES = [
  'text', 'number', 'currency', 'email', 'phone', 'url', 'address', 'zip',
  'select', 'lookup', 'boolean', 'date', 'timestamp', 'json', 'json-tree',
  'textarea', 'readonly', 'geo', 'hidden', 'editor',
];

interface BehaviorOverrideDialogProps {
  open: boolean;
  onClose: () => void;
  onReload?: () => void;  // invalidate DataBrowser behavior cache after save
  model: string;
  fieldName: string;
}

interface BehaviorSpec {
  type?: string;
  action?: string;
  options?: { value: string; label: string }[];
  model?: string;
  display?: string;
  label?: string;
  pair?: string;
  source?: string;
  [key: string]: unknown;
}

export default function BehaviorOverrideDialog({ open, onClose, onReload, model, fieldName }: BehaviorOverrideDialogProps) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [settingId, setSettingId] = useState<number | null>(null);
  const [computed, setComputed] = useState<BehaviorSpec>({});
  const [override, setOverride] = useState<BehaviorSpec>({});
  const [editType, setEditType] = useState('');
  const [editAction, setEditAction] = useState('');
  const [editLabel, setEditLabel] = useState('');
  const [editOptions, setEditOptions] = useState('');
  const [editLookupModel, setEditLookupModel] = useState('');
  const [message, setMessage] = useState('');

  // Load computed + stored behaviors
  useEffect(() => {
    if (!open || !model || !fieldName) return;
    let cancelled = false;
    setLoading(true);
    setMessage('');

    (async () => {
      try {
        // Fetch the wc:model Setting
        const res = await getRecords('setting', { parent_model: model, purpose: 'wc:model', limit: 1 }) as any;
        if (cancelled) return;
        const rec = (res?.results || [])[0];
        const behaviors = rec?.config?.behaviors || {};
        const fieldBehavior = behaviors[fieldName] || {};

        setSettingId(rec?.id || null);
        setComputed(fieldBehavior);

        // Check if there's a stored override that differs
        // For now, show what's stored as both computed and override
        setOverride(fieldBehavior);
        setEditType(fieldBehavior.type || '');
        setEditAction(fieldBehavior.action || '');
        setEditLabel(fieldBehavior.label || '');
        setEditLookupModel(fieldBehavior.model || '');
        if (fieldBehavior.options && Array.isArray(fieldBehavior.options)) {
          setEditOptions(fieldBehavior.options.map((o: any) => `${o.value}:${o.label}`).join('\n'));
        } else {
          setEditOptions('');
        }
      } catch {
        setMessage('Failed to load behaviors');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [open, model, fieldName]);

  const handleSave = useCallback(async () => {
    if (!settingId) {
      setMessage('No wc:model Setting found for this model');
      return;
    }
    setSaving(true);
    setMessage('');

    try {
      // Build the override object
      const newBehavior: BehaviorSpec = { type: editType };
      if (editAction) newBehavior.action = editAction;
      if (editLabel) newBehavior.label = editLabel;
      if (editLookupModel && editType === 'lookup') newBehavior.model = editLookupModel;
      if (editType === 'select' && editOptions.trim()) {
        newBehavior.options = editOptions.trim().split('\n').map(line => {
          const [value, ...rest] = line.split(':');
          return { value: value.trim(), label: rest.join(':').trim() || value.trim() };
        });
        newBehavior.source = 'inline';
      }

      // Fetch current config, merge the override, save
      const res = await getRecords('setting', { id: settingId }) as any;
      const rec = (res?.results || [])[0];
      if (!rec) { setMessage('Setting not found'); setSaving(false); return; }

      const config = { ...rec.config };
      const behaviors = { ...(config.behaviors || {}) };
      behaviors[fieldName] = newBehavior;
      config.behaviors = behaviors;

      await saveRecord('setting', { id: settingId, config });
      setMessage('Saved — reload to see changes');
      setOverride(newBehavior);
      if (onReload) onReload();
    } catch (err: any) {
      setMessage(err?.message || 'Save failed');
    } finally {
      setSaving(false);
    }
  }, [settingId, fieldName, editType, editAction, editLabel, editOptions, editLookupModel]);

  const handleReset = useCallback(async () => {
    if (!settingId) return;
    setSaving(true);
    setMessage('');

    try {
      const res = await getRecords('setting', { id: settingId }) as any;
      const rec = (res?.results || [])[0];
      if (!rec) { setMessage('Setting not found'); setSaving(false); return; }

      const config = { ...rec.config };
      const behaviors = { ...(config.behaviors || {}) };
      delete behaviors[fieldName];
      config.behaviors = behaviors;

      await saveRecord('setting', { id: settingId, config });
      setMessage('Override removed — using computed behavior');
      setOverride({});
      if (onReload) onReload();
      setEditType(computed.type || '');
      setEditAction(computed.action || '');
      setEditLabel(computed.label || '');
      setEditOptions('');
      setEditLookupModel('');
    } catch (err: any) {
      setMessage(err?.message || 'Reset failed');
    } finally {
      setSaving(false);
    }
  }, [settingId, fieldName, computed]);

  if (!open) return null;

  return (
    <div className="bov-overlay" onClick={onClose}>
      <div className="bov-dialog" onClick={e => e.stopPropagation()}>
        <div className="bov-header">
          <span className="bov-title">Field Behavior: <strong>{fieldName}</strong></span>
          <span className="bov-model">{model}</span>
          <button className="bov-close" onClick={onClose}>×</button>
        </div>

        {loading ? (
          <div className="bov-body">Loading…</div>
        ) : (
          <div className="bov-body">
            {/* Current computed behavior */}
            <div className="bov-section">
              <div className="bov-section-label">Current</div>
              <div className="bov-computed">
                <span className="bov-tag">{computed.type || 'untyped'}</span>
                {computed.action && <span className="bov-tag bov-tag--action">{computed.action}</span>}
                {computed.model && <span className="bov-tag bov-tag--lookup">→ {computed.model}</span>}
                {computed.label && <span className="bov-tag bov-tag--label">"{computed.label}"</span>}
                {computed.options && <span className="bov-tag bov-tag--opts">{computed.options.length} options</span>}
              </div>
            </div>

            {/* Edit override */}
            <div className="bov-section">
              <div className="bov-section-label">Override</div>

              <div className="bov-row">
                <label className="bov-field-label">Type</label>
                <select className="bov-select" value={editType} onChange={e => setEditType(e.target.value)}>
                  <option value="">— auto —</option>
                  {WIDGET_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>

              <div className="bov-row">
                <label className="bov-field-label">Action</label>
                <select className="bov-select" value={editAction} onChange={e => setEditAction(e.target.value)}>
                  <option value="">none</option>
                  <option value="mailto">mailto</option>
                  <option value="tel">tel</option>
                  <option value="map">map</option>
                  <option value="link">link</option>
                </select>
              </div>

              <div className="bov-row">
                <label className="bov-field-label">Label</label>
                <input className="bov-input" value={editLabel} onChange={e => setEditLabel(e.target.value)}
                  placeholder="auto from field name" />
              </div>

              {editType === 'lookup' && (
                <div className="bov-row">
                  <label className="bov-field-label">Lookup model</label>
                  <input className="bov-input" value={editLookupModel} onChange={e => setEditLookupModel(e.target.value)}
                    placeholder="e.g. contact, customer" />
                </div>
              )}

              {editType === 'select' && (
                <div className="bov-row">
                  <label className="bov-field-label">Options (value:label per line)</label>
                  <textarea className="bov-textarea" rows={5} value={editOptions}
                    onChange={e => setEditOptions(e.target.value)}
                    placeholder={"active:Active\ninactive:Inactive\nretired:Retired"} />
                </div>
              )}
            </div>

            {message && (
              <div className={`bov-message ${message === 'Saved' ? 'bov-message--ok' : ''}`}>{message}</div>
            )}
          </div>
        )}

        <div className="bov-footer">
          <button className="bov-btn bov-btn--reset" onClick={handleReset} disabled={saving}>
            Reset to computed
          </button>
          <div className="bov-footer-right">
            <button className="bov-btn" onClick={onClose}>Cancel</button>
            <button className="bov-btn bov-btn--save" onClick={handleSave} disabled={saving || loading}>
              {saving ? 'Saving…' : 'Save Override'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
