import { describe, expect, it } from 'vitest';
import { orderedObjects } from './JsonSectionRenderer';

describe('json panel — every object the viewer may see; the layout orders and hides', () => {
  const available = ['company', 'addresses', 'emails', 'phones', 'totals', 'metadata', 'refs', 'prefs'];

  it('with no layout list shows them all, as the model has them', () => {
    expect(orderedObjects(available)).toEqual(available);
  });

  it('puts the layout\'s objects first, in its order, then the rest', () => {
    expect(orderedObjects(available, ['totals', 'addresses'])).toEqual(
      ['totals', 'addresses', 'company', 'emails', 'phones', 'metadata', 'refs', 'prefs']);
  });

  it('drops a name the server does not give, and the ones the layout hides', () => {
    expect(orderedObjects(['totals', 'refs'], ['sell', 'totals'], ['refs'])).toEqual(['totals']);
  });
});
