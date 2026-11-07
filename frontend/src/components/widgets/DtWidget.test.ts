import { describe, it, expect } from 'vitest';
import { dtToLocal, localToDt, localDay, localClock, monthGrid } from './DtWidget';

describe('DtWidget — stored UTC, shown local', () => {
  it('reads epoch ms, epoch seconds, an ISO instant and a datetime-local string as the same local moment', () => {
    const ms = Date.UTC(2026, 9, 25, 0, 0, 0);               // 2026-10-25T00:00Z
    const local = dtToLocal(ms)!;
    expect(dtToLocal(Math.floor(ms / 1000))!.getTime()).toBe(ms);
    expect(dtToLocal('2026-10-25T00:00:00Z')!.getTime()).toBe(ms);
    expect(dtToLocal(String(ms))!.getTime()).toBe(ms);
    const asLocalText = `${localDay(local)}T${localClock(local)}`;
    expect(dtToLocal(asLocalText)!.getTime()).toBe(ms);
  });

  it('shows the local day, not the UTC one (1041-cash: 10/24 19:00 -05 read 10/25)', () => {
    const d = new Date(2026, 9, 24, 19, 0);                    // local 2026-10-24 19:00
    expect(localDay(dtToLocal(d.toISOString()))).toBe('2026-10-24');
    expect(localClock(dtToLocal(d.getTime()))).toBe('19:00');
  });

  it('a day with no clock is 23:59:59.999 local, sent as the UTC instant', () => {
    const out = localToDt('2026-11-03', '')!;
    expect(out.endsWith('Z')).toBe(true);
    const back = new Date(out);
    expect([back.getFullYear(), back.getMonth(), back.getDate(), back.getHours(), back.getMinutes()]).toEqual([2026, 10, 3, 23, 59]);
  });

  it('a day and a clock are that local moment', () => {
    const back = new Date(localToDt('2026-11-03', '14:30')!);
    expect([back.getDate(), back.getHours(), back.getMinutes()]).toEqual([3, 14, 30]);
  });

  it('no day is no dt; a bare stored date reads as the end of that local day', () => {
    expect(localToDt('', '14:30')).toBeNull();
    expect(dtToLocal(null)).toBeNull();
    expect(dtToLocal(0)).toBeNull();
    expect(localClock(dtToLocal('2026-11-03'))).toBe('23:59');
  });
});

describe('DtWidget — the month grid', () => {
  it('shows six Sunday-first weeks around the month (November 2026 opens on Sunday the 1st)', () => {
    const grid = monthGrid(2026, 10);
    expect(grid).toHaveLength(42);
    expect(grid[0].getDay()).toBe(0);
    expect([grid[0].getMonth(), grid[0].getDate()]).toEqual([10, 1]);
    expect([grid[41].getMonth(), grid[41].getDate()]).toEqual([11, 12]);
  });

  it('a month that starts mid-week leads with the end of the month before (October 2026 starts Thursday)', () => {
    const grid = monthGrid(2026, 9);
    expect([grid[0].getMonth(), grid[0].getDate()]).toEqual([8, 27]);
    expect([grid[4].getMonth(), grid[4].getDate()]).toEqual([9, 1]);
  });
});
