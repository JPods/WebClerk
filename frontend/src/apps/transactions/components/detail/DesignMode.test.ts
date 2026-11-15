import { describe, it, expect } from 'vitest';
import { moveField, shiftWeight } from './DesignMode';
import { columnTemplate } from './HeaderRenderer';

const cols = () => [
  { title: 'a', fields: [{ field: 'a1' }, { field: 'a2' }, { field: 'a3' }] },
  { title: 'b', fields: [{ field: 'b1' }] },
  { title: 'c', fields: [] },
];
const names = (c: any[]) => c.map((x) => x.fields.map((f: any) => f.field));

describe('design mode: a field is dragged', () => {
  it('down within its card', () => {
    expect(names(moveField(cols(), { col: 0, idx: 0 }, { col: 0, idx: 2 }))).toEqual([['a2', 'a1', 'a3'], ['b1'], []]);
  });
  it('up within its card', () => {
    expect(names(moveField(cols(), { col: 0, idx: 2 }, { col: 0, idx: 0 }))).toEqual([['a3', 'a1', 'a2'], ['b1'], []]);
  });
  it('to another card, before a field', () => {
    expect(names(moveField(cols(), { col: 0, idx: 1 }, { col: 1, idx: 0 }))).toEqual([['a1', 'a3'], ['a2', 'b1'], []]);
  });
  it('to the end of an empty card', () => {
    expect(names(moveField(cols(), { col: 1, idx: 0 }, { col: 2, idx: 0 }))).toEqual([['a1', 'a2', 'a3'], [], ['b1']]);
  });
  it('leaves the columns it was given untouched', () => {
    const before = cols();
    moveField(before, { col: 0, idx: 0 }, { col: 1, idx: 1 });
    expect(names(before)).toEqual([['a1', 'a2', 'a3'], ['b1'], []]);
  });
});

describe('design mode: the bar between two cards is dragged', () => {
  it('moves width from one card to its neighbour and keeps the pair total', () => {
    const next = shiftWeight(cols(), 0, 0.1);          // a tenth of the row, three cards of 1
    expect(next[0].weight).toBeCloseTo(1.3);
    expect(next[1].weight).toBeCloseTo(0.7);
    expect(next[2].weight).toBeUndefined();
  });
  it('never closes a card', () => {
    const next = shiftWeight(cols(), 0, -5);
    expect(next[0].weight).toBeGreaterThan(0);
    expect(next[0].weight + next[1].weight).toBeCloseTo(2);
  });
});

describe('a header row of cards', () => {
  it('shares the row equally when no card has a weight, whatever its number of fields', () => {
    expect(columnTemplate(cols())).toBe('minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr)');
  });
  it('gives each card its weight', () => {
    expect(columnTemplate([{ weight: 1.3 }, { weight: 0.7 }, {}])).toBe('minmax(0, 1.3fr) minmax(0, 0.7fr) minmax(0, 1fr)');
  });
});
