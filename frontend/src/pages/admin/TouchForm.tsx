/* LastChecked: 2026-08-17 | WhereUsed: TouchBar (dialog), ActionFloatingWindow (inline) | WhoCreated: Bill+Claude */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { ContactPanel, normalizeRefsLinksContact } from '@/apps/common/components/panels/ContactPanel';
import type { RefContact } from '@/apps/common/components/panels/ContactPanel';

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

// ---------------------------------------------------------------------------
// ContactPicker — type-ahead search for a single contact
// ---------------------------------------------------------------------------

interface ContactPickerProps {
  label: string;
  contactId: number;
  contactName: string;
  contactPhone?: string;
  contactEmail?: string;
  onChange: (id: number, name: string, phone: string, email: string) => void;
  fontSize: number;
}

const ContactPicker: React.FC<ContactPickerProps> = ({ label, contactId, contactName, contactPhone, contactEmail, onChange, fontSize }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [searching, setSearching] = useState(false);
  const [editing, setEditing] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const doSearch = useCallback(async (q: string) => {
    if (q.length < 2) { setResults([]); return; }
    setSearching(true);
    try {
      const { getRecords } = await import('@/api/wcapi');
      const res = await getRecords('contact', { keyword: q, is_active: true, limit: 10 }) as any;
      setResults(res?.results || []);
    } catch { setResults([]); }
    setSearching(false);
  }, []);

  const handleInput = (val: string) => {
    setQuery(val);
    setShowResults(true);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(val), 300);
  };

  const handleSelect = (r: any) => {
    onChange(r.id, r.attention || r.name || `#${r.id}`, r.phone || '', r.email || '');
    setQuery('');
    setShowResults(false);
    setResults([]);
    setEditing(false);
  };

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) setShowResults(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleLabelClick = async (e: React.MouseEvent) => {
    if (!contactId) return;
    if (e.shiftKey) {
      // Shift-click = refresh contact data
      try {
        const { getRecord } = await import('@/api/wcapi');
        const res = await getRecord('contact', contactId);
        const c = res?.record || res;
        if (c) onChange(contactId, c.attention || c.display_name || c.name || contactName, c.phone || '', c.email || '');
      } catch {}
    } else {
      // Click = open contact record
      window.open(`/contact/${contactId}`, `contact-${contactId}`, 'width=900,height=700');
    }
  };

  return (
    <div ref={wrapperRef} style={{ position: 'relative' }}>
      <div className="db-label--default" style={{ fontSize: fontSize - 1, marginBottom: 2 }}>
        <button className="touch-contact-label" onClick={handleLabelClick}
          title={contactId > 0 ? 'Click: open contact · Shift-click: refresh' : label}
          style={{ fontSize: fontSize - 1 }}>
          {label}
        </button>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'nowrap' }}>
        <button className="touch-contact-name" onClick={() => setEditing(!editing)}
          title="Click to change contact">
          {contactName || (contactId > 0 ? `#${contactId}` : '— none —')}
        </button>
        {copyBadge(contactPhone || 'missing', contactPhone ? 'phone' : 'no phone')}
        {copyBadge(contactEmail || 'missing', contactEmail ? 'email' : 'no email')}
      </div>
      {editing && (
        <input
          type="text"
          value={query}
          onChange={(e) => handleInput(e.target.value)}
          onFocus={() => { if (results.length > 0) setShowResults(true); }}
          placeholder="Search contacts..."
          className="touch-contact-search"
          style={{ fontSize: fontSize - 1, width: '100%', marginTop: 4 }}
          autoFocus
        />
      )}
      {showResults && results.length > 0 && (
        <div className="touch-contact-results">
          {results.map((r: any) => (
            <button key={r.id} className="touch-contact-result"
              onClick={() => handleSelect(r)}>
              <span className="touch-contact-result-name">{r.attention || r.name || `#${r.id}`}</span>
              {r.phone && <span className="touch-contact-result-detail">{r.phone}</span>}
              {r.email && <span className="touch-contact-result-detail">{r.email}</span>}
            </button>
          ))}
        </div>
      )}
      {showResults && searching && <div className="touch-contact-results"><div style={{ padding: 8, fontSize: fontSize - 1, color: 'var(--db-text-muted)' }}>Searching...</div></div>}
    </div>
  );
};

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
  /** Linkage group ID — ties touch to transaction graph */
  linkageId?: number;
  /** Default channel */
  defaultChannel?: Channel;
  /** Default direction */
  defaultDirection?: 'out' | 'in';
  /** URI action prefs — controls what fires on Save */
  phoneAction?: 'tel' | 'facetime' | 'facetime-audio' | 'log_only';
  emailAction?: 'mailto' | 'log_only';
  textAction?: 'sms' | 'log_only';
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

interface TouchTemplate {
  id: number;
  name: string;
  topic: string;
  channel: string;
  subject?: string;
  body: string;
}

export const TouchForm: React.FC<TouchFormProps> = ({ mode, ctx, fontSize = 12, onClose, onSaved }) => {
  const [channel, setChannel] = useState<Channel>(ctx.defaultChannel || 'call');
  const [direction, setDirection] = useState<'out' | 'in'>(ctx.defaultDirection || 'out');
  const [subject, setSubject] = useState(ctx.defaultSubject);
  const [summary, setSummary] = useState('');
  const [duration, setDuration] = useState('');
  const [emailId, setEmailId] = useState('');
  const [outcome, setOutcome] = useState('');
  const [impact, setImpact] = useState(0);
  const [plan, setPlan] = useState(0);
  const [purpose, setPurpose] = useState('');
  const [purposeOptions, setPurposeOptions] = useState<{value: string; label: string}[]>([]);
  const [templates, setTemplates] = useState<TouchTemplate[]>([]);
  const [selectedTopic, setSelectedTopic] = useState('');

  // Fetch purpose selectlist from wc-model-touch Setting
  useEffect(() => {
    (async () => {
      try {
        const { getRecords } = await import('@/api/wcapi');
        const res = await getRecords('setting', { ida: 'wc-model-touch', limit: 1 }) as any;
        const rec = res?.results?.[0];
        const opts = rec?.config?.selectlists?.purpose || [];
        setPurposeOptions(opts);
      } catch { /* no purpose options */ }
    })();
  }, []);

  // Fetch touch templates
  useEffect(() => {
    (async () => {
      try {
        const { getRecords } = await import('@/api/wcapi');
        const res = await getRecords('report', {
          category: 'touch_template',
          is_active: true,
          limit: 100,
        }) as any;
        const records = res?.results || [];
        setTemplates(records.map((r: any) => ({
          id: r.id,
          name: r.name,
          topic: r.config?.topic || 'general',
          channel: r.config?.channel || 'email',
          subject: r.config?.subject,
          body: r.config?.body || '',
        })));
      } catch { /* no templates */ }
    })();
  }, []);

  // From/To contacts — auto-filled, user-changeable
  const loggedByUser = (window as any).__WC_USER_ID || 0;
  const loggedByName = (window as any).__WC_USER_NAME || 'Me';
  const [fromContact, setFromContact] = useState({ id: loggedByUser, name: loggedByName, phone: '', email: '' });
  const [toContact, setToContact] = useState({ id: ctx.contactId, name: ctx.contactName, phone: ctx.contactPhone, email: ctx.contactEmail });

  // Resolve {{tokens}} in template text
  const resolveTokens = useCallback((text: string) => {
    const companyName = (window as any).__WC_COMPANY_NAME || '';
    return text
      .replace(/\{\{contact_name\}\}/g, toContact.name || ctx.contactName || '')
      .replace(/\{\{company_name\}\}/g, toContact.name || ctx.contactName || '')
      .replace(/\{\{user_name\}\}/g, fromContact.name || loggedByName)
      .replace(/\{\{our_company\}\}/g, companyName)
      .replace(/\{\{subject\}\}/g, ctx.defaultSubject || subject)
      .replace(/\{\{record_ida\}\}/g, `${ctx.model}-${ctx.recordId}`)
      .replace(/\{\{follow_up_date\}\}/g, plan > 0
        ? new Date(Date.now() + plan * 86400000).toLocaleDateString()
        : '');
  }, [ctx, subject, plan, toContact.name, fromContact.name, loggedByName]);

  const [selectedTemplate, setSelectedTemplate] = useState<TouchTemplate | null>(null);

  const applyTemplate = useCallback((tpl: TouchTemplate) => {
    // Only fill subject if user hasn't typed more than 3 characters
    if (subject.trim().length <= 3) {
      setSubject(tpl.subject ? resolveTokens(tpl.subject) : tpl.name);
    }
    setSelectedTemplate(tpl);
    if (tpl.channel === 'email' || tpl.channel === 'text') {
      setChannel(tpl.channel as Channel);
    }
  }, [resolveTokens, subject]);

  // Filter templates by channel and topic
  const channelTemplates = templates.filter(t => t.channel === channel);
  const topics = [...new Set(channelTemplates.map(t => t.topic))].sort();
  const visibleTemplates = selectedTopic
    ? channelTemplates.filter(t => t.topic === selectedTopic)
    : channelTemplates;
  const [saving, setSaving] = useState(false);
  const [createAction, setCreateAction] = useState(false);
  const [linkedContacts, setLinkedContacts] = useState<RefContact[]>([]);

  const [touchId, setTouchId] = useState<number | null>(null);
  const [sent, setSent] = useState(false);

  // Build touch data from current form state
  const buildTouchData = () => {
    const fromId = direction === 'out' ? fromContact.id : toContact.id;
    const toId = direction === 'out' ? toContact.id : fromContact.id;
    const externalContactId = toContact.id || ctx.contactId;
    const parents: Record<string, number | null> = {
      from: fromId || null, to: toId || null, contact: externalContactId || null,
      customer: ctx.orgModel === 'customer' ? ctx.orgId : null,
      vendor: ctx.orgModel === 'vendor' ? ctx.orgId : null,
      manufacturer: ctx.orgModel === 'manufacturer' ? ctx.orgId : null,
      rep: ctx.orgModel === 'rep' ? ctx.orgId : null,
      action: ctx.model === 'action' ? ctx.recordId : null,
    };
    const contactLinks = linkedContacts.map(c => ({
      id: c.contact_id, purpose: c.purpose || 'primary',
      attention: c.attention, email: c.email, phone: c.phone,
    }));
    return {
      ...(touchId ? { id: touchId } : {}),
      contact_id: externalContactId || null, channel, direction, subject, summary,
      duration: duration ? parseInt(duration, 10) : null,
      email_message_id: emailId || null, outcome: outcome || null,
      impact: impact || 0, plan: plan || 0, purpose: purpose || null,
      action_id: ctx.model === 'action' ? ctx.recordId : null,
      org_id: ctx.orgId || null, org_model: ctx.orgModel || null,
      project_id: null, linkage_id: ctx.linkageId || null,
      logged_by: fromContact.id || loggedByUser,
      config: { template_id: selectedTemplate?.id || null, template_name: selectedTemplate?.name || null },
      refs: { parents, links: { contact: contactLinks } },
    };
  };

  // Save — record the touch, stay open
  const handleSave = async () => {
    setSaving(true);
    try {
      const { saveRecord } = await import('@/api/wcapi');
      const res = await saveRecord('touch', buildTouchData());
      const id = (res as any)?.record?.id;
      if (id) setTouchId(id);
      onSaved?.();
    } catch (err) {
      console.error('Failed to save touch:', err);
    } finally {
      setSaving(false);
    }
  };

  // URI links in the contact line handle send — no programmatic URI firing needed

  // Update — save changes after send (email_message_id, summary notes, outcome)
  const handleUpdate = async () => {
    if (!touchId) return;
    setSaving(true);
    try {
      const { saveRecord } = await import('@/api/wcapi');
      await saveRecord('touch', {
        id: touchId,
        summary,
        email_message_id: emailId || null,
        outcome: outcome || null,
        impact: impact || 0,
      });
      onSaved?.();
      onClose();
    } catch (err) {
      console.error('Failed to update touch:', err);
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
          {purposeOptions.length > 0 && (
            <select value={purpose} onChange={(e) => setPurpose(e.target.value)}
              className="touch-form-select">
              {purposeOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          )}
        </div>
        <div className="touch-form-contact-line">
          <span style={{ fontSize: '0.75em', color: 'var(--db-text-muted)' }}>{direction === 'out' ? 'To:' : 'From:'}</span>
          <span>{toContact.name || '—'}</span>
          {toContact.phone && <a href={`tel:${toContact.phone}`} className="touch-copy-badge" title="Dial">📞 {toContact.phone}</a>}
          {toContact.phone && <a href={`sms:${toContact.phone}`} className="touch-copy-badge" title="Text">💬</a>}
          {toContact.email && <a href={`mailto:${toContact.email}`} target="_blank" className="touch-copy-badge" title="Email">✉ {toContact.email}</a>}
        </div>
        {/* Template selector */}
        {(channel === 'email' || channel === 'text') && channelTemplates.length > 0 && (
          <div className="touch-form-row">
            {topics.length > 1 && (
              <select value={selectedTopic} onChange={e => setSelectedTopic(e.target.value)}
                className="touch-form-select">
                <option value="">all</option>
                {topics.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            )}
            <select value="" onChange={e => {
              const tpl = templates.find(t => t.id === Number(e.target.value));
              if (tpl) applyTemplate(tpl);
            }} className="touch-form-select" style={{ flex: 1 }}>
              <option value="">— template —</option>
              {visibleTemplates.map(t => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>
        )}
        <input type="text" value={subject} onChange={(e) => setSubject(e.target.value)}
          placeholder="subject" className="touch-form-input" />
        <textarea value={summary} onChange={(e) => setSummary(e.target.value)}
          placeholder="summary / notes" rows={2}
          className="touch-form-input touch-form-textarea" />
        {/* Send link — real <a> tags, not buttons, so browser handles protocol natively */}
        {!sent && (() => {
          const phone = toContact.phone || ctx.contactPhone || '';
          const email = toContact.email || ctx.contactEmail || '';
          const onSend = () => { setSent(true); handleSave(); };
          if (channel === 'call' && phone) {
            return <a href={`tel:${phone}`}
              className="touch-form-btn touch-form-btn--save" style={{ width: '100%', textAlign: 'center', textDecoration: 'none', display: 'block' }}
              onClick={onSend}>📞 Dial {phone}</a>;
          }
          if (channel === 'text' && phone) {
            const body = subject ? `?body=${encodeURIComponent(subject)}` : '';
            return <a href={`sms:${phone}${body}`}
              className="touch-form-btn touch-form-btn--save" style={{ width: '100%', textAlign: 'center', textDecoration: 'none', display: 'block' }}
              onClick={onSend}>💬 Text {phone}</a>;
          }
          if (channel === 'email' && email) {
            const p = new URLSearchParams();
            if (subject) p.set('subject', subject);
            const tplBody = selectedTemplate ? resolveTokens(selectedTemplate.body) : '';
            if (tplBody) p.set('body', tplBody);
            else if (summary) p.set('body', summary);
            const qs = p.toString();
            return <a href={`mailto:${email}${qs ? '?' + qs : ''}`}
              className="touch-form-btn touch-form-btn--save" style={{ width: '100%', textAlign: 'center', textDecoration: 'none', display: 'block' }}
              onClick={onSend}>✉ Send to {email}</a>;
          }
          return null;
        })()}
        <div className="touch-form-row">
          <div className="touch-form-impact">
            {[1,2,3,4,5].map(n => (
              <button key={n} className={`touch-impact-dot${impact === n ? ' touch-impact-dot--active' : ''}`}
                onClick={() => setImpact(impact === n ? 0 : n)} title={`Impact ${n}`}>{n}</button>
            ))}
          </div>
          <span style={{ flex: 1 }} />
          <button onClick={onClose} className="touch-form-btn">{sent ? 'Close' : 'Cancel'}</button>
          {sent ? (
            <button onClick={handleUpdate} disabled={saving}
              className="touch-form-btn touch-form-btn--save">
              {saving ? 'Saving...' : 'Save & Close'}
            </button>
          ) : (
            <button onClick={handleSave} disabled={saving || !subject.trim()}
              className="touch-form-btn touch-form-btn--save">
              {saving ? 'Saving...' : 'Log Only'}
            </button>
          )}
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
        {/* Header — actions at top, most-likely first */}
        <div className="db-md-header" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="db-md-title" style={{ fontSize: fontSize + 1 }}>
            {sent ? '✓ Sent' : 'Log Touch'}
          </span>
          <span style={{ flex: 1 }} />
          {sent ? (
            <>
              <button className="db-btn db-btn--small db-btn--save" onClick={handleUpdate} disabled={saving}>
                {saving ? 'Saving...' : 'Save & Close'}
              </button>
              <button className="db-btn db-btn--small" onClick={onClose}>Close</button>
            </>
          ) : (
            <>
              <button className="db-btn db-btn--small" onClick={handleSave} disabled={saving || !subject.trim()}>
                {saving ? 'Saving...' : 'Log Only'}
              </button>
              <button className="db-btn db-btn--small" onClick={onClose}>Cancel</button>
            </>
          )}
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

        {/* Template selector — topic then template */}
        {(channel === 'email' || channel === 'text') && channelTemplates.length > 0 && (
          <div className="db-border-bottom" style={{ padding: '8px 16px', display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <label className="db-label--default" style={{ fontSize: fontSize - 1 }}>Template</label>
            {topics.length > 1 && (
              <select value={selectedTopic} onChange={e => setSelectedTopic(e.target.value)}
                className="db-input" style={{ fontSize, width: 100, padding: '2px 4px' }}>
                <option value="">all</option>
                {topics.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            )}
            <select value="" onChange={e => {
              const tpl = templates.find(t => t.id === Number(e.target.value));
              if (tpl) applyTemplate(tpl);
            }} className="db-input" style={{ fontSize, flex: 1, padding: '2px 4px' }}>
              <option value="">— select template —</option>
              {visibleTemplates.map(t => (
                <option key={t.id} value={t.id}>{t.name}</option>
              ))}
            </select>
          </div>
        )}

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

          {/* From / To contacts with search */}
          <div style={{ display: 'flex', gap: 16 }}>
            <div style={{ flex: 1 }}>
              <ContactPicker label={direction === 'out' ? 'From (you)' : 'From (external)'}
                contactId={direction === 'out' ? fromContact.id : toContact.id}
                contactName={direction === 'out' ? fromContact.name : toContact.name}
                contactPhone={direction === 'out' ? fromContact.phone : toContact.phone}
                contactEmail={direction === 'out' ? fromContact.email : toContact.email}
                onChange={(id, name, phone, email) => {
                  if (direction === 'out') setFromContact({ id, name, phone, email });
                  else setToContact({ id, name, phone, email });
                }}
                fontSize={fontSize}
              />
            </div>
            <div style={{ flex: 1 }}>
              <ContactPicker label={direction === 'out' ? 'To (external)' : 'To (you)'}
                contactId={direction === 'out' ? toContact.id : fromContact.id}
                contactName={direction === 'out' ? toContact.name : fromContact.name}
                contactPhone={direction === 'out' ? toContact.phone : fromContact.phone}
                contactEmail={direction === 'out' ? toContact.email : fromContact.email}
                onChange={(id, name, phone, email) => {
                  if (direction === 'out') setToContact({ id, name, phone, email });
                  else setFromContact({ id, name, phone, email });
                }}
                fontSize={fontSize}
              />
            </div>
          </div>

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

          {/* Purpose + Outcome + Impact + Plan row */}
          <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap' }}>
            {purposeOptions.length > 0 && (
              <div>
                <label className="db-label--default" style={{ fontSize: fontSize - 1, display: 'block', marginBottom: 4 }}>Purpose</label>
                <select className="db-input" value={purpose} onChange={(e) => setPurpose(e.target.value)}
                  style={{ fontSize, width: 130 }}>
                  {purposeOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
            )}
            <div>
              <label className="db-label--default" style={{ fontSize: fontSize - 1, display: 'block', marginBottom: 4 }}>Outcome</label>
              <select className="db-input" value={outcome} onChange={(e) => setOutcome(e.target.value)}
                style={{ fontSize, width: 130 }}>
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
            <div>
              <label className="db-label--default" style={{ fontSize: fontSize - 1, display: 'block', marginBottom: 4 }}>Follow-up (days)</label>
              <input className="db-input" type="number" min="0" value={plan || ''} placeholder="0"
                onChange={(e) => setPlan(parseInt(e.target.value, 10) || 0)}
                style={{ width: 70, fontSize }} />
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

        {/* Contacts panel — additional people in this touch */}
        <div style={{ padding: '0 16px 12px' }}>
          <ContactPanel
            contacts={linkedContacts}
            isEditing={true}
            parent_model="touch"
            onChange={setLinkedContacts}
            title="Contacts"
            defaultCollapsed={linkedContacts.length === 0}
          />
        </div>

        {/* Footer removed — Save/Cancel in header per WC3 standard: actions top-down by priority */}
      </div>
    </div>
  );
};

export default TouchForm;
