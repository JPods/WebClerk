import { describe, expect, it } from 'vitest';
import { fileNameOf, thisMonth } from './SendPeriodToAccounting';

describe('SendPeriodToAccounting', () => {
  it('names the month as the endpoint takes it', () => {
    expect(thisMonth(new Date(2026, 10, 27))).toBe('2026-11');
    expect(thisMonth(new Date(2027, 0, 3))).toBe('2027-01');
  });
  it('keeps the file name the server gave', () => {
    expect(fileNameOf('attachment; filename="2026-11_gl_journal.csv"', '2026-11')).toBe('2026-11_gl_journal.csv');
    expect(fileNameOf(undefined, '2026-11')).toBe('2026-11_gl_journal');
  });
});
