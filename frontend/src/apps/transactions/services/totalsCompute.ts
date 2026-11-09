/**
 * totalsCompute — the browser's copy of the server's one totals engine (readme 107).
 *
 * Bill, 2026-11-08: "have the front end manage calculations until transactions are saved …
 * The front end and backend calculations must match." This file mirrors
 * backend/apps/transactions/services/pricing/totals_compute.py compute_totals() line for
 * line, with exact decimal arithmetic (dec.ts). It is a preview: the save stores what the
 * server computes (server is truth, Bill 2026-11-04), and a difference is reported at save.
 *
 * The match is guarded by one fixture: backend/tests/test_totals_fixture.py runs the server's
 * compute_totals on every case and writes __tests__/fixtures/totals_cases.json; the vitest
 * alignment test runs this engine on the same cases and expects the same figures, exactly.
 * Change the server's rule → regenerate the fixture → this file must follow.
 *
 * Inputs the browser does not hold come in `ctx` (the record's calc_context from the GET,
 * plus the settlement figures carried from the loaded record — they are journal facts, not
 * arithmetic, and cannot change while editing).
 */
import { Dec, dec, sum } from './dec';

export const SELL_SIDE = ['quote', 'order', 'invoice'];
export const LINE_TOTAL_KEYS = ['amount', 'discount', 'taxable', 'tax', 'shipping', 'other',
                                'finance_charge', 'cost', 'margin', 'total'] as const;
const LANDED_COMPONENTS = ['freight', 'duty', 'handling', 'vat'] as const;
const LANDED_BASES = ['value', 'weight', 'quantity'];
const TO_KG: Record<string, string> = { kg: '1', g: '0.001', lb: '0.45359237', lbs: '0.45359237', oz: '0.028349523125' };

export interface ShippingService {
  name?: string; carrier_code?: string; account?: string; aliases?: string[];
  rate_method?: string; rate_percent?: number | string;
}

/** What the server reads from outside the document: the record's `calc_context` (GET) and
 *  the settlement figures from its stored totals. */
export interface CalcContext {
  tax_policy?: { tax_on_shipping?: boolean; tax_on_costs?: boolean };
  shipping_services?: ShippingService[];
  customer_exempt?: boolean;
  settlement: { received: number | string; adjusted: number | string; settled: number | string };
}

export interface LineTotals {
  amount: number; discount: number; taxable: number; tax: number; shipping: number; other: number;
  finance_charge: number; cost: number; margin: number; total: number;
  discounted_unit?: number; tax_rate?: number; rate_source?: string;
  landed?: Record<string, number>;
}

export interface ComputedTotals {
  totals: Record<string, number | string>;
  /** Parallel to the `lines` given; null for an inactive line. */
  lineTotals: (LineTotals | null)[];
}

export function isSellSide(model: string): boolean { return SELL_SIDE.includes(model); }

/** The server's _settlement, as the loaded record carries it (totals written by the last save). */
export function settlementOf(record: any, model: string): CalcContext['settlement'] {
  const t = record?.totals || {};
  if (model === 'invoice') return { received: t.received ?? 0, adjusted: t.adjusted ?? 0, settled: t.received ?? 0 };
  if (model === 'receipt') return { received: t.received ?? 0, adjusted: t.adjusted ?? 0, settled: t.paid ?? 0 };
  return { received: t.received ?? 0, adjusted: t.adjusted ?? 0, settled: t.received ?? 0 };
}

const num = (env: any, key: string, places = 2): Dec => dec((env || {})[key] || 0, places);

/** Split total by weight in exact cents; the last share takes the remainder. */
function allocate(total: Dec, weights: Dec[]): Dec[] {
  const n = weights.length;
  if (n === 0 || total.isZero()) return weights.map(() => Dec.zero);
  let base = sum(weights);
  if (base.isZero()) { weights = weights.map(() => dec(1)); base = dec(n); }
  const shares: Dec[] = [];
  let given = Dec.zero;
  weights.forEach((w, i) => {
    const share = i === n - 1 ? total.sub(given) : total.mul(w).div(base).quantize(2);
    shares.push(share);
    given = given.add(share);
  });
  return shares;
}

function discountedUnit(unit: Dec, qty: Dec, pct: Dec, flat: Dec, places: number): Dec {
  const byPct = unit.mul(pct).div(dec(100));
  const byFlat = qty.isZero() ? Dec.zero : flat.div(qty);
  let best = byPct.gt(byFlat) ? byPct : byFlat;
  if (best.lt(Dec.zero)) best = Dec.zero;
  return unit.sub(best).quantize(places);
}

function lineLabel(line: any): string { return `line ${line.line_number || line.id || '?'}`; }

function unitWeightKg(line: any): Dec | null {
  const weight = line.physical?.weight;
  if (!weight || typeof weight !== 'object') return null;
  const value = dec(weight.value || 0, 6);
  if (!value.gt(Dec.zero)) return null;
  const unit = String(weight.unit || '').trim().toLowerCase();
  if (!(unit in TO_KG)) {
    throw new Error(`${lineLabel(line)}: weight unit '${unit}' is not one of ${Object.keys(TO_KG).sort().join(', ')} — set it before spreading by weight.`);
  }
  return value.mul(dec(TO_KG[unit], -1));
}

function percentOfGoodsShipping(shipVia: string, goods: Dec, services: ShippingService[]): Dec | null {
  const wanted = (shipVia || '').trim().toLowerCase();
  if (!wanted) return null;
  const svc = services.find((s) => {
    const keys = new Set([s.name, s.carrier_code, s.account, ...(s.aliases || [])].map((k) => String(k ?? '').trim().toLowerCase()));
    return keys.has(wanted);
  });
  if (!svc || svc.rate_method !== 'percent_of_goods') return null;
  return goods.mul(dec(svc.rate_percent || 0, -1)).div(dec(100)).quantizeHalfEven(2);
}

type Good = { line: any; qty: Dec; unit: Dec; lineUnit: Dec; places: number };

function spreadLanded(comp: string, total: Dec, basis: string, goods: Good[], amounts: Map<any, Dec>): Dec[] {
  if (!LANDED_BASES.includes(basis)) throw new Error(`allocations.method.${comp} is '${basis}'; use one of ${LANDED_BASES.join(', ')}.`);
  const pins = new Map<any, Dec>();
  for (const g of goods) {
    const pin = g.line.cost?.landed_override?.[comp];
    if (pin !== null && pin !== undefined) pins.set(g.line, dec(pin));
  }
  const pinned = sum([...pins.values()]);
  if (pinned.gt(total)) throw new Error(`The lines pin ${pinned} of ${comp}, but the receipt's ${comp} is ${total}. Lower a pinned share or raise the receipt's ${comp}.`);
  const free = goods.filter((g) => !pins.has(g.line));
  if (goods.length && !free.length && !pinned.eq(total)) {
    throw new Error(`Every line pins its ${comp} and they add to ${pinned}, not the receipt's ${total}. Clear one pin so that line takes the remainder, or make the pins add up.`);
  }
  let used = basis;
  let kgs: (Dec | null)[] = [];
  if (basis === 'weight') {
    kgs = free.map((g) => unitWeightKg(g.line));
    if (kgs.some((kg) => kg === null)) used = 'value';
  }
  let weights: Dec[];
  if (used === 'weight') weights = free.map((g, i) => g.qty.mul(kgs[i] as Dec));
  else if (used === 'quantity') weights = free.map((g) => g.qty);
  else weights = free.map((g) => amounts.get(g.line) as Dec);
  const spread = new Map<any, Dec>();
  allocate(total.sub(pinned), weights).forEach((s, i) => spread.set(free[i].line, s));
  return goods.map((g) => pins.get(g.line) ?? spread.get(g.line) ?? Dec.zero);
}

function cashState(total: Dec, received: Dec): string {
  if (total.eq(received)) return 'paid';
  if (received.isZero()) return total.lt(Dec.zero) ? 'credit' : 'open';
  if (received.sign() !== total.sign() || received.abs().gt(total.abs())) return 'over';
  return 'partial';
}

/** compute_totals, exactly. `header` is the edited document (finance, tax, allocations, ship_via),
 *  `lines` its lines on screen (inactive ones answered null). Throws the server's own refusal
 *  sentences where the server would refuse. */
export function computeTotals(header: any, lines: any[], model: string, ctx: CalcContext): ComputedTotals {
  const isSell = isSellSide(model);
  const policy = { tax_on_shipping: !!ctx.tax_policy?.tax_on_shipping, tax_on_costs: !!ctx.tax_policy?.tax_on_costs };
  const active = lines.map((l) => (l?.is_active ?? true) !== false ? l : null);
  const live = active.filter((l) => l) as any[];

  const finance = header?.finance || {};
  let headerTaxRate = dec(finance.sales_tax_rate || 0, 6);
  if (headerTaxRate.gt(dec(1))) headerTaxRate = headerTaxRate.div(dec(100));
  const taxEnv = header?.tax || {};
  let isExempt = !!(taxEnv.exempt_code || finance.tax_exempt_id || finance.tax_exempt);
  if (!isExempt) isExempt = !!ctx.customer_exempt;
  let shippingTaxRate = dec(taxEnv.shipping || finance.tax_on_shipping_rate || 0, 6);
  if (shippingTaxRate.gt(dec(1))) shippingTaxRate = shippingTaxRate.div(dec(100));
  if (isExempt || !policy.tax_on_shipping) shippingTaxRate = Dec.zero;

  const alloc = header?.allocations || {};
  let docPct = dec(alloc.discount_percent || 0, 6);
  const docAmt = dec(alloc.discount_amount || 0);
  const docShipping = dec(alloc.shipping || 0);
  const docOther = dec(alloc.other || 0);
  const landed: Record<string, Dec> = {};
  if (model === 'receipt') for (const k of LANDED_COMPONENTS) landed[k] = dec(alloc[k] || 0);

  // ── Pass 1: each product line's discounted unit before the document discount ──
  const goods: Good[] = [];
  for (const line of live) {
    if ((line.line_type || 'product') !== 'product') continue;
    const qty = num(line.quantity, 'active', 6);
    const env = (isSell ? line.price : line.cost) || {};
    const places = Number(env.precision || 2) || 2;
    const unit = num(env, 'unit', 6);
    const lineUnit = discountedUnit(unit, qty, num(env, 'discount_percent', 6), num(env, 'discount_amount'), places);
    goods.push({ line, qty, unit, lineUnit, places });
  }
  goods.sort((a, b) => (Number(a.line.line_number) || 0) - (Number(b.line.line_number) || 0)
                    || (Number(a.line.id) || 0) - (Number(b.line.id) || 0));

  if (!goods.length) {
    const stranded = [['discount_percent', docPct], ['discount_amount', docAmt], ['shipping', docShipping],
                      ['other', docOther], ...Object.entries(landed)]
      .filter(([, v]) => !(v as Dec).isZero()).map(([k]) => k as string);
    if (stranded.length) {
      const one = stranded.length === 1;
      throw new Error(`This ${model} has ${stranded.join(', ')} but no product line to carry ${one ? 'it' : 'them'}. Add a product line, or clear ${one ? 'that allocation' : 'those allocations'}.`);
    }
  }

  // ── The document discount, as a per-unit reduction ──
  const docShare = new Map<any, Dec>();
  if (isSell && goods.length && (!docPct.isZero() || !docAmt.isZero())) {
    const pre = goods.map((g) => g.qty.mul(g.lineUnit).quantize(2));
    if (!docAmt.isZero() && docAmt.gte(sum(pre).mul(docPct).div(dec(100)).quantize(2))) {
      docPct = Dec.zero;
      allocate(docAmt, pre).forEach((share, i) => docShare.set(goods[i].line, share));
    }
  }

  const lineTotals = new Map<any, Record<string, any>>();
  const amounts = new Map<any, Dec>();
  for (const g of goods) {
    const { line, qty, unit, lineUnit, places } = g;
    let du: Dec;
    if (!docPct.isZero()) du = lineUnit.mul(dec(1).sub(docPct.div(dec(100)))).quantize(places);
    else if (docShare.has(line) && !qty.isZero()) du = lineUnit.sub((docShare.get(line) as Dec).div(qty)).quantize(places);
    else du = lineUnit;
    const amount = qty.mul(du).quantize(2);
    const gross = qty.mul(unit).quantize(2);
    amounts.set(line, amount);

    const costEnv = line.cost || {};
    const cplaces = Number(costEnv.precision || 2) || 2;
    const costUnit = discountedUnit(num(costEnv, 'unit', 6), qty, num(costEnv, 'discount_percent', 6), num(costEnv, 'discount_amount'), cplaces);
    const cost = isSell ? qty.mul(costUnit).quantize(2) : amount;

    const lineTax = line.tax || {};
    const typed = num(lineTax, 'sales_rate', 6);
    const taxCode = String(costEnv.tax_code || '').toUpperCase();
    let rate: Dec; let source: string;
    if (isExempt) { rate = Dec.zero; source = 'exempt'; }
    else if (lineTax.rate_source === 'line') { rate = typed.gt(dec(1)) ? typed.div(dec(100)) : typed; source = 'line'; }
    else if (!isSell && !policy.tax_on_costs) { rate = Dec.zero; source = 'costs_not_taxed'; }
    else if (['EXEMPT', 'NONTAXABLE', 'NON-TAXABLE'].includes(taxCode)) { rate = Dec.zero; source = 'item_exempt'; }
    else { rate = headerTaxRate; source = 'header'; }

    lineTotals.set(line, {
      discounted_unit: du.toNumber(),
      amount,
      discount: isSell ? gross.sub(amount) : Dec.zero,
      taxable: rate.gt(Dec.zero) ? amount : Dec.zero,
      tax_rate: rate.toNumber(),
      rate_source: source,
      tax: amount.mul(rate).quantize(2),
      shipping: num(costEnv, 'shipping').add(num(costEnv, 'handling')),
      other: Dec.zero,
      finance_charge: Dec.zero,
      cost,
    });
  }

  // ── Document shipping (+ ship-via % of goods) and other: exact cents by amount ──
  const goodsAmount = sum([...amounts.values()]);
  let shippingToSpread = docShipping;
  if (isSell) {
    const charge = percentOfGoodsShipping(header?.ship_via || '', goodsAmount, ctx.shipping_services || []);
    if (charge !== null) shippingToSpread = shippingToSpread.add(charge);
  }
  const weights = goods.map((g) => amounts.get(g.line) as Dec);
  const sShares = allocate(shippingToSpread, weights);
  const oShares = allocate(docOther, weights);
  goods.forEach((g, i) => {
    const lt = lineTotals.get(g.line)!;
    lt.shipping = lt.shipping.add(sShares[i]);
    lt.other = lt.other.add(oShares[i]);
  });

  // ── A receipt's landed costs: freight into shipping, the rest into other ──
  if (model === 'receipt') {
    const methods = alloc.method ?? {};
    if (typeof methods !== 'object' || Array.isArray(methods)) {
      throw new Error("allocations.method names a basis for each landed cost, e.g. {'freight': 'weight', 'duty': 'value'} — not a single word.");
    }
    for (const comp of LANDED_COMPONENTS) {
      const shares = spreadLanded(comp, landed[comp], methods[comp] || 'value', goods, amounts);
      goods.forEach((g, i) => {
        const lt = lineTotals.get(g.line)!;
        (lt.landed ??= {})[comp] = shares[i].toNumber();
        const key = comp === 'freight' ? 'shipping' : 'other';
        lt[key] = lt[key].add(shares[i]);
      });
    }
  }

  // ── Non-product lines ──
  for (const line of live) {
    const type = line.line_type || 'product';
    if (type === 'product') continue;
    const qty = num(line.quantity, 'active', 6);
    const env = (isSell ? line.price : line.cost) || {};
    const value = qty.mul(num(env, 'unit', 6)).quantize(2);
    const t: Record<string, any> = Object.fromEntries(LINE_TOTAL_KEYS.map((k) => [k, Dec.zero]));
    if (type === 'tax') t.tax = value;
    else if (type === 'shipping') t.shipping = value;
    else if (type === 'finance_charge') t.finance_charge = value;
    else if (type === 'discount' && isSell) { t.amount = value.abs().neg(); t.discount = value.abs(); }
    lineTotals.set(line, t);
  }

  // ── Finish each line: tax on its shipping, margin, total ──
  for (const t of lineTotals.values()) {
    for (const k of LINE_TOTAL_KEYS) t[k] ??= Dec.zero;
    if (!t.shipping.isZero() && !shippingTaxRate.isZero()) {
      t.tax = t.tax.add(t.shipping.mul(shippingTaxRate).quantize(2));
      t.taxable = t.taxable.add(t.shipping);
    }
    t.margin = isSell ? t.amount.sub(t.cost) : Dec.zero;
    t.total = t.amount.add(t.tax).add(t.shipping).add(t.other).add(t.finance_charge);
  }

  // ── The document: Σ of its lines ──
  const doc: Record<string, Dec> = {};
  for (const k of LINE_TOTAL_KEYS) doc[k] = sum([...lineTotals.values()].map((t) => t[k]));
  const marginPc = doc.amount.gt(Dec.zero) ? doc.margin.mul(dec(100)).div(doc.amount).quantize(2).toNumber() : 0;

  const received = dec(ctx.settlement.received);
  const adjusted = dec(ctx.settlement.adjusted);
  const settled = dec(ctx.settlement.settled);
  const balance = doc.total.sub(settled).sub(adjusted);
  const state = model === 'invoice' ? cashState(doc.total.quantize(2), received.add(adjusted).quantize(2)) : '';

  const totals: Record<string, number | string> = Object.fromEntries(Object.entries(doc).map(([k, v]) => [k, v.toNumber()]));
  Object.assign(totals, { margin_pc: marginPc, received: received.toNumber(), adjusted: adjusted.toNumber(),
                          balance: balance.toNumber(), cash_state: state });
  if (model === 'receipt') {
    for (const k of LANDED_COMPONENTS) totals[k] = landed[k].toNumber();
    totals.paid = settled.toNumber();
  }

  const asNumbers = (t: Record<string, any>): LineTotals =>
    Object.fromEntries(Object.entries(t).map(([k, v]) => [k, v instanceof Dec ? v.toNumber() : v])) as LineTotals;
  return {
    totals,
    lineTotals: active.map((l) => (l && lineTotals.has(l) ? asNumbers(lineTotals.get(l)!) : null)),
  };
}
