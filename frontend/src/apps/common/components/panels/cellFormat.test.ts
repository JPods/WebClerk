import { describe, expect, it } from 'vitest';
import { formatCell } from './cellFormat';

describe('formatCell — money keeps its cents', () => {
  it('a column saved as currency shows .00 even when the behavior typed it number', () => {
    // cash.available: behavior type number, column format currency — 115.50 once showed as 116
    expect(formatCell(115.5, 'available', { type: 'number', format: 'currency' })).toBe('115.50');
  });
  it('a plain number column keeps whole units', () => {
    expect(formatCell(115.5, 'count', { type: 'number' })).toBe('116');
  });
});
