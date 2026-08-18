/* LastChecked: 2026-08-17 | WhereUsed: TouchBar (dialog), ActionFloatingWindow (inline) | WhoCreated: Bill+Claude */
import React, { useState } from 'react';

// ---------------------------------------------------------------------------
// TouchForm — unified touch entry form, two rendering modes
//   dialog: modal overlay with full fields
//   inline: compact embedded form
// ---------------------------------------------------------------------------

type Channel = 'call' | 'email' | 'visit' | 'text' | 'meeting';

const CHANNELS: [Channel, string][] = [
  ['call', '☎ Call'], ['email', '✉ Email'], ['visit', '📋 Visit'],
  ['text', '💬 Text'], ['meeting', '🤝 Meeting'],
];

const OUTCOMES: [string, string][] = [
  ['', '—'], ['connected', 'Connected'], ['voicemail', 'Voicemail'],
  ['no_answer', 'No Answer'], ['bounced', 'Bounced'], ['rescheduled', 'Rescheduled'],
];

export interface TouchFormContext {
  /** Parent model name (action, contact, customer, etc.) */
  model: string;
  /** Parent record ID */
  recordId: number;
  /** Resolved contact ID (0 if none) */
  contactId: number;
  /** Contact display name */
  contactName: string;
  /** Contact phone */
  contactPhone: string;
  /** Contact email */
  contactEmail: string;
  /** Org ID (customer/vendor/manufacturer record ID) */
  orgId: number;
  /** Org model name */
  orgModel: string;
  /** Pre-fill subject from parent record */
  defaultSubject: string;
  /** Default channel */
  defaultChannel?: Channel;
  /** Default direction */
  defaultDirection?: 'out' | 'in';
}

interface TouchFormProps {
  mode: 'dialog' | 'inline';
  ctx: TouchFormContext;
  fontSize?: number;
  onClose: () => void;
  onSaved?: () => void;
}

const copyBadge = (text: string, label: string) => (
  <button className="touch-copy-badge" title={`Copy ${label}`}
    onClick={(e) => { e.preventDefault(); e.stopPropagation(); navigator.clipboard.writeText(text); }}>
    {text} <span className="touch-copy-icon">⧉</span>
  </button>
);

export const TouchForm: React.FC<TouchFormProps> = ({ mode, ctx, fontSize = 12, onClose, onSaved }) => {
  const [channel, setChannel] = useState<Channel>(ctx.defaultChannel || 'call');
  const [direction, setDirection] = useState<'out' | 'in'>(ctx.defaultDirection || 'out');
  const [subject, setSubject] = useState(ctx.defaultSubject);
  const [summary, setSummary] = useState('');
  const [duration, setDuration] = useState('');
  const [emailId, setEmailId] = useState('');
  const [outcome, setOutcome] = useState('');
  const [impact, setImpact] = useState(0);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      const { saveRecord } = await import('@/api/wcapi');
      const loggedBy = (window as any).__WC_USER_ID || 0;

      const parents: Record<string, number | null> = {
        from: direction === 'out' ? loggedBy : (ctx.contactId || null),
        to: direction === 'out' ? (ctx.contactId || null) : loggedBy,
        contact: ctx.contactId || null,
        customer: ctx.orgModel === 'customer' ? ctx.orgId : null,
        vendor: ctx.orgModel === 'vendor' ? ctx.orgId : null,
        manufacturer: ctx.orgModel === 'manufacturer' ? ctx.orgId : null,
        rep: ctx.orgModel === 'rep' ? ctx.orgId : null,
        action: ctx.model === 'action' ? ctx.recordId : null,
      };

      await saveRecord('touch', {
        contact_id: ctx.contactId || null,
        channel,
        direction,
        subject,
        summary,
        duration: duration ? parseInt(duration, 10) : null,
        email_message_id: emailId || null,
        outcome: outcome || null,
        impact: impact || 0,
        action_id: ctx.model === 'action' ? ctx.recordId : null,
        org_id: ctx.orgId || null,
        org_model: ctx.orgModel || null,
        project_id: null,
        logged_by: loggedBy,
        refs: { parents },
      });

      onSaved?.();
      onClose();
    } catch (err) {
      console.error('Failed to save touch:', err);
    } finally {
      setSaving(false);
    }
  };

  // -- Inline mode --
  if (mode === 'inline') {
    return (
      <div className="touch-form-inline">
        <div className="touch-form-row">
          <span className="touch-form-channel-label">
            {CHANNELS.find(([c]) => c === channel)?.[1] || '☎ Call'}
          </span>
          <select value={channel} onChange={(e) => setChannel(e.target.value as Channel)}
            className="touch-form-select">
            {CHANNELS.map(([c, label]) => <option key={c} value={c}>{label}</option>)}
          </select>
          <select value={direction} onChange={(e) => setDirection(e.target.value as 'out' | 'in')}
            className="touch-form-select">
            <option value="out">→ Out</option>
            <option value="in">← In</option>
          </select>
          <select value={outcome} onChange={(e) => setOutcome(e.target.value)}
            className="touch-form-select">
            {OUTCOMES.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
          </select>
        </div>
        {ctx.contactName && (
          <div className="touch-form-contact-line">
            <span>{ctx.contactName}</span>
            {ctx.contactPhone && copyBadge(ctx.contactPhone, 'phone')}
            {ctx.contactEmail && copyBadge(ctx.contactEmail, 'email')}
          </div>
        )}
        <input type="text" value={subject} onChange={(e) => setSubject(e.target.value)}
          placeholder="Subject" className="touch-form-input" autoFocus />
        <textarea value={summary} onChange={(e) => setSummary(e.target.value)}
          placeholder="Summary — what happened, next steps" rows={2}
          className="touch-form-input touch-form-textarea" />
        <div className="touch-form-row">
          <div className="touch-form-impact">
            {[1,2,3,4,5].map(n => (
              <button key={n} className={`touch-impact-dot${impact === n ? ' touch-impact-dot--active' : ''}`}
                onClick={() => setImpact(impact === n ? 0 : n)} title={`Impact ${n}`}>{n}</button>
            ))}
          </div>
          <span style={{ flex: 1 }} />
          <button onClick={onClose} className="touch-form-btn">Cancel</button>
          <button onClick={handleSave} disabled={saving || !subject.trim()}
            className="touch-form-btn touch-form-btn--save">
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    );
  }

  // -- Dialog mode --
  return (
    <div data-wc="touch-dialog-backdrop" className="db-md-overlay"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div data-wc="touch-dialog" className="db-md-dialog"
        style={{ width: 520, maxHeight: '80vh' }}>
        {/* Header */}
        <div className="db-md-header">
          <span className="db-md-title" style={{ fontSize: fontSize + 1 }}>Log Touch</span>
          <button className="db-md-close" onClick={onClose}>&times;</button>
        </div>

        {/* Channel selector */}
        <div className="db-border-bottom" style={{ padding: '12px 16px', display: 'flex', gap: 6 }}>
          {CHANNELS.map(([ch, label]) => (
            <button key={ch}
              className={channel === ch ? 'touch-channel-btn touch-channel-btn--active' : 'touch-channel-btn'}
              onClick={() => setChannel(ch)} style={{ fontSize }}>
              {label}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="db-md-body" style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* Direction */}
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <label className="db-label--default" style={{ fontSize: fontSize - 1 }}>Direction</label>
            <label className="db-text" style={{ cursor: 'pointer' }}>
              <input type="radio" name="touch-dir" value="out" checked={direction === 'out'}
                onChange={() => setDirection('out')} style={{ marginRight: 4 }} /> Outbound
            </label>
            <label className="db-text" style={{ cursor: 'pointer' }}>
              <input type="radio" name="touch-dir" value="in" checked={direction === 'in'}
                onChange={() => setDirection('in')} style={{ marginRight: 4 }} /> Inbound
            </label>
          </div>

          {/* Contact line with copy badges */}
          {(ctx.contactName || ctx.contactId > 0) && (
            <div>
              <label className="db-label--default" style={{ fontSize: fontSize - 1, display: 'block', marginBottom: 4 }}>Contact</label>
              <div className="db-text" style={{ fontSize, display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
                <span>{ctx.contactName || `#${ctx.contactId}`}</span>
                {ctx.contactPhone && copyBadge(ctx.contactPhone, 'phone')}
                {ctx.contactEmail && copyBadge(ctx.contactEmail, 'email')}
              </div>
            </div>
          )}

          <div>
            <label className="db-label--default" style={{ fontSize: fontSize - 1, display: 'block', marginBottom: 4 }}>Subject</label>
            <input className="db-input" value={subject} onChange={(e) => setSubject(e.target.value)}
              style={{ fontSize }} />
          </div>
          <div>
            <label className="db-label--default" style={{ fontSize: fontSize - 1, display: 'block', marginBottom: 4 }}>Summary</label>
            <textarea className="db-input" value={summary} onChange={(e) => setSummary(e.target.value)}
              rows={4} placeholder="What happened, what was discussed, next steps..."
              style={{ fontSize, resize: 'vertical' }} />
          </div>

          {/* Outcome + Impact row */}
          <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
            <div>
              <label className="db-label--default" style={{ fontSize: fontSize - 1, display: 'block', marginBottom: 4 }}>Outcome</label>
              <select className="db-input" value={outcome} onChange={(e) => setOutcome(e.target.value)}
                style={{ fontSize, width: 140 }}>
                {OUTCOMES.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
              </select>
            </div>
            <div>
              <label className="db-label--default" style={{ fontSize: fontSize - 1, display: 'block', marginBottom: 4 }}>Impact</label>
              <div style={{ display: 'flex', gap: 4 }}>
                {[1,2,3,4,5].map(n => (
                  <button key={n} className={`touch-impact-dot${impact === n ? ' touch-impact-dot--active' : ''}`}
                    onClick={() => setImpact(impact === n ? 0 : n)} title={`Impact ${n}`}
                    style={{ fontSize }}>{n}</button>
                ))}
              </div>
            </div>
          </div>

          {(channel === 'call' || channel === 'meeting') && (
            <div>
              <label className="db-label--default" style={{ fontSize: fontSize - 1, display: 'block', marginBottom: 4 }}>Duration (minutes)</label>
              <input className="db-input" type="number" value={duration} onChange={(e) => setDuration(e.target.value)}
                style={{ width: 100, fontSize }} />
            </div>
          )}
          {channel === 'email' && (
            <div>
              <label className="db-label--default" style={{ fontSize: fontSize - 1, display: 'block', marginBottom: 4 }}>Email Message ID (paste from email program)</label>
              <input className="db-input" value={emailId} onChange={(e) => setEmailId(e.target.value)}
                placeholder="<abc123@mail.example.com>" style={{ fontSize }} />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="db-border-top" style={{ padding: '12px 16px', display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <button className="db-btn db-btn--small" onClick={onClose}>Cancel</button>
          <button className="db-btn db-btn--small db-btn--save" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save Touch'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default TouchForm;
