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
});
