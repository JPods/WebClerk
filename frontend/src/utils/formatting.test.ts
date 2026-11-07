import { describe, expect, it } from 'vitest';
import { SHIPPED_FORMATTING, dateText, formattingOf, money, number, resolveFormatting } from './formatting';

describe('formatting — the stored formatting, resolved and applied', () => {
  it("a model's precision change shows", () => {
    const quote = formattingOf({ defaults: { formatting: { number_precision: 3 } } });
    expect(money(1234.5, quote)).toBe('$1,234.500');
    expect(number(1234.5, quote)).toBe('1,234.500');
    expect(money(1234.5, SHIPPED_FORMATTING)).toBe('$1,234.50');
  });

  it("an org's currency and locale overlay its document's model, key by key", () => {
    const model = formattingOf({ defaults: { formatting: { number_precision: 2 } } });
    const acme = { defaults: { formatting: { currency: 'CAD', locale: 'en-CA' } } };
    const fmt = resolveFormatting(model, acme);
    expect(fmt).toEqual({ currency: 'CAD', locale: 'en-CA', date_format: 'short', number_precision: 2 });
    expect(money(1234.5, fmt)).toMatch(/\$1,234\.50$/);
    expect(money(1234.5, resolveFormatting(model, { defaults: { formatting: { currency: 'CAD' } } }))).toBe('CA$1,234.50');
    expect(resolveFormatting(model, { defaults: { formatting: {} } })).toEqual(model);
    expect(resolveFormatting(model, undefined)).toEqual(model);
  });

  it('a date in the stored style and locale', () => {
    const d = new Date(2026, 10, 7, 14, 30);
    expect(dateText(d, SHIPPED_FORMATTING)).toBe('11/7/2026');
    expect(dateText(d, { ...SHIPPED_FORMATTING, date_format: 'medium' })).toBe('Nov 7, 2026');
    expect(dateText(d, { ...SHIPPED_FORMATTING, locale: 'en-GB' })).toBe('07/11/2026');
  });

  it('an unknown currency still shows a number, never throws', () => {
    expect(money(5, { ...SHIPPED_FORMATTING, currency: 'NOPE' })).toBe('NOPE 5.00');
    expect(money('abc')).toBe('');
  });
});
