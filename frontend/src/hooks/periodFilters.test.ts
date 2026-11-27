import { describe, expect, it } from 'vitest';
import { periodFilters } from './useDataBrowser';

describe('periodFilters', () => {
  it('turns the _period signal into the declared field’s range, and leaves other filters alone', () => {
    expect(periodFilters({ _period: { gte: 1, lte: 9 }, contact_id: 5 }, 'dt_document'))
      .toEqual({ dt_document__gte: 1, dt_document__lte: 9, contact_id: 5 });
  });
  it('sends only the bound that is set, on the default field when none is declared', () => {
    expect(periodFilters({ _period: { gte: 3 } }, 'dt_created')).toEqual({ dt_created__gte: 3 });
    expect(periodFilters({}, 'dt_document')).toEqual({});
  });
});
