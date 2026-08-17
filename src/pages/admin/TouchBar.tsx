/* LastChecked: 2026-08-14 | WhereUsed: DataBrowser detail pane | WhoCreated: Bill+Claude */
import React, { useState, useEffect } from 'react';

// ---------------------------------------------------------------------------
// TouchBar — phone/email/sms action icons for contact-linked records
// ---------------------------------------------------------------------------

export const TOUCH_MODELS = new Set(['action', 'contact', 'customer', 'vendor', 'manufacturer', 'rep', 'employee', 'other_org']);

export interface TouchPrefs {
  default_channel?: 'call' | 'email' | 'text' | 'visit' | 'meeting';
  default_direction?: 'out' | 'in';
  phone_action?: 'tel' | 'facetime' | 'facetime-audio' | 'log_only';
  email_action?: 'mailto' | 'log_only';
  text_action?: 'sms' | 'log_only';
  auto_log?: boolean;
}

export const TouchBar: React.FC<{ model: string; record: any; recordId: number; theme: any; fontSize: number; touchPrefs?: TouchPrefs }> = ({ model, record, recordId, fontSize, touchPrefs }) => {
  const tp: TouchPrefs = touchPrefs || {};
  const [showTouchForm, setShowTouchForm] = useState(false);
  const [touchChannel, setTouchChannel] = useState<'call' | 'email' | 'text' | 'visit' | 'meeting'>(tp.default_channel || 'call');
  const [touchSummary, setTouchSummary] = useState('');
  const [touchSubject, setTouchSubject] = useState('');
  const [touchDuration, setTouchDuration] = useState('');
  const [touchEmailId, setTouchEmailId] = useState('');
  const [saving, setSaving] = useState(false);

  const isContact = model === 'contact';
  const isOrg = ['customer', 'vendor', 'manufacturer', 'rep', 'employee', 'other_org'].includes(model);

  const contactId = isContact ? recordId : (record.contact_id || record.contact || 0);

  // For models that don't carry phone/email directly (e.g. action),
  // fetch the linked contact record to resolve phone/email/name.
  const [resolvedContact, setResolvedContact] = useState<{ phone?: string; email?: string; name?: string } | null>(null);
  useEffect(() => {
    if (record.phone || record.email || isContact || !contactId) {
      setResolvedContact(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const { getRecord } = await import('@/api/wcapi');
        const res = await getRecord('contact', contactId);
        const c = res?.record || res;
        if (!cancelled && c) {
          setResolvedContact({
            phone: c.phone || '',
            email: c.email || '',
            name: c.attention || c.display_name || c.name || '',
          });
        }
      } catch { /* contact not found — show Log only */ }
    })();
    return () => { cancelled = true; };
  }, [contactId, record.phone, record.email, isContact]);

  const contactPhone = record.phone || resolvedContact?.phone || '';
  const contactEmail = record.email || resolvedContact?.email || '';
  const contactName = record.attention || record.display_name || record.name || record.company || record.contact_name || resolvedContact?.name || '';

  const orgId = isOrg ? recordId
    : record.customer_id || record.vendor_id || record.manufacturer_id || 0;
  const orgModel = isOrg ? model
    : record.customer_id ? 'customer'
    : record.vendor_id ? 'vendor'
    : record.manufacturer_id ? 'manufacturer'
    : '';

  const handleTouch = (channel: 'call' | 'email' | 'text') => {
    // Fire URI based on user's touch preferences
    if (channel === 'call' && contactPhone && tp.phone_action !== 'log_only') {
      const scheme = tp.phone_action === 'facetime' ? 'facetime' : tp.phone_action === 'facetime-audio' ? 'facetime-audio' : 'tel';
      const a = document.createElement('a'); a.href = `${scheme}:${contactPhone}`; a.click();
    } else if (channel === 'email' && contactEmail && tp.email_action !== 'log_only') {
      const subject = encodeURIComponent(
        typeof record.action === 'object' ? (record.action?.en || '') :
        String(record.action || record.subject || record.company || '')
      );
      const a = document.createElement('a'); a.href = `mailto:${contactEmail}?subject=${subject}`; a.click();
    } else if (channel === 'text' && contactPhone && tp.text_action !== 'log_only') {
      const a = document.createElement('a'); a.href = `sms:${contactPhone}`; a.click();
    }
    setTouchChannel(channel);
    setTouchSubject(
      typeof record.action === 'object' ? (record.action?.en || '') :
      String(record.action || record.subject || '')
    );
    setTouchSummary('');
    setTouchDuration('');
    setTouchEmailId('');
    setShowTouchForm(true);
  };

  const handleSaveTouch = async () => {
    setSaving(true);
    try {
      const { saveRecord } = await import('@/api/wcapi');
      // refs.parents — canonical lineage: who it was from, who it was to, what it belongs to
      const dir = document.querySelector<HTMLInputElement>('input[name="touch-dir"]:checked')?.value || 'out';
      const loggedByContact = (window as any).__WC_USER_ID || 0;
      const parents: Record<string, number | null> = {
        from: dir === 'out' ? loggedByContact : (contactId || null),
        to: dir === 'out' ? (contactId || null) : loggedByContact,
        contact: contactId || null,
        customer: orgModel === 'customer' ? orgId : null,
        vendor: orgModel === 'vendor' ? orgId : null,
        manufacturer: orgModel === 'manufacturer' ? orgId : null,
        rep: orgModel === 'rep' ? orgId : null,
        action: model === 'action' ? recordId : null,
      };

      await saveRecord('touch', {
        contact_id: contactId || null,
        channel: touchChannel,
        direction: dir,
        subject: touchSubject,
        summary: touchSummary,
        duration: touchDuration ? parseInt(touchDuration, 10) : null,
        email_message_id: touchEmailId,
        action_id: model === 'action' ? recordId : null,
        org_id: orgId,
        org_model: orgModel,
        project_id: record.project_id || null,
        logged_by: (window as any).__WC_USER_ID || 0,
        refs: { parents },
      });
      setShowTouchForm(false);
    } catch (err) {
      console.error('Failed to save touch:', err);
    } finally {
      setSaving(false);
    }
  };

  const hasPhone = !!contactPhone;
  const hasEmail = !!contactEmail;

  const copyBadge = (text: string, label: string) => (
    <button className="touch-copy-badge" title={`Copy ${label}`}
      onClick={(e) => { e.preventDefault(); e.stopPropagation(); navigator.clipboard.writeText(text); }}>
      {text} <span className="touch-copy-icon">⧉</span>
    </button>
  );

  const openLogTouch = () => {
    setTouchChannel('call');
    setTouchSubject(
      typeof record.action === 'object' ? (record.action?.en || '') :
      String(record.action || record.subject || '')
    );
    setTouchSummary('');
    setTouchDuration('');
    setTouchEmailId('');
    setShowTouchForm(true);
  };

  return (
    <>
      <div className="db-spawn-bar" style={{ gap: 8 }}>
        <span className="db-spawn-label">Touch:</span>
        {hasPhone && tp.phone_action !== 'log_only' && (
          <a href={`${tp.phone_action === 'facetime' ? 'facetime' : tp.phone_action === 'facetime-audio' ? 'facetime-audio' : 'tel'}:${contactPhone}`}
            className="touch-icon db-text-green"
            onClick={(e) => { /* don't prevent default — let the <a> fire the URI */ handleTouch('call'); }}
            title={`Call ${contactName || contactPhone}`}>
            &#9742; Call
          </a>
        )}
        {hasEmail && tp.email_action !== 'log_only' && (
          <a href={`mailto:${contactEmail}?subject=${encodeURIComponent(typeof record.action === 'object' ? (record.action?.en || '') : String(record.action || record.subject || record.company || ''))}`}
            className="touch-icon db-text-accent"
            onClick={() => { handleTouch('email'); }}
            title={`Email ${contactName || contactEmail}`}>
            &#9993; Email
          </a>
        )}
        {hasPhone && tp.text_action !== 'log_only' && (
          <a href={`sms:${contactPhone}`}
            className="touch-icon db-text-gold"
            onClick={() => { handleTouch('text'); }}
            title={`Text ${contactName || contactPhone}`}>
            &#128172; Text
          </a>
        )}
        <button className="touch-icon db-text-muted" onClick={openLogTouch}
          title="Log a touch (call, email, visit, text, meeting)">
          &#128221; Log
        </button>
        <span style={{ flex: 1 }} />
        {contactName && <span className="db-text-muted" style={{ fontSize: fontSize - 1 }}>{contactName}</span>}
        {hasPhone && copyBadge(contactPhone, 'phone')}
        {hasEmail && copyBadge(contactEmail, 'email')}
      </div>

      {showTouchForm && (
        <div data-wc="touch-dialog-backdrop"
          className="db-md-overlay"
          onClick={(e) => { if (e.target === e.currentTarget) setShowTouchForm(false); }}>
          <div data-wc="touch-dialog"
            className="db-md-dialog"
            style={{ width: 520, maxHeight: '80vh' }}>
            {/* Header */}
            <div className="db-md-header">
              <span className="db-md-title" style={{ fontSize: fontSize + 1 }}>Log Touch</span>
              <button className="db-md-close" onClick={() => setShowTouchForm(false)}>&times;</button>
            </div>

            {/* Channel selector */}
            <div className="db-border-bottom" style={{ padding: '12px 16px', display: 'flex', gap: 6 }}>
              {([['call', '☎ Call'], ['email', '✉ Email'], ['visit', '📋 Visit'], ['text', '💬 Text'], ['meeting', '🤝 Meeting']] as const).map(([ch, label]) => (
                <button key={ch}
                  className={touchChannel === ch ? 'touch-channel-btn touch-channel-btn--active' : 'touch-channel-btn'}
                  onClick={() => setTouchChannel(ch as any)}
                  style={{ fontSize }}>
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
                  <input type="radio" name="touch-dir" value="out" defaultChecked={tp.default_direction !== 'in'} style={{ marginRight: 4 }} /> Outbound
                </label>
                <label className="db-text" style={{ cursor: 'pointer' }}>
                  <input type="radio" name="touch-dir" value="in" defaultChecked={tp.default_direction === 'in'} style={{ marginRight: 4 }} /> Inbound
                </label>
              </div>

              {/* Contact line with copy badges */}
              {(contactName || contactId > 0) && (
                <div>
                  <label className="db-label--default" style={{ fontSize: fontSize - 1, display: 'block', marginBottom: 4 }}>Contact</label>
                  <div className="db-text" style={{ fontSize, display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' }}>
                    <span>{contactName || `#${contactId}`}</span>
                    {contactPhone && copyBadge(contactPhone, 'phone')}
                    {contactEmail && copyBadge(contactEmail, 'email')}
                  </div>
                </div>
              )}

              <div>
                <label className="db-label--default" style={{ fontSize: fontSize - 1, display: 'block', marginBottom: 4 }}>Subject</label>
                <input className="db-input" value={touchSubject} onChange={(e) => setTouchSubject(e.target.value)}
                  style={{ fontSize }} />
              </div>
              <div>
                <label className="db-label--default" style={{ fontSize: fontSize - 1, display: 'block', marginBottom: 4 }}>Summary</label>
                <textarea className="db-input" value={touchSummary} onChange={(e) => setTouchSummary(e.target.value)}
                  rows={4} placeholder="What happened, what was discussed, next steps..."
                  style={{ fontSize, resize: 'vertical' }} />
              </div>
              {(touchChannel === 'call' || touchChannel === 'meeting') && (
                <div>
                  <label className="db-label--default" style={{ fontSize: fontSize - 1, display: 'block', marginBottom: 4 }}>Duration (minutes)</label>
                  <input className="db-input" type="number" value={touchDuration} onChange={(e) => setTouchDuration(e.target.value)}
                    style={{ width: 100, fontSize }} />
                </div>
              )}
              {touchChannel === 'email' && (
                <div>
                  <label className="db-label--default" style={{ fontSize: fontSize - 1, display: 'block', marginBottom: 4 }}>Email Message ID (paste from email program)</label>
                  <input className="db-input" value={touchEmailId} onChange={(e) => setTouchEmailId(e.target.value)}
                    placeholder="<abc123@mail.example.com>"
                    style={{ fontSize }} />
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="db-border-top" style={{
              padding: '12px 16px',
              display: 'flex', justifyContent: 'flex-end', gap: 8,
            }}>
              <button className="db-btn db-btn--small" onClick={() => setShowTouchForm(false)}>Cancel</button>
              <button className="db-btn db-btn--small db-btn--save" onClick={handleSaveTouch} disabled={saving}>
                {saving ? 'Saving...' : 'Save Touch'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default TouchBar;
