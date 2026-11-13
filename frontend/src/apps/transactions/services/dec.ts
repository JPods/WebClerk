/**
 * dec — exact decimal arithmetic for the browser's totals (readme 107).
 *
 * The server computes with Python Decimal and quantizes ROUND_HALF_UP (common/decimals.py
 * safe_decimal). A float `Math.round` is not that: round(8.575) gave 8.57 where the server
 * stores 8.58 (2026-11-08). Every figure here is a BigInt scaled by 10^18, so products of the
 * document's inputs (quantities and units to 6 places, money to 2) are exact, and quantize
 * rounds half away from zero on the exact digits — the same arithmetic as Decimal.quantize.
 *
 * Division truncates at the 18th place; the server's Decimal keeps 28 significant digits.
 * Both then quantize, so they agree unless the exact quotient sits within 1e-18 of a half-cent
 * boundary — the pytest-written fixture (test_totals_fixture.py) is the guard.
 */

const SCALE = 18;
const ONE = 10n ** BigInt(SCALE);

export class Dec {
  constructor(readonly m: bigint) {}

  static zero = new Dec(0n);

  add(o: Dec): Dec { return new Dec(this.m + o.m); }
  sub(o: Dec): Dec { return new Dec(this.m - o.m); }
  neg(): Dec { return new Dec(-this.m); }
  abs(): Dec { return new Dec(this.m < 0n ? -this.m : this.m); }
  /** Exact for inputs with ≤ 9 places each; truncates beyond the 18th place otherwise. */
  mul(o: Dec): Dec { return new Dec((this.m * o.m) / ONE); }
  /** Truncated at the 18th place (toward zero), as BigInt division is. */
  div(o: Dec): Dec {
    if (o.m === 0n) throw new Error('division by zero');
    return new Dec((this.m * ONE) / o.m);
  }
  /** Round half away from zero to `places` — Decimal.quantize(ROUND_HALF_UP). */
  quantize(places: number): Dec {
    const step = 10n ** BigInt(SCALE - places);
    const q = this.m / step;          // toward zero
    const r = this.m % step;          // sign of this.m
    const twice = r < 0n ? -r * 2n : r * 2n;
    const bump = twice >= step ? (this.m < 0n ? -1n : 1n) : 0n;
    return new Dec((q + bump) * step);
  }

  isZero(): boolean { return this.m === 0n; }
  gt(o: Dec): boolean { return this.m > o.m; }
  gte(o: Dec): boolean { return this.m >= o.m; }
  lt(o: Dec): boolean { return this.m < o.m; }
  eq(o: Dec): boolean { return this.m === o.m; }
  sign(): number { return this.m === 0n ? 0 : this.m < 0n ? -1 : 1; }

  /** The number the server's float(Decimal) gives; never -0. */
  toNumber(): number {
    const n = Number(this.toString());
    return n === 0 ? 0 : n;
  }

  toString(): string {
    const neg = this.m < 0n;
    const digits = (neg ? -this.m : this.m).toString().padStart(SCALE + 1, '0');
    const whole = digits.slice(0, -SCALE);
    const frac = digits.slice(-SCALE).replace(/0+$/, '');
    return (neg ? '-' : '') + whole + (frac ? '.' + frac : '');
  }
}

/** Parse a number or numeric string exactly, as Decimal(str(value)) does. */
function parse(value: unknown): bigint | null {
  if (value === null || value === undefined || value === '') return null;
  if (typeof value === 'boolean') return null;
  let s = typeof value === 'number' ? String(value) : String(value).trim();
  if (!s || s === 'NaN' || s === 'Infinity' || s === '-Infinity') return null;
  let neg = false;
  if (s[0] === '-' || s[0] === '+') { neg = s[0] === '-'; s = s.slice(1); }
  // 1e-7 → shift the point
  let exp = 0;
  const e = s.search(/[eE]/);
  if (e >= 0) { exp = parseInt(s.slice(e + 1), 10); s = s.slice(0, e); if (!Number.isFinite(exp)) return null; }
  if (!/^\d*\.?\d*$/.test(s) || s === '.') return null;
  let [whole, frac = ''] = s.split('.');
  if (exp > 0) { frac = frac.padEnd(exp, '0'); whole += frac.slice(0, exp); frac = frac.slice(exp); }
  else if (exp < 0) { whole = whole.padStart(-exp + 1, '0'); frac = whole.slice(exp) + frac; whole = whole.slice(0, exp); }
  if (frac.length > SCALE) frac = frac.slice(0, SCALE);   // beyond the 18th place is noise here
  const m = BigInt((whole || '0') + frac.padEnd(SCALE, '0'));
  return neg ? -m : m;
}

/**
 * The server's safe_decimal: coerce, quantize half-up to `places` (−1: no quantize), 0 on
 * anything unparseable.
 */
export function dec(value: unknown, places = 2): Dec {
  const m = parse(value);
  if (m === null) return Dec.zero;
  const d = new Dec(m);
  return places >= 0 ? d.quantize(places) : d;
}

export function sum(values: Dec[]): Dec {
  return values.reduce((s, v) => s.add(v), Dec.zero);
}
