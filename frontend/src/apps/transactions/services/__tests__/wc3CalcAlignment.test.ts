/* LastChecked: 2026-03-14 | WhereUsed: TODO(wc3-schema-audit) | WhoCreated: Unknown */
/**
 * WC3 Calculation Alignment Tests
 *
 * Verifies that the React2025 frontend calculation utilities produce
 * identical results to the WC3 Django backend services.
 *
 * Backend reference:
 *   apps/transactions/models/base_line_model.py      — _calculate_extended_price()
 *
 * @see webClerk3/readmes/topics/transactions/transactions-totals.md
 */
import { describe, it, expect } from 'vitest';
import { round, toNumber, formatCurrency, formatPercent } from '../calculationUtils';
import { LineItemService, isSalesTransaction, isExecTransaction } from '../lineItemService';
import type { TransactionLine } from '../../types/transactionTypes';

// ============================================================================
// calculationUtils
// ============================================================================

describe('round()', () => {
  it('rounds to 2dp by default', () => {
    expect(round(1.005)).toBe(1.01);
    expect(round(1.004)).toBe(1);
    expect(round(100.555)).toBe(100.56);
  });
  it('rounds to custom precision', () => {
    expect(round(1.2345, 3)).toBe(1.235);
    expect(round(1.2345, 0)).toBe(1);
  });
  it('handles non-finite', () => {
    expect(round(NaN)).toBe(0);
    expect(round(Infinity)).toBe(0);
  });
});

describe('toNumber()', () => {
  it('coerces various types', () => {
    expect(toNumber('42.5')).toBe(42.5);
    expect(toNumber(null)).toBe(0);
    expect(toNumber(undefined)).toBe(0);
    expect(toNumber('')).toBe(0);
    expect(toNumber('abc')).toBe(0);
    expect(toNumber(0)).toBe(0);
  });
  it('uses fallback', () => {
    expect(toNumber(null, 99)).toBe(99);
  });
});

describe('formatCurrency()', () => {
  it('formats USD', () => {
    expect(formatCurrency(1234.5)).toBe('$1,234.50');
  });
  it('returns empty string for null/undefined', () => {
    expect(formatCurrency(null)).toBe('');
    expect(formatCurrency(undefined)).toBe('');
  });
});

describe('formatPercent()', () => {
  it('formats to 1dp by default', () => {
    expect(formatPercent(32)).toBe('32.0%');
  });
  it('returns empty string for null', () => {
    expect(formatPercent(null)).toBe('');
  });
});

// ============================================================================
// LineItemService — mirrors _calculate_extended_price()
// ============================================================================

describe('LineItemService.calculateLine()', () => {
  const svc = new LineItemService({ transactionType: 'order' });

  it('computes extended = qty × unit − discount (price & cost)', () => {
    const line: Partial<TransactionLine> = {
      quantity: { staged: 10 },
      price: { unit: 100, discount_percent: 10, precision: 2 },
      cost: { unit: 60, precision: 2 },
    };
    const calc = svc.calculateLine(line as TransactionLine);

    // price: gross = 10 × 100 = 1000, discount = 1000 × 0.10 = 100, ext = 900
    expect(calc.gross).toBe(1000);
    expect(calc.discountAmount).toBe(100);
    expect(calc.extended).toBe(900);

    // cost: gross = 10 × 60 = 600, no discount, ext = 600
    expect(calc.grossCost).toBe(600);
    expect(calc.costExtended).toBe(600);

    // margin = 900 − 600 = 300, margin% = 300/900 × 100 = 33.33
    expect(calc.margin).toBe(300);
    expect(calc.marginPc).toBe(33.33);
  });

  it('prefers explicit discount_amount over percent (WC3 rule)', () => {
    const line: Partial<TransactionLine> = {
      quantity: { staged: 5 },
      price: { unit: 200, discount_percent: 10, discount_amount: 50, precision: 2 },
      cost: { unit: 80, precision: 2 },
    };
    const calc = svc.calculateLine(line as TransactionLine);

    // explicit amount 50, not gross × 10% = 100
    expect(calc.discountAmount).toBe(50);
    expect(calc.extended).toBe(950); // 1000 − 50
  });

  it('uses line precision from envelope', () => {
    const line: Partial<TransactionLine> = {
      quantity: { staged: 3 },
      price: { unit: 33.333, precision: 3 },
      cost: { unit: 10, precision: 0 },
    };
    const calc = svc.calculateLine(line as TransactionLine);

    // price: 3 × 33.333 = 99.999, rounded to 3dp = 99.999
    expect(calc.gross).toBe(99.999);
    // cost: 3 × 10 = 30, rounded to 0dp = 30
    expect(calc.grossCost).toBe(30);
  });

  it('handles zero quantity', () => {
    const line: Partial<TransactionLine> = {
      quantity: { staged: 0 },
      price: { unit: 100, precision: 2 },
      cost: { unit: 50, precision: 2 },
    };
    const calc = svc.calculateLine(line as TransactionLine);
    expect(calc.extended).toBe(0);
    expect(calc.costExtended).toBe(0);
    expect(calc.marginPc).toBe(0);
  });
});



// ============================================================================
// Transaction type helpers
// ============================================================================

describe('isSalesTransaction / isExecTransaction', () => {
  it.each(['order', 'quote', 'invoice'])('%s is sales', (type) => {
    expect(isSalesTransaction(type)).toBe(true);
    expect(isExecTransaction(type)).toBe(false);
  });
  it.each(['purchase', 'workorder'])('%s is exec', (type) => {
    expect(isSalesTransaction(type)).toBe(false);
    expect(isExecTransaction(type)).toBe(true);
  });
});
