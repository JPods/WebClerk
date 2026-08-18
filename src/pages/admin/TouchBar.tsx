/* LastChecked: 2026-08-17 | WhereUsed: DataBrowser detail pane | WhoCreated: Bill+Claude */
import React, { useState, useEffect } from 'react';
import { TouchForm, type TouchFormContext } from './TouchForm';

// ---------------------------------------------------------------------------
// TouchBar — phone/email/sms action icons for contact-linked records
// Uses TouchForm (dialog mode) for the touch entry form.
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
  const [formChannel, setFormChannel] = useState<'call' | 'email' | 'text' | 'visit' | 'meeting'>(tp.default_channel || 'call');

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

  const defaultSubject = typeof record.action === 'object' ? (record.action?.en || '')
    : String(record.action || record.subject || '');

  const openForm = (channel: 'call' | 'email' | 'text' | 'visit' | 'meeting') => {
    // Fire URI for communication channels
    if (channel === 'call' && contactPhone && tp.phone_action !== 'log_only') {
      const scheme = tp.phone_action === 'facetime' ? 'facetime' : tp.phone_action === 'facetime-audio' ? 'facetime-audio' : 'tel';
      const a = document.createElement('a'); a.href = `${scheme}:${contactPhone}`; a.click();
    } else if (channel === 'email' && contactEmail && tp.email_action !== 'log_only') {
      const subj = encodeURIComponent(defaultSubject);
      const a = document.createElement('a'); a.href = `mailto:${contactEmail}?subject=${subj}`; a.click();
    } else if (channel === 'text' && contactPhone && tp.text_action !== 'log_only') {
      const a = document.createElement('a'); a.href = `sms:${contactPhone}`; a.click();
    }
    setFormChannel(channel);
    setShowTouchForm(true);
  };

  const hasPhone = !!contactPhone;
  const hasEmail = !!contactEmail;

  const copyBadge = (text: string, label: string) => (
    <button className="touch-copy-badge" title={`Copy ${label}`}
      onClick={(e) => { e.preventDefault(); e.stopPropagation(); navigator.clipboard.writeText(text); }}>
      {text} <span className="touch-copy-icon">⧉</span>
    </button>
  );

  const formCtx: TouchFormContext = {
    model, recordId, contactId, contactName, contactPhone, contactEmail,
    orgId, orgModel, defaultSubject,
    defaultChannel: formChannel,
    defaultDirection: tp.default_direction,
  };

  return (
    <>
      <div className="db-spawn-bar" style={{ gap: 8 }}>
        <span className="db-spawn-label">Touch:</span>
        {hasPhone && tp.phone_action !== 'log_only' && (
          <a href={`${tp.phone_action === 'facetime' ? 'facetime' : tp.phone_action === 'facetime-audio' ? 'facetime-audio' : 'tel'}:${contactPhone}`}
            className="touch-icon db-text-green"
            onClick={(e) => { openForm('call'); }}
            title={`Call ${contactName || contactPhone}`}>
            &#9742; Call
          </a>
        )}
        {hasEmail && tp.email_action !== 'log_only' && (
          <a href={`mailto:${contactEmail}?subject=${encodeURIComponent(defaultSubject)}`}
            className="touch-icon db-text-accent"
            onClick={() => { openForm('email'); }}
            title={`Email ${contactName || contactEmail}`}>
            &#9993; Email
          </a>
        )}
        {hasPhone && tp.text_action !== 'log_only' && (
          <a href={`sms:${contactPhone}`}
            className="touch-icon db-text-gold"
            onClick={() => { openForm('text'); }}
            title={`Text ${contactName || contactPhone}`}>
            &#128172; Text
          </a>
        )}
        <button className="touch-icon db-text-muted" onClick={() => openForm('call')}
          title="Log a touch (call, email, visit, text, meeting)">
          &#128221; Log
        </button>
        <span style={{ flex: 1 }} />
        {contactName && <span className="db-text-muted" style={{ fontSize: fontSize - 1 }}>{contactName}</span>}
        {hasPhone && copyBadge(contactPhone, 'phone')}
        {hasEmail && copyBadge(contactEmail, 'email')}
      </div>

      {showTouchForm && (
        <TouchForm mode="dialog" ctx={formCtx} fontSize={fontSize}
          onClose={() => setShowTouchForm(false)} />
      )}
    </>
  );
};

export default TouchBar;
