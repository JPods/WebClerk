import { describe, expect, it } from 'vitest';
import { contactsToSend } from './LineContactsPanel';
import { lineRefsToSend } from '@/hooks/useRecordForm';

const stored = { role: 'warranty_holder', contact_id: 12, display_name: 'Pat Holder', company: 'Holder Household', email: 'pat@example.com', phone: '' };

describe('line contacts — what the form sends (readme 110)', () => {
  it('sends a person picked in this edit as role and contact only: the server copies the rest', () => {
    expect(contactsToSend([{ role: 'warranty_holder', contact_id: 12, display_name: 'Pat (browser)', _unsaved: true }]))
      .toEqual([{ role: 'warranty_holder', contact_id: 12 }]);
  });

  it('echoes a stored entry as the server gave it', () => {
    expect(contactsToSend([stored])).toEqual([stored]);
    expect(contactsToSend(undefined)).toEqual([]);
  });

  it('of a line\'s refs sends only its contacts, never the links or the source', () => {
    const loaded = { id: 5, refs: { links: { item: [{ id: 1 }] }, keywords: ['sofa'], contacts: [] } };
    const body = { id: 5, version: 3, _dirty: true, refs: { ...loaded.refs, contacts: [{ role: 'warranty_holder', contact_id: 12, _unsaved: true }] } };
    expect(lineRefsToSend(body, loaded)).toEqual({ id: 5, version: 3, _dirty: true, refs: { contacts: [{ role: 'warranty_holder', contact_id: 12 }] } });
  });

  it('sends no refs when the people did not change, and an empty list when they were all taken off', () => {
    const loaded = { id: 5, refs: { keywords: ['a'], contacts: [stored] } };
    expect(lineRefsToSend({ id: 5, refs: { keywords: ['b'], contacts: [stored] } }, loaded)).toEqual({ id: 5 });
    expect(lineRefsToSend({ id: 5, refs: { contacts: [] } }, loaded)).toEqual({ id: 5, refs: { contacts: [] } });
    expect(lineRefsToSend({ id: 5, quantity: { active: 2 } }, loaded)).toEqual({ id: 5, quantity: { active: 2 } });
  });
});
