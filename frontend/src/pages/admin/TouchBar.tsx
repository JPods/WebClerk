/* LastChecked: 2026-08-17 | WhereUsed: DataBrowser detail pane | WhoCreated: Bill+Claude */
import React, { useState, useEffect } from 'react';
import { TouchForm, type TouchFormContext } from './TouchForm';
import { TouchBadge } from './TouchBadge';

// ---------------------------------------------------------------------------
// TouchBar — phone/email/sms action icons for contact-linked records
// Uses TouchForm (dialog mode) for the touch entry form.
// ---------------------------------------------------------------------------

export const TOUCH_MODELS = new Set([
  'action', 'contact', 'customer', 'vendor', 'manufacturer', 'rep', 'employee', 'other_org',
  'invoice', 'order', 'proposal', 'purchase', 'workorder', 'requisition',
]);

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
  const [refreshKey, setRefreshKey] = useState(0);

  const isContact = model === 'contact';
  const isOrg = ['customer', 'vendor', 'manufacturer', 'rep', 'employee', 'other_org'].includes(model);
  const isTx = ['invoice', 'order', 'proposal', 'purchase', 'workorder', 'requisition'].includes(model);

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

  // For transactions, pass the linkage_id so touches tie into the transaction graph
  const txLinkageId = isTx ? recordId : undefined;

  const defaultSubject = typeof record.action === 'object' ? (record.action?.en || '')
    : String(record.action || record.subject || '');

  const openForm = (channel: 'call' | 'email' | 'text' | 'visit' | 'meeting') => {
    // URI firing moved to TouchForm.handleSave — open form only here
    setFormChannel(channel);
    setShowTouchForm(true);
  };

  const formCtx: TouchFormContext = {
    model, recordId, contactId, contactName, contactPhone, contactEmail,
    orgId, orgModel, defaultSubject,
    linkageId: txLinkageId,
    defaultChannel: formChannel,
    defaultDirection: tp.default_direction,
    phoneAction: tp.phone_action,
    emailAction: tp.email_action,
    textAction: tp.text_action,
  };

  return (
    <>
      <TouchBadge model={model} recordId={recordId} contactId={contactId} fontSize={fontSize}
        onClick={() => openForm('call')} refreshKey={refreshKey} />

      {showTouchForm && (
        <TouchForm mode="dialog" ctx={formCtx} fontSize={fontSize}
          onClose={() => setShowTouchForm(false)}
          onSaved={() => setRefreshKey(k => k + 1)} />
      )}
    </>
  );
};

export default TouchBar;
