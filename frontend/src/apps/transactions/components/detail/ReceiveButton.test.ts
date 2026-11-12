import { describe, expect, it } from 'vitest';
import { waitingToReceive } from './ReceiveButton';

describe('waitingToReceive', () => {
  it('is what a held receipt has planned and not yet received', () => {
    expect(waitingToReceive({ lines: [{ quantity: { staged: 5, active: 0 } }, { quantity: { staged: 4, active: 1 } }] })).toBe(8);
  });
  it('is nothing once every line is received, or over-received', () => {
    expect(waitingToReceive({ lines: [{ quantity: { staged: 5, active: 5 } }, { quantity: { staged: 2, active: 3 } }] })).toBe(0);
  });
  it('is nothing for a receipt with no lines', () => {
    expect(waitingToReceive({})).toBe(0);
    expect(waitingToReceive(null)).toBe(0);
  });
});
