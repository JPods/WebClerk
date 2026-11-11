import { describe, expect, it } from 'vitest';
import { convertLines, convertRows } from '../WorkflowSelect';

const record = { lines: [
  { id: 1, line_number: 1, item: { ida_item: 'AF-2011', description: 'Charger' }, quantity: { remaining: 7 } },
  { id: 2, line_number: 2, item: { ida_item: 'BB200' }, quantity: { remaining: 0 } },
  { id: 3, line_number: 3, item: {}, quantity: { remaining: 2 }, _removed: true },
  { id: 4, line_number: 4, item: { description: 'Cable' }, quantity: { remaining: 3 } },
] };

describe('a conversion asks its quantities (Bill, 2026-11-11)', () => {
  it('offers the saved lines with something left, at what is left', () => {
    expect(convertRows(record)).toEqual([
      { line_id: 1, left: 7, qty: '7', label: 'AF-2011 — Charger' },
      { line_id: 4, left: 3, qty: '3', label: 'Cable' },
    ]);
  });
  it('sends no lines when nothing was changed: the server takes everything left', () => {
    expect(convertLines(convertRows(record))).toBeNull();
  });
  it('sends every line above 0 when one was changed, and leaves a 0 out', () => {
    const rows = convertRows(record);
    rows[0].qty = '5';
    expect(convertLines(rows)).toEqual([{ line_id: 1, qty: 5 }, { line_id: 4, qty: 3 }]);
    rows[1].qty = '0';
    expect(convertLines(rows)).toEqual([{ line_id: 1, qty: 5 }]);
  });
  it('a record without lines offers nothing (the plain question is asked instead)', () => {
    expect(convertRows({})).toEqual([]);
  });
});
