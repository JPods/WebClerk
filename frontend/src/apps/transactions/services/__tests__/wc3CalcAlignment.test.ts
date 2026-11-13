/**
 * The browser's totals equal the server's (Bill, 2026-11-08; readme 107).
 *
 * fixtures/totals_cases.json is written by the server: backend/tests/test_totals_fixture.py
 * runs compute_totals on every case and records its figures. This test replays the same cases
 * through the browser engine and expects the same figures, exactly — rounding, precision,
 * remainders and all. Do not edit the fixture by hand: regenerate it with
 * WC_TOTALS_FIXTURE_WRITE=1 pytest tests/test_totals_fixture.py.
 *
 * The first case is the drift that opened this work: 8.575 was 8.57 in the browser's float
 * round() and 8.58 on the server.
 */
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, it, expect } from 'vitest';
import { Dec, dec } from '../dec';
import { computeTotals, settlementOf } from '../totalsCompute';

interface Case {
  name: string; model: string; header: any; lines: any[];
  context: { tax_policy: any; shipping_services: any[]; customer_exempt: boolean;
             settlement: { received: number; adjusted: number; settled: number } };
  expect: { totals: Record<string, number | string>; line_totals: (Record<string, any> | null)[] };
}

const fixture = JSON.parse(readFileSync(join(__dirname, 'fixtures', 'totals_cases.json'), 'utf8'));
const cases: Case[] = fixture.cases;

describe('dec — Decimal arithmetic, half-up', () => {
  it('rounds half away from zero like safe_decimal', () => {
    expect(dec(8.575).toNumber()).toBe(8.58);
    expect(dec(1.005).toNumber()).toBe(1.01);
    expect(dec(2.675).toNumber()).toBe(2.68);
    expect(dec(-1.005).toNumber()).toBe(-1.01);
    expect(dec(1.2345, 3).toNumber()).toBe(1.235);
    expect(dec(1.2345, 0).toNumber()).toBe(1);
  });
  it('multiplies exactly where floats do not', () => {
    expect(dec(3, 6).mul(dec(12.345, 6)).toString()).toBe('37.035');
    expect(dec(0.1).add(dec(0.2)).toString()).toBe('0.3');
    expect(dec(7, 6).mul(dec(8.975, 6)).quantize(2).toNumber()).toBe(62.83);
  });
  it('rounds half up, the one rule (Bill, 2026-11-12)', () => {
    expect(dec('0.125', -1).quantize(2).toNumber()).toBe(0.13);
    expect(dec('0.135', -1).quantize(2).toNumber()).toBe(0.14);
    expect(dec('0.124', -1).quantize(2).toNumber()).toBe(0.12);
    expect(dec('-0.125', -1).quantize(2).toNumber()).toBe(-0.13);
  });
  it('coerces as Decimal(str(value)) and answers 0 for nonsense', () => {
    expect(dec('42.5').toNumber()).toBe(42.5);
    expect(dec(1e-7, 8).toString()).toBe('0.0000001');
    expect(dec(null).toNumber()).toBe(0);
    expect(dec('abc').toNumber()).toBe(0);
    expect(dec('').toNumber()).toBe(0);
    expect(Object.is(dec(-0.001).toNumber(), 0)).toBe(true);   // never -0
    expect(Dec.zero.toString()).toBe('0');
  });
});

describe('computeTotals replays the server fixture exactly', () => {
  it('has the drift case first', () => {
    expect(cases[0].name).toBe('half_up_8575_drift');
    expect(cases[0].expect.line_totals[0]!.discounted_unit).toBe(8.58);
  });

  it.each(cases.map((c) => [c.name, c] as const))('%s', (_name, c) => {
    const got = computeTotals(c.header, c.lines, c.model, c.context);
    // Through JSON, as the fixture is: the same keys, the same numbers, nothing extra.
    expect(JSON.parse(JSON.stringify(got.lineTotals))).toEqual(c.expect.line_totals);
    expect(JSON.parse(JSON.stringify(got.totals))).toEqual(c.expect.totals);
  });
});

describe('settlementOf — the journal facts the record carries', () => {
  it('reads an invoice and a receipt by their own keys', () => {
    expect(settlementOf({ totals: { received: 60, adjusted: 0.5, paid: 1 } }, 'invoice'))
      .toEqual({ received: 60, adjusted: 0.5, settled: 60 });
    expect(settlementOf({ totals: { received: 0, adjusted: 1.25, paid: 20 } }, 'receipt'))
      .toEqual({ received: 0, adjusted: 1.25, settled: 20 });
    expect(settlementOf({}, 'order')).toEqual({ received: 0, adjusted: 0, settled: 0 });
  });
});

describe('computeTotals refuses what the server refuses', () => {
  it('an allocation with no product line to carry it', () => {
    const header = { allocations: { shipping: 5 } };
    expect(() => computeTotals(header, [], 'order', { settlement: { received: 0, adjusted: 0, settled: 0 } }))
      .toThrow(/no product line to carry it/);
  });
  it('a weight unit it does not know', () => {
    const header = { allocations: { freight: 5, method: { freight: 'weight' } } };
    const lines = [{ id: 1, line_number: 1, quantity: { active: 1 }, cost: { unit: 10 }, physical: { weight: { value: 2, unit: 'stone' } } }];
    expect(() => computeTotals(header, lines, 'receipt', { settlement: { received: 0, adjusted: 0, settled: 0 } }))
      .toThrow(/weight unit 'stone'/);
  });
});
