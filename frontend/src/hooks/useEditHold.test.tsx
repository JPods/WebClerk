/**
 * useEditHold — one hold per mount. React's StrictMode mounts, unmounts and remounts every effect in
 * development; the hook used to send hold, release, hold, three requests the server may run in any
 * order on its threads, so a late release could drop the hold the form believes it has (allie-25
 * audit, 2026-11-25).
 */
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { act, cleanup, renderHook } from '@testing-library/react';

const post = vi.fn();
vi.mock('@/api/axios', () => ({ default: { post: (...a: any[]) => post(...a) } }));

import { useEditHold } from './useEditHold';

const mine = { data: { data: { result: { mine: true, held_by: 'Bill James', until: '2026-11-26T15:00:00Z', minutes: 15 } } } };
const calls = () => post.mock.calls.map(([url]) => url as string);
// The option, not a <StrictMode> wrapper: as a renderHook wrapper it does not double the effects.
const strict = { reactStrictMode: true } as const;

beforeEach(() => {
  vi.useFakeTimers();
  post.mockReset();
  post.mockResolvedValue(mine);
});
// Unmount and flush the deferred release here, so no test's release lands in the next test.
afterEach(async () => {
  cleanup();
  await act(async () => { await vi.runOnlyPendingTimersAsync(); });
  vi.useRealTimers();
});

describe('useEditHold', () => {
  it('takes one hold per mount under StrictMode and sends no release while the form is open', async () => {
    renderHook(() => useEditHold('order', 188), strict);
    await act(async () => { await vi.runOnlyPendingTimersAsync(); });
    expect(calls()).toEqual(['/wcapi/order/188/hold/']);
  });

  it('gives the hold back once when the form closes', async () => {
    const hook = renderHook(() => useEditHold('order', 188), strict);
    await act(async () => { await vi.runOnlyPendingTimersAsync(); });
    hook.unmount();
    await act(async () => { await vi.runOnlyPendingTimersAsync(); });
    expect(calls()).toEqual(['/wcapi/order/188/hold/', '/wcapi/order/188/release/']);
  });

  it('moving to another record takes the new hold before giving the old one back', async () => {
    const hook = renderHook(({ id }) => useEditHold('order', id), { ...strict, initialProps: { id: 188 } });
    await act(async () => { await vi.runOnlyPendingTimersAsync(); });
    hook.rerender({ id: 189 });
    await act(async () => { await vi.runOnlyPendingTimersAsync(); });
    expect(calls()).toEqual(['/wcapi/order/188/hold/', '/wcapi/order/189/hold/', '/wcapi/order/188/release/']);
  });

  it('takes no hold without a record', async () => {
    renderHook(() => useEditHold('order', null), strict);
    await act(async () => { await vi.runOnlyPendingTimersAsync(); });
    expect(calls()).toEqual([]);
  });
});
