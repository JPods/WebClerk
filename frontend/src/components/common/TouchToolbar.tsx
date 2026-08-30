/**
 * TouchToolbar — universal touch entry component.
 *
 * Two divs:
 *   1. Channel buttons — Call, Email, Text, Visit, Meeting
 *   2. Options panel — appears below the selected channel button
 *
 * One component, used everywhere: db.detail, db.form, Kanban, Gantt, floating windows.
 * No dialog overlay. Inline. Click button to expand, click again to collapse.
 *
 * On Save: records the touch, then fires the appropriate URI (tel:, mailto:, sms:).
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { getRecord, getRecords, saveRecord } from '@/api/wcapi';

type Channel = 'call' | 'email' | 'text' | 'visit' | 'meeting';

const CHANNELS: { ch: Channel; icon: string; label: string }[] = [
  { ch: 'call', icon: '☎', label: 'Call' },
  { ch: 'email', icon: '✉', label: 'Email' },
  { ch: 'text', icon: '💬', label: 'Text' },
  { ch: 'visit', icon: '📋', label: 'Visit' },
  { ch: 'meeting', icon: '🤝', label: 'Meeting' },
];

const OUTCOMES: { value: string; label: string }[] = [
  { value: '', label: '—' },
  { value: 'connected', label: 'Connected' },
  { value: 'voicemail', label: 'Voicemail' },
  { value: 'no_answer', label: 'No Answer' },
  { value: 'bounced', label: 'Bounced' },
  { value: 'rescheduled', label: 'Rescheduled' },
];

export interface TouchToolbarProps {
  /** Parent model name */
  model: string;
  /** Parent record ID */
  recordId: number;
  /** The parent record (for resolving contact info) */
  record: Record<string, any>;
  /** Called after a touch is saved */
  onSaved?: () => void;
  /** URI action prefs */
  phoneAction?: 'tel' | 'facetime' | 'facetime-audio' | 'log_only';
  emailAction?: 'mailto' | 'log_only';
  textAction?: 'sms' | 'log_only';
}

export const TouchToolbar: React.FC<TouchToolbarProps> = ({
  model, recordId, record, onSaved,
  phoneAction, emailAction, textAction,
}) => {
  const [activeChannel, setActiveChannel] = useState<Channel | null>(null);
  const [direction, setDirection] = useState<'out' | 'in'>('out');
  const [subject, setSubject] = useState('');
  const [summary, setSummary] = useState('');
  const [duration, setDuration] = useState('');
  const [outcome, setOutcome] = useState('');
  const [impact, setImpact] = useState(0);
  const [saving, setSaving] = useState(false);
  const [touchCount, setTouchCount] = useState(0);

  // Resolve contact info from the record
  const isContact = model === 'contact';
  const contactId = isContact ? recordId : (record.contact_id || record.contact || 0);
  const [contactPhone, setContactPhone] = useState(record.phone || '');
  const [contactEmail, setContactEmail] = useState(record.email || '');
  const [contactName, setContactName] = useState(
    record.attention || record.display_name || record.name || record.company || record.contact_name || ''
  );

  // Resolve contact if not directly on record
  useEffect(() => {
    if (record.phone || record.email || isContact || !contactId) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await getRecord('contact', contactId);
        const c = res?.record || res;
        if (!cancelled && c) {
          setContactPhone(c.phone || '');
          setContactEmail(c.email || '');
          setContactName(c.attention || c.display_name || c.name || '');
        }
      } catch { /* contact not found */ }
    })();
    return () => { cancelled = true; };
  }, [contactId, record.phone, record.email, isContact]);

  // Load touch count
  useEffect(() => {
    if (!recordId) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await getRecords('touch', {
          contact_id: contactId || undefined,
          [`refs__parents__${model}`]: recordId,
          limit: 0,
        }) as any;
        if (!cancelled) setTouchCount(res?.count || res?.total || 0);
      } catch { /* silent */ }
    })();
    return () => { cancelled = true; };
  }, [model, recordId, contactId]);

  // Default subject from record
  useEffect(() => {
    const s = typeof record.action === 'object' ? (record.action?.en || '')
      : String(record.action || record.subject || '');
    setSubject(s);
  }, [record]);

  const toggleChannel = (ch: Channel) => {
    setActiveChannel(prev => prev === ch ? null : ch);
  };

  const orgId = record.customer_id || record.vendor_id || record.manufacturer_id || 0;
  const orgModel = record.customer_id ? 'customer'
    : record.vendor_id ? 'vendor'
    : record.manufacturer_id ? 'manufacturer' : '';

  const handleSave = async () => {
    if (!activeChannel || !subject.trim()) return;
    setSaving(true);
    try {
      const loggedBy = (window as any).__WC_USER_ID || 0;
      const externalContactId = contactId || 0;

      const touchData = {
        contact_id: externalContactId || null,
        channel: activeChannel,
        direction,
        subject,
        summary,
        duration: duration ? parseInt(duration, 10) : null,
        outcome: outcome || null,
        impact: impact || 0,
        action_id: model === 'action' ? recordId : null,
        org_id: orgId || null,
        org_model: orgModel || null,
        logged_by: loggedBy,
        refs: {
          parents: {
            contact: externalContactId || null,
            [model]: recordId,
          },
          links: {},
        },
      };

      await saveRecord('touch', touchData);

      // Fire URI after save
      const phone = contactPhone;
      const email = contactEmail;

      if (activeChannel === 'email' && email && emailAction !== 'log_only') {
        const params = new URLSearchParams();
        params.set('subject', subject);
        if (summary) params.set('body', summary);
        const a = document.createElement('a');
        a.href = `mailto:${encodeURIComponent(email)}?${params.toString()}`;
        a.click();
      } else if (activeChannel === 'call' && phone && phoneAction !== 'log_only') {
        const scheme = phoneAction === 'facetime' ? 'facetime'
          : phoneAction === 'facetime-audio' ? 'facetime-audio' : 'tel';
        const a = document.createElement('a');
        a.href = `${scheme}:${phone}`;
        a.click();
      } else if (activeChannel === 'text' && phone && textAction !== 'log_only') {
        const body = subject ? `?body=${encodeURIComponent(subject)}` : '';
        const a = document.createElement('a');
        a.href = `sms:${phone}${body}`;
        a.click();
      }

      setTouchCount(c => c + 1);
      setSummary('');
      setDuration('');
      setOutcome('');
      setImpact(0);
      setActiveChannel(null);
      onSaved?.();
    } catch (err) {
      console.error('Failed to save touch:', err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="touch-toolbar">
      {/* Div 1: Channel buttons */}
      <div className="touch-toolbar-buttons">
        {CHANNELS.map(({ ch, icon, label }) => (
          <button
            key={ch}
            className={`touch-toolbar-btn${activeChannel === ch ? ' touch-toolbar-btn--active' : ''}`}
            onClick={() => toggleChannel(ch)}
            title={label}
          >
            {icon}
          </button>
        ))}
        {touchCount > 0 && (
          <span className="touch-toolbar-count" title={`${touchCount} touches`}>{touchCount}</span>
        )}
      </div>

      {/* Div 2: Options panel — shown when a channel is selected */}
      {activeChannel && (
        <div className="touch-toolbar-panel">
          {/* Contact line */}
          <div className="touch-toolbar-contact">
            <span className="touch-toolbar-dir">
              <button onClick={() => setDirection(d => d === 'out' ? 'in' : 'out')}
                className="touch-toolbar-dir-btn" title={direction === 'out' ? 'Outbound' : 'Inbound'}>
                {direction === 'out' ? '→' : '←'}
              </button>
            </span>
            <span className="touch-toolbar-contact-name">{contactName || '(no contact)'}</span>
            {activeChannel === 'call' && contactPhone && (
              <span className="touch-toolbar-contact-detail">{contactPhone}</span>
            )}
            {activeChannel === 'email' && contactEmail && (
              <span className="touch-toolbar-contact-detail">{contactEmail}</span>
            )}
            {activeChannel === 'text' && contactPhone && (
              <span className="touch-toolbar-contact-detail">{contactPhone}</span>
            )}
          </div>

          {/* Subject */}
          <input
            type="text"
            value={subject}
            onChange={e => setSubject(e.target.value)}
            placeholder="Subject"
            className="touch-toolbar-input"
            style={{ fontSize: 16 }}
            autoFocus
          />

          {/* Summary */}
          <textarea
            value={summary}
            onChange={e => setSummary(e.target.value)}
            placeholder="Summary — what happened, next steps"
            rows={2}
            className="touch-toolbar-input touch-toolbar-textarea"
            style={{ fontSize: 16 }}
          />

          {/* Channel-specific fields */}
          <div className="touch-toolbar-extras">
            {(activeChannel === 'call' || activeChannel === 'meeting') && (
              <label className="touch-toolbar-field">
                <span>min</span>
                <input type="number" value={duration} onChange={e => setDuration(e.target.value)}
                  className="touch-toolbar-input-sm" placeholder="0" />
              </label>
            )}
            <label className="touch-toolbar-field">
              <span>outcome</span>
              <select value={outcome} onChange={e => setOutcome(e.target.value)}
                className="touch-toolbar-input-sm">
                {OUTCOMES.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </label>
            <div className="touch-toolbar-impact">
              {[1,2,3,4,5].map(n => (
                <button key={n}
                  className={`touch-toolbar-dot${impact === n ? ' touch-toolbar-dot--active' : ''}`}
                  onClick={() => setImpact(impact === n ? 0 : n)}>{n}</button>
              ))}
            </div>
            <span style={{ flex: 1 }} />
            <button onClick={handleSave} disabled={saving || !subject.trim()}
              className="touch-toolbar-save">
              {saving ? '...' : `Save ${CHANNELS.find(c => c.ch === activeChannel)?.label}`}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default TouchToolbar;
