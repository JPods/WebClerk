import { describe, expect, it } from 'vitest';
import { postable, type ReportRow } from './JournalizeReport';

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
