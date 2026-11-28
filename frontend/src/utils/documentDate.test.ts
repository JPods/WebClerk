/** Who is offered the document-date lock, and what the save sends (Bill, 2026-11-27). */
import { describe, expect, it } from 'vitest';
import { mayChangeDocumentDate, unlockableFields, withDocumentDateUnlock, DOCUMENT_DATE_MODELS } from './documentDate';

const open = { id: 5, dt_created: 1_791_000_000_000, dt_journaled: null };
const journalized = { ...open, dt_journaled: 1_794_500_000_000 };

describe('document date', () => {
  it.each(DOCUMENT_DATE_MODELS)('a superuser or an admin may change a %s before it is journalized', (model) => {
    expect(mayChangeDocumentDate({ is_superuser: true, role: 'sales' }, model, open)).toBe(true);
    expect(mayChangeDocumentDate({ role: 'admin' }, model, open)).toBe(true);
  });

  it.each(['accounting', 'sales', 'warehouse', 'support', 'rep', 'production', 'agent', ''])('a %s login is offered nothing', (role) => {
    expect(unlockableFields({ role }, 'invoice', open)).toEqual([]);
  });

  it('a journalized document, an unsaved one, another model and no login offer nothing', () => {
    expect(unlockableFields({ role: 'admin' }, 'invoice', journalized)).toEqual([]);
    expect(unlockableFields({ role: 'admin' }, 'invoice', { dt_created: 1 })).toEqual([]);
    expect(unlockableFields({ role: 'admin' }, 'order', open)).toEqual([]);
    expect(unlockableFields(null, 'invoice', open)).toEqual([]);
    expect(unlockableFields({ role: 'admin' }, 'receipt', open)).toEqual(['dt_created']);
  });

  it('a changed date goes as epoch ms with _unlock; an unchanged one adds nothing', () => {
    expect(withDocumentDateUnlock('cash', { id: 1, dt_created: '2026-10-01T04:59:59.999Z' }))
      .toEqual({ id: 1, dt_created: Date.parse('2026-10-01T04:59:59.999Z'), _unlock: ['dt_created'] });
    expect(withDocumentDateUnlock('cash', { id: 1, dt_created: 1_791_000_000_000 }))
      .toEqual({ id: 1, dt_created: 1_791_000_000_000, _unlock: ['dt_created'] });
    expect(withDocumentDateUnlock('cash', { id: 1, status: 'x' })).toEqual({ id: 1, status: 'x' });
    expect(withDocumentDateUnlock('order', { id: 1, dt_created: 5 })).toEqual({ id: 1, dt_created: 5 });
  });
});
