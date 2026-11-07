import { describe, expect, it, vi } from 'vitest';
vi.mock('@/api/wcapi', () => ({ getRecord: vi.fn(), getRecords: vi.fn() }));
import { renderPrintHtml } from './TransactionPrint';
import { formatValue } from '@/components/print/UniversalPrint';
import { SHIPPED_FORMATTING, resolveFormatting } from '@/utils/formatting';

const quote = { ida: '1108-qt', status: 'planned', company: 'Acme', totals: { amount: 1234.5, tax: 61.73, total: 1296.23 },
  lines: [{ item: { ida_item: 'AF-2011', description: 'Boost' }, quantity: { active: 2, remaining: 2 }, price: { unit: 617.25 }, totals: { amount: 1234.5 } }] };

describe("a customer's currency reaches its quote's print", () => {
  it('the detail print shows CA$ for a CAD customer and $ for the rest', () => {
    const cad = resolveFormatting(SHIPPED_FORMATTING, { defaults: { formatting: { currency: 'CAD' } } });
    const html = renderPrintHtml(quote, { name: 'Us' }, {}, 'quote', null, '', cad);
    expect(html).toContain('total: CA$1,296.23');
    expect(html).toContain('tax: CA$61.73');
    const usd = renderPrintHtml(quote, { name: 'Us' }, {}, 'quote', null, '');
    expect(usd).toContain('total: $1,296.23');
  });

  it('the universal print formats every money cell in the formatting it is given', () => {
    const cad = resolveFormatting(SHIPPED_FORMATTING, { defaults: { formatting: { currency: 'CAD', number_precision: 3 } } });
    expect(formatValue(1296.23, 'currency', cad)).toBe('CA$1,296.230');
    expect(formatValue(1296.23, 'number', SHIPPED_FORMATTING)).toBe('1,296.23');
  });
});
