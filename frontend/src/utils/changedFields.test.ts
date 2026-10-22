import { describe, expect, it } from 'vitest';
import { changedFields } from './changedFields';

describe('changedFields', () => {
  const loaded = {
    id: 7, version: 3, uuid: 'u-1', model_name: 'project', ida: 'P-7', dt_modified: 1,
    name: 'Old', metadata: { kanban: { a: 1 } },
  };

  it('sends only what changed, with id and version', () => {
    expect(changedFields(loaded, { ...loaded, name: 'New' })).toEqual({ id: 7, version: 3, name: 'New' });
  });

  it('never echoes model_name, uuid, ida or dt_* back', () => {
    const body = changedFields(loaded, { ...loaded });
    expect(body).toEqual({ id: 7, version: 3 });
  });

  it('sends a changed JSON field whole', () => {
    const edited = { ...loaded, metadata: { kanban: { a: 2 } } };
    expect(changedFields(loaded, edited)).toEqual({ id: 7, version: 3, metadata: { kanban: { a: 2 } } });
  });

  it('keeps the loaded version, not an edited one', () => {
    expect(changedFields(loaded, { ...loaded, version: 99 }).version).toBe(3);
  });

  it('sends a field the person emptied as the door\'s clear', () => {
    const linked = { ...loaded, customer: { id: 5648, name: 'Que Supply' } };
    expect(changedFields(linked, { ...linked, customer: null }).customer).toEqual({ mode: 'delete' });
  });
});
