import { describe, expect, it } from 'vitest';
import { columnsOf, disagreements, type DefaultsRow } from './DefaultsConsole';

const row = (model: string, fields: Record<string, unknown>): DefaultsRow =>
  ({ model, settingId: 1, version: 1, fields, formatting: {}, lists: {} });

describe('DefaultsConsole — compare, not store', () => {
  it('marks the models whose shared value is not the one most models share', () => {
    const rows = [row('quote', { terms: 'N30' }), row('order', { terms: 'N30' }), row('customer', { terms: 'N10' }), row('contact', {})];
    expect([...disagreements(rows, 'terms')]).toEqual(['customer']);
    expect(disagreements(rows, 'priority').size).toBe(0);
  });

  it('a model without the field is not compared, and one voice is no disagreement', () => {
    expect(disagreements([row('quote', { terms: 'N30' }), row('contact', {})], 'terms').size).toBe(0);
  });

  it('lays the shared fields first, then whatever any model names', () => {
    const rows = [row('item', { status: 'active' }), row('quote', { terms: 'N30', ship_via: 'ups' })];
    expect(columnsOf(rows, ['terms', 'priority'])).toEqual(['terms', 'priority', 'status', 'ship_via']);
  });
});
