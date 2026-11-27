import { describe, expect, it } from 'vitest';
import { periodParams, postable, rowOptions, type ReportRow } from './JournalizeReport';

const row = (id: number, waiting = ''): ReportRow =>
  ({ id, ida: `${id}-inv`, status: 'released', party: '', total: 10, dt_created: 0, waiting, preview: null });

describe('postable', () => {
  it('sends only the ticked rows that are ready', () => {
    const rows = [row(1), row(2, 'Release it first'), row(3)];
    expect(postable(rows, new Set([1, 2]))).toEqual([1]);
    expect(postable(rows, new Set([2]))).toEqual([]);
    expect(postable(rows, new Set([1, 3]))).toEqual([1, 3]);
  });
});

describe('rowOptions', () => {
  const receipt = (id: number, unallocated?: Record<string, number>): ReportRow =>
    ({ ...row(id), unallocated });
  it('sends post_unallocated only for a posted row the person ticked for it', () => {
    const rows = [receipt(1, { freight: 5 }), receipt(2, { duty: 3 }), receipt(3)];
    expect(rowOptions(rows, [1, 2, 3], new Set([1, 3]))).toEqual({ '1': { post_unallocated: true } });
    expect(rowOptions(rows, [2], new Set([1]))).toEqual({});       // ticked, but not posted
    expect(rowOptions(rows, [1, 2], new Set())).toEqual({});       // never ticked by default
  });
});

describe('periodParams', () => {
  it('is a local day from its first to its last moment, in epoch ms', () => {
    const { begin, end } = periodParams('2026-11-02', '2026-11-08');
    expect(new Date(begin!).getHours()).toBe(0);
    expect(new Date(begin!).getDate()).toBe(2);
    expect(new Date(end!).getHours()).toBe(23);
    expect(new Date(end!).getMinutes()).toBe(59);
    expect(new Date(end!).getDate()).toBe(8);
  });
  it('sends neither bound when none is set', () => {
    expect(periodParams('', '')).toEqual({});
    expect(Object.keys(periodParams('2026-11-02', ''))).toEqual(['begin']);
  });
});
