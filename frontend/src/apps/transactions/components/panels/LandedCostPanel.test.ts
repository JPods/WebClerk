import { describe, it, expect } from 'vitest';
import { withLanded, landedUnit } from './LandedCostPanel';
import { computeTotals } from '../../services/totalsCompute';

describe('withLanded', () => {
  it('sets this line only, keeps the other charges, marks it dirty', () => {
    const line = { id: 1, cost: { unit: 5, landed: { freight: 2, duty: 1 } } };
    const out = withLanded(line, 'freight', 12.5);
    expect(out.cost.landed).toEqual({ freight: 12.5, duty: 1 });
    expect(out.cost.unit).toBe(5);
    expect(out._dirty).toBe(true);
    expect(line.cost.landed.freight).toBe(2);
  });
  it('starts cost.landed on a line that has none', () => {
    expect(withLanded({ id: 2, cost: { unit: 1 } }, 'vat', 0).cost.landed).toEqual({ vat: 0 });
  });
  it('never writes landed_override', () => {
    expect(withLanded({ id: 3, cost: {} }, 'duty', 4).cost).not.toHaveProperty('landed_override');
  });
});

describe('landedUnit', () => {
  it('is the discounted unit plus each share over qty', () => {
    const l = { quantity: { active: 7 }, totals: { discounted_unit: 9.15, landed: { freight: 7, duty: 3.5, handling: 0, vat: 0 } } };
    expect(landedUnit(l)).toBe(10.65);
  });
  it('is null without qty or totals', () => {
    expect(landedUnit({ quantity: { active: 0 }, totals: { discounted_unit: 1 } })).toBeNull();
    expect(landedUnit({ quantity: { active: 3 } })).toBeNull();
  });
});

describe('computeTotals on a receipt: a save never spreads (Bill, 2026-11-25)', () => {
  const ctx = { settlement: { received: 0, adjusted: 0, settled: 0 } };
  const line = (id: number, qty: number, unit: number, landed: Record<string, number> = {}) => ({
    id, line_number: id * 10, line_type: 'product', is_active: true,
    quantity: { active: qty }, cost: { unit, landed },
  });
  const header = { allocations: { freight: 10, duty: 0, handling: 0, vat: 3, method: { freight: 'value' } } };

  it('takes each line\'s cost.landed as typed and previews what is left unallocated', () => {
    const out = computeTotals(header, [line(1, 2, 5, { freight: 4 }), line(2, 1, 10)], 'receipt', ctx);
    expect(out.lineTotals[0]!.landed).toEqual({ freight: 4, duty: 0, handling: 0, vat: 0 });
    expect(out.lineTotals[1]!.landed).toEqual({ freight: 0, duty: 0, handling: 0, vat: 0 });
    expect(out.lineTotals[0]!.shipping).toBe(4);
    expect((out.totals as any).unallocated).toEqual({ freight: 6, duty: 0, handling: 0, vat: 3 });
    // What is owed does not depend on how the lines carry it: 20 goods + 10 freight + 3 vat.
    expect(out.totals.shipping).toBe(10);
    expect(out.totals.other).toBe(3);
    expect(out.totals.total).toBe(33);
    expect(out.totals.balance).toBe(33);
  });
  it('lines over the charge leave a negative unallocated, not a refusal', () => {
    const out = computeTotals(header, [line(1, 2, 5, { freight: 8 }), line(2, 1, 10, { freight: 5 })], 'receipt', ctx);
    expect((out.totals as any).unallocated.freight).toBe(-3);
  });
  it('a single-word method is still refused', () => {
    expect(() => computeTotals({ allocations: { method: 'value' } }, [line(1, 1, 1)], 'receipt', ctx))
      .toThrow(/not a single word/);
  });
});
