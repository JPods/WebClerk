/**
 * AddRelatedDialog — one dialog for adding a record related to the one on screen.
 *
 * Bill, 2026-09-26 (release #9): the add-cash dialog behaves like the add-Action /
 * add-Touch dialog — one generic add-a-related-record dialog. A caller describes its
 * fields and what Save does; the dialog draws them, collects the values and shows the
 * server's own sentence when a save is refused. Extra content (a list to pick from, a
 * second action) goes in `children`.
 */
import React, { useEffect, useState } from 'react';
import { FaTimes, FaSpinner } from 'react-icons/fa';

export type RelatedField =
  | { name: string; label: string; kind: 'text' | 'textarea' | 'date'; placeholder?: string; required?: boolean }
  | { name: string; label: string; kind: 'number'; placeholder?: string; required?: boolean; step?: string }
  | { name: string; label: string; kind: 'select'; options: { value: string; label: string }[]; required?: boolean }
  | { name: string; label: string; kind: 'checkbox'; hint?: string };

export type RelatedValues = Record<string, string | boolean>;

interface AddRelatedDialogProps {
  isOpen: boolean;
  title: string;
  subtitle?: React.ReactNode;
  fields: RelatedField[];
  initial?: RelatedValues;
  saveLabel?: string;
  /** Resolve to close; throw an Error whose message is shown (use refusedFrom for the door's sentence). */
  onSave: (values: RelatedValues) => Promise<void>;
  onClose: () => void;
  children?: React.ReactNode;
}

const INPUT = 'w-full px-2 py-1.5 text-sm rounded border db-border-all db-bg-surface db-text';
const LABEL = 'block text-xs font-medium db-text-muted mb-1';

const AddRelatedDialog: React.FC<AddRelatedDialogProps> = ({
  isOpen, title, subtitle, fields, initial, saveLabel = 'Save', onSave, onClose, children,
}) => {
  const [values, setValues] = useState<RelatedValues>(initial ?? {});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen) { setValues(initial ?? {}); setError(''); }
  }, [isOpen]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!isOpen) return null;

  const set = (name: string, v: string | boolean) => setValues((prev) => ({ ...prev, [name]: v }));
  const missing = fields.some((f) => f.kind !== 'checkbox' && f.required && !String(values[f.name] ?? '').trim());

  const save = async () => {
    setSaving(true);
    setError('');
    try {
      await onSave(values);
      onClose();
    } catch (e: any) {
      setError(e?.message || 'Not saved');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" role="dialog" aria-label={title}>
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative db-bg-surface rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[calc(100vh-4rem)] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-3 db-border-bottom-light">
          <div>
            <h2 className="text-base font-semibold db-text">{title}</h2>
            {subtitle && <div className="text-xs db-text-muted">{subtitle}</div>}
          </div>
          <button onClick={onClose} className="p-2 db-text-muted rounded" aria-label="Close"><FaTimes /></button>
        </div>

        <div className="px-5 py-3 grid grid-cols-2 gap-3">
          {fields.map((f) => {
            const wide = f.kind === 'textarea' || f.kind === 'checkbox';
            const v = values[f.name];
            return (
              <div key={f.name} className={wide ? 'col-span-2' : ''}>
                {f.kind === 'checkbox' ? (
                  <label className="flex items-center gap-2 text-sm db-text cursor-pointer" title={f.hint}>
                    <input type="checkbox" checked={!!v} onChange={(e) => set(f.name, e.target.checked)} />
                    {f.label}
                  </label>
                ) : (
                  <>
                    <label className={LABEL} htmlFor={`ard-${f.name}`}>{f.label}{f.required ? ' *' : ''}</label>
                    {f.kind === 'select' ? (
                      <select id={`ard-${f.name}`} className={INPUT} value={String(v ?? '')}
                              onChange={(e) => set(f.name, e.target.value)}>
                        {f.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                      </select>
                    ) : f.kind === 'textarea' ? (
                      <textarea id={`ard-${f.name}`} className={INPUT} rows={2} placeholder={f.placeholder}
                                value={String(v ?? '')} onChange={(e) => set(f.name, e.target.value)} />
                    ) : (
                      <input id={`ard-${f.name}`} className={INPUT}
                             type={f.kind === 'number' ? 'number' : f.kind === 'date' ? 'date' : 'text'}
                             step={f.kind === 'number' ? (f.step ?? '0.01') : undefined}
                             placeholder={'placeholder' in f ? f.placeholder : undefined}
                             value={String(v ?? '')} onChange={(e) => set(f.name, e.target.value)} />
                    )}
                  </>
                )}
              </div>
            );
          })}
        </div>

        {error && <div className="mx-5 mb-2 text-sm db-text-red">{error}</div>}

        <div className="flex justify-end gap-2 px-5 pb-4">
          <button onClick={onClose} className="px-3 py-1.5 text-sm rounded db-text-muted">Cancel</button>
          <button onClick={save} disabled={saving || missing}
                  className="px-3 py-1.5 text-sm rounded disabled:opacity-50 flex items-center gap-1"
                  style={{ background: 'var(--db-btn-primary)', color: 'var(--db-btn-primary-text)' }}>
            {saving && <FaSpinner className="animate-spin" />} {saveLabel}
          </button>
        </div>

        {children && <div className="px-5 pb-4">{children}</div>}
      </div>
    </div>
  );
};

export default AddRelatedDialog;
